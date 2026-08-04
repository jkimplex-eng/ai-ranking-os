# Regional Providers

Provider and model metadata uses `GLOBAL` or `RUSSIA`. The production Router
accepts `region` in `/router/route`, filters candidates by that attribute and
scores regional fit and success probability as ordinary model factors.

Current GLOBAL providers are OpenAI, Anthropic, Gemini, DeepSeek, Perplexity,
Mistral, Grok and Local. RUSSIA providers are YandexGPT and GigaChat.
`config/regions.yaml` owns these groupings and default policies.

YandexGPT uses the Yandex Foundation Models completion API with `YANDEX_API_KEY`
and `YANDEX_FOLDER_ID`. GigaChat uses its OpenAI-compatible chat API with a
hot-readable `GIGACHAT_ACCESS_TOKEN`. Production deployments may supply a token
rotation process through the Credential Manager override/Vault adapter.

Example regional route:

```json
{
  "query": "Сравни предложения с источниками",
  "region": "RUSSIA",
  "language": "ru",
  "policy_id": "multilingual"
}
```

The resulting execution plan can use SINGLE, PARALLEL, ENSEMBLE, CONSENSUS or
FALLBACK without regional branching in Query Executor.
