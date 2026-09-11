import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from authentication.dependencies import CurrentPrincipal
from backend.app.config import get_settings
from backend.app.database import get_db
from billing.models import TBankPayment
from closed_beta.models import BetaUserProfile, SubscriptionStatus
from closed_beta.schemas import TariffRead
from closed_beta.service import ClosedBetaService

router = APIRouter(tags=["billing"])
DbSession = Annotated[Session, Depends(get_db)]


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=40)


class CheckoutResponse(BaseModel):
    payment_id: str
    payment_url: str
    amount: int


class SubscriptionSummary(BaseModel):
    plan_code: str
    plan_name: str
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    payment_provider: str | None
    checkout_available: bool
    checkout_message: str


def _token(payload: dict[str, object], password: str) -> str:
    values = {
        key: value
        for key, value in payload.items()
        if key != "Token" and not isinstance(value, (dict, list))
    }
    values["Password"] = password
    raw = "".join(str(values[key]) for key in sorted(values))
    return hashlib.sha256(raw.encode()).hexdigest()


def _settings_or_error():
    settings = get_settings()
    if not settings.tbank_terminal_key or not settings.tbank_password:
        raise HTTPException(status_code=503, detail="Приём оплаты ещё не настроен")
    return settings


@router.get("/billing/tariffs", response_model=list[TariffRead])
def tariffs(principal: CurrentPrincipal) -> list[TariffRead]:
    del principal
    return ClosedBetaService.tariffs()


@router.get("/billing/subscription", response_model=SubscriptionSummary)
def subscription(principal: CurrentPrincipal, db: DbSession) -> SubscriptionSummary:
    profile = db.scalar(select(BetaUserProfile).where(BetaUserProfile.user_id == int(principal.user_id)))
    plan_code = profile.plan_code if profile else "trial"
    tariff = ClosedBetaService.TARIFFS.get(plan_code, ClosedBetaService.TARIFFS["trial"])
    settings = get_settings()
    configured = bool(settings.tbank_terminal_key and settings.tbank_password)
    return SubscriptionSummary(
        plan_code=plan_code, plan_name=tariff[0],
        status=profile.subscription_status if profile else SubscriptionStatus.NONE.value,
        starts_at=profile.subscription_started_at if profile else None,
        ends_at=profile.subscription_ends_at if profile else None,
        payment_provider=profile.payment_provider if profile else None,
        checkout_available=configured,
        checkout_message="Оплата откроется на защищённой странице Т‑Банка." if configured else "Приём оплаты ещё настраивается.",
    )


@router.post(
    "/billing/tbank/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED
)
def checkout(
    payload: CheckoutRequest, principal: CurrentPrincipal, db: DbSession
) -> CheckoutResponse:
    settings = _settings_or_error()
    tariff = ClosedBetaService.TARIFFS.get(payload.plan_code)
    if tariff is None or tariff[1] <= 0:
        raise HTTPException(status_code=422, detail="Выберите платный тариф")
    user_id = int(principal.user_id)
    order_id = f"sub-{user_id}-{secrets.token_hex(8)}"
    amount = tariff[1] * 100
    request_payload: dict[str, object] = {
        "TerminalKey": settings.tbank_terminal_key,
        "Amount": amount,
        "OrderId": order_id,
        "Description": f"AI Ranking OS — тариф {tariff[0]}",
        "PayType": "O",
        "CustomerKey": f"ai-ranking-{user_id}",
        "Recurrent": "Y",
        "NotificationURL": settings.tbank_notification_url,
        "SuccessURL": settings.tbank_success_url,
        "FailURL": settings.tbank_fail_url,
        "DATA": {"OperationInitiatorType": "1"},
    }
    request_payload["Token"] = _token(request_payload, settings.tbank_password)
    endpoint = (
        "https://rest-api-test.tinkoff.ru/v2/Init"
        if settings.tbank_mode == "test"
        else "https://securepay.tinkoff.ru/v2/Init"
    )
    try:
        request = UrlRequest(
            endpoint,
            data=json.dumps(request_payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        if settings.tbank_mode == "test" and error.code == 403:
            raise HTTPException(
                status_code=424,
                detail=(
                    "Тестовый API Т‑Банка пока не разрешил IP сервера. "
                    "Добавьте IP 72.56.33.7 в allowlist тестовой среды через acq_help@tbank.ru."
                ),
            ) from error
        raise HTTPException(status_code=502, detail="Т‑Банк отклонил создание платежа") from error
    except (URLError, TimeoutError) as error:
        raise HTTPException(status_code=502, detail="Т-Банк временно недоступен") from error
    if not result.get("Success") or not result.get("PaymentURL"):
        raise HTTPException(status_code=502, detail="Т-Банк не создал платёж")
    payment = TBankPayment(
        user_id=user_id,
        plan_code=payload.plan_code,
        order_id=order_id,
        amount=amount,
        status=str(result.get("Status", "NEW")),
        payment_id=str(result.get("PaymentId")),
        payment_url=str(result["PaymentURL"]),
    )
    db.add(payment)
    db.commit()
    return CheckoutResponse(
        payment_id=payment.payment_id or "", payment_url=payment.payment_url or "", amount=amount
    )


@router.post("/billing/tbank/notification")
async def notification(request: Request, db: DbSession) -> dict[str, bool]:
    settings = _settings_or_error()
    payload = await request.json()
    if not isinstance(payload, dict) or not secrets.compare_digest(
        str(payload.get("Token", "")), _token(payload, settings.tbank_password)
    ):
        raise HTTPException(status_code=401, detail="Invalid payment signature")
    payment = db.scalar(
        select(TBankPayment).where(TBankPayment.payment_id == str(payload.get("PaymentId", "")))
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment.status = str(payload.get("Status", "UNKNOWN"))
    payment.raw_notification = json.dumps(payload, ensure_ascii=False)
    if payment.status == "CONFIRMED" and payment.confirmed_at is None:
        profile = db.scalar(
            select(BetaUserProfile).where(BetaUserProfile.user_id == payment.user_id)
        )
        if profile is None:
            profile = BetaUserProfile(user_id=payment.user_id)
            db.add(profile)
        tariff = ClosedBetaService.TARIFFS[payment.plan_code]
        profile.plan_code = payment.plan_code
        profile.subscription_status = SubscriptionStatus.ACTIVE.value
        profile.subscription_started_at = datetime.now(UTC)
        profile.subscription_ends_at = datetime.now(UTC) + timedelta(days=30)
        profile.payment_provider = "TBANK"
        profile.external_customer_id = f"ai-ranking-{payment.user_id}"
        profile.external_subscription_id = payment.payment_id
        for field, value in tariff[3].model_dump().items():
            setattr(profile, field, value)
        payment.confirmed_at = datetime.now(UTC)
    db.commit()
    return {"ok": True}
