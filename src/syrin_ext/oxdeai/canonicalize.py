import json
import math
import unicodedata
from typing import Any


SAFE_INT_MIN = -(2**53 - 1)
SAFE_INT_MAX = 2**53 - 1


class CanonicalizationError(ValueError):
    """Base error for canonicalization failures."""

    code = "CANONICALIZATION_ERROR"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.code)


class FloatNotAllowedError(CanonicalizationError):
    code = "FLOAT_NOT_ALLOWED"


class UnsafeIntegerError(CanonicalizationError):
    code = "UNSAFE_INTEGER_NUMBER"


class DuplicateKeyError(CanonicalizationError):
    code = "DUPLICATE_KEY"


class InvalidTimestampError(CanonicalizationError):
    code = "INVALID_TIMESTAMP"


class UnsupportedTypeError(CanonicalizationError):
    code = "UNSUPPORTED_TYPE"


def _is_safe_int(value: int) -> bool:
    return SAFE_INT_MIN <= value <= SAFE_INT_MAX


def _normalize_string(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _normalize_key(key: Any) -> str:
    if not isinstance(key, str):
        raise UnsupportedTypeError("Object keys must be strings")
    return _normalize_string(key)


def _normalize(value: Any, *, parent_key: str | None = None) -> Any:
    """
    Normalize a Python value into the constrained JSON domain required by
    OxDeAI canonicalization-v1.

    Rules implemented:
    - strings -> NFC normalized
    - dict keys -> NFC normalized, duplicate-after-normalization rejected
    - arrays -> order preserved
    - ints -> safe IEEE-754 integer range only
    - bool/null -> allowed
    - floats/NaN/Inf -> rejected
    - unsupported runtime types -> rejected
    - key == "ts" -> value must be safe integer
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    # bool is a subclass of int, so int handling must come after bool.
    if isinstance(value, int):
        if not _is_safe_int(value):
            if parent_key == "ts":
                raise InvalidTimestampError("Timestamp must be a safe integer")
            raise UnsafeIntegerError("Integer outside safe IEEE-754 range")
        if parent_key == "ts":
            return value
        return value

    if isinstance(value, float):
        # Explicitly reject all floats, including integral-looking ones.
        if parent_key == "ts":
            raise InvalidTimestampError("Timestamp must be an integer")
        raise FloatNotAllowedError("Floats are not allowed")

    if isinstance(value, str):
        normalized = _normalize_string(value)
        if parent_key == "ts":
            raise InvalidTimestampError("Timestamp must be an integer")
        return normalized

    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]

    if isinstance(value, dict):
        normalized_obj: dict[str, Any] = {}
        seen_keys: set[str] = set()

        for raw_key, raw_value in value.items():
            key = _normalize_key(raw_key)
            if key in seen_keys:
                raise DuplicateKeyError(
                    f"Duplicate key after NFC normalization: {key!r}"
                )
            seen_keys.add(key)
            normalized_obj[key] = _normalize(raw_value, parent_key=key)

        return normalized_obj

    raise UnsupportedTypeError(f"Unsupported type: {type(value).__name__}")


def canonicalize_to_string(value: Any) -> str:
    """
    Return canonical JSON text.

    Uses:
    - UTF-8 safe JSON text
    - sorted keys
    - no insignificant whitespace
    - ensure_ascii=False so NFC-normalized Unicode is emitted directly
    """
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonicalize(value: Any) -> bytes:
    """
    Return canonical UTF-8 JSON bytes.
    """
    return canonicalize_to_string(value).encode("utf-8")