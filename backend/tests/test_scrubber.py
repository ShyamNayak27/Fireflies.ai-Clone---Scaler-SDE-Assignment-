"""Scrubbing must be airtight: no original name, email, phone, or URL survives
it. This is the test docs/ARCHITECTURE.md §5.4 flagged as missing — "no
automated test yet asserts 'no original name survives scrubbing'"."""
from __future__ import annotations

from app.ingest.scrub import Scrubber


def test_pseudonym_is_deterministic_within_a_scrubber() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    first = scrubber.pseudonymize_name("Alex Kim")
    second = scrubber.pseudonymize_name("Alex Kim")
    assert first == second
    assert first != "Alex Kim"


def test_pseudonym_is_deterministic_across_scrubbers_with_same_salt() -> None:
    a = Scrubber(salt="fixed-salt").pseudonymize_name("Priya Shah")
    b = Scrubber(salt="fixed-salt").pseudonymize_name("Priya Shah")
    assert a == b


def test_different_names_get_different_pseudonyms() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    assert scrubber.pseudonymize_name("Alex Kim") != scrubber.pseudonymize_name("Priya Shah")


def test_original_name_never_survives_in_prose() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    fake = scrubber.pseudonymize_name("Alex Kim")
    text = scrubber.scrub_text("Thanks, Alex Kim, that's a great point.")
    assert "Alex Kim" not in text
    assert fake in text


def test_email_is_scrubbed_and_stays_email_shaped() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    text = scrubber.scrub_text("Reach me at alex.kim@hypotenuse-analytics.com for details.")
    assert "alex.kim@hypotenuse-analytics.com" not in text
    assert "@" in text  # still looks like an email, not a [REDACTED] token
    assert "[REDACTED]" not in text


def test_trailing_sentence_punctuation_after_email_is_preserved() -> None:
    """Regression test for the live-caught bug (docs/ARCHITECTURE.md §5.4):
    the email regex once greedily swallowed a trailing sentence period."""
    scrubber = Scrubber(salt="fixed-salt")
    text = scrubber.scrub_text("Email me at alex@corp.com.")
    assert text.endswith(".")
    assert "corp.com." not in text  # the fake address didn't inherit the bug either


def test_phone_number_is_scrubbed() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    text = scrubber.scrub_text("Call me at 415-555-0182 tomorrow.")
    assert "415-555-0182" not in text


def test_url_is_scrubbed() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    text = scrubber.scrub_text("See https://internal.hypotenuse-analytics.com/dash for the numbers.")
    assert "internal.hypotenuse-analytics.com" not in text


def test_long_digit_run_is_scrubbed() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    text = scrubber.scrub_text("The account number is 4111222233334444, keep that private.")
    assert "4111222233334444" not in text


def test_ordinary_text_is_left_alone() -> None:
    scrubber = Scrubber(salt="fixed-salt")
    text = scrubber.scrub_text("The build is stable and we shipped on time.")
    assert text == "The build is stable and we shipped on time."
