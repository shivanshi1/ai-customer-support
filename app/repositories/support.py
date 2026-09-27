"""Persistence operations for conversations and seed data."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import (
    AuditEvent,
    AutomationAction,
    Conversation,
    Customer,
    Message,
    Order,
    OrderItem,
    ReturnRequest,
    SupportTicket,
    SupportTicketNote,
    utc_now,
)


class SupportRepository:
    """Encapsulate support-domain reads and writes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_customer(self, external_id: str) -> Customer:
        customer = await self.session.scalar(
            select(Customer).where(Customer.external_id == external_id)
        )
        if customer:
            return customer

        customer = Customer(external_id=external_id, name=f"Customer {external_id}")
        self.session.add(customer)
        await self.session.flush()
        return customer

    async def get_or_create_conversation(
        self, customer: Customer, conversation_id: str | None
    ) -> Conversation:
        if conversation_id:
            conversation = await self.session.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.customer_id == customer.id,
                )
            )
            if not conversation:
                raise NotFoundError("Conversation was not found for this customer.")
            return conversation

        conversation = Conversation(customer_id=customer.id)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def add_message(self, conversation_id: str, sender: str, content: str) -> Message:
        message = Message(conversation_id=conversation_id, sender=sender, content=content)
        self.session.add(message)
        conversation = await self.session.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = utc_now()
        await self.session.flush()
        return message

    async def get_history(self, conversation_id: str, limit: int) -> list[Message]:
        result = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(result)))

    async def add_audit_event(
        self, conversation_id: str, event_type: str, detail: str | None = None
    ) -> None:
        self.session.add(
            AuditEvent(conversation_id=conversation_id, event_type=event_type, detail=detail)
        )

    async def get_customer_profile(self, customer_id: int) -> Customer | None:
        """Return a customer profile by its internal, already-authorized ID."""

        return await self.session.get(Customer, customer_id)

    async def search_orders(self, customer_id: int) -> list[Order]:
        """Return orders belonging only to the authorized customer."""

        result = await self.session.scalars(
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )
        return list(result)

    async def get_order_status(self, customer_id: int, order_number: str) -> Order | None:
        """Look up an order only when it belongs to the requesting customer."""

        return await self.session.scalar(
            select(Order).where(
                Order.customer_id == customer_id,
                Order.order_number == order_number,
            )
        )

    async def create_support_ticket(
        self,
        customer_id: int,
        conversation_id: str,
        priority: str,
        summary: str,
    ) -> tuple[SupportTicket, bool]:
        """Create one open ticket per conversation, returning whether it is new."""

        existing = await self.session.scalar(
            select(SupportTicket).where(
                SupportTicket.customer_id == customer_id,
                SupportTicket.conversation_id == conversation_id,
                SupportTicket.status.in_(["open", "pending"]),
            )
        )
        if existing:
            return existing, False

        ticket = SupportTicket(
            customer_id=customer_id,
            conversation_id=conversation_id,
            priority=priority,
            summary=summary,
        )
        self.session.add(ticket)
        await self.session.flush()
        return ticket, True

    async def add_ticket_note(self, ticket_id: str, content: str) -> SupportTicketNote:
        """Record an automation-authored note on a support ticket."""

        note = SupportTicketNote(ticket_id=ticket_id, content=content)
        self.session.add(note)
        await self.session.flush()
        return note

    async def start_return_request(
        self,
        customer_id: int,
        conversation_id: str,
        order_id: int | None,
        reason: str,
    ) -> tuple[ReturnRequest, bool]:
        """Create an idempotent return request in a human-approval state."""

        existing = await self.session.scalar(
            select(ReturnRequest).where(
                ReturnRequest.customer_id == customer_id,
                ReturnRequest.conversation_id == conversation_id,
                ReturnRequest.status == "pending_approval",
            )
        )
        if existing:
            return existing, False

        request = ReturnRequest(
            customer_id=customer_id,
            conversation_id=conversation_id,
            order_id=order_id,
            status="pending_approval",
            reason=reason,
        )
        self.session.add(request)
        await self.session.flush()
        return request, True

    async def add_automation_action(
        self,
        conversation_id: str,
        action_type: str,
        status: str,
        detail: str | None = None,
    ) -> AutomationAction:
        """Record a system action and its final or pending state."""

        action = AutomationAction(
            conversation_id=conversation_id,
            action_type=action_type,
            status=status,
            detail=detail,
        )
        self.session.add(action)
        await self.session.flush()
        return action

    async def list_conversations(self, customer_external_id: str) -> list[Conversation]:
        result = await self.session.scalars(
            select(Conversation)
            .join(Customer)
            .where(Customer.external_id == customer_external_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result)

    async def get_conversation(self, customer_external_id: str, conversation_id: str) -> Conversation:
        conversation = await self.session.scalar(
            select(Conversation)
            .join(Customer)
            .where(
                Conversation.id == conversation_id,
                Customer.external_id == customer_external_id,
            )
        )
        if not conversation:
            raise NotFoundError("Conversation was not found for this customer.")
        return conversation

    async def get_messages(self, conversation_id: str) -> list[Message]:
        result = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result)

    async def seed_demo_data(self) -> None:
        """Insert a small idempotent dataset for local demonstrations."""

        existing = await self.session.scalar(select(Customer).where(Customer.external_id == "C001"))
        if existing:
            return

        customer = Customer(
            external_id="C001",
            name="Aarav Sharma",
            email="aarav.sharma@example.test",
        )
        self.session.add(customer)
        await self.session.flush()
        order = Order(
            customer_id=customer.id,
            order_number="ORD-1001",
            status="shipped",
            total_cents=7999,
        )
        self.session.add(order)
        await self.session.flush()
        self.session.add(
            OrderItem(
                order_id=order.id,
                product_name="Wireless Noise-Cancelling Headphones",
                quantity=1,
                unit_price_cents=7999,
            )
        )
