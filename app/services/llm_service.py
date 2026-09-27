import json

from groq import AsyncGroq
from pydantic import ValidationError

from app.agents.schemas import SupportDecision
from app.config import Settings
from app.core.errors import ServiceUnavailableError, UpstreamResponseError


class LLMService:
    """Service responsible for communication with the Groq API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a response from the configured Groq model."""

        if not self.client:
            raise ServiceUnavailableError("The LLM provider is not configured.")

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        try:
            completion = await self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.2,
            )
        except Exception as exc:
            raise ServiceUnavailableError("The LLM provider is temporarily unavailable.") from exc

        content = completion.choices[0].message.content

        if not content:
            raise ServiceUnavailableError("The LLM provider returned an empty response.")

        return content

    async def generate_support_decision(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> SupportDecision:
        """Generate and validate a structured support decision from Groq."""

        if not self.client:
            raise ServiceUnavailableError("The LLM provider is not configured.")

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history or [])
        messages.append({"role": "user", "content": user_message})
        try:
            completion = await self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,  # type: ignore[arg-type]
                response_format={"type": "json_object"},
                temperature=0.1,
            )
        except Exception as exc:
            raise ServiceUnavailableError("The LLM provider is temporarily unavailable.") from exc

        content = completion.choices[0].message.content
        if not isinstance(content, str) or not content:
            raise UpstreamResponseError()
        try:
            return SupportDecision.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise UpstreamResponseError() from exc

    async def close(self) -> None:
        """Close the provider client if it was configured."""

        if self.client:
            await self.client.close()
