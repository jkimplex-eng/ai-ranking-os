"""Stage competitor alerts in the same transaction as newly discovered posts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from competitor_intelligence.models import CompetitorSocialSource
from notification_center.models import Notification, NotificationDelivery
from workspace.models import Project, ProjectCompetitor, UserWorkspace


def notify_new_posts(db: Session, source: CompetitorSocialSource, posts: list[dict]) -> None:
    owner = db.execute(
        select(UserWorkspace.user_id, ProjectCompetitor.name, Project.id)
        .join(Project, Project.workspace_id == UserWorkspace.id)
        .join(ProjectCompetitor, ProjectCompetitor.project_id == Project.id)
        .where(ProjectCompetitor.id == source.competitor_id)
    ).one_or_none()
    if owner is None:
        return
    notification = Notification(
        user_id=owner[0],
        event_type="SIGNIFICANT_CHANGE",
        category="RESEARCH",
        priority="NORMAL",
        title=f"Новые материалы: {owner[1]}"[:250],
        message=(
            f"Впервые обнаружено материалов: {len(posts)}. Источник: {source.platform}. "
            "Дата обнаружения не обязательно совпадает с датой публикации. "
            "Влияние на рекомендации ИИ пока не установлено.\n"
            + "\n".join(f"{post['title'] or 'Материал'} — {post['url']}" for post in posts[:20])
        ),
        resource_type="COMPETITOR",
        resource_id=str(source.competitor_id),
        metadata_payload={
            "project_id": owner[2],
            "source_id": source.id,
            "new_count": len(posts),
            "posts": posts[:20],
        },
    )
    db.add(notification)
    db.flush()
    db.add(NotificationDelivery(notification_id=notification.id, channel="UI", status="DELIVERED"))
