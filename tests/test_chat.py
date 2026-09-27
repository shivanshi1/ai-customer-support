from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.agents.schemas import SupportDecision


def test_chat_endpoint_persists_conversation_history() -> None:
    decision = SupportDecision(
        intent="password_reset",
        priority="low",
        sentiment="neutral",
        confidence=0.96,
        needs_human=False,
        suggested_action="answer",
        reasoning_summary="The customer asks for password-reset instructions.",
        response="To reset your password, use the password reset option.",
    )
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        groq_api_key="test-key",
    )

    with patch(
        "app.services.llm_service.LLMService.generate_support_decision",
        new_callable=AsyncMock,
        return_value=decision,
    ), TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/chat",
            json={"customer_id": "C001", "message": "How do I reset my password?"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["intent"] == "password_reset"
        assert data["priority"] == "low"
        assert data["response"] == decision.response
        assert data["confidence"] == decision.confidence
        assert data["escalated"] is False

        conversation_id = data["conversation_id"]
        follow_up = client.post(
            "/api/v1/chat",
            json={
                "customer_id": "C001",
                "conversation_id": conversation_id,
                "message": "Thanks. What should I do next?",
            },
        )
        assert follow_up.status_code == 200
        assert follow_up.json()["conversation_id"] == conversation_id

        history = client.get(
            f"/api/v1/conversations/{conversation_id}",
            params={"customer_id": "C001"},
        )
        assert history.status_code == 200
        assert [message["sender"] for message in history.json()["messages"]] == [
            "customer",
            "assistant",
            "customer",
            "assistant",
        ]


def test_chat_escalates_mandatory_security_risk() -> None:
    decision = SupportDecision(
        intent="general_inquiry",
        priority="low",
        sentiment="neutral",
        confidence=0.99,
        needs_human=False,
        suggested_action="answer",
        reasoning_summary="The model did not identify the security signal.",
        response="I have flagged your request for review.",
    )
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", groq_api_key="test-key")

    with patch(
        "app.services.llm_service.LLMService.generate_support_decision",
        new_callable=AsyncMock,
        return_value=decision,
    ), TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/chat",
            json={"customer_id": "C001", "message": "I see an unauthorized charge on my card."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["escalated"] is True
    assert data["needs_human"] is True
    assert data["action_taken"] == "support_ticket_created"
    assert "security_or_fraud" in data["escalation_reasons"]
    assert "created support ticket" in data["response"].lower()


def test_chat_looks_up_only_the_customers_order() -> None:
    decision = SupportDecision(
        intent="order_status",
        priority="low",
        sentiment="neutral",
        confidence=0.95,
        needs_human=False,
        suggested_action="fetch_order",
        reasoning_summary="The customer asks about an order status.",
        response="I checked the order details.",
    )
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", groq_api_key="test-key")

    with patch(
        "app.services.llm_service.LLMService.generate_support_decision",
        new_callable=AsyncMock,
        return_value=decision,
    ), TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/chat",
            json={"customer_id": "C001", "message": "What is the status of ORD-1001?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["action_taken"] == "order_status_lookup"
    assert data["escalated"] is False
    assert "ORD-1001 is currently **shipped**" in data["response"]


def test_return_request_requires_approval_and_is_idempotent() -> None:
    decision = SupportDecision(
        intent="refund_request",
        priority="medium",
        sentiment="frustrated",
        confidence=0.94,
        needs_human=False,
        suggested_action="answer",
        reasoning_summary="The customer requests a refund.",
        response="I can help with your return request.",
    )
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", groq_api_key="test-key")

    with patch(
        "app.services.llm_service.LLMService.generate_support_decision",
        new_callable=AsyncMock,
        return_value=decision,
    ), TestClient(create_app(settings)) as client:
        first = client.post(
            "/api/v1/chat",
            json={"customer_id": "C001", "message": "I would like a refund."},
        )
        conversation_id = first.json()["conversation_id"]
        second = client.post(
            "/api/v1/chat",
            json={
                "customer_id": "C001",
                "conversation_id": conversation_id,
                "message": "I would like a refund.",
            },
        )

    assert first.status_code == 200
    assert first.json()["escalated"] is True
    assert first.json()["action_taken"] == "return_request_pending_approval"
    assert "pending human approval" in first.json()["response"].lower()
    assert second.status_code == 200
    assert "found an existing return request" in second.json()["response"].lower()
