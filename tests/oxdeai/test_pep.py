import base64

from nacl.signing import SigningKey

from syrin_ext.oxdeai.canonicalize import canonicalize
from syrin_ext.oxdeai.pep_server import (
    PEPConfig,
    PEPGateway,
    UpstreamExecutionError,
    UpstreamExecutionTimeout,
)
from syrin_ext.oxdeai.verifier import compute_intent_hash


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


def build_gateway(upstream_executor):
    _, public_key_b64 = make_keypair()
    # overwritten per test where needed
    return PEPGateway(
        config=PEPConfig(
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
            now=1712448500,
        ),
        upstream_executor=upstream_executor,
    )


def test_pep_allow_upstream_success():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    gateway = PEPGateway(
        config=PEPConfig(
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
            now=1712448500,
        ),
        upstream_executor=lambda incoming_action: {
            "status": "charged",
            "tool": incoming_action["tool"],
        },
    )

    status, body = gateway.execute({"action": action, "authorization": authorization})

    assert status == 200
    assert body["decision"] == "ALLOW"
    assert body["executed"] is True
    assert body["upstream_result"]["status"] == "charged"


def test_pep_auth_invalid_signature():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)
    authorization["signature"]["sig"] = base64.b64encode(b"\x00" * 64).decode("ascii")

    upstream_called = {"value": False}

    def upstream_executor(_action):
        upstream_called["value"] = True
        return {"status": "charged"}

    gateway = PEPGateway(
        config=PEPConfig(
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
            now=1712448500,
        ),
        upstream_executor=upstream_executor,
    )

    status, body = gateway.execute({"action": action, "authorization": authorization})

    assert status == 403
    assert body["decision"] == "DENY"
    assert body["reason"] == "INVALID_SIGNATURE"
    assert upstream_called["value"] is False


def test_pep_auth_intent_mismatch():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, "a" * 64)

    upstream_called = {"value": False}

    def upstream_executor(_action):
        upstream_called["value"] = True
        return {"status": "charged"}

    gateway = PEPGateway(
        config=PEPConfig(
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
            now=1712448500,
        ),
        upstream_executor=upstream_executor,
    )

    status, body = gateway.execute({"action": action, "authorization": authorization})

    assert status == 403
    assert body["decision"] == "DENY"
    assert body["reason"] == "INTENT_HASH_MISMATCH"
    assert upstream_called["value"] is False


def test_pep_upstream_error():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    def upstream_executor(_action):
        raise UpstreamExecutionError("boom")

    gateway = PEPGateway(
        config=PEPConfig(
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
            now=1712448500,
        ),
        upstream_executor=upstream_executor,
    )

    status, body = gateway.execute({"action": action, "authorization": authorization})

    assert status == 502
    assert body["decision"] == "DENY"
    assert body["reason"] == "UPSTREAM_ERROR"


def test_pep_upstream_timeout():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    def upstream_executor(_action):
        raise UpstreamExecutionTimeout("timeout")

    gateway = PEPGateway(
        config=PEPConfig(
            expected_audience="pep-gateway.local",
            trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
            now=1712448500,
        ),
        upstream_executor=upstream_executor,
    )

    status, body = gateway.execute({"action": action, "authorization": authorization})

    assert status == 504
    assert body["decision"] == "DENY"
    assert body["reason"] == "UPSTREAM_TIMEOUT"