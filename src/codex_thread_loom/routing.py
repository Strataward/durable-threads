"""Resolve role selectors against a live model catalog."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelInfo:
    """The small model subset needed by the router."""

    model_id: str
    display_name: str
    tier: str
    is_default: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelInfo:
        model_id = data.get("id", data.get("model"))
        display_name = data.get("displayName", data.get("display_name", model_id))
        tier = data.get("tier", data.get("costTier", "unknown"))
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model catalog entries need an id")
        return cls(
            model_id=model_id.strip(),
            display_name=str(display_name).strip(),
            tier=str(tier).strip().lower(),
            is_default=bool(data.get("isDefault", data.get("default", False))),
        )


@dataclass(frozen=True)
class Resolution:
    """A model choice with a reason that can be shown to the user."""

    model: ModelInfo | None
    reason: str
    matched: bool


def catalog_from_payload(payload: Any) -> tuple[ModelInfo, ...]:
    """Read common Codex model-list shapes without assuming model names."""

    if isinstance(payload, dict):
        raw_models = payload.get("models", [])
    else:
        raw_models = payload
    if not isinstance(raw_models, list):
        raise ValueError("model catalog must contain a models array")
    return tuple(ModelInfo.from_dict(item) for item in raw_models if isinstance(item, dict))


def _normal(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").replace("-", " ").split())


def resolve_model(catalog: Iterable[ModelInfo], selector: str) -> Resolution:
    """Resolve an exact id or a stable role selector.

    Role selectors use catalog metadata first. The fallback keeps the runtime's
    default model instead of guessing a stale provider-specific slug.
    """

    models = tuple(catalog)
    wanted = _normal(selector)
    for model in models:
        names = {
            _normal(model.model_id),
            _normal(model.display_name),
            *_normal(model.model_id).split(),
            *_normal(model.display_name).split(),
        }
        if wanted in names:
            return Resolution(model, f"exact catalog match for {selector!r}", True)

    tier_groups = {
        "frontier": {"frontier", "flagship", "high"},
        "balanced": {"balanced", "standard", "medium"},
        "efficient": {"efficient", "low", "mini"},
    }
    if wanted in tier_groups:
        candidates = [model for model in models if model.tier in tier_groups[wanted]]
        if candidates:
            default = next((model for model in candidates if model.is_default), candidates[0])
            return Resolution(default, f"{wanted} role matched live catalog metadata", True)
        default = next((model for model in models if model.is_default), None)
        if default:
            return Resolution(
                default,
                f"{wanted} role was unavailable; using the runtime default without guessing",
                False,
            )
    return Resolution(None, f"no live model matched selector {selector!r}", False)
