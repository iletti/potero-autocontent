from typing import Any, Dict

MODEL_ALIASES = {
    "gemini-1.5-flash": "gemini-3-flash-preview",
    "gemini-1.5-pro": "gemini-3-flash-preview",
    "gemini-2.5-flash-image-preview": "gemini-2.5-flash-image",
}


def update_model(model: Any, update: Dict[str, Any]) -> Any:
    if hasattr(model, "model_copy"):
        return model.model_copy(update=update)
    return model.copy(update=update)


def model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def normalize_model_name(name: str) -> str:
    if not name:
        return name
    raw = name.strip()
    if raw.startswith("models/"):
        raw = raw[len("models/") :]
    raw = MODEL_ALIASES.get(raw, raw)
    return f"models/{raw}"
