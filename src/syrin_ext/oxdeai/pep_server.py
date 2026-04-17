from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .verifier import VerificationError, verify_authorization


class UpstreamExecutionError(RuntimeError):
    pass


class UpstreamExecutionTimeout(RuntimeError):
    pass


class ReplayDetectedError(RuntimeError):
    pass


class ReplayStore(Protocol):
    def consume(self, auth_id: str) -> bool:
        """
        Mark auth_id as consumed.

        Returns:
            True  -> consumption succeeded, auth_id was not previously used
            False -> auth_id has already been consumed
        """
        ...


class InMemoryReplayStore:
    def __init__(self) -> None:
        self._consumed: set[str] = set()

    def consume(self, auth_id: str) -> bool:
        if auth_id in self._consumed:
            return False
        self._consumed.add(auth_id)
        return True


@dataclass(frozen=True)
class PEPConfig:
    expected_audience: str
    trusted_key_sets: dict[str, dict[str, str]]
    now: int


class PEPGateway:
    """
    Minimal in-process PEP boundary.

    This models the normative /execute contract and validates boundary logic
    before wiring a real HTTP server or Syrin runtime integration.
    """

    def __init__(
        self,
        config: PEPConfig,
        upstream_executor: Callable[[dict[str, Any]], dict[str, Any]],
        replay_store: ReplayStore | None = None,
    ):
        self.config = config
        self.upstream_executor = upstream_executor
        self.replay_store = replay_store or InMemoryReplayStore()

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

        auth_id = authorization.get("auth_id")
        if not isinstance(auth_id, str):
            return 403, {
                "ok": False,
                "decision": "DENY",
                "reason": "MALFORMED_ARTIFACT",
            }

        if not self.replay_store.consume(auth_id):
            return 403, {
                "ok": False,
                "decision": "DENY",
                "reason": "REPLAY_DETECTED",
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


def direct_upstream_call(
    action: dict[str, Any],
    provided_internal_token: str | None,
    expected_internal_token: str,
    executor: Callable[[dict[str, Any]], dict[str, Any]],
) -> tuple[int, dict[str, Any]]:
    """
    Minimal direct-upstream guard simulation.

    Models the PEP spec requirement that upstream reject calls that do not carry
    the internal executor token.
    """
    if provided_internal_token != expected_internal_token:
        return 403, {
            "ok": False,
            "decision": "DENY",
            "reason": "DIRECT_BYPASS_REJECTED",
        }

    result = executor(action)
    return 200, {
        "ok": True,
        "decision": "ALLOW",
        "executed": True,
        "upstream_result": result,
    }