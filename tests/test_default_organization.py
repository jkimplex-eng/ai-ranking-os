import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from authentication.models import AuthUser
from backend.app.database import Base
from organization_workspace.models import Organization, OrganizationMember
from provider_connections.dependencies import default_organization


def test_first_use_creates_private_workspace_and_preserves_existing_memberships():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                AuthUser(
                    id=i,
                    email=f"user{i}@example.org",
                    display_name=f"User {i}",
                    password_hash="unused",
                )
                for i in (1, 2)
            ]
        )
        other = Organization(name="Existing", slug="existing")
        db.add(other)
        db.flush()
        db.add(
            OrganizationMember(organization_id=other.id, user_id=2, role="VIEWER", is_default=True)
        )
        db.commit()
        personal_id = default_organization(db, 1)
        assert personal_id != other.id
        assert default_organization(db, 1) == personal_id
        assert default_organization(db, 2) == other.id
        members = list(db.scalars(select(OrganizationMember)))
        assert len(members) == 2
        assert next(m for m in members if m.user_id == 1).role == "OWNER"
        assert next(m for m in members if m.user_id == 2).role == "VIEWER"


def test_unknown_account_cannot_provision_workspace():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(HTTPException) as error:
            default_organization(db, 999)
        assert error.value.status_code == 401
        assert list(db.scalars(select(Organization))) == []
