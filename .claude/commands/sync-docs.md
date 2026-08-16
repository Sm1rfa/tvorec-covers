---
description: Reconcile docs/en and docs/bg after a documentation change, keeping both language versions structurally in sync.
---

Reconcile the English and Bulgarian docs after a recent change: $ARGUMENTS

Tvorec Cover keeps three doc pairs in sync:

- `docs/en/index.md` <-> `docs/bg/index.md`
- `docs/en/installation.md` <-> `docs/bg/installation.md`
- `docs/en/usage-manual.md` <-> `docs/bg/usage-manual.md`

`docs/en/architecture.md` is intentionally EN-only (dev-facing) — do not
create a Bulgarian version of it. `README.md` is English-only with a short
Bulgarian summary near the top; it does not need full bilingual parity.

Steps:

1. Diff the recently-changed EN (or BG) doc against its counterpart to find
   what's missing or out of date — same sections, same steps, same
   information, not necessarily a literal word-for-word translation.
2. Update the other language file to match in content and structure.
3. Keep terminology consistent with the existing Bulgarian translations used
   in `src/cover_generator/i18n/cover_generator_bg.ts` (e.g. "Подрязване"
   for Bleed, "Формат" for Trim size) so the docs and the app UI use the
   same words for the same concepts.
4. If the change is about a GUI string (not just prose), check whether
   `.claude/skills/add-translation/SKILL.md` also needs to be run for the
   app itself — docs and app translations are separate but should agree.
5. If `docs/en/usage-manual.md` or `docs/bg/usage-manual.md` changed, copy the
   updated file(s) over their bundled counterparts read by the in-app "User
   manual" dialog:
   `src/cover_generator/resources/docs/en/usage-manual.md` and
   `src/cover_generator/resources/docs/bg/usage-manual.md` — these must be
   byte-identical to the `docs/` originals, since they're what
   `gui/main_window.py:_show_manual` actually displays.
