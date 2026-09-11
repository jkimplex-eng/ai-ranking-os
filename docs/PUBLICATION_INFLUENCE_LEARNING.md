# Publication Influence Learning v1.2

The engine estimates which publications are associated with changes in brand recommendations for
each AI provider. It does not claim access to a provider's private ranking algorithm.

## Measurement protocol

1. Complete a baseline research using a frozen prompt set and fixed provider/model matrix.
2. Publish one registered material and store its canonical URL, publication date and target queries.
3. Keep at least one unchanged query as a control.
4. Repeat the same prompt, provider, model, language and region matrix after publication.
5. The engine verifies that the publication URL appears in an eligible normalized AI response.
6. It pairs responses by normalized query, provider and model.
7. For mention, recommendation and citation it calculates:

   `effect = target-query change - control-query change`

8. Results are accumulated separately by resource domain, content type, category, language, region,
   provider and model.

## Evidence levels

- `HYPOTHESIS`: the publication URL was not observed in an AI response.
- `OBSERVATION`: URL observed and a matched before/after comparison exists.
- `CONTROLLED`: target and control query pairs exist in the same matched research matrix.
- `CORRELATION`: at least three repeated observations exist for an aggregate dimension.

`CONTROLLED_ASSOCIATION` is not proof of causality. Search indexes, model versions, sampling and
unobserved external changes can still affect the result.

## Stored evidence

Every experiment stores baseline/follow-up research IDs, matrix fingerprint, response IDs,
exclusions, treatment/control pair counts, raw and adjusted deltas, provider/model deltas,
confidence method, limitations and algorithm version. Historical v1.1 results are not overwritten.

## Product workflow

In a completed report open **Обучение на публикациях**, enter the material title and canonical URL,
then select only the queries the material was intended to influence. Leave other relevant prompts
unchecked as controls. After the content has been indexed, repeat the research with the same frozen
query set and the same models. The report and GEO dashboard will show whether the estimate was
control-adjusted and how many controlled experiments support it.
