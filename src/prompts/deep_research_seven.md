# Deep research pass (seven ranked topics)

This pass runs **after** the corpus has been clustered and the **top seven** topics selected. Your job is to produce the weekly digest JSON using **only** the evidence in `clusters_for_digest` (RSS + optional web search hits already merged into those clusters).

## Depth

- **Synthesize** momentum, disagreement, and regulatory uncertainty where the articles support it.
- **Citations**: every `citations[].url` **must** appear as an article URL in the corresponding cluster’s `articles` list (or a clearly cited article in that cluster). Do **not** invent URLs, paywalled titles, or statistics.
- **Repost highlights**: `primary_article_url` **must** be one of the URLs listed under articles for the matching topic cluster (the pipeline will realign if needed—still, do not hallucinate links).
- If evidence is thin, set `low_confidence_note` and keep language cautious.

## Anti-patterns

- Do not claim LinkedIn or media coverage that is not reflected in the provided article URLs.
- Do not fabricate regulatory citations or firm names not grounded in the excerpts.
