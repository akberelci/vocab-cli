# vocab

A local-first English vocabulary learning tool for Turkish speakers.

It imports text (YouTube subtitles, plain text files), extracts words and
multi-word expressions such as phrasal verbs, estimates their difficulty,
filters out what you already know, and schedules reviews with spaced
repetition. All data stays on your machine.

**Status:** early development. Only the project skeleton exists so far.

## Development

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync              # create .venv and install dependencies
uv run vocab --help  # run the CLI
uv run pytest        # run tests
uv run ruff check .  # lint
uv run ruff format . # format
```
