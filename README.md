# vocab

A local-first English vocabulary learning tool for Turkish speakers.

It imports text (YouTube subtitles, plain text files), extracts words and
multi-word expressions such as phrasal verbs, estimates their difficulty,
filters out what you already know, and schedules reviews with spaced
repetition. All data stays on your machine.

**Status:** early development. Storage, the text file source and word
extraction exist; the CLI commands do not yet.

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
