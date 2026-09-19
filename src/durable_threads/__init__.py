"""Deterministic contracts for durable multi-provider thread orchestration."""

__version__ = "0.6.0"

from .config import ConfigError, Roster, load_roster
from .decisions import (
    DecisionAnswer,
    DecisionBatch,
    DecisionEngine,
    DecisionGate,
    DecisionPolicy,
    DecisionQuestion,
    JevDecisionEngine,
    QuestionKind,
    StaticDecisionEngine,
)
from .evidence import (
    EvidenceError,
    WorkerEvidence,
    git_changed_paths,
    parse_worker_result,
    validate_evidence,
)
from .execution import (
    ExecutionBackend,
    ExecutionError,
    ExecutionRegistry,
    ExecutionRequirements,
    ExecutionSelection,
    ExecutorDescriptor,
    ExecutorPlugin,
    default_execution_registry,
)
from .intelligence import ResultAssessment, TaskAssessment, assess_result, assess_task
from .ledger import Ledger, LedgerBusyError, LedgerStateError
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
from .routing import ModelInfo, Resolution, RouteDecision, resolve_model, select_workers

__all__ = [
    "ConfigError",
    "DecisionAnswer",
    "DecisionBatch",
    "DecisionEngine",
    "DecisionGate",
    "DecisionPolicy",
    "DecisionQuestion",
    "ExecutionBackend",
    "ExecutionError",
    "ExecutionRegistry",
    "ExecutionRequirements",
    "ExecutionSelection",
    "ExecutorDescriptor",
    "ExecutorPlugin",
    "JevDecisionEngine",
    "QuestionKind",
    "ResultAssessment",
    "StaticDecisionEngine",
    "TaskAssessment",
    "EvidenceError",
    "DelegationPacket",
    "DispatchResult",
    "Ledger",
    "LedgerBusyError",
    "LedgerStateError",
    "ModelInfo",
    "PacketError",
    "PROVIDERS",
    "ProviderCapability",
    "ProviderError",
    "ProviderInvocation",
    "Resolution",
    "RouteDecision",
    "Roster",
    "WorkerEvidence",
    "build_packet",
    "build_invocation",
    "assess_result",
    "assess_task",
    "default_execution_registry",
    "extract_session_id",
    "get_capabilities",
    "git_changed_paths",
    "load_roster",
    "provider_status",
    "parse_worker_result",
    "resolve_model",
    "select_workers",
    "run_invocation",
    "validate_evidence",
]
