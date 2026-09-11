# AI Provider & Media Influence Research Base

Version 1.0 · checked 2026-08-11. This is a capability register, not a claim about proprietary training corpora or ranking influence.

## Provider research matrix

| Provider | Web search | Returned citations | Proprietary index / update cadence / use of Reddit, YouTube, GitHub, Habr, VC, media, papers |
|---|---|---|---|
| OpenAI | Supported by the Web Search tool | Supported in web-search responses | `unknown` unless demonstrated in a recorded experiment |
| Anthropic | Supported by the web search tool | Supported | `unknown` |
| Gemini | Supported through Grounding with Google Search | Grounding metadata and sources supported | `unknown` |
| Perplexity | Search API is search-grounded | Citations supported | `unknown` |
| Grok | `unknown` in this register | `unknown` | `unknown` |
| DeepSeek | `unknown` | `unknown` | `unknown` |
| Qwen/Ollama | No platform web search is assumed; depends on configured tools/RAG | `unknown` | Local model knowledge and attached retrieval only |
| Mistral | `unknown` | `unknown` | `unknown` |
| Copilot | `unknown` | `unknown` | `unknown` |
| YandexGPT | `unknown` | `unknown` | `unknown` |
| GigaChat | `unknown` | `unknown` | `unknown` |

Official references:

- [OpenAI Web Search tool](https://platform.openai.com/docs/guides/tools-web-search)
- [Anthropic Web Search tool](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool)
- [Gemini Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search)
- [Perplexity Search guide](https://docs.perplexity.ai/guides/search-guide)

## Media influence matrix

No universal `High/Medium/Low` values are asserted in version 1.0. Provider documentation about search capability does not prove that publishing on a domain causes a score increase.

| Source type | OpenAI | Claude | Gemini | Perplexity | Grok | Evidence status |
|---|---|---|---|---|---|---|
| Wikipedia | unknown | unknown | unknown | unknown | unknown | experiment required |
| PubMed / scientific paper | unknown | unknown | unknown | unknown | unknown | experiment required |
| VC / Habr / industry media | unknown | unknown | unknown | unknown | unknown | experiment required |
| Reddit | unknown | unknown | unknown | unknown | unknown | experiment required |
| GitHub | unknown | unknown | unknown | unknown | unknown | experiment required |
| YouTube | unknown | unknown | unknown | unknown | unknown | experiment required |

## Reproducible experiment protocol

1. Record publication URL, content hash and publication timestamp.
2. Freeze a prompt set, provider/model versions, language and region.
3. Run a pre-publication baseline at least three times.
4. Run scheduled observations without changing prompts.
5. Record the first response that contains the publication URL/content and its provider timestamp.
6. Report observed deltas with sample size and confidence; label them correlation unless a controlled design supports attribution.

## Crawl timeline

`published_at` and `first_observed_at_by_provider` are distinct. A research timestamp is not a crawl timestamp. Until an exact URL/content is observed in a provider response, the timeline value remains `NOT_OBSERVED`; it is never backfilled from publication or research dates.
