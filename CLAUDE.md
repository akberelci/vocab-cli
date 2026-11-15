# Instructions for Claude Code in this repository

## Commit messages

- Do not add `Co-Authored-By:` trailers to commit messages.
- Do not add `Claude-Session:` trailers or any other AI attribution line
  ("Generated with ...") to commit messages or pull request descriptions.
- Commits use the repository's local git identity only. Do not change it.

## Working rules

- Small, separate commits; run `uv run pytest` and `uv run ruff check .`
  before each one.
- No secrets, personal data or local paths in the repository.
- Do not push unless asked.
