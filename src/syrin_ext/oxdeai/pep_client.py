from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class PEPResponse:
    status_code: int
    body: dict[str, Any]


class PEPClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def execute(self, action: dict[str, Any], authorization: dict[str, Any]) -> PEPResponse:
        response = requests.post(
            f"{self.base_url}/execute",
            json={
                "action": action,
                "authorization": authorization,
            },
            timeout=self.timeout,
        )
        return PEPResponse(status_code=response.status_code, body=response.json())