"""add Russian AI visibility prompt

Revision ID: 0088
Revises: 0087
"""

import sqlalchemy as sa
from alembic import op

revision = "0088"
down_revision = "0087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    prompts = sa.table(
        "prompt_definitions",
        sa.column("code", sa.String),
        sa.column("version", sa.Integer),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("language", sa.String),
        sa.column("variables", sa.JSON),
        sa.column("template", sa.Text),
        sa.column("expected_output", sa.JSON),
        sa.column("tags", sa.JSON),
        sa.column("status", sa.String),
        sa.column("active", sa.Boolean),
    )
    op.bulk_insert(
        prompts,
        [
            {
                "code": "ai-visibility",
                "version": 2,
                "title": "GEO-видимость бренда",
                "description": "Проверка присутствия бренда по естественным вопросам покупателей.",
                "category": "AI Visibility",
                "language": "ru",
                "variables": ["brand", "language", "region"],
                "template": (
                    "Проверьте видимость бренда {brand} в ответах ИИ для языка {language} "
                    "и региона {region}. Отвечайте на каждый вопрос как независимый помощник: "
                    "не добавляйте бренд только потому, что он указан в этом техническом задании. "
                    "Называйте бренд, конкурентов и источники только когда они действительно "
                    "относятся к вопросу. Не придумывайте ссылки и отделяйте факты "
                    "от предположений."
                ),
                "expected_output": {
                    "content": "string",
                    "citations": "array",
                    "recommendations": "array",
                },
                "tags": ["ai visibility", "geo", "ru", "evidence"],
                "status": "ACTIVE",
                "active": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM prompt_definitions "
            "WHERE code = 'ai-visibility' AND version = 2 AND language = 'ru'"
        )
    )
