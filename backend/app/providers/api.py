from fastapi import APIRouter

from backend.app.providers.ollama import OllamaModelInfo, ollama_provider

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/ollama/models", response_model=list[OllamaModelInfo])
def ollama_models(refresh: bool = False) -> list[OllamaModelInfo]:
    return ollama_provider.discover_models(refresh=refresh)


@router.get("/ollama/health")
def ollama_health() -> dict[str, object]:
    return ollama_provider.health()
