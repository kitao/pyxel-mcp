"""Tests for _errors module."""

from pyxel_mcp._errors import (
    enrich_error,
    decode_stderr,
    extract_stdout,
    HARNESS_JSON_PREFIX,
)

def test_enrich_error_empty():
    assert enrich_error("") == ""

def test_enrich_error_no_match():
    assert enrich_error("some random error") == "some random error"

def test_enrich_error_blt_hint():
    result = enrich_error("TypeError in blt()")
    assert "blt(x, y, img, u, v, w, h" in result

def test_enrich_error_index_hint():
    result = enrich_error("IndexError: image index out of range")
    assert "Default slots" in result

def test_enrich_error_attribute_hint():
    result = enrich_error("AttributeError: module 'pyxel' has no attribute 'foo'")
    assert "Check API spelling" in result

def test_enrich_error_name_hint():
    result = enrich_error("NameError: name 'KEY_SPACE' is not defined")
    assert "pyxel.KEY_SPACE" in result

def test_enrich_error_int_callable_hint():
    result = enrich_error("TypeError: 'int' object is not callable")
    assert "mouse_x" in result

def test_enrich_error_recursion_hint():
    result = enrich_error("RecursionError: maximum recursion depth exceeded")
    assert "pyxel.run()" in result

def test_decode_stderr_empty():
    assert decode_stderr(b"") == ""
    assert decode_stderr(None) == ""

def test_decode_stderr_normal():
    result = decode_stderr(b"some warning\n")
    assert "some warning" in result

def test_decode_stderr_truncates():
    long_msg = b"x" * 5000
    result = decode_stderr(long_msg)
    assert "truncated" in result
    assert len(result) < 5000

def test_extract_stdout_empty():
    assert extract_stdout(b"") == ("", "")
    assert extract_stdout(b"   ") == ("", "")

def test_extract_stdout_json_only():
    json_str, user = extract_stdout(b'{"key": "value"}')
    assert json_str == '{"key": "value"}'
    assert user == ""

def test_extract_stdout_json_with_user_output():
    raw = b'Hello world\nDebug info\n{"result": 42}'
    json_str, user = extract_stdout(raw)
    assert json_str == '{"result": 42}'
    assert "Hello world" in user
    assert "Debug info" in user

def test_extract_stdout_array_json():
    json_str, user = extract_stdout(b'[1, 2, 3]')
    assert json_str == "[1, 2, 3]"

def test_extract_stdout_no_json():
    text, user = extract_stdout(b"just plain text")
    assert text == "just plain text"

# --- Tests for HARNESS_JSON_PREFIX marker ---

def test_extract_stdout_prefix_only():
    raw = (HARNESS_JSON_PREFIX + '{"key": "value"}').encode()
    json_str, user = extract_stdout(raw)
    assert json_str == '{"key": "value"}'
    assert user == ""

def test_extract_stdout_prefix_with_user_output():
    raw = ("Hello\nDebug\n" + HARNESS_JSON_PREFIX + '{"result": 42}').encode()
    json_str, user = extract_stdout(raw)
    assert json_str == '{"result": 42}'
    assert "Hello" in user
    assert "Debug" in user

def test_extract_stdout_prefix_array():
    raw = (HARNESS_JSON_PREFIX + "[1, 2, 3]").encode()
    json_str, user = extract_stdout(raw)
    assert json_str == "[1, 2, 3]"
    assert user == ""

def test_extract_stdout_prefix_takes_priority_over_legacy():
    """Prefixed line is found before the legacy heuristic."""
    raw = (
        HARNESS_JSON_PREFIX + '{"real": true}\n'
        '{"fake": true}'
    ).encode()
    json_str, user = extract_stdout(raw)
    assert json_str == '{"real": true}'

def test_extract_stdout_user_brace_not_misidentified():
    """User output starting with { is not mistaken for harness JSON
    when a prefixed line is present."""
    raw = (
        'print("{hello}")\n'
        + HARNESS_JSON_PREFIX + '{"status": "ok"}'
    ).encode()
    json_str, user = extract_stdout(raw)
    assert json_str == '{"status": "ok"}'
    assert 'print("{hello}")' in user

def test_extract_stdout_user_brace_without_prefix_uses_fallback():
    """Without a prefix line, the legacy fallback still fires."""
    raw = b'some text\n{"legacy": true}'
    json_str, user = extract_stdout(raw)
    assert json_str == '{"legacy": true}'
    assert "some text" in user
