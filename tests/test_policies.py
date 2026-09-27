from app.agents.policies import evaluate_escalation
from app.agents.schemas import SupportDecision


def make_decision(**overrides: object) -> SupportDecision:
    values: dict[str, object] = {
        "intent": "general_inquiry",
        "priority": "medium",
        "sentiment": "neutral",
        "confidence": 0.9,
        "needs_human": False,
        "suggested_action": "answer",
        "reasoning_summary": "A routine question.",
        "response": "Here is the information you requested.",
    }
    values.update(overrides)
    return SupportDecision.model_validate(values)


def test_low_confidence_requires_human_review() -> None:
    result = evaluate_escalation("Can you help me?", make_decision(confidence=0.4))

    assert result.escalated is True
    assert result.reasons == ["low_confidence"]


def test_payment_dispute_cannot_be_overridden_by_model() -> None:
    result = evaluate_escalation("I want to file a chargeback.", make_decision())

    assert result.escalated is True
    assert "payment_dispute" in result.reasons
