"""Request-scoped ownership checks for the research and wizard API routers."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from organization_workspace.models import OrganizationMember
from rbac.beta_adapter import RbacBetaRoles
from research.models import Research, ResearchJob, ResearchTask, Response
from workspace.models import Project, UserWorkspace


def research_scope(db: Session, user_id: int):
    projects = select(Project.id).join(UserWorkspace).where(UserWorkspace.user_id == user_id)
    organizations = select(OrganizationMember.organization_id).where(
        OrganizationMember.user_id == user_id
    )
    return or_(
        Research.project_id.in_(projects),
        Research.metadata_payload["organization_id"].as_integer().in_(organizations),
        Research.metadata_payload["created_by_user_id"].as_integer() == user_id,
    )


def require_research_access(request: Request, db: Annotated[Session, Depends(get_db)]) -> None:
    if not get_settings().security_enforce_auth:
        return
    principal = getattr(request.state, "principal", None)
    user_id = getattr(principal, "user_id", getattr(principal, "id", None))
    if user_id is None:
        raise HTTPException(401, "Authentication required")
    if RbacBetaRoles(db).is_admin(int(user_id)):
        return
    db.info["research_user_id"] = int(user_id)
    params = request.path_params
    research_id = params.get("research_id")
    # IDs in nested endpoints must not bypass ownership of the parent research.
    for key, model in (
        ("task_id", ResearchTask),
        ("response_id", Response),
        ("job_id", ResearchJob),
    ):
        if params.get(key) is not None:
            item = db.get(model, int(params[key]))
            if item is None:
                raise HTTPException(404, "Research not found")
            if model is Response:
                item = db.get(ResearchTask, item.research_task_id)
            research_id = item.research_id if item is not None else None
            if research_id is None:
                raise HTTPException(404, "Research not found")
    if research_id is not None:
        found = db.scalar(
            select(Research.id).where(
                Research.id == int(research_id), research_scope(db, int(user_id))
            )
        )
        if found is None:
            raise HTTPException(404, "Research not found")
    elif (
        request.method == "GET"
        and request.url.path
        not in {
            "/research",
            "/researches",
            "/research-tasks",
            "/responses",
            "/prompts",
            "/research/templates",
            "/reports",
        }
        and not ("code" in params or "prompt_id" in params)
    ):
        raise HTTPException(403, "Cross-research views require platform administrator")
    # Low-level writes alter shared datasets and bypass the wizard's contracts.
    # First-client flow uses the wizard; raw management remains platform-admin-only.
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not request.url.path.startswith(
        "/research/wizard/"
    ):
        raise HTTPException(403, "Use the research wizard; raw management requires platform admin")
