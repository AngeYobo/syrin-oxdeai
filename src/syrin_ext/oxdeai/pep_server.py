from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .verifier import VerificationError, verify_authorization


class UpstreamExecutionError(RuntimeError):
    pass


class UpstreamExecutionTimeout(RuntimeError):
    pass


@dataclass(frozen=True)
class PEPConfig:
    expected_audience: str
    trusted_key_sets: dict[str, dict[str, str]]
    now: int


class PEPGateway:
    """
    Minimal in-process PEP boundary.

    This is not yet a real HTTP server.
    It models the normative /execute contract and lets us validate boundary logic
    before wiring Syrin runtime integration.
    """

    def __init__(
        self,
        config: PEPConfig,
        upstream_executor: Callable[[dict[str, Any]], dict[str, Any]],
    ):
        self.config = config
        self.upstream_executor = upstream_executor

    def execute(self, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not isinstance(request, dict):
            return 403, {
                "ok": False,
                "decision": "DENY",
                "reason": "MALFORMED_REQUEST",
            }

        action = request.get("action")
        authorization = request.get("authorization")

        if not isinstance(action, dict) or not isinstance(authorization, dict):
            return 403, {
                "ok": False,
                "decision": "DENY",
                "reason": "MALFORMED_REQUEST",
            }

        try:
            verify_authorization(
                authorization=authorization,
                action=action,
                now=self.config.now,
                expected_audience=self.config.expected_audience,
                trusted_key_sets=self.config.trusted_key_sets,
            )
        except VerificationError as exc:
            return 403, {
                "ok": False,
                "decision": "DENY",
                "reason": exc.code,
            }

        try:
            upstream_result = self.upstream_executor(action)
        except UpstreamExecutionTimeout:
            return 504, {
                "ok": False,
                "decision": "DENY",
                "reason": "UPSTREAM_TIMEOUT",
            }
        except UpstreamExecutionError:
            return 502, {
                "ok": False,
                "decision": "DENY",
                "reason": "UPSTREAM_ERROR",
            }

        return 200, {
            "ok": True,
            "decision": "ALLOW",
            "executed": True,
            "auth_id": authorization["auth_id"],
            "intent_hash": authorization["intent_hash"],
            "upstream_result": upstream_result,
        }