# Multi-Provider Layer

RC2.1 provides one production contract for OpenAI, Anthropic, Gemini, DeepSeek,
Perplexity, Mistral, Grok, Ollama/vLLM-compatible Local, YandexGPT, and GigaChat.
Every implementation exposes `generate`, `stream`, `embed`, `health`,
`estimate_cost`, `estimate_tokens`, `capabilities`, `models`, and capability
helpers. Router and Executor contain no provider-name conditions.

Provider HTTP behavior is selected by declarative protocol metadata. OpenAI,
DeepSeek, Perplexity, Mistral, Grok, GigaChat, Ollama and vLLM use the
OpenAI-compatible protocol; Anthropic, Gemini and Yandex use their native
contracts. New OpenAI-compatible providers require only YAML configuration.

Set `PROVIDER_MOCK_MODE=false` to enable live HTTP transport. With mock mode
enabled, the same contracts, token/cost calculation, cache, rate limiter,
streaming, usage persistence and metrics remain testable without external
traffic. Verify live readiness through `/system/providers`.

Each completed Query Executor provider step writes prompt, completion and total
tokens, estimated cost, currency, provider, model, execution ID and timestamp to
`provider_usage`.
