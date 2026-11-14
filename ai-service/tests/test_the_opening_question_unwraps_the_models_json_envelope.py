"""The opening question reaches the reader as words, not as the model's JSON envelope.

The live relay (gpt-6-sol via wkapi.pro) answered the opening prompt with
`{"message": "..."}` in production verification (2026-11-15): the turn stored the whole
envelope as the question text and the runner rendered raw JSON to the candidate.
`unwrap_text_envelope` is the pure seam that fixes it — these cases bound it.
"""

from app.features.interview import unwrap_text_envelope


def test_the_single_message_envelope_unwraps_to_its_words():
    out = unwrap_text_envelope('{"message":"Hi, thanks for joining today. Could you walk me through your background?"}')
    assert out == "Hi, thanks for joining today. Could you walk me through your background?"


def test_the_envelope_preferred_keys_arrive_in_order():
    assert unwrap_text_envelope('{"question":"Why this role?"}') == "Why this role?"
    assert unwrap_text_envelope('{"text":"Tell me about the outage."}') == "Tell me about the outage."
    assert unwrap_text_envelope('{"content":"Design a rate limiter."}') == "Design a rate limiter."


def test_a_single_string_leaf_unwraps_however_it_is_named():
    assert unwrap_text_envelope('{"opener":"Walk me through a migration."}') == "Walk me through a migration."
    assert unwrap_text_envelope('{"opening":"What do you know about the product?"}') == "What do you know about the product?"


def test_prose_passes_through_untouched():
    assert unwrap_text_envelope("Hello, and welcome. First question: tell me about yourself.") == \
        "Hello, and welcome. First question: tell me about yourself."


def test_a_braces_wrapped_json_object_with_multiple_strings_stays_json():
    raw = '{"message":"Question one.","topic":"background"}'
    assert unwrap_text_envelope(raw) == "Question one."


def test_malformed_json_stays_verbatim():
    assert unwrap_text_envelope("{message: not json") == "{message: not json"
    assert unwrap_text_envelope('{"message": 42}') == '{"message": 42}'


def test_whitespace_and_newlines_are_trimmed():
    assert unwrap_text_envelope('  \n{"message":"  Ask about the migration.  "}\n  ') == "Ask about the migration."
