import hashlib

import pytest

from syrin_ext.oxdeai.canonicalize import (
    DuplicateKeyError,
    FloatNotAllowedError,
    InvalidTimestampError,
    UnsafeIntegerError,
    UnsupportedTypeError,
    canonicalize,
    canonicalize_to_string,
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_object_key_ordering():
    input_data = {"b": 1, "a": 2}
    result = canonicalize(input_data)
    assert result == b'{"a":2,"b":1}'
    assert (
        sha256_hex(result)
        == "d3626ac30a87e6f7a6428233b3c68299976865fa5508e4267c5415c76af7a772"
    )


def test_nested_ordering():
    input_data = {"z": {"b": 2, "a": 1}}
    result = canonicalize(input_data)
    assert result == b'{"z":{"a":1,"b":2}}'
    assert (
        sha256_hex(result)
        == "0560517cc75a67b3c41aaf18da6d75dff0d66b5874f9c38e6f420913f9035b64"
    )


def test_array_order_preserved():
    input_data = ["b", "a"]
    result = canonicalize(input_data)
    assert result == b'["b","a"]'
    assert (
        sha256_hex(result)
        == "02d8bc3008a9bb0dcc4b86d7fd3428ced792355c733c19756bec5a56dc61b2c5"
    )


def test_unicode_nfc_normalization():
    input_data = {"text": "e\u0301"}
    result = canonicalize(input_data)
    assert result == '{"text":"é"}'.encode("utf-8")
    assert (
        sha256_hex(result)
        == "42d3cbf59fdccced04e5dff14433fb52d34d58e385e9770ffd896ff517d63b92"
    )


def test_realistic_intent_example():
    input_data = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {
            "amount": "500",
            "currency": "USD",
        },
    }
    result = canonicalize(input_data)
    assert (
        result
        == b'{"params":{"amount":"500","currency":"USD"},"tool":"payments.charge","type":"EXECUTE"}'
    )
    assert (
        sha256_hex(result)
        == "b75c8d1d9952254b2386f4e412f8fd0b8ac7361ddb54e50c22b19ffc1a3c8c2d"
    )


def test_float_rejected():
    with pytest.raises(FloatNotAllowedError) as exc:
        canonicalize({"value": 1.5})
    assert exc.value.code == "FLOAT_NOT_ALLOWED"


def test_string_timestamp_rejected():
    with pytest.raises(InvalidTimestampError) as exc:
        canonicalize({"ts": "2026-04-03T12:00:00Z"})
    assert exc.value.code == "INVALID_TIMESTAMP"


def test_float_timestamp_rejected():
    with pytest.raises(InvalidTimestampError) as exc:
        canonicalize({"ts": 1712448000.5})
    assert exc.value.code == "INVALID_TIMESTAMP"


def test_unsafe_integer_rejected():
    with pytest.raises(UnsafeIntegerError) as exc:
        canonicalize({"value": 9007199254740992})
    assert exc.value.code == "UNSAFE_INTEGER_NUMBER"


def test_duplicate_key_after_nfc_rejected():
    with pytest.raises(DuplicateKeyError) as exc:
        canonicalize({"é": 1, "e\u0301": 2})
    assert exc.value.code == "DUPLICATE_KEY"


def test_unsupported_type_rejected():
    with pytest.raises(UnsupportedTypeError) as exc:
        canonicalize({"x": {1, 2}})
    assert exc.value.code == "UNSUPPORTED_TYPE"