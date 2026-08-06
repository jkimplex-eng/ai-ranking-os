"""Run the reproducible Skinjestique research and write its final report."""

# ruff: noqa: E402 -- direct script execution adds the repository root before app imports.

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from backend.app import main as application  # noqa: F401
from backend.app.database import Base, SessionLocal, engine
from product.models import PromptDefinition, ResearchTemplateDefinition
from product.schemas import WizardRequest
from product.service import FinalReportService, ProductPipeline
from recommendation.simulation import models as recommendation_simulation_models  # noqa: F401
from research.schemas import ResearchModelSelection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="skinjestique-report.json")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
    else:
        alembic = Config(str(PROJECT_ROOT / "backend" / "alembic.ini"))
        command.upgrade(alembic, "head")

    with SessionLocal() as db:
        if db.scalar(select(PromptDefinition.id).limit(1)) is None:
            db.add(
                PromptDefinition(
                    code="ai-visibility",
                    version=1,
                    title="AI Visibility",
                    description="Demo prompt",
                    category="Visibility",
                    language="en",
                    variables=["brand", "language", "region"],
                    template=(
                        "Analyze the AI visibility of {brand} in {language} for {region}. "
                        "Cite sources and provide ranked recommendations."
                    ),
                    expected_output={"content": "string", "citations": "array"},
                    tags=["demo"],
                    status="ACTIVE",
                    active=True,
                )
            )
            db.add(
                ResearchTemplateDefinition(
                    code="ai-visibility",
                    version=1,
                    title="AI Visibility",
                    description="Complete demo pipeline",
                    prompt_code="ai-visibility",
                    pipeline=[
                        "provider",
                        "normalization",
                        "extraction",
                        "knowledge_graph",
                        "scoring",
                        "recommendations",
                        "analytics",
                        "insights",
                        "report",
                    ],
                    default_languages=["en"],
                    default_regions=["GLOBAL"],
                    active=True,
                )
            )
            db.commit()
        research = ProductPipeline(db).run(
            WizardRequest(
                brand="Skinjestique",
                models=[
                    ResearchModelSelection(provider="openai", model="gpt-4o-mini"),
                    ResearchModelSelection(provider="gemini", model="gemini-2-flash"),
                    ResearchModelSelection(provider="perplexity", model="sonar-pro"),
                ],
                languages=["en"],
                regions=["GLOBAL"],
            )
        )
        report = FinalReportService(db).get(research.id)
    destination = Path(args.output).resolve()
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Research {research.id} completed. Report: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
