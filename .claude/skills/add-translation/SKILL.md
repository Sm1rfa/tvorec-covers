---
name: add-translation
description: Use after adding, changing, or removing a self.tr(...) string anywhere in src/cover_generator/gui/, to regenerate and fill in the Bulgarian translation files so the app stays fully localized. Also use when asked to "add a translation", "update translations", or "sync the .ts files".
---

# Add / update a translation

Tvorec Cover's UI strings are translated via Qt Linguist (`.ts` source
files, compiled to `.qm`). English is the source language baked directly
into `self.tr("...")` calls — there is no `en.ts`. Bulgarian lives in
`src/cover_generator/i18n/cover_generator_bg.ts` / `.qm`.

## Steps

1. **Make sure every new/changed string is wrapped in `self.tr(...)`.**
   Strings not wrapped in `tr()` will never be extracted and will always
   show up in English regardless of the selected language.

2. **Re-extract strings** from all GUI source files into the Bulgarian `.ts`
   file:

   ```bash
   find src/cover_generator -name "*.py" > /tmp/pyfiles.txt
   uv run pyside6-lupdate $(cat /tmp/pyfiles.txt) \
     -ts src/cover_generator/i18n/cover_generator_bg.ts
   ```

   This is non-destructive: existing translations are preserved, only new
   or changed `<source>` strings get added (marked
   `type="unfinished"`), and removed strings are marked obsolete.

3. **Fill in new translations.** Open
   `src/cover_generator/i18n/cover_generator_bg.ts` and find `<message>`
   blocks where `<translation type="unfinished"></translation>` is empty.
   Add the Bulgarian text and drop the `type="unfinished"` attribute, e.g.:

   ```xml
   <message>
       <source>New Label:</source>
       <translation>Нов етикет:</translation>
   </message>
   ```

   Keep translations natural Bulgarian, not literal word-for-word — match
   the tone of existing entries in the file.

4. **Compile to `.qm`:**

   ```bash
   uv run pyside6-lrelease src/cover_generator/i18n/cover_generator_bg.ts \
     -qm src/cover_generator/i18n/cover_generator_bg.qm
   ```

   Confirm the output says `0 unfinished`. If it doesn't, go back to step 3.

5. **Verify at runtime:**

   ```bash
   QT_QPA_PLATFORM=offscreen uv run python -c "
   import sys
   from PySide6.QtWidgets import QApplication
   from cover_generator.app import load_translator
   from cover_generator.gui.main_window import MainWindow
   app = QApplication(sys.argv)
   load_translator(app, 'bg')
   w = MainWindow()
   print(w.windowTitle())
   "
   ```

   The printed text should be Bulgarian.

6. If the change is user-facing (not just an internal label), check whether
   `docs/en/usage-manual.md` and `docs/bg/usage-manual.md` need a matching
   update — see the `i18n-maintainer` agent for that responsibility.
