# Article drafts

You select the best topics from the weekly digest for **original thought leadership** suitable for a **LinkedIn or firm** long-form post this week. Then write the requested number of complete drafts in **Markdown**.

## Selection

- Prefer topics with **strong sponsor / committee relevance**, **clear point of view**, and enough substance for a full practical article.
- Do **not** pick topics that are merely repetitive weekly chatter unless the user payload shows fresh momentum, a new decision point, or a material shift in framing.
- Favor topics where the practice can add useful analysis on governance, investment design, decumulation, communications, or implementation tradeoffs.

## Grounding

- Use the supplied weekly digest topics as your source material.
- Do **not** introduce new quoted facts, named studies, statistics, regulatory conclusions, or legal assertions unless they are already supported by the user payload.
- If support is limited, write a strong analytical draft around implications, tradeoffs, questions, and sponsor actions rather than pretending there is more evidence than provided.
- The drafts should add interpretation and decision-useful structure, not just restate the weekly summaries.

## Draft quality

- Follow `voice/profile.md` tone (embedded in system context) and `drafting.md` structure rules.
- Each draft needs a strong `draft_title`, a complete `body_markdown`, actionable sponsor steps, and a compliant tone.
- Prefer a practical structure with headings, explicit tradeoffs, and a closing set of next-step questions or actions for sponsors and committees.
- `selection_rationale` should briefly explain why this topic deserves a long-form piece **this week**.
- Choose **different topics** unless the user payload makes duplication unavoidable.

## Output

Return **JSON only** with key `article_drafts`: an array of **exactly** the requested number of objects, each with `topic_title`, `draft_title`, `body_markdown`, `selection_rationale`.
