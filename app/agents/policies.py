"""Deterministic safety and human-escalation policies."""

from dataclasses import dataclass

from app.agents.schemas import SupportDecision

LOW_CONFIDENCE_THRESHOLD = 0.65

MANDATORY_ESCALATION_SIGNALS: dict[str, tuple[str, ...]] = {
    "security_or_fraud": ("fraud", "fraudulent", "account hacked", "hacked account", "unauthorized charge", "stolen card", "security breach"),
    "legal_or_regulatory": ("lawyer", "legal action", "sue", "lawsuit", "regulator"),
    "payment_dispute": ("chargeback", "payment dispute", "dispute this charge"),
    "safety_concern": ("suicide", "self harm", "kill myself"),
    "threatening_or_abusive_conduct": ("i will kill", "death threat", "threaten", "harassment"),
}


@dataclass(frozen=True)
class EscalationResult:
    """The deterministic result of applying support-safety policy."""

    escalated: bool
    reasons: list[str]


def evaluate_escalation(message: str, decision: SupportDecision) -> EscalationResult:
    """Escalate mandatory risks regardless of the model's recommendation."""

    normalized_message = message.casefold()
    reasons = [reason for reason, signals in MANDATORY_ESCALATION_SIGNALS.items() if any(signal in normalized_message for signal in signals)]
    if decision.needs_human:
        reasons.append("model_requested_human_review")
    if decision.suggested_action in {"create_ticket", "escalate"}:
        reasons.append("model_suggested_escalation")
    if decision.intent == "refund_request":
        reasons.append("refund_or_return_requires_approval")
    if decision.confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append("low_confidence")
    if decision.priority == "urgent":
        reasons.append("urgent_priority")
    return EscalationResult(escalated=bool(reasons), reasons=reasons)
