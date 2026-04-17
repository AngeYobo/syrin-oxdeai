def build_intent(tool: str, params: dict) -> dict:
    return {
        "type": "EXECUTE",
        "tool": tool,
        "params": params,
    }