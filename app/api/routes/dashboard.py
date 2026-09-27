"""Review queue and analytics endpoints for the portfolio dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import DashboardMetrics, TicketResponse, TicketUpdate
from app.api.dependencies import get_session
from app.models import AuditEvent, Conversation, Message, SupportTicket, SupportTicketNote

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: str | None = Query(default=None),
) -> list[TicketResponse]:
    query = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    if status:
        query = query.where(SupportTicket.status == status)
    tickets = list(await session.scalars(query))
    return [TicketResponse.model_validate(ticket) for ticket in tickets]


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    request: TicketUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TicketResponse:
    ticket = await session.get(SupportTicket, ticket_id)
    if not ticket:
        from app.core.errors import NotFoundError
        raise NotFoundError("Support ticket was not found.")
    ticket.status = request.status
    if request.assignee is not None:
        ticket.assignee = request.assignee
    if request.note:
        session.add(SupportTicketNote(ticket_id=ticket.id, author_type="human", content=request.note))
    await session.flush()
    return TicketResponse.model_validate(ticket)


@router.get("/metrics", response_model=DashboardMetrics)
async def dashboard_metrics(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardMetrics:
    conversations = int((await session.scalar(select(func.count(Conversation.id)))) or 0)
    messages = int((await session.scalar(select(func.count(Message.id)))) or 0)
    tickets = int((await session.scalar(select(func.count(SupportTicket.id)))) or 0)
    open_tickets = int((await session.scalar(
        select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(["open", "pending"]))
    )) or 0)
    escalated = int((await session.scalar(
        select(func.count(AuditEvent.id)).where(AuditEvent.event_type == "human_review_flagged")
    )) or 0)
    decisions = int((await session.scalar(
        select(func.count(AuditEvent.id)).where(AuditEvent.event_type == "support_decision_created")
    )) or 0)
    top_intents: dict[str, int] = {}
    events = await session.scalars(select(AuditEvent).where(AuditEvent.event_type == "support_decision_created"))
    import json
    for event in events:
        try:
            intent = json.loads(event.detail or "{}").get("intent", "unknown")
            top_intents[intent] = top_intents.get(intent, 0) + 1
        except json.JSONDecodeError:
            continue
    return DashboardMetrics(
        conversations=conversations, messages=messages, tickets=tickets,
        open_tickets=open_tickets, escalated_tickets=escalated,
        automation_rate=round(max(0, decisions - escalated) / decisions, 3) if decisions else 0,
        top_intents=dict(sorted(top_intents.items(), key=lambda item: item[1], reverse=True)[:5]),
    )
