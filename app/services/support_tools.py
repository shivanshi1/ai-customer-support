"""Controlled business tools available to the support agent."""

import re
from dataclasses import dataclass

from app.agents.policies import EscalationResult
from app.agents.schemas import SupportDecision
from app.models import Customer, Order
from app.repositories.support import SupportRepository

ORDER_NUMBER_PATTERN = re.compile(r"\bORD-\d+\b", re.IGNORECASE)

RETURN_POLICY = (
    "Eligible items can be submitted for review within 30 days of delivery. "
    "Return and refund requests require human approval before any refund is issued."
)
SHIPPING_POLICY = "Shipping updates are available after an order has been dispatched."


@dataclass(frozen=True)
class AutomationOutcome:
    """A customer-safe summary of a server-authorized automation workflow."""

    response_suffix: str | None = None
    action_taken: str | None = None


class SupportTools:
    """Expose typed, customer-scoped support operations to the agent."""

    def __init__(self, repository: SupportRepository) -> None:
        self.repository = repository

    async def get_customer_profile(self, customer_id: int) -> Customer | None:
        return await self.repository.get_customer_profile(customer_id)

    async def search_orders(self, customer_id: int) -> list[Order]:
        return await self.repository.search_orders(customer_id)

    async def get_order_status(self, customer_id: int, order_number: str) -> Order | None:
        return await self.repository.get_order_status(customer_id, order_number)

    def get_shipping_or_return_policy(self, topic: str) -> str:
        """Return a local policy placeholder until Phase 5 knowledge retrieval."""

        return RETURN_POLICY if topic == "return" else SHIPPING_POLICY

    async def execute_authorized_workflow(
        self,
        customer: Customer,
        conversation_id: str,
        customer_message: str,
        decision: SupportDecision,
        escalation: EscalationResult,
    ) -> AutomationOutcome:
        """Run only workflows permitted by server-side policy and the decision."""

        if decision.intent == "refund_request":
            return await self._start_return_and_ticket(
                customer, conversation_id, customer_message, decision
            )
        if escalation.escalated:
            return await self._create_escalation_ticket(
                customer, conversation_id, customer_message, decision
            )
        if decision.intent == "order_status":
            return await self._lookup_order(customer, conversation_id, customer_message)
        return AutomationOutcome()

    async def _lookup_order(
        self, customer: Customer, conversation_id: str, customer_message: str
    ) -> AutomationOutcome:
        match = ORDER_NUMBER_PATTERN.search(customer_message)
        order = (
            await self.get_order_status(customer.id, match.group().upper())
            if match
            else None
        )
        if order is None and not match:
            orders = await self.search_orders(customer.id)
            order = orders[0] if orders else None
        if not order:
            return AutomationOutcome(
                response_suffix="I could not find a matching order. Please share your order number.",
                action_taken="order_status_lookup_no_match",
            )

        await self.repository.add_automation_action(
            conversation_id,
            "order_status_lookup",
            "completed",
            f"Retrieved order {order.order_number} for the authorized customer.",
        )
        return AutomationOutcome(
            response_suffix=f"Order {order.order_number} is currently **{order.status}**.",
            action_taken="order_status_lookup",
        )

    async def _create_escalation_ticket(
        self,
        customer: Customer,
        conversation_id: str,
        customer_message: str,
        decision: SupportDecision,
    ) -> AutomationOutcome:
        ticket, created = await self.repository.create_support_ticket(
            customer.id, conversation_id, decision.priority, decision.reasoning_summary
        )
        if created:
            await self.repository.add_ticket_note(ticket.id, f"Customer message: {customer_message}")
            await self.repository.add_automation_action(
                conversation_id,
                "support_ticket_creation",
                "completed",
                f"Created ticket {ticket.id} for human review.",
            )
        return AutomationOutcome(
            response_suffix=(
                f"I created support ticket {ticket.id} for a human support specialist."
                if created
                else f"Support ticket {ticket.id} is already open for this conversation."
            ),
            action_taken="support_ticket_created" if created else "existing_support_ticket",
        )

    async def _start_return_and_ticket(
        self,
        customer: Customer,
        conversation_id: str,
        customer_message: str,
        decision: SupportDecision,
    ) -> AutomationOutcome:
        orders = await self.search_orders(customer.id)
        order = orders[0] if orders else None
        request, created = await self.repository.start_return_request(
            customer.id,
            conversation_id,
            order.id if order else None,
            customer_message,
        )
        if created:
            await self.repository.add_automation_action(
                conversation_id,
                "return_request",
                "pending_approval",
                f"Return request {request.id} is awaiting human approval.",
            )
        ticket_outcome = await self._create_escalation_ticket(
            customer, conversation_id, customer_message, decision
        )
        request_status = "created" if created else "found an existing"
        return AutomationOutcome(
            response_suffix=(
                f"I {request_status} return request {request.id}. It is pending human approval; "
                f"{ticket_outcome.response_suffix}"
            ),
            action_taken="return_request_pending_approval",
        )
