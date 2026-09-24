from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from closed_beta.dependencies import require_beta_admin
from rbac.beta_adapter import RbacBetaRoles


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("organization_admin", False),
        ("ORGANIZATION_ADMIN", False),
        ("member", False),
        ("admin", True),
        ("superadmin", True),
    ],
)
def test_only_platform_roles_can_manage_all_customers(role, allowed):
    roles = RbacBetaRoles(SimpleNamespace(scalars=lambda query: [role]))
    assert roles.is_admin(2) is allowed


def test_missing_principal_never_falls_back_to_user_one(monkeypatch):
    monkeypatch.setattr(
        "closed_beta.dependencies.get_settings", lambda: SimpleNamespace(security_enforce_auth=True)
    )
    with pytest.raises(HTTPException) as error:
        require_beta_admin(SimpleNamespace(state=SimpleNamespace()), None)
    assert error.value.status_code == 401
