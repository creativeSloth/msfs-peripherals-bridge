"""Tests for the GUI translation layer."""

from __future__ import annotations

import pytest

from msfs_peripherals_bridge import i18n


@pytest.fixture(autouse=True)
def _reset_language():
    """Every test starts (and leaves) the module on the default language."""
    i18n.set_language(i18n.DEFAULT_LANG)
    yield
    i18n.set_language(i18n.DEFAULT_LANG)


def test_every_key_defines_the_non_default_languages():
    # German is optional per entry: a key may BE the German source string
    # (gettext-msgid style), in which case tr() falls back to it. But every
    # entry must translate the three non-default languages.
    assert set(i18n.LANGUAGES) == {"de", "en", "es", "fr"}
    required = {"en", "es", "fr"}
    missing = {
        key: required - set(entry)
        for key, entry in i18n._STRINGS.items()
        if required - set(entry)
    }
    assert not missing, f"keys missing translations: {missing}"


def test_no_blank_translations():
    blanks = [
        (key, lang)
        for key, entry in i18n._STRINGS.items()
        for lang, text in entry.items()
        if not text.strip()
    ]
    assert not blanks, f"blank translations: {blanks}"


def test_tr_returns_active_language():
    i18n.set_language("es")
    assert i18n.tr("conn.start") == "Iniciar"
    i18n.set_language("fr")
    assert i18n.tr("conn.start") == "Démarrer"


def test_tr_falls_back_to_german_then_key():
    # A key that exists but (hypothetically) lacks the active language falls back
    # to German; we simulate by pointing at a real German-only situation via a
    # temporary entry.
    i18n._STRINGS["__test.partial"] = {"de": "nur Deutsch"}
    try:
        i18n.set_language("fr")
        assert i18n.tr("__test.partial") == "nur Deutsch"
        assert i18n.tr("__test.does_not_exist") == "__test.does_not_exist"
    finally:
        del i18n._STRINGS["__test.partial"]


def test_tr_formats_kwargs():
    assert "3" in i18n.tr("conn.prereq_problems", n=3)


def test_tr_bad_format_does_not_raise():
    # Missing kwargs must not crash a widget label.
    assert i18n.tr("conn.prereq_problems") == i18n._STRINGS["conn.prereq_problems"]["de"]


def test_language_name_round_trip():
    for code in i18n.LANGUAGES:
        assert i18n.code_for_name(i18n.language_name(code)) == code


def test_set_language_rejects_unknown():
    i18n.set_language("xx")
    assert i18n.get_language() == i18n.DEFAULT_LANG
    i18n.set_language(None)
    assert i18n.get_language() == i18n.DEFAULT_LANG
