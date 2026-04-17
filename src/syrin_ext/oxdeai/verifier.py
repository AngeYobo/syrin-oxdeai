import base64
import hashlib
from dataclasses import dataclass
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from .canonicalize import canonicalize


class VerificationError(ValueError):
    code = "VERIFICATION_ERROR"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.code)


class StructuralValidationError(VerificationError):
    code = "MALFORMED_ARTIFACT"


class UnsupportedAlgorithmError(VerificationError):
    code = "UNSUPPORTED_ALG"


class KeyResolutionError(VerificationError):
    code = "KEY_RESOLUTION_FAILED"


class InvalidSignatureError(VerificationError):
    code = "INVALID_SIGNATURE"


class ExpiredAuthorizationError(VerificationError):
    code = "EXPIRED"


class AudienceMismatchError(VerificationError):
    code = "AUDIENCE_MISMATCH"


class DecisionDeniedError(VerificationError):
    code = "DECISION_NOT_ALLOW"


class IntentHashMismatchError(VerificationError):
    code = "INTENT_HASH_MISMATCH"


@dataclass(frozen=True)
class VerificationResult:
    decision: str
    reason_code: str


REQUIRED_AUTH_FIELDS = {
    "version",
    "auth_id",
    "issuer",
    "audience",
    "decision",
    "intent_hash",
    "state_hash",
    "policy_id",
    "issued_at",
    "expiry",
    "alg",
    "kid",
    "signature",
}

REQUIRED_SIGNATURE_FIELDS = {"alg", "kid", "sig"}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_intent_hash(action: dict[str, Any]) -> str:
    return sha256_hex(canonicalize(action))


def _validate_structure(authorization: dict[str, Any]) -> None:
    if not isinstance(authorization, dict):
        raise StructuralValidationError("Authorization must be an object")

    missing = REQUIRED_AUTH_FIELDS - set(authorization.keys())
    if missing:
        raise StructuralValidationError(f"Missing fields: {sorted(missing)}")

    signature = authorization.get("signature")
    if not isinstance(signature, dict):
        raise StructuralValidationError("signature must be an object")

    sig_missing = REQUIRED_SIGNATURE_FIELDS - set(signature.keys())
    if sig_missing:
        raise StructuralValidationError(
            f"Missing signature fields: {sorted(sig_missing)}"
        )

    if authorization["version"] != "AuthorizationV1":
        raise StructuralValidationError("version must be AuthorizationV1")

    if not isinstance(authorization["auth_id"], str):
        raise StructuralValidationError("auth_id must be a string")

    if not isinstance(authorization["issuer"], str):
        raise StructuralValidationError("issuer must be a string")

    if not isinstance(authorization["audience"], str):
        raise StructuralValidationError("audience must be a string")

    if not isinstance(authorization["decision"], str):
        raise StructuralValidationError("decision must be a string")

    if not isinstance(authorization["intent_hash"], str):
        raise StructuralValidationError("intent_hash must be a string")

    if not isinstance(authorization["state_hash"], str):
        raise StructuralValidationError("state_hash must be a string")

    if not isinstance(authorization["policy_id"], str):
        raise StructuralValidationError("policy_id must be a string")

    if not isinstance(authorization["issued_at"], int):
        raise StructuralValidationError("issued_at must be an integer")

    if not isinstance(authorization["expiry"], int):
        raise StructuralValidationError("expiry must be an integer")

    if not isinstance(authorization["alg"], str):
        raise StructuralValidationError("alg must be a string")

    if not isinstance(authorization["kid"], str):
        raise StructuralValidationError("kid must be a string")

    if not isinstance(signature["alg"], str):
        raise StructuralValidationError("signature.alg must be a string")

    if not isinstance(signature["kid"], str):
        raise StructuralValidationError("signature.kid must be a string")

    if not isinstance(signature["sig"], str):
        raise StructuralValidationError("signature.sig must be a string")


def _resolve_key(
    authorization: dict[str, Any],
    trusted_key_sets: dict[str, dict[str, str]],
) -> VerifyKey:
    issuer = authorization["issuer"]
    kid = authorization["kid"]
    alg = authorization["alg"]
    signature = authorization["signature"]

    if alg != "Ed25519":
        raise UnsupportedAlgorithmError("Only Ed25519 is supported")

    if signature["alg"] != "Ed25519":
        raise UnsupportedAlgorithmError("Only Ed25519 signatures are supported")

    if signature["kid"] != kid:
        raise KeyResolutionError("signature.kid must match top-level kid")

    issuer_keys = trusted_key_sets.get(issuer)
    if issuer_keys is None:
        raise KeyResolutionError("Unknown issuer")

    public_key_b64 = issuer_keys.get(kid)
    if public_key_b64 is None:
        raise KeyResolutionError("Unknown kid")

    try:
        key_bytes = base64.b64decode(public_key_b64)
        return VerifyKey(key_bytes)
    except Exception as exc:
        raise KeyResolutionError("Invalid public key encoding") from exc


def _signature_preimage(authorization: dict[str, Any]) -> bytes:
    preimage = dict(authorization)
    signature = dict(preimage["signature"])
    signature.pop("sig", None)
    preimage["signature"] = signature
    return canonicalize(preimage)


def verify_authorization(
    authorization: dict[str, Any],
    action: dict[str, Any],
    now: int,
    expected_audience: str,
    trusted_key_sets: dict[str, dict[str, str]],
) -> VerificationResult:
    _validate_structure(authorization)

    if authorization["decision"] != "ALLOW":
        raise DecisionDeniedError("Authorization decision is not ALLOW")

    if authorization["audience"] != expected_audience:
        raise AudienceMismatchError("Audience mismatch")

    if now >= authorization["expiry"]:
        raise ExpiredAuthorizationError("Authorization expired")

    verify_key = _resolve_key(authorization, trusted_key_sets)

    try:
        sig_bytes = base64.b64decode(authorization["signature"]["sig"])
    except Exception as exc:
        raise InvalidSignatureError("Invalid signature encoding") from exc

    preimage = _signature_preimage(authorization)

    try:
        verify_key.verify(preimage, sig_bytes)
    except BadSignatureError as exc:
        raise InvalidSignatureError("Signature verification failed") from exc

    computed_intent_hash = compute_intent_hash(action)
    if computed_intent_hash != authorization["intent_hash"]:
        raise IntentHashMismatchError("intent_hash does not match action")

    return VerificationResult(decision="ALLOW", reason_code="AUTHORIZED")