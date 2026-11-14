# vocab

A local-first English vocabulary learning tool for Turkish speakers.

It imports text (YouTube subtitles, plain text files), extracts words and
multi-word expressions such as phrasal verbs, estimates their difficulty,
filters out what you already know, and schedules reviews with spaced
repetition. All data stays on your machine.

**Status:** early development. Importing text files, difficulty filtering and
listing candidates work. Learning, review and YouTube import do not exist yet.

## Usage

```sh
uv run vocab add story.txt      # import a text file
uv run vocab list               # candidates: rare words first, then phrases
uv run vocab list --limit 50    # show more rows per section
uv run vocab known reluctant "give up"    # mark items as known (base form)
uv run vocab known --undo reluctant
uv run vocab config             # show settings and file locations
uv run vocab config known-zipf 3.8        # change the difficulty threshold
```

### Difficulty threshold

Words are scored by how common they are (Zipf scale: higher = more common).
Words at or above `known_zipf` count as known and are not offered. The default
is 4.0, a rough fit for B2; try 4.5 for B1 or 3.5 for C1. Phrasal verbs and
idioms are never filtered by this setting. Changing the value takes effect
immediately, without importing again.

### Where your data lives

| What | Location |
|---|---|
| Settings | `~/.config/vocab/config.toml` |
| Database | `~/.local/share/vocab/vocab.db` |

Both are created on the first run. Nothing is stored in this repository.
Set `VOCAB_CONFIG_DIR` / `VOCAB_DATA_DIR` to use other folders.

See [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for what the tool gets wrong.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone <repo-url> vocab
cd vocab
uv sync         # creates .venv and installs everything, including the spaCy model
uv run pytest   # checks that the setup works
```

### The spaCy language model

Tokenization, lemmatization and parsing use spaCy's small English model,
`en_core_web_sm` (about 13 MB). The model is not stored in this repository.

spaCy models are ordinary Python packages, but they are published on GitHub
instead of PyPI. `pyproject.toml` therefore lists `en-core-web-sm` as a
dependency and tells uv where to download it (`[tool.uv.sources]`), and
`uv.lock` pins the exact file. That is why `uv sync` is the only command
needed: it downloads the model into `.venv` together with the other packages.

The model version must match the spaCy version (model 3.8.x for spaCy 3.8.x).
To upgrade later, change the URL in `pyproject.toml` to the matching release
from <https://github.com/explosion/spacy-models/releases> and run `uv sync`.

## Development

```sh
uv run vocab --help  # run the CLI
uv run pytest        # run tests
uv run ruff check .  # lint
uv run ruff format . # format
```
