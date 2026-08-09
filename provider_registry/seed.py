from provider_registry.schemas import ProviderCreate


def seed_providers() -> list[ProviderCreate]:
    definitions = [
        ("ollama", "Ollama", True, True, True, True, True, True, 0, True),
        ("groq", "Groq", False, False, True, True, True, True, 10, True),
        ("google", "Google Gemini", True, True, True, True, True, True, 20, True),
        ("github", "GitHub Models", True, True, True, True, True, True, 30, True),
        ("cloudflare", "Cloudflare Workers AI", True, True, False, True, True, True, 40, True),
        ("huggingface", "HuggingFace", True, True, True, True, True, True, 50, True),
        ("nvidia", "NVIDIA NIM", True, True, True, True, True, True, 60, True),
        ("openrouter", "OpenRouter", True, True, True, True, True, True, 70, True),
        ("openai", "OpenAI", True, True, True, True, True, True, 100, False),
        ("anthropic", "Anthropic", True, False, True, True, True, True, 110, False),
        ("deepseek", "DeepSeek", False, False, True, True, True, True, 120, False),
        ("qwen", "Qwen", True, True, True, True, True, True, 130, True),
        ("mistral", "Mistral", True, True, True, True, True, True, 140, True),
        ("yandexgpt", "YandexGPT", True, True, True, True, True, True, 150, False),
        ("gigachat", "GigaChat", True, True, True, True, True, True, 160, False),
    ]
    return [
        ProviderCreate(
            id=provider_id,
            display_name=display_name,
            capabilities=[
                "chat",
                *( ["vision"] if vision else []),
                *( ["embeddings"] if embeddings else []),
                *( ["reasoning"] if reasoning else []),
                *( ["tools"] if tools else []),
                *( ["json_mode"] if json_mode else []),
                *( ["streaming"] if streaming else []),
            ],
            pricing={"source": "provider", "currency": "USD"},
            context_window=128_000,
            vision=vision,
            embeddings=embeddings,
            reasoning=reasoning,
            tools=tools,
            json_mode=json_mode,
            streaming=streaming,
            free_tier=free_tier,
            priority=priority,
        )
        for (
            provider_id,
            display_name,
            vision,
            embeddings,
            reasoning,
            tools,
            json_mode,
            streaming,
            priority,
            free_tier,
        ) in definitions
    ]
