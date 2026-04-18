from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .intent import build_intent
from .pep_client import PEPClient


class OxDeAIDeniedError(RuntimeError):
    def __init__(self, reason: str, response_body: dict[str, Any] | None = None):
        self.reason = reason
        self.response_body = response_body or {}
        super().__init__(f"OxDeAI denied execution: {reason}")


class OxDeAIExecutionError(RuntimeError):
    def __init__(self, status_code: int, response_body: dict[str, Any] | None = None):
        self.status_code = status_code
        self.response_body = response_body or {}
        super().__init__(f"OxDeAI execution failed with status {status_code}")


AuthorizationProvider = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class WrappedToolResult:
    decision: str
    status_code: int
    response_body: dict[str, Any]


def oxdeai_protected(
    tool_name: str,
    pep_client: PEPClient,
    authorization_provider: AuthorizationProvider,
):
    """
    Wrap a tool call behind the OxDeAI PEP boundary.

    Flow:
    1. Normalize tool call -> OxDeAI intent
    2. Obtain AuthorizationV1 from authorization_provider
    3. Call PEP /execute
    4. Return structured result if allowed
    5. Raise on DENY / execution failure
    """

    def decorator(tool_fn: Callable[..., Any]):
        def wrapper(*args, **kwargs):
            if args:
                raise TypeError(
                    "Wrapped OxDeAI tools currently support keyword arguments only"
                )

            intent = build_intent(tool=tool_name, params=kwargs)
            authorization = authorization_provider(intent)

            pep_response = pep_client.execute(
                action=intent,
                authorization=authorization,
            )

            body = pep_response.body
            status_code = pep_response.status_code

            if status_code == 200 and body.get("decision") == "ALLOW":
                return WrappedToolResult(
                    decision="ALLOW",
                    status_code=status_code,
                    response_body=body,
                )

            if status_code == 403 and body.get("decision") == "DENY":
                raise OxDeAIDeniedError(
                    reason=body.get("reason", "DENY"),
                    response_body=body,
                )

            raise OxDeAIExecutionError(
                status_code=status_code,
                response_body=body,
            )

        wrapper.__name__ = tool_fn.__name__
        wrapper.__doc__ = tool_fn.__doc__
        return wrapper

    return decorator