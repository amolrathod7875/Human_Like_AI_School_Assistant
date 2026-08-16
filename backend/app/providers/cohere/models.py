from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class LLMMessage(BaseModel):
    """A single conversation message sent to the LLM."""

    model_config = ConfigDict(extra="ignore")

    role: str  # system | user | assistant | tool
    content: str
    name: Optional[str] = None


class LLMToolDefinition(BaseModel):
    """A tool the model is allowed to call."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str
    parameters: Dict[str, Any] = {}


class LLMToolCall(BaseModel):
    """A tool call produced by the model."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    name: str
    arguments: Dict[str, Any] = {}


class LLMRequest(BaseModel):
    """Normalized generation request.

    Contains everything the model needs for prompting. It must NOT contain
    secrets (API keys, tokens, private keys).
    """

    model_config = ConfigDict(extra="ignore")

    messages: List[LLMMessage]
    system_instructions: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    tool_definitions: Optional[List[LLMToolDefinition]] = None
    language_instruction: Optional[str] = None
    persona_instruction: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = None


class LLMResponse(BaseModel):
    """Normalized generation response across providers."""

    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None
    tool_calls: List[LLMToolCall] = []
    finish_reason: Optional[str] = None
