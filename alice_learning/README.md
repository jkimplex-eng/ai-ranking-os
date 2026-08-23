# Alice Learning Engine

`alice_learning` builds an explainable local surrogate of observed Alice/YandexGPT recommendation
behaviour. It does **not** claim access to Yandex's private ranking or recommendation algorithm.

## Learning loop

1. `POST /alice-learning/observations/{research_id}` converts processed Yandex research responses
   into immutable evidence rows.
2. `POST /alice-learning/train` trains a deterministic regularized logistic model for the selected
   category, language and region.
3. `POST /alice-learning/predict` stores a probability, formula inputs and single-feature
   counterfactuals.
4. `GET /alice-learning/dashboard` separates model associations from effects confirmed by the
   existing Publication Learning experiment engine.
5. `POST /alice-learning/rebuild` safely imports all historical Yandex researches visible to the
   active organization and retrains the model.

The model requires at least 12 observations, including at least three recommendations and three
non-recommendations. Below that threshold it is stored as `INSUFFICIENT_SAMPLE`; no improvement
counterfactuals are produced.

All feature values are normalized to `0..1`. Missing evidence is explicitly recorded as
`NOT_MEASURED` and neutrally imputed to `0.5`; it is never represented as an observed zero.

## Limitations

- Alice answers are non-deterministic and can change with search results and personalization.
- Learned coefficients are associations, not causal effects.
- Only controlled publication experiments may be presented as experiment-supported evidence.
- Predictions apply only to the declared sample, category, language, region and model version.
