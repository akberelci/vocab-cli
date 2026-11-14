"""User settings and the places where vocab keeps its files.

    settings:  ~/.config/vocab/config.toml
    database:  ~/.local/share/vocab/vocab.db

These follow the XDG convention used by many command-line tools. The folders
can be moved with the environment variables VOCAB_CONFIG_DIR and
VOCAB_DATA_DIR; the tests use this so they never touch your real files.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KNOWN_ZIPF = 4.0

# Zipf scores run from about 1 (very rare) to about 8 ("the").
_MIN_ZIPF, _MAX_ZIPF = 0.0, 8.0

_TEMPLATE = """\
# Settings for vocab.
#
# known_zipf: words with a frequency score at or above this value count as
# already known and are not offered for learning. The score is the Zipf scale:
# higher = more common = easier. Lower this value to see fewer, harder words.
#
# Rough guide (an estimate, not an official mapping):
#   B1  4.5
#   B2  4.0
#   C1  3.5
#
# Phrasal verbs and idioms are not affected by this setting.
known_zipf = {known_zipf}
"""


class ConfigError(Exception):
    """The settings file or a new value is not valid. The message is shown to the user."""


@dataclass(frozen=True)
class Config:
    known_zipf: float = DEFAULT_KNOWN_ZIPF


# --- locations ----------------------------------------------------------------


def config_dir() -> Path:
    return _directory("VOCAB_CONFIG_DIR", "XDG_CONFIG_HOME", Path.home() / ".config")


def data_dir() -> Path:
    return _directory("VOCAB_DATA_DIR", "XDG_DATA_HOME", Path.home() / ".local" / "share")


def _directory(own_variable: str, xdg_variable: str, default_base: Path) -> Path:
    """Our own variable names the folder itself; otherwise it is "<base>/vocab"."""
    if os.environ.get(own_variable):
        return Path(os.environ[own_variable]).expanduser()
    base = os.environ.get(xdg_variable)
    return (Path(base).expanduser() if base else default_base) / "vocab"


def config_path() -> Path:
    return config_dir() / "config.toml"


def database_path() -> Path:
    return data_dir() / "vocab.db"


# --- reading and writing --------------------------------------------------------


def load() -> tuple[Config, bool]:
    """Read the settings. On the first run, create the file with default values.

    Returns the settings and whether the file was just created.
    """
    path = config_path()
    if not path.exists():
        config = Config()
        save(config)
        return config, True

    try:
        values = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Cannot read {path}: {error}") from None

    known_zipf = validate_known_zipf(values.get("known_zipf", DEFAULT_KNOWN_ZIPF))
    return Config(known_zipf=known_zipf), False


def save(config: Config) -> None:
    """Write the settings file, including its explanatory comments."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TEMPLATE.format(known_zipf=config.known_zipf), encoding="utf-8")


def validate_known_zipf(value: object) -> float:
    # bool is a kind of int in Python, so "known_zipf = true" must be refused explicitly.
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigError(f"known_zipf must be a number, not {value!r}.")
    if not _MIN_ZIPF <= value <= _MAX_ZIPF:
        raise ConfigError(
            f"known_zipf must be between {_MIN_ZIPF:g} and {_MAX_ZIPF:g}, not {value:g}."
        )
    return float(value)
