# Entity Linking

Entity Linking v1 maps graph nodes to shared canonical entities through the public
`GraphProvider` and `EntityResolver` interfaces. The module has no dependency on
Research and consumes Graph Engine through its public snapshot response.

Names are normalized with Unicode NFKC, case folding, punctuation removal, and
whitespace collapsing. Exact canonical matches score `1.0`, exact aliases score
`0.97`, and fuzzy matches above `0.80` become pending candidates. Unmatched nodes
create a new canonical entity automatically.

Every automatic or manual resolution creates an immutable `LinkDecision`. Manual
approval can select another canonical entity; rejection preserves the proposed link
and its confidence for audit.

- `POST /entity-linking/run`
- `GET /entity-linking/candidates`
- `POST /entity-linking/{candidate_id}/approve`
- `POST /entity-linking/{candidate_id}/reject`

