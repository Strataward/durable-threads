"""Deterministic contracts for durable multi-provider thread orchestration."""

__version__ = "0.2.0"

from .config import ConfigError, Roster, load_roster
from .ledger import Ledger
from .packets import DelegationPacket, PacketError, build_packet
from .providers import (
    PROVIDERS,
    DispatchResult,
    ProviderCapability,
    ProviderError,
    ProviderInvocation,
    build_invocation,
    extract_session_id,
    get_capabilities,
    provider_status,
    run_invocation,
)
from .routing import ModelInfo, Resolution, resolve_model

__all__ = [
    "ConfigError",
    "DelegationPacket",
    "DispatchResult",
    "Ledger",
    "ModelInfo",
    "PacketError",
    "PROVIDERS",
    "ProviderCapability",
    "ProviderError",
    "ProviderInvocation",
    "Resolution",
    "Roster",
    "build_packet",
    "build_invocation",
    "extract_session_id",
    "get_capabilities",
    "load_roster",
    "provider_status",
    "resolve_model",
    "run_invocation",
]
