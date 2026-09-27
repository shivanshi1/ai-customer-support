import json

from app.agents.prompts import SUPPORT_SYSTEM_PROMPT
from app.agents.policies import evaluate_escalation
from app.agents.schemas import ChatResponse
from app.config import Settings
from app.repositories.support import SupportRepository
from app.services.llm_service import LLMService
from app.services.support_tools import SupportTools


class SupportAgent:
    """AI agent responsible for handling customer support requests."""

    def __init__(
        self,
        llm_service: LLMService,
        repository: SupportRepository,
        settings: Settings,
    ) -> None:
        self.llm_service = llm_service
        self.repository = repository
        self.settings = settings
        self.tools = SupportTools(repository)

    async def process_message(
        self,
        customer_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> ChatResponse:
        """Process a customer message and generate a response."""

        customer = await self.repository.get_or_create_customer(customer_id)
        conversation = await self.repository.get_or_create_conversation(customer, conversation_id)
        history = await self.repository.get_history(
            conversation.id, self.settings.chat_history_limit
        )
        await self.repository.add_message(conversation.id, "customer", message)

        decision = await self.llm_service.generate_support_decision(
            system_prompt=SUPPORT_SYSTEM_PROMPT,
            user_message=message,
            conversation_history=[
                {"role": "assistant" if item.sender == "assistant" else "user", "content": item.content}
                for item in history
            ],
        )
        escalation = evaluate_escalation(message, decision)
        outcome = await self.tools.execute_authorized_workflow(
            customer,
            conversation.id,
            message,
            decision,
            escalation,
        )
        response = self._combine_response(decision.response, outcome.response_suffix)
        await self.repository.add_message(conversation.id, "assistant", response)
        await self.repository.add_audit_event(
            conversation.id,
            "support_decision_created",
            json.dumps(
                {
                    "intent": decision.intent,
                    "priority": decision.priority,
                    "sentiment": decision.sentiment,
                    "confidence": decision.confidence,
                    "needs_human": decision.needs_human,
                    "suggested_action": decision.suggested_action,
                    "reasoning_summary": decision.reasoning_summary,
                }
            ),
        )
        if escalation.escalated:
            await self.repository.add_audit_event(
                conversation.id,
                "human_review_flagged",
                json.dumps({"reasons": escalation.reasons}),
            )

        return ChatResponse(
            conversation_id=conversation.id,
            intent=decision.intent,
            priority=decision.priority,
            sentiment=decision.sentiment,
            confidence=decision.confidence,
            needs_human=decision.needs_human or escalation.escalated,
            suggested_action=decision.suggested_action,
            response=response,
            action_taken=outcome.action_taken or (
                "human_review_flagged" if escalation.escalated else None
            ),
            escalated=escalation.escalated,
            escalation_reasons=escalation.reasons,
        )

    @staticmethod
    def _combine_response(response: str, suffix: str | None) -> str:
        """Append only server-verified action results to the model response."""

        return f"{response}\n\n{suffix}" if suffix else response
