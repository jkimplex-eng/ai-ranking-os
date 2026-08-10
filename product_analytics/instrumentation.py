import hashlib

from product_analytics.models import EventCategory
from product_analytics.schemas import EventCreate

ROUTE_EVENTS = {
    ("POST", "/auth/login"): ("LOGIN", EventCategory.AUTHENTICATION),
    ("POST", "/auth/logout"): ("LOGOUT", EventCategory.AUTHENTICATION),
    ("POST", "/research"): ("CREATE_RESEARCH", EventCategory.RESEARCH),
    ("POST", "/research/{research_id}/run"): ("START_RESEARCH", EventCategory.RESEARCH),
    ("POST", "/research/wizard/run"): ("FINISH_RESEARCH", EventCategory.RESEARCH),
    ("GET", "/research/{research_id}/final-report"): ("OPEN_REPORT", EventCategory.REPORT),
    ("GET", "/reports/{research_id}/export"): ("EXPORT_REPORT", EventCategory.REPORT),
    ("POST", "/feedback"): ("SUBMIT_FEEDBACK", EventCategory.FEEDBACK),
    ("POST", "/admin/beta/invitations"): ("INVITE_USER", EventCategory.ADMINISTRATION),
    ("PATCH", "/workspace"): ("UPDATE_SETTINGS", EventCategory.SETTINGS),
}


def request_event(
    *,
    method: str,
    route: str,
    status: int,
    latency_ms: float,
    user_id: int | None,
    session_id: str | None,
    ip_address: str | None,
    ip_salt: str,
    user_agent: str | None,
) -> EventCreate:
    event_name, category = ROUTE_EVENTS.get(
        (method, route),
        ("ERROR", EventCategory.ERROR)
        if status >= 500
        else ("API_CALL", EventCategory.API),
    )
    metadata = {
        "method": method,
        "path": route,
        "status": status,
        "latency_ms": round(latency_ms, 2),
    }
    if event_name == "FINISH_RESEARCH":
        metadata.update({"duration_ms": round(latency_ms, 2), "success": status < 400})
    if event_name == "OPEN_REPORT":
        metadata["generation_ms"] = round(latency_ms, 2)
    return EventCreate(
        user_id=user_id,
        session_id=session_id,
        event_name=event_name,
        event_category=category,
        metadata=metadata,
        ip_hash=hashlib.sha256(f"{ip_salt}:{ip_address}".encode()).hexdigest()
        if ip_address
        else None,
        user_agent=user_agent,
    )
