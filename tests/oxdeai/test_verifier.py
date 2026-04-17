import base64

import pytest
from nacl.signing import SigningKey

from syrin_ext.oxdeai.canonicalize import canonicalize
from syrin_ext.oxdeai.verifier import (
    AudienceMismatchError,
    ExpiredAuthorizationError,
    IntentHashMismatchError,
    InvalidSignatureError,
    VerificationResult,
    compute_intent_hash,
    verify_authorization,
)


def make_keypair():
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    return signing_key, base64.b64encode(bytes(verify_key)).decode("ascii")


def sign_authorization_payload(signing_key: SigningKey, payload: dict) -> str:
    signature = signing_key.sign(canonicalize(payload)).signature
    return base64.b64encode(signature).decode("ascii")


def make_authorization(signing_key: SigningKey, intent_hash: str) -> dict:
    payload = {
        "version": "AuthorizationV1",
        "auth_id": "auth-allow-1",
        "issuer": "issuer-1",
        "audience": "pep-gateway.local",
        "decision": "ALLOW",
        "intent_hash": intent_hash,
        "state_hash": "89d739f4d161ed9c8de4319bd2ab140d4d2f7de0d0ae172133cb79cd70187823",
        "policy_id": "policy-1",
        "issued_at": 1712448000,
        "expiry": 1712448600,
        "alg": "Ed25519",
        "kid": "auth-key-1",
        "signature": {
            "alg": "Ed25519",
            "kid": "auth-key-1",
        },
    }

    sig = sign_authorization_payload(signing_key, payload)
    return {
        **payload,
        "signature": {
            **payload["signature"],
            "sig": sig,
        },
    }


def test_verify_authorization_valid():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    result = verify_authorization(
        authorization=authorization,
        action=action,
        now=1712448500,
        expected_audience="pep-gateway.local",
        trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
    )

    assert result == VerificationResult(decision="ALLOW", reason_code="AUTHORIZED")


def test_verify_authorization_expired():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    with pytest.raises(ExpiredAuthorizationError) as exc:
        verify_authorization(
            authorization=authorization,
            action=action,
            now=1712448600,
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        )

    assert exc.value.code == "EXPIRED"


def test_verify_authorization_invalid_signature():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    authorization["signature"]["sig"] = base64.b64encode(b"\x00" * 64).decode("ascii")

    with pytest.raises(InvalidSignatureError) as exc:
        verify_authorization(
            authorization=authorization,
            action=action,
            now=1712448500,
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        )

    assert exc.value.code == "INVALID_SIGNATURE"


def test_verify_authorization_intent_mismatch():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, "a" * 64)

    with pytest.raises(IntentHashMismatchError) as exc:
        verify_authorization(
            authorization=authorization,
            action=action,
            now=1712448500,
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        )

    assert exc.value.code == "INTENT_HASH_MISMATCH"


def test_verify_authorization_audience_mismatch():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    with pytest.raises(AudienceMismatchError) as exc:
        verify_authorization(
            authorization=authorization,
            action=action,
            now=1712448500,
            expected_audience="other-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        )

    assert exc.value.code == "AUDIENCE_MISMATCH"