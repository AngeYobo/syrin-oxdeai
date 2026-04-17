from .intent import build_intent

def oxdeai_protected(tool_fn):
    def wrapper(*args, **kwargs):
        intent = build_intent(tool_fn.__name__, kwargs)
        raise NotImplementedError("OxDeAI wrapper not implemented")
    return wrapper