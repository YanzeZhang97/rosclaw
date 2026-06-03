"""rosclaw.how — Heuristic Rules & Recovery Strategies.

Two coexisting layers:

  * **v1.0 (reactive)** — :class:`HeuristicEngine`, :class:`RecoveryEngine`,
    :class:`RecoveryLoop`. Event-driven: subscribes to ``praxis.failed`` /
    ``firewall.action_blocked`` / ``safety.violation`` on the EventBus,
    looks up a rule, emits a recovery hint, manages retry bookkeeping.
    Backed by SeekDB; outcome counters update on every success/failure.

  * **v1.5 (proactive)** — :mod:`rosclaw.how.v15`. Pure-rules pipeline:
    ``InterventionRequest`` → :func:`v15.diagnose` (RuntimeState across
    optimization × feasibility × safety axes) → :func:`v15.decide_strategy`
    (one of 11 strategies with cooldown awareness) → :func:`v15.compose`
    (strategy-specific markdown snippet). Standalone — no FastAPI, no
    embedding model — and integrated into
    :meth:`HeuristicEngine.decide_recovery` so v1.5 decisions still feed
    outcome tracking via ``record_outcome``.

The two layers share the SAFETY_TAXONOMY (S0-S4 vocabulary). The engine
consults the taxonomy before its substring matcher, then falls back to
v1.0 rules. Existing v1.0 callers / tests are unchanged.

Integration:
  Runtime    -> _how = HeuristicEngine(seekdb_client)
  Firewall   -> on block: query _how.suggest_recovery() -> EventBus
  Agent      -> analyze_failure(): try _how first, fall back to LLM
  Practice   -> on praxis.failed: record outcome -> update rule stats
  RuntimeLoop-> v1.5: _how.decide_recovery(InterventionRequest) ->
                full decision + rule_id (when safety-attributable).
"""
from .engine import HeuristicEngine
from .recovery import RecoveryEngine, RecoveryFormatter, format_recovery_suggestion
from .recovery_loop import RecoveryLoop
from .v15 import (
    SAFETY_TAXONOMY,
    AgentContext,
    ArtifactContext,
    FeasibilityState,
    InterventionDecision,
    InterventionRequest,
    ObjectiveDirection,
    OptimizationContext,
    OptimizationState,
    RuntimeState,
    SafetyContext,
    SafetySeverity,
    SafetyState,
    StrategyV15,
    TaskContext,
    compose,
    decide_strategy,
    decision_as_v1_response,
    diagnose,
    diagnose_safety,
    from_v1_prompt_build,
    is_blocking,
)

__all__ = [
    # v1.0
    "HeuristicEngine",
    "RecoveryEngine",
    "RecoveryFormatter",
    "format_recovery_suggestion",
    "RecoveryLoop",
    # v1.5 schemas
    "AgentContext",
    "ArtifactContext",
    "FeasibilityState",
    "InterventionDecision",
    "InterventionRequest",
    "ObjectiveDirection",
    "OptimizationContext",
    "OptimizationState",
    "RuntimeState",
    "SafetyContext",
    "SafetySeverity",
    "SafetyState",
    "StrategyV15",
    "TaskContext",
    # v1.5 ops
    "SAFETY_TAXONOMY",
    "compose",
    "decide_strategy",
    "decision_as_v1_response",
    "diagnose",
    "diagnose_safety",
    "from_v1_prompt_build",
    "is_blocking",
]
