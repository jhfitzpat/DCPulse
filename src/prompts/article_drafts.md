# Article drafts (two long-form pieces)

You **select** the best **two** topics from the seven for **original thought leadership** suitable for a **LinkedIn or firm** long-form post this week. Then write **two complete drafts** in **Markdown**.

## Selection

- Prefer topics with **strong sponsor/committee relevance**, **clear point of view**, and enough substance for ~800–1200 words combined guidance (per draft target provided in the user message).
- Do **not** pick topics that are purely repetitive of last week’s generic chatter unless the user payload shows fresh momentum.

## Draft quality

- Follow `voice/profile.md` tone (embedded in system context) and `drafting.md` structure rules.
- Each draft: **title (`draft_title`)**, **body (`body_markdown`)** with headings as appropriate, **actionable** sponsor steps, compliant tone (no performance promises, no personalized advice).
- **`selection_rationale`**: one short paragraph per draft explaining why this topic merits a long-form piece **this** week.

## Output

Return **JSON only** with key `article_drafts`: an array of **exactly** the requested number of objects, each with `topic_title`, `draft_title`, `body_markdown`, `selection_rationale`.
