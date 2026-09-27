from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Request body for a customer support conversation."""

    customer_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of the customer.",
    )

    message: str = Field(
        ...,
        min_length=1,
        description="Customer's support message.",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Existing conversation identifier; omit to start a new conversation.",
    )


class ChatResponse(BaseModel):
    """Response returned by the customer support API."""

    conversation_id: str
    intent: Literal["password_reset", "order_status", "refund_request", "billing_issue", "product_question", "complaint", "technical_issue", "general_inquiry"]
    priority: Literal["low", "medium", "high", "urgent"]
    sentiment: Literal["positive", "neutral", "frustrated"]
    confidence: float = Field(ge=0, le=1)
    needs_human: bool
    suggested_action: Literal["answer", "fetch_order", "create_ticket", "request_more_details", "escalate"]
    response: str
    action_taken: str | None = None
    escalated: bool = False
    escalation_reasons: list[str] = Field(default_factory=list)
    sources: list["KnowledgeSource"] = Field(default_factory=list)


class KnowledgeSource(BaseModel):
    """A source used to ground a customer answer."""

    title: str
    source: str
    excerpt: str


class SupportDecision(BaseModel):
    """Validated structured output produced by the support model."""

    intent: Literal["password_reset", "order_status", "refund_request", "billing_issue", "product_question", "complaint", "technical_issue", "general_inquiry"]
    priority: Literal["low", "medium", "high", "urgent"]
    sentiment: Literal["positive", "neutral", "frustrated"]
    confidence: float = Field(ge=0, le=1)
    needs_human: bool
    suggested_action: Literal["answer", "fetch_order", "create_ticket", "request_more_details", "escalate"]
    reasoning_summary: str = Field(min_length=1, max_length=500)
    response: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    """A persisted conversation message."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    sender: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    """A compact representation for customer conversation lists."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    subject: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    """A conversation and its persisted message history."""

    messages: list[MessageResponse]
