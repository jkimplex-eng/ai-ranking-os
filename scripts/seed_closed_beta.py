"""Idempotently prepare the closed-beta organization, users, projects and sample research."""

# ruff: noqa: E402 -- direct execution adds the repository root before app imports.

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from authentication.dependencies import get_authentication_service
from authentication.repository import SqlAlchemyAuthenticationRepository
from backend.app import main as application  # noqa: F401
from backend.app.database import Base, SessionLocal, engine
from organization_workspace.models import Organization
from organization_workspace.repository import OrganizationRepository
from organization_workspace.schemas import InvitationCreate, OrganizationCreate
from organization_workspace.service import OrganizationService
from product.schemas import WizardRequest
from product.service import ProductPipeline
from research.models import Research
from research.schemas import ResearchModelSelection
from workspace.schemas import ProjectCreate
from workspace.service import ProjectService


def ensure_user(db, email: str, password: str, display_name: str):
    repository = SqlAlchemyAuthenticationRepository(db)
    user = repository.get_user_by_email(email)
    return user or get_authentication_service(db).create_user(email, password, display_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-research", action="store_true")
    args = parser.parse_args()
    password = os.getenv("BETA_DEMO_PASSWORD")
    if not password or len(password) < 12:
        raise SystemExit("BETA_DEMO_PASSWORD must contain at least 12 characters")
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)

    with SessionLocal() as db:
        owner = ensure_user(db, "demo.owner@example.com", password, "Demo Owner")
        analyst = ensure_user(db, "demo.analyst@example.com", password, "Demo Analyst")
        viewer = ensure_user(db, "demo.viewer@example.com", password, "Demo Viewer")
        organization_service = OrganizationService(OrganizationRepository(db))
        organization = db.scalar(
            select(Organization).where(Organization.slug == "demo-organization")
        )
        if organization is None:
            organization_read = organization_service.create(
                owner.id,
                OrganizationCreate(
                    name="Demo Organization",
                    slug="demo-organization",
                    description="Closed Beta reproducible workspace",
                    industry="Technology",
                    country="RU",
                    timezone="Europe/Moscow",
                ),
            )
            organization = db.get(Organization, organization_read.id)
        for user, role in ((analyst, "ANALYST"), (viewer, "VIEWER")):
            if OrganizationRepository(db).member(organization.id, user.id) is None:
                invitation = organization_service.invite(
                    organization.id,
                    owner.id,
                    InvitationCreate(email=user.email, role="MEMBER"),
                )
                membership = organization_service.accept_invitation(user.id, invitation.token)
                member = OrganizationRepository(db).member(membership.id, user.id)
                if role == "VIEWER" and member is not None:
                    member.role = role
                    db.commit()

        project_service = ProjectService(db)
        existing = {item.name: item for item in project_service.list(owner.id)}
        linked_project_ids = set(OrganizationRepository(db).projects(organization.id))
        for name in ("AI Ranking OS", "РазумМаркета", "Skinjestique"):
            project = existing.get(name) or project_service.create(
                owner.id, ProjectCreate(name=name, favorite=True, tags=["demo", "closed-beta"])
            )
            if project.id not in linked_project_ids:
                organization_service.link_project(organization.id, owner.id, project.id)

        if not args.skip_research and db.scalar(
            select(Research.id).where(Research.title == "AI Visibility: Skinjestique").limit(1)
        ) is None:
            ProductPipeline(db).run(
                WizardRequest(
                    brand="Skinjestique",
                    models=[ResearchModelSelection(provider="openai", model="gpt-4o-mini")],
                    languages=["ru"],
                    regions=["GLOBAL"],
                )
            )
    print("Closed Beta demo data is ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
