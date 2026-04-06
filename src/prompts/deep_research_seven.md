# Deep research pass (seven ranked topics)

This pass runs **after** the corpus has been clustered and the **top seven** topics selected. Produce the weekly digest JSON using **only** the evidence in `clusters_for_digest` (RSS + optional web search hits already merged into those clusters).

## Evidence and source quality

- Work from the supplied cluster articles only. Treat search snippets and indexed LinkedIn results as **weak evidence** unless the linked article itself supports the point.
- Prefer and cite, when present in the clusters: regulators and public agencies, Canadian pension/benefits trade media, major consulting firms' public insights, asset-manager educational commentary relevant to DC design, and credible business media with plan-sponsor relevance.
- Do **not** invent URLs, article titles, quotes, statistics, firm positions, or regulatory citations.

## Topic construction

- For each topic, explain **why it is surfacing now**, not just what the theme is.
- Translate each topic into **Canadian sponsor / committee / consulting implications**: governance, default design, decumulation, member communication, fees, recordkeeping, implementation, or investment structure as relevant.
- When cluster evidence is **TELUS** pension or benefits consulting (including **non-DC** plan types such as DB or hybrid), still cover it substantively: use `why_matters_dc` for **plan-sponsor and consultant takeaways** in Canadian pension/benefits practice even if the headline theme is not strictly DC—the field name is fixed; readers interpret it as “why it matters this week” for your audience.
- Show **momentum, disagreement, or uncertainty** only when the article set supports it.
- If evidence is thin, say so directly and use `low_confidence_note`.

## Output guidance

- `why_matters_dc`: focus on what a sponsor, committee, or consultant may need to monitor, question, or decide next.
- `evidence_momentum`: point to repeated coverage, an authoritative source, or a forming consensus. If there is no real momentum, say that clearly.
- `suggested_repost_copy`: concise third-party commentary grounded in the cluster evidence; add value through a sponsor/committee lens without overstating the source.
- `suggested_original_angle`: propose a clear consulting point of view with room for original analysis, tradeoffs, and next-step guidance.
- `best_repost_this_week`: choose topics with the strongest **timely third-party article anchor** and the least need for extra unsupported context.
- `best_thought_leadership_month`: choose topics with the best room for a distinct consulting perspective, practical framework, and sponsor decision-making value.
- `topics_to_avoid`: identify overplayed, weakly evidenced, or low-transferability themes and briefly signal why they are poor editorial bets. **Do not** list “non-DC” as a reason to avoid when the cluster is anchored on **TELUS** primary sources and pension/benefits consulting relevance is clear.
- `citations[].url` must appear in the matching cluster's `articles` list.
- `repost_highlights.primary_article_url` must be one of the URLs listed under articles for the matching topic cluster.

## Anti-patterns

- Do not claim LinkedIn or broader media coverage that is not reflected in the provided article URLs.
- Do not drift into US-only or retail-investor framing unless the cluster evidence clearly ties it back to Canadian pension/benefits practice (including TELUS-sourced Canadian consulting angles when present).
