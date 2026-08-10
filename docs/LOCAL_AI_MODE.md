# Local AI Mode

Set `AI_ROUTING_MODE=LOCAL` and `OLLAMA_BASE_URL` to the internal Ollama endpoint. The router
then emits execution plans containing only LOCAL-tier models. Provider access remains behind the
public Provider interface, so Research and other domains never import Ollama or cloud SDKs.
