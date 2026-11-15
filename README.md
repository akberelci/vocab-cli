# vocab

A local-first command-line tool for learning English vocabulary from texts you
actually read or watch, built for Turkish speakers.

You give it a text. It finds the words and multi-word expressions in it,
reduces them to their base form, estimates how hard each one is, hides what is
below your level or already known, and shows you what is left with the sentence
it came from.

> **Status: early development.** Importing, analysing and listing work.
> Learning with Turkish explanations and spaced-repetition review are **not
> built yet**. See [Current status](#current-status).

## Why it is different

- **Phrasal verbs and idioms, not just single words.** In "She gave up
  smoking" you are offered *give up*, not *give* and *up*. Separated forms are
  found too: "turned the light off" gives *turn off*. Three-part verbs (*put up
  with*, *look forward to*) and listed idioms (*call it a day*) are recognised.
- **Filtered to your level.** Every word gets a frequency score. Words common
  enough for your level are hidden, with one setting you can change at any
  time. Phrasal verbs and idioms are never hidden by this filter, because they
  are made of easy words and are still hard.
- **Made for Turkish speakers (planned).** Explanations will be in Turkish,
  with a place to note typical pitfalls such as false friends and
  prepositions. This part does not exist yet.
- **Local-first.** No account, no subscription, no server. Your vocabulary is
  one SQLite file on your own machine.
- **Works on spoken text.** Fillers (*uh*, *um*), caption markers and stumbled
  repetitions are removed before analysis, and endless caption "sentences" are
  cut to a readable excerpt.

## Install

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/akberelci/vocab-cli.git
cd vocab-cli
uv sync         # creates .venv and installs everything, including the language model
uv run pytest   # optional: check that the setup works
```

`uv sync` also downloads spaCy's small English model (`en_core_web_sm`, about
13 MB). spaCy models are published on GitHub rather than PyPI, so
`pyproject.toml` lists the model with its download URL and `uv.lock` pins the
exact file. Nothing else needs to be installed.

## Usage

```sh
uv run vocab add story.txt      # import a plain text file (UTF-8)
uv run vocab list               # candidates: rare words first, then phrases
uv run vocab list --limit 50    # more rows per section
uv run vocab known reluctant "give up"    # mark items as known (base form)
uv run vocab known --undo reluctant
uv run vocab config             # show settings and file locations
uv run vocab config known-zipf 3.8        # change the difficulty threshold
```

What an import looks like:

```
$ uv run vocab add story.txt
Imported "story": 146 different words and phrases

  New candidates                 23
    words                         4
    phrasal verbs                18
    idioms                        1
  Skipped
    too easy (Zipf >= 4)        123
    marked known or ignored       0
  Seen in earlier imports         0
```

And the list (long sentences shortened here with "…"):

```
$ uv run vocab list --limit 2
Words below Zipf 4, rarest first (showing 2 of 4)
  ZIPF  TYPE          ITEM / EXAMPLE
  3.21  word          kilometre
                        On the 14th of March, she finished a 10 kilometre race in under an hour.
  3.21  word          organiser
                        When the organisers called off the winter race because of the snow, …
  ... 2 more. Use --limit to see more.

Phrasal verbs and idioms (showing 2 of 19)
  ZIPF  TYPE          ITEM / EXAMPLE
     -  idiom         at first
                        At first, she couldn't keep up with the others, and she nearly gave up after the third week.
     -  phrasal verb  call off
                        When the organisers called off the winter race because of the snow, …
  ... 17 more. Use --limit to see more.
```

Both words in this sample are offered only because of their British spelling,
which is one of the known issues.

### Difficulty threshold

Words are scored by how common they are, on the Zipf scale: 7 is "the", 5 is
"decision", 4 is "athlete", 3 is one occurrence per million words. Words at or
above `known_zipf` count as known and are not offered. The default is 4.0, a
rough fit for B2; try 4.5 for B1 or 3.5 for C1. This mapping is an estimate,
not an official one. Changing the value takes effect immediately, without
importing again.

### Adding your own phrasal verbs and idioms

The lists are plain text files with one entry per line and a short explanation
at the top:

- `src/vocab/nlp/data/phrasal_verbs.txt`
- `src/vocab/nlp/data/idioms.txt`

### Where your data lives

| What | Location |
|---|---|
| Settings | `~/.config/vocab/config.toml` |
| Database | `~/.local/share/vocab/vocab.db` |

Both are created on the first run. Nothing personal is stored in this
repository. Set `VOCAB_CONFIG_DIR` / `VOCAB_DATA_DIR` to use other folders.

## Current status

| Part | State |
|---|---|
| Import plain text files | works |
| Lemmas; skipping names, numbers, punctuation | works |
| Phrasal verbs (joined, separated, three-part) | works, with known false positives |
| Idioms from a list | works for fixed wording only |
| Difficulty score and level filter | works |
| Cleaning of spoken text and long sentences | works |
| `vocab list`, `vocab known`, `vocab config` | works |
| `vocab learn` with Turkish meanings | not built |
| Turkish dictionary lookup | not built |
| Spaced-repetition review (SM-2) | not built; the database tables exist |
| `vocab stats` | not built |
| YouTube import | not built; paste a transcript into a text file for now |

Things it gets wrong today, in short: it recognises the form of a phrasal
verb, not its meaning ("looked up at the sky" is offered as *look up*);
British spellings look rarer than they are; the small language model makes
lemma mistakes; and auto-generated captions without punctuation give poor
sentence boundaries. The full list, with the tests that document each case, is
in [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

What comes next is in [ROADMAP.md](ROADMAP.md).

## How it works

```
text file -> cleaning -> spaCy (sentences, lemmas, parse) -> phrases + words
          -> difficulty score (wordfreq) -> SQLite -> vocab list
```

| Module | Job |
|---|---|
| `sources/` | turn an input into plain text |
| `nlp/cleaning.py` | remove fillers, repetitions and caption markers |
| `nlp/pipeline.py` | load spaCy once; fix sentence boundaries |
| `nlp/phrases.py` | phrasal verbs (parser particle + list) and idioms (list) |
| `nlp/words.py` | single words: lemma, and what is not vocabulary |
| `nlp/examples.py` | shorten long sentences; choose the best example |
| `difficulty.py` | Zipf score and the "too easy" check |
| `importer.py` | connect the steps above and save the result |
| `storage/` | the SQLite schema and all SQL queries |
| `config.py` | the settings file and file locations |
| `cli.py` | the commands; no logic of its own |

All code in this repository was written from scratch for this project. The
phrasal verb and idiom lists were written by hand, not copied from another
source.

## Development

```sh
uv run pytest         # tests (they never touch your real settings or data)
uv run ruff check .   # lint
uv run ruff format .  # format
```

Tests marked `xfail` are known limitations: they describe what the tool should
ideally do and currently does not.

## License

[MIT](LICENSE)
