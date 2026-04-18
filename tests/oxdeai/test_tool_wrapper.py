import base64
from threading import Thread
from typing import Any

import uvicorn
from nacl.signing import SigningKey

from syrin_ext.oxdeai.canonicalize import canonicalize
from syrin_ext.oxdeai.http_server import create_pep_app
from syrin_ext.oxdeai.pep_client import PEPClient
from syrin_ext.oxdeai.tool_wrapper import (
    OxDeAIDeniedError,
    WrappedToolResult,
    oxdeai_protected,
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
        "auth_id": "auth-wrapper-1",
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


def test_tool_wrapper_allow():
    action_capture: dict[str, Any] = {}

    signing_key, public_key_b64 = make_keypair()

    app = create_pep_app(
        expected_audience="pep-gateway.local",
        trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        now=1712448500,
        upstream_executor=lambda incoming_action: {
            "status": "charged",
            "tool": incoming_action["tool"],
            "amount": incoming_action["params"]["amount"],
        },
    )

    client = PEPClient(base_url="http://testserver")
    # Monkey patch the underlying HTTP call path through FastAPI TestClient
    from fastapi.testclient import TestClient

    test_client = TestClient(app)

    def execute_override(action: dict, authorization: dict):
        response = test_client.post(
            "/execute",
            json={"action": action, "authorization": authorization},
        )
        from syrin_ext.oxdeai.pep_client import PEPResponse
        return PEPResponse(status_code=response.status_code, body=response.json())

    client.execute = execute_override  # type: ignore[method-assign]

    def authorization_provider(intent: dict[str, Any]) -> dict[str, Any]:
        action_capture["intent"] = intent
        return make_authorization(signing_key, compute_intent_hash(intent))

    @oxdeai_protected(
        tool_name="payments.charge",
        pep_client=client,
        authorization_provider=authorization_provider,
    )
    def charge_payment(**kwargs):
        return kwargs

    result = charge_payment(amount="500", currency="USD", user_id="user_123")

    assert isinstance(result, WrappedToolResult)
    assert result.decision == "ALLOW"
    assert result.status_code == 200
    assert action_capture["intent"]["tool"] == "payments.charge"
    assert result.response_body["upstream_result"]["amount"] == "500"


def test_tool_wrapper_deny():
    signing_key, public_key_b64 = make_keypair()

    app = create_pep_app(
        expected_audience="pep-gateway.local",
        trusted_key_sets={"issuer-1": {"auth-key-1": public_key_b64}},
        now=1712448500,
        upstream_executor=lambda incoming_action: {
            "status": "charged",
            "tool": incoming_action["tool"],
        },
    )

    client = PEPClient(base_url="http://testserver")
    from fastapi.testclient import TestClient

    test_client = TestClient(app)

    def execute_override(action: dict, authorization: dict):
        response = test_client.post(
            "/execute",
            json={"action": action, "authorization": authorization},
        )
        from syrin_ext.oxdeai.pep_client import PEPResponse
        return PEPResponse(status_code=response.status_code, body=response.json())

    client.execute = execute_override  # type: ignore[method-assign]

    def authorization_provider(intent: dict[str, Any]) -> dict[str, Any]:
        # Intentionally wrong intent hash to force DENY
        return make_authorization(signing_key, "a" * 64)

    @oxdeai_protected(
        tool_name="payments.charge",
        pep_client=client,
        authorization_provider=authorization_provider,
    )
    def charge_payment(**kwargs):
        return kwargs

    try:
        charge_payment(amount="500", currency="USD", user_id="user_123")
        assert False, "Expected OxDeAIDeniedError"
    except OxDeAIDeniedError as exc:
        assert exc.reason == "INTENT_HASH_MISMATCH"
        assert exc.response_body["decision"] == "DENY"