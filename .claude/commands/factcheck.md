**Arguments:** `$ARGUMENTS` is `<slug>` or `<slug> --verify`. The first word is `<slug>` (required) — the post directory name. If `--verify` appears after it, verification mode is on.

Fact-check `content/<slug>/index.md`. Follow these rules exactly:

- Do not edit the file.
- Do not comment on spelling, grammar, typos, wording, or style — that's handled by /spellcheck, not this command.
- Read through the post and identify factual claims that seem questionable: numbers, dates, technical claims, historical or scientific assertions, product specs, etc.
- **Without `--verify`:** judge claims against your existing knowledge only. Do not use WebSearch, WebFetch, or read any file other than the post itself.
- **With `--verify`:** for each questionable claim, actively verify it — use WebSearch/WebFetch and/or read any files or sources the post references — before deciding whether it's actually wrong.
- For each questionable claim, quote it, explain why it seems questionable, and state the correct fact if you can determine it.

Output one section:
1. **Questionable facts** — a bullet list of claims worth double-checking, each with a short explanation. Note whether each was checked via lookup (`--verify`) or from existing knowledge only. If nothing seems questionable, say so plainly instead of inventing something.
