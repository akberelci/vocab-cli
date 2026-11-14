# Roadmap

Concrete next tasks, grouped by type. Each one is meant to be small enough for
one focused piece of work, with tests. The order inside a group is a suggested
order, not a promise. Limitations referred to here are described in
[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## Features: finishing the first version

These complete the loop "import, choose, learn, review".

1. **`vocab learn`.** Go through the candidates one by one (rarest words
   first, then phrases), showing the best example sentence. Keys: learn, mark
   known, ignore, skip, quit. Learning an item asks for a Turkish meaning and
   creates a card. Needs repository functions for cards and review state.
2. **Dictionary provider interface and MyMemory provider.** A small interface
   (`lookup(text) -> suggestion or nothing`) and a first provider using the
   free MyMemory translation API. `vocab learn` shows the result as an editable
   suggestion. Network calls are mocked in tests; without internet, learning
   still works with manual input.
3. **Pitfall notes.** In `vocab learn`, an optional note per card for typical
   Turkish-speaker traps: false friends, wrong prepositions ("depend on", not
   "depend from"), countability. Shown during review after the answer.
4. **SM-2 scheduler behind an interface.** A pure function: current state +
   grade (again / hard / good / easy) -> next state and due date. No database
   access, so every rule of the algorithm can be tested directly. The interface
   must not expose SM-2 details, so FSRS can replace it.
5. **`vocab review`.** The daily session: show the English item and example,
   reveal the Turkish meaning and pitfall note, self-grade, save the new
   schedule and a row in the review log. Ends with a short summary.
6. **`vocab stats`.** Counts of items by status, cards due today and in the
   next seven days, reviews done per day, and the number of imported sources.
7. **YouTube source.** `vocab add <url>`: parse the video id from the usual URL
   shapes, fetch the transcript with `youtube-transcript-api`, prefer manual
   captions over auto-generated ones, and pass the text through the existing
   cleaning step. Network calls are mocked in tests.

## Features: after the first version

8. **`vocab add --replace <file>`.** Re-import a text whose extraction has
   improved: delete the old source and its example sentences, remove items left
   without any example that were never marked or learned, then import again.
9. **`vocab sources`.** List imported sources with date and item counts, and
   remove one by number.
10. **`vocab ignore`.** Mark items as ignored from the command line (names,
    typos, noise), with `--undo`, mirroring `vocab known`.
11. **Offline Turkish dictionary provider.** A second provider built from a
    freely licensed dictionary dump (for example Wiktionary data), so lookups
    work without internet and give real dictionary senses rather than machine
    translation. Includes a documented download step; the data is not committed.
12. **Turkish to English review direction.** Show the Turkish meaning and ask
    for the English item, scheduled separately from the other direction.
13. **FSRS scheduler.** A second scheduler behind the interface from task 4,
    initialised from the review log, selectable in the settings.
14. **Export.** `vocab export` to CSV, and to a tab-separated file that Anki
    can import (item, meaning, example, pitfall note).

## Bugs and quality (from KNOWN_ISSUES.md)

15. **British spellings score too low.** Add a small British-to-American
    spelling map (-our, -ise, -re, doubled l) and score both spellings, keeping
    the higher. Removes "neighbour", "organiser", "kilometre" from B2 lists.
16. **Particle-type and preposition-type list entries.** Extend the format of
    `phrasal_verbs.txt` so an entry can say whether it needs a true particle
    ("take on") or accepts a preposition ("count on"), and review every entry.
    Fixes "She was taken on a tour" (currently an xfail test).
17. **Accidental three-part matches.** "She put the tent up with her brother"
    is reported as "put up with". Use the parse to require that the last part
    belongs to the verb (currently an xfail test).
18. **Update the score when a more common form appears.** An item keeps the
    score from its first import; recompute it when a later import contains a
    more frequent written form.
19. **Flag probable typos.** Check candidates against a word list and show a
    marker in `vocab list` and `vocab learn`, without deleting anything.
20. **Idioms with a changing part.** Allow a placeholder in `idioms.txt`
    ("pull *'s leg") that matches one or two arbitrary words, and allow one
    inserted modifier ("makes perfect sense"). Two xfail tests cover this.
21. **`vocab known` with any word form.** Accept "gave up" or "children" by
    looking the text up among the stored written forms, and say which base form
    was marked.
22. **Evaluate a larger spaCy model.** Run `en_core_web_md` and
    `en_core_web_trf` on the same test sentences and compare lemmas, names and
    particle detection against `en_core_web_sm`. Write the result down; make the
    model name a setting if a larger one is clearly better.
23. **Punctuation for auto-generated captions.** Try a punctuation-restoration
    step before parsing, as an optional extra dependency. Measure whether
    sentence boundaries and phrasal verb detection improve on caption-style text.
24. **Word families.** Group related items ("geopolitics", "geopolitical") so a
    family is offered together and knowing one member can hide the others.

## Refactors

25. **Split `cli.py`.** One module per command group (`add`, `list`, `known`,
    `config`, later `learn` and `review`) before the interactive commands make
    it long. No behaviour change; the CLI tests must pass unchanged.
26. **One query for `vocab list`.** The list currently runs one query per item
    to fetch its example sentences. Fetch items and occurrences together, and
    consider capping the number of stored examples per item and source.

## Tests and tooling

27. **Continuous integration.** A GitHub Actions workflow that runs `uv sync`,
    `ruff check`, `ruff format --check` and `pytest` on every push and pull
    request, on Python 3.12 and 3.13, with the uv cache enabled.
28. **Package-content test.** Build the wheel in CI and check that the word
    lists and `schema.sql` are inside it. (The lists were once silently left
    out of the repository by an ignore rule; a test should catch that kind of
    mistake.)
29. **Type checking.** Add a type checker (mypy or pyright) to the development
    tools and to CI, and fix what it reports.
30. **Gold set for phrase detection.** A file of sentences labelled with the
    phrasal verbs and idioms they contain, and a script that reports precision
    and recall. Gives a number to compare before and after tasks 16, 17, 20, 22
    and 23.
