from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from audit.repository import AuditRepository
from audit.service import AuditService
from authentication.beta_adapter import AuthenticationBetaIdentity
from backend.app.config import get_settings
from backend.app.database import get_db
from closed_beta.repository import BetaRepository
from closed_beta.service import ClosedBetaService
from rbac.beta_adapter import RbacBetaRoles
from workspace.beta_adapter import WorkspaceBetaUsage


def beta_service(db: Annotated[Session, Depends(get_db)]) -> ClosedBetaService:
    return ClosedBetaService(
        BetaRepository(db),
        AuthenticationBetaIdentity(db),
        WorkspaceBetaUsage(db),
        RbacBetaRoles(db),
        AuditService(AuditRepository(db)),
    )


def require_beta_admin(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> int:
    principal = getattr(request.state, "principal", None)
    user_id = int(getattr(principal, "user_id", getattr(principal, "id", 1)))
    if get_settings().security_enforce_auth and not RbacBetaRoles(db).is_admin(user_id):
        raise HTTPException(status_code=403, detail="Closed Beta administrator required")
    return user_id


BetaServiceDependency = Annotated[ClosedBetaService, Depends(beta_service)]
BetaAdminId = Annotated[int, Depends(require_beta_admin)]
