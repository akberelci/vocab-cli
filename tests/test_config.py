from pathlib import Path

import pytest

from vocab import config

# The autouse fixture in conftest.py points both folders at tmp_path.


def test_first_load_creates_the_file_with_the_b2_default():
    assert not config.config_path().exists()

    settings, created = config.load()

    assert created
    assert settings.known_zipf == 4.0
    assert config.config_path().exists()


def test_second_load_reads_the_existing_file():
    config.load()

    settings, created = config.load()

    assert not created
    assert settings.known_zipf == 4.0


def test_created_file_explains_the_setting():
    config.load()

    text = config.config_path().read_text(encoding="utf-8")

    assert "known_zipf = 4.0" in text
    assert text.startswith("#")
    assert "Zipf" in text


def test_saved_value_is_read_back():
    config.save(config.Config(known_zipf=3.5))

    settings, _ = config.load()

    assert settings.known_zipf == 3.5


def test_value_edited_by_hand_is_read():
    config.config_path().parent.mkdir(parents=True)
    config.config_path().write_text("known_zipf = 4.5\n", encoding="utf-8")

    assert config.load()[0].known_zipf == 4.5


def test_whole_number_is_accepted():
    config.config_path().parent.mkdir(parents=True)
    config.config_path().write_text("known_zipf = 4\n", encoding="utf-8")

    assert config.load()[0].known_zipf == 4.0


def test_missing_setting_falls_back_to_the_default():
    config.config_path().parent.mkdir(parents=True)
    config.config_path().write_text("# nothing set\n", encoding="utf-8")

    assert config.load()[0].known_zipf == config.DEFAULT_KNOWN_ZIPF


@pytest.mark.parametrize("content", ['known_zipf = "four"', "known_zipf = true", "known_zipf = 12"])
def test_invalid_value_is_refused_with_a_readable_message(content):
    config.config_path().parent.mkdir(parents=True)
    config.config_path().write_text(content + "\n", encoding="utf-8")

    with pytest.raises(config.ConfigError, match="known_zipf"):
        config.load()


def test_broken_file_is_refused_with_a_readable_message():
    config.config_path().parent.mkdir(parents=True)
    config.config_path().write_text("known_zipf = = 4\n", encoding="utf-8")

    with pytest.raises(config.ConfigError, match="Cannot read"):
        config.load()


@pytest.mark.parametrize("value", [-0.1, 8.1])
def test_threshold_outside_the_scale_is_refused(value):
    with pytest.raises(config.ConfigError, match="between 0 and 8"):
        config.validate_known_zipf(value)


# --- locations ---------------------------------------------------------------------


def test_own_variables_name_the_folders_directly(tmp_path):
    assert config.config_path() == tmp_path / "config" / "config.toml"
    assert config.database_path() == tmp_path / "data" / "vocab.db"


def test_xdg_variables_are_used_with_a_vocab_subfolder(tmp_path, monkeypatch):
    monkeypatch.delenv("VOCAB_CONFIG_DIR")
    monkeypatch.delenv("VOCAB_DATA_DIR")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))

    assert config.config_path() == tmp_path / "xdg-config" / "vocab" / "config.toml"
    assert config.database_path() == tmp_path / "xdg-data" / "vocab" / "vocab.db"


def test_default_locations_are_in_the_home_folder(tmp_path, monkeypatch):
    for variable in ("VOCAB_CONFIG_DIR", "VOCAB_DATA_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

    assert config.config_path() == tmp_path / "home" / ".config" / "vocab" / "config.toml"
    assert config.database_path() == tmp_path / "home" / ".local" / "share" / "vocab" / "vocab.db"
