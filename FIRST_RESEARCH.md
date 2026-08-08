# First Research

## One-command demo

Copy `.env.example` to `.env`, keep `PROVIDER_MOCK_MODE=true`, then run:

```bash
python scripts/run_skinjestique_demo.py --output skinjestique-report.json
```

The command upgrades the database, creates a Skinjestique AI Visibility research for OpenAI,
Gemini and Perplexity, executes every stage, and writes the final JSON report.

## API flow

1. Inspect `GET /prompts` and `GET /research/templates`.
2. Submit the selection to `POST /research/wizard/review`.
3. Submit the same payload to `POST /research/wizard/run`.
4. Read the persisted aggregate at the returned `report_url`.

Example payload:

```json
{
  "brand": "Skinjestique",
  "models": [
    {"provider": "openai", "model": "gpt-4o-mini"},
    {"provider": "gemini", "model": "gemini-2-flash"},
    {"provider": "perplexity", "model": "sonar-pro"}
  ],
  "languages": ["en"],
  "regions": ["GLOBAL"],
  "prompt_code": "ai-visibility",
  "research_template_code": "ai-visibility"
}
```

For real providers, set `PROVIDER_MOCK_MODE=false` and provide the corresponding credentials.
