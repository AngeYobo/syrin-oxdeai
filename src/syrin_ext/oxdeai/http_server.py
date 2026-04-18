from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .pep_server import PEPConfig, PEPGateway


def create_pep_app(
    *,
    expected_audience: str,
    trusted_key_sets: dict[str, dict[str, str]],
    now: int,
    upstream_executor: Callable[[dict[str, Any]], dict[str, Any]],
) -> FastAPI:
    app = FastAPI(title="OxDeAI PEP Gateway", version="0.1.0")

    gateway = PEPGateway(
        config=PEPConfig(
            expected_audience=expected_audience,
            trusted_key_sets=trusted_key_sets,
            now=now,
        ),
        upstream_executor=upstream_executor,
    )

    @app.post("/execute")
    async def execute(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "decision": "DENY",
                    "reason": "MALFORMED_REQUEST",
                },
            )

        status_code, body = gateway.execute(payload)
        return JSONResponse(status_code=status_code, content=body)

    return app