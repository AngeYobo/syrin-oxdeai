import base64

from fastapi.testclient import TestClient
from nacl.signing import SigningKey

from syrin_ext.oxdeai.canonicalize import canonicalize
from syrin_ext.oxdeai.http_server import create_pep_app
from syrin_ext.oxdeai.pep_server import UpstreamExecutionError, UpstreamExecutionTimeout
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
        "auth_id": "auth-http-1",
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


def test_http_execute_allow():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    app = create_pep_app(
        expected_audience="pep-gateway.local",
        trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        now=1712448500,
        upstream_executor=lambda incoming_action: {
            "status": "charged",
            "tool": incoming_action["tool"],
        },
    )

    client = TestClient(app)
    response = client.post("/execute", json={"action": action, "authorization": authorization})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["decision"] == "ALLOW"
    assert body["executed"] is True
    assert body["upstream_result"]["status"] == "charged"


def test_http_execute_invalid_signature():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)
    authorization["signature"]["sig"] = base64.b64encode(b"\x00" * 64).decode("ascii")

    app = create_pep_app(
        expected_audience="pep-gateway.local",
        trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        now=1712448500,
        upstream_executor=lambda _incoming_action: {"status": "charged"},
    )

    client = TestClient(app)
    response = client.post("/execute", json={"action": action, "authorization": authorization})

    assert response.status_code == 403
    body = response.json()
    assert body["ok"] is False
    assert body["decision"] == "DENY"
    assert body["reason"] == "INVALID_SIGNATURE"


def test_http_execute_upstream_error():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    def upstream_executor(_incoming_action):
        raise UpstreamExecutionError("boom")

    app = create_pep_app(
        expected_audience="pep-gateway.local",
        trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        now=1712448500,
        upstream_executor=upstream_executor,
    )

    client = TestClient(app)
    response = client.post("/execute", json={"action": action, "authorization": authorization})

    assert response.status_code == 502
    body = response.json()
    assert body["ok"] is False
    assert body["decision"] == "DENY"
    assert body["reason"] == "UPSTREAM_ERROR"


def test_http_execute_upstream_timeout():
    action = {
        "type": "EXECUTE",
        "tool": "payments.charge",
        "params": {"amount": "500", "currency": "USD", "user_id": "user_123"},
    }
    intent_hash = compute_intent_hash(action)
    signing_key, public_key_b64 = make_keypair()
    authorization = make_authorization(signing_key, intent_hash)

    def upstream_executor(_incoming_action):
        raise UpstreamExecutionTimeout("timeout")

    app = create_pep_app(
        expected_audience="pep-gateway.local",
        trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        now=1712448500,
        upstream_executor=upstream_executor,
    )

    client = TestClient(app)
    response = client.post("/execute", json={"action": action, "authorization": authorization})

    assert response.status_code == 504
    body = response.json()
    assert body["ok"] is False
    assert body["decision"] == "DENY"
    assert body["reason"] == "UPSTREAM_TIMEOUT"


def test_http_execute_malformed_request():
    app = create_pep_app(
        expected_audience="pep-gateway.local",
        trusted_key_sets={},
        now=1712448500,
        upstream_executor=lambda _incoming_action: {"status": "charged"},
    )

    client = TestClient(app)
    response = client.post(
        "/execute",
        data="not-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["ok"] is False
    assert body["decision"] == "DENY"
    assert body["reason"] == "MALFORMED_REQUEST"