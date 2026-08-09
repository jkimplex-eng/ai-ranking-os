from backend.app.llm_router.ports import ProviderState
from backend.app.providers.readiness import RuntimeProviderReadiness
from backend.app.providers.registry import registry
from provider_registry.schemas import ProviderAvailability, ProviderCreate


def seed_providers() -> list[ProviderCreate]:
    """Translate bootstrap YAML into the authoritative runtime DB registry."""

    readiness = RuntimeProviderReadiness()
    prices = registry.prices()
    items: list[ProviderCreate] = []
    for priority, definition in enumerate(registry.all(), start=1):
        models = definition.models(prices)
        capabilities = sorted(
            {feature.value for model in models for feature in model.capabilities.features}
        )
        state = readiness.state(definition.name)
        availability = {
            ProviderState.READY: ProviderAvailability.READY,
            ProviderState.NOT_CONFIGURED: ProviderAvailability.NOT_CONFIGURED,
            ProviderState.DISABLED: ProviderAvailability.DISABLED,
            ProviderState.UNAVAILABLE: ProviderAvailability.UNAVAILABLE,
        }[state]
        items.append(
            ProviderCreate(
                id=definition.name,
                display_name=definition.name.replace("_", " ").title(),
                capabilities=capabilities,
                pricing={"source": "config/pricing.yaml", "currency": "USD"},
                context_window=max(model.capabilities.context_window for model in models),
                vision="vision" in capabilities,
                embeddings="embeddings" in capabilities,
                reasoning="reasoning" in capabilities,
                tools="tool_use" in capabilities,
                json_mode="json_mode" in capabilities,
                streaming="streaming" in capabilities,
                availability=availability,
                free_tier=all(
                    model.price.input_per_million == 0
                    and model.price.output_per_million == 0
                    for model in models
                ),
                priority=priority * 10,
                metadata={
                    "protocol": definition.protocol,
                    "models": [model.id for model in models],
                    "credential": definition.credential,
                    "enabled": definition.enabled,
                },
            )
        )
    return items
