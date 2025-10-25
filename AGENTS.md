# AI Agents Architecture

Guide for building AI agent systems on top of the FastAPI Backend Template.

## Overview

This document outlines patterns and best practices for integrating AI agents, LLM-powered features, and autonomous agent systems into this FastAPI backend template. The template's modular architecture, security features, and observability make it well-suited for production AI agent deployments.

## Backend Documentation

For comprehensive understanding of the FastAPI backend architecture that underlies these AI agent patterns, see **[docs/BACKEND_GUIDE.md](docs/BACKEND_GUIDE.md)**. That guide covers:

- Architecture overview and component design
- Factory pattern, middleware pipeline, configuration management
- Security implementation (authentication, rate limiting, security headers)
- Database integration with SQLAlchemy 2.0 async
- Logging, observability, and request tracing
- Deployment and production operations

The patterns in this document build upon the backend architecture described in the Backend Guide.

## Table of Contents

- [Architecture Patterns](#architecture-patterns)
- [Agent Service Layer](#agent-service-layer)
- [Conversation Management](#conversation-management)
- [Tool Integration](#tool-integration)
- [Security Considerations](#security-considerations)
- [Rate Limiting for AI Endpoints](#rate-limiting-for-ai-endpoints)
- [Monitoring & Observability](#monitoring--observability)
- [Example Implementations](#example-implementations)

## Architecture Patterns

### 1. Agent Service Pattern

Create dedicated services for agent functionality in [src/app/services/](src/app/services/):

```python
# src/app/services/agent.py
import structlog
from typing import AsyncIterator
from app.core.config import AppSettings

logger = structlog.get_logger(__name__)

class AgentService:
    """Manages AI agent interactions and orchestration."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.llm_client = self._initialize_llm_client()

    async def process_message(
        self,
        user_id: str,
        message: str,
        context: dict | None = None
    ) -> dict:
        """Process a user message through the agent."""
        logger.info(
            "agent.process_message.start",
            user_id=user_id,
            message_length=len(message)
        )

        # Agent processing logic
        response = await self._execute_agent_chain(message, context)

        logger.info(
            "agent.process_message.complete",
            user_id=user_id,
            tokens_used=response.get("usage", {})
        )

        return response

    async def stream_response(
        self,
        message: str,
        context: dict | None = None
    ) -> AsyncIterator[str]:
        """Stream agent responses for real-time UX."""
        async for chunk in self._stream_agent_chain(message, context):
            yield chunk
```

### 2. Tool/Function Calling Pattern

Implement agent tools as structured services:

```python
# src/app/services/agent_tools.py
from typing import Protocol
import structlog

logger = structlog.get_logger(__name__)

class AgentTool(Protocol):
    """Protocol for agent tool implementations."""

    name: str
    description: str

    async def execute(self, **kwargs) -> dict:
        """Execute the tool with given parameters."""
        ...

class WebSearchTool:
    """Tool for web search capability."""

    name = "web_search"
    description = "Search the web for current information"

    async def execute(self, query: str, max_results: int = 5) -> dict:
        logger.info("agent.tool.web_search", query=query)
        # Implementation
        return {"results": [...]}

class DatabaseQueryTool:
    """Tool for database queries."""

    name = "database_query"
    description = "Query application database"

    async def execute(self, query: str) -> dict:
        logger.info("agent.tool.database_query", query=query)
        # Implementation with proper access control
        return {"results": [...]}
```

## Agent Service Layer

### Service Structure

```
src/app/services/
├── agent.py              # Core agent orchestration
├── agent_tools.py        # Tool implementations
├── conversation.py       # Conversation/session management
├── prompt_manager.py     # Prompt templates and versioning
└── llm_provider.py       # LLM client abstraction
```

### LLM Provider Abstraction

Create provider-agnostic LLM clients:

```python
# src/app/services/llm_provider.py
from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> dict:
        """Generate completion."""
        pass

    @abstractmethod
    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """Stream completion."""
        pass

class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation."""

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, messages: list[dict], **kwargs) -> dict:
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            **kwargs
        )
        return self._format_response(response)

class OpenAIProvider(LLMProvider):
    """OpenAI implementation."""
    # Similar implementation
```

## Conversation Management

### Session Storage

Leverage the template's Redis integration (Phase 2) for conversation state:

```python
# src/app/services/conversation.py
import structlog
from datetime import timedelta
from app.dependencies.redis import get_redis_client

logger = structlog.get_logger(__name__)

class ConversationManager:
    """Manage conversation history and context."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = timedelta(hours=24)

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> None:
        """Store a conversation message."""
        key = f"conversation:{session_id}"
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.redis.rpush(key, orjson.dumps(message))
        await self.redis.expire(key, self.ttl)

        logger.info(
            "conversation.message_saved",
            session_id=session_id,
            role=role
        )

    async def get_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> list[dict]:
        """Retrieve conversation history."""
        key = f"conversation:{session_id}"
        messages = await self.redis.lrange(key, -limit, -1)
        return [orjson.loads(msg) for msg in messages]

    async def clear_session(self, session_id: str) -> None:
        """Clear conversation history."""
        await self.redis.delete(f"conversation:{session_id}")
        logger.info("conversation.session_cleared", session_id=session_id)
```

### Context Window Management

```python
# src/app/services/context_manager.py
class ContextManager:
    """Manage conversation context and token limits."""

    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens

    def truncate_messages(
        self,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> list[dict]:
        """Truncate messages to fit context window."""
        # Token counting and truncation logic
        # Keep system prompt, recent messages, and important context
        return truncated_messages

    def extract_relevant_context(
        self,
        messages: list[dict],
        query: str
    ) -> list[dict]:
        """Extract most relevant messages for current query."""
        # Semantic search or relevance scoring
        return relevant_messages
```

## Tool Integration

### Tool Registry

```python
# src/app/services/tool_registry.py
import structlog
from typing import Callable

logger = structlog.get_logger(__name__)

class ToolRegistry:
    """Central registry for agent tools."""

    def __init__(self):
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        """Register a new tool."""
        self._tools[tool.name] = tool
        logger.info("tool.registered", tool_name=tool.name)

    def get_tool(self, name: str) -> AgentTool | None:
        """Get tool by name."""
        return self._tools.get(name)

    def get_tool_schemas(self) -> list[dict]:
        """Get OpenAPI schemas for all tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(
        self,
        tool_name: str,
        user_id: str,
        **kwargs
    ) -> dict:
        """Execute a tool with security checks."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        # Check user permissions
        if not await self._check_permissions(user_id, tool_name):
            raise PermissionError(f"User {user_id} cannot use {tool_name}")

        logger.info(
            "tool.execution.start",
            tool_name=tool_name,
            user_id=user_id
        )

        result = await tool.execute(**kwargs)

        logger.info(
            "tool.execution.complete",
            tool_name=tool_name,
            user_id=user_id
        )

        return result
```

## Security Considerations

### 1. User Authentication & Authorization

Leverage the template's JWT middleware for agent endpoints:

```python
# src/app/api/routes/agent.py
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.services.agent import AgentService

router = APIRouter(prefix="/agent", tags=["AI Agent"])

@router.post("/chat")
async def chat(
    message: str,
    user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """Authenticated agent chat endpoint."""
    response = await agent_service.process_message(
        user_id=user["user_id"],
        message=message
    )
    return response
```

### 2. Input Validation & Sanitization

```python
# src/app/schemas/agent.py
from pydantic import BaseModel, Field, validator

class AgentMessageRequest(BaseModel):
    """Validated agent message request."""

    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str | None = Field(None, max_length=100)
    context: dict | None = None

    @validator("message")
    def sanitize_message(cls, v: str) -> str:
        """Sanitize user input."""
        # Remove potential injection attempts
        # Block suspicious patterns
        return v.strip()

    @validator("context")
    def validate_context(cls, v: dict | None) -> dict | None:
        """Validate context structure."""
        if v is None:
            return v
        # Validate context doesn't contain sensitive data
        # Limit context size
        return v
```

### 3. Tool Execution Sandboxing

```python
# src/app/services/sandbox.py
import asyncio
from typing import Any

class ToolSandbox:
    """Sandbox for safe tool execution."""

    async def execute_with_timeout(
        self,
        func: Callable,
        timeout: int = 30,
        **kwargs
    ) -> Any:
        """Execute tool with timeout and resource limits."""
        try:
            result = await asyncio.wait_for(
                func(**kwargs),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error("tool.execution.timeout", func=func.__name__)
            raise
        except Exception as e:
            logger.error(
                "tool.execution.error",
                func=func.__name__,
                error=str(e)
            )
            raise
```

### 4. Prompt Injection Protection

```python
# src/app/services/security.py
import re

class PromptSecurityValidator:
    """Validate prompts for injection attempts."""

    INJECTION_PATTERNS = [
        r"ignore previous instructions",
        r"system:\s*",
        r"<\|im_start\|>",
        # Add more patterns
    ]

    def validate(self, message: str) -> bool:
        """Check for prompt injection attempts."""
        message_lower = message.lower()

        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, message_lower):
                logger.warning(
                    "prompt.injection.detected",
                    pattern=pattern
                )
                return False

        return True
```

## Rate Limiting for AI Endpoints

### Tiered Rate Limits

Extend the template's rate limiting for AI-specific limits:

```python
# In SecuritySettings (src/app/core/config.py)
class AIRateLimitSettings(BaseSettings):
    """AI-specific rate limiting configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_"
    )

    # Per-tier limits for AI calls
    free_tier_rpm: int = 10  # Requests per minute
    free_tier_tpm: int = 50000  # Tokens per minute

    basic_tier_rpm: int = 30
    basic_tier_tpm: int = 200000

    pro_tier_rpm: int = 100
    pro_tier_tpm: int = 1000000

    # Cost tracking
    enable_cost_tracking: bool = True
    max_daily_cost_per_user: float = 10.0  # USD
```

### Token-based Rate Limiting

```python
# src/app/middleware/ai_rate_limit.py
from starlette.middleware.base import BaseHTTPMiddleware

class AITokenRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit based on AI token usage."""

    async def dispatch(self, request, call_next):
        if not self._is_ai_endpoint(request.url.path):
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        user_tier = getattr(request.state, "user_tier", "free")

        # Check token budget
        available_tokens = await self._get_available_tokens(
            user_id,
            user_tier
        )

        if available_tokens <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Token quota exceeded",
                    "reset_at": await self._get_reset_time(user_id)
                }
            )

        response = await call_next(request)

        # Track token usage from response
        if hasattr(request.state, "tokens_used"):
            await self._decrement_tokens(user_id, request.state.tokens_used)

        return response
```

## Monitoring & Observability

### Agent-Specific Metrics

```python
# src/app/services/agent_metrics.py
import structlog
from prometheus_client import Counter, Histogram, Gauge

# Metrics
agent_requests_total = Counter(
    "agent_requests_total",
    "Total agent requests",
    ["user_tier", "tool_name", "status"]
)

agent_latency_seconds = Histogram(
    "agent_latency_seconds",
    "Agent response latency",
    ["user_tier", "has_tools"]
)

agent_tokens_used = Counter(
    "agent_tokens_used_total",
    "Total tokens used",
    ["user_tier", "model"]
)

agent_cost_usd = Counter(
    "agent_cost_usd_total",
    "Total cost in USD",
    ["user_tier", "model"]
)

active_conversations = Gauge(
    "agent_active_conversations",
    "Number of active conversations"
)

class AgentMetricsCollector:
    """Collect and export agent metrics."""

    def record_request(
        self,
        user_tier: str,
        tool_name: str | None,
        status: str,
        latency: float,
        tokens: int,
        cost: float,
        model: str
    ) -> None:
        """Record agent request metrics."""
        agent_requests_total.labels(
            user_tier=user_tier,
            tool_name=tool_name or "none",
            status=status
        ).inc()

        agent_latency_seconds.labels(
            user_tier=user_tier,
            has_tools=bool(tool_name)
        ).observe(latency)

        agent_tokens_used.labels(
            user_tier=user_tier,
            model=model
        ).inc(tokens)

        agent_cost_usd.labels(
            user_tier=user_tier,
            model=model
        ).inc(cost)
```

### Structured Logging for Agent Operations

```python
# Use the template's structlog for rich agent logging
import structlog

logger = structlog.get_logger(__name__)

# Log agent interactions
logger.info(
    "agent.interaction",
    user_id=user_id,
    session_id=session_id,
    message_length=len(message),
    tools_used=["web_search", "calculator"],
    tokens_used=1234,
    cost_usd=0.0123,
    latency_ms=456.78,
    model="claude-3-5-sonnet-20241022"
)

# Log tool executions
logger.info(
    "agent.tool.execution",
    tool_name="database_query",
    user_id=user_id,
    parameters={"query": "SELECT ..."},
    result_size=150,
    latency_ms=23.45
)

# Log errors with context
logger.error(
    "agent.error",
    error_type="RateLimitExceeded",
    user_id=user_id,
    user_tier="free",
    requested_tokens=10000,
    available_tokens=500
)
```

## Example Implementations

### 1. Simple Chat Endpoint

```python
# src/app/api/routes/agent.py
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.agent import AgentMessageRequest, AgentMessageResponse
from app.services.agent import AgentService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/agent", tags=["AI Agent"])

@router.post("/chat", response_model=AgentMessageResponse)
async def chat(
    request: AgentMessageRequest,
    user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """
    Chat with the AI agent.

    Requires authentication. Rate limited based on user tier.
    """
    try:
        response = await agent_service.process_message(
            user_id=user["user_id"],
            message=request.message,
            session_id=request.session_id,
            context=request.context
        )
        return response
    except Exception as e:
        logger.error("chat.error", error=str(e), user_id=user["user_id"])
        raise HTTPException(status_code=500, detail="Agent processing failed")
```

### 2. Streaming Response

```python
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(
    request: AgentMessageRequest,
    user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """Stream agent responses for real-time UX."""

    async def generate():
        async for chunk in agent_service.stream_response(
            user_id=user["user_id"],
            message=request.message,
            session_id=request.session_id
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

### 3. Tool Execution Endpoint

```python
@router.post("/tools/{tool_name}")
async def execute_tool(
    tool_name: str,
    parameters: dict,
    user: dict = Depends(get_current_user),
    tool_registry: ToolRegistry = Depends()
):
    """
    Execute a specific agent tool.

    Requires authentication and appropriate permissions.
    """
    try:
        result = await tool_registry.execute_tool(
            tool_name=tool_name,
            user_id=user["user_id"],
            **parameters
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### 4. Conversation Management

```python
@router.get("/conversations/{session_id}")
async def get_conversation(
    session_id: str,
    user: dict = Depends(get_current_user),
    conv_manager: ConversationManager = Depends()
):
    """Retrieve conversation history."""

    # Verify user owns this session
    if not await conv_manager.verify_ownership(session_id, user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    history = await conv_manager.get_history(session_id)
    return {"session_id": session_id, "messages": history}

@router.delete("/conversations/{session_id}")
async def clear_conversation(
    session_id: str,
    user: dict = Depends(get_current_user),
    conv_manager: ConversationManager = Depends()
):
    """Clear conversation history."""

    if not await conv_manager.verify_ownership(session_id, user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    await conv_manager.clear_session(session_id)
    return {"status": "cleared"}
```

## Configuration

### Environment Variables

Add AI-specific configuration to `.env`:

```bash
# AI Agent Configuration
AI_PROVIDER=anthropic  # anthropic, openai, azure
AI_API_KEY=your-api-key-here
AI_MODEL=claude-3-5-sonnet-20241022
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.7

# Rate Limiting
AI_FREE_TIER_RPM=10
AI_FREE_TIER_TPM=50000
AI_BASIC_TIER_RPM=30
AI_BASIC_TIER_TPM=200000
AI_PRO_TIER_RPM=100
AI_PRO_TIER_TPM=1000000

# Cost Management
AI_ENABLE_COST_TRACKING=true
AI_MAX_DAILY_COST_PER_USER=10.0

# Features
AI_ENABLE_STREAMING=true
AI_ENABLE_TOOLS=true
AI_ENABLE_CONVERSATION_MEMORY=true
AI_CONVERSATION_TTL_HOURS=24
```

### Settings Class

```python
# src/app/core/config.py
class AISettings(BaseSettings):
    """AI agent configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_"
    )

    provider: str = "anthropic"
    api_key: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 0.7

    enable_streaming: bool = True
    enable_tools: bool = True
    enable_conversation_memory: bool = True
    conversation_ttl_hours: int = 24

    # Rate limiting
    free_tier_rpm: int = 10
    free_tier_tpm: int = 50000

    # Cost management
    enable_cost_tracking: bool = True
    max_daily_cost_per_user: float = 10.0

@lru_cache
def get_ai_settings() -> AISettings:
    """Get cached AI settings."""
    return AISettings()
```

## Testing

### Unit Tests for Agent Service

```python
# tests/test_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.agent import AgentService

@pytest.mark.asyncio
async def test_agent_process_message(agent_service):
    """Test basic message processing."""
    response = await agent_service.process_message(
        user_id="test-user",
        message="Hello, agent!"
    )

    assert response is not None
    assert "content" in response
    assert response["tokens_used"] > 0

@pytest.mark.asyncio
async def test_agent_with_tools(agent_service, tool_registry):
    """Test agent with tool execution."""
    with patch.object(tool_registry, "execute_tool") as mock_execute:
        mock_execute.return_value = {"result": "success"}

        response = await agent_service.process_message(
            user_id="test-user",
            message="Search for Python tutorials"
        )

        assert mock_execute.called

@pytest.mark.asyncio
async def test_rate_limiting(client, mock_user):
    """Test AI endpoint rate limiting."""
    # Make requests up to limit
    for _ in range(10):
        response = await client.post(
            "/api/v1/agent/chat",
            json={"message": "test"},
            headers={"Authorization": f"Bearer {mock_user['token']}"}
        )
        assert response.status_code == 200

    # Next request should be rate limited
    response = await client.post(
        "/api/v1/agent/chat",
        json={"message": "test"},
        headers={"Authorization": f"Bearer {mock_user['token']}"}
    )
    assert response.status_code == 429
```

### Integration Tests

```python
# tests/integration/test_agent_flow.py
@pytest.mark.asyncio
async def test_full_conversation_flow(client, mock_user):
    """Test complete conversation flow."""
    # Start conversation
    response = await client.post(
        "/api/v1/agent/chat",
        json={"message": "Start new project"},
        headers={"Authorization": f"Bearer {mock_user['token']}"}
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Continue conversation
    response = await client.post(
        "/api/v1/agent/chat",
        json={
            "message": "Add user authentication",
            "session_id": session_id
        },
        headers={"Authorization": f"Bearer {mock_user['token']}"}
    )
    assert response.status_code == 200

    # Retrieve history
    response = await client.get(
        f"/api/v1/agent/conversations/{session_id}",
        headers={"Authorization": f"Bearer {mock_user['token']}"}
    )
    assert response.status_code == 200
    assert len(response.json()["messages"]) >= 2
```

## Best Practices

### 1. Always Authenticate Agent Endpoints
- Use JWT middleware for all agent routes
- Implement proper authorization checks for tool access
- Track usage per user for billing/quotas

### 2. Implement Comprehensive Rate Limiting
- Use token-based limits in addition to request limits
- Tier limits based on user subscription level
- Monitor and alert on quota violations

### 3. Log Everything
- Use structured logging for all agent interactions
- Track token usage, costs, and latency
- Log tool executions with parameters (excluding sensitive data)

### 4. Handle Failures Gracefully
- Implement retries with exponential backoff for LLM calls
- Provide meaningful error messages to users
- Fall back to simpler responses on tool failures

### 5. Optimize Context Management
- Truncate old messages to fit context windows
- Use semantic search to retrieve relevant history
- Cache common prompts and responses

### 6. Monitor Costs Closely
- Track per-user and per-endpoint costs
- Set up alerts for unusual spending patterns
- Implement daily/monthly budget caps

### 7. Security First
- Validate and sanitize all inputs
- Check for prompt injection attempts
- Sandbox tool executions
- Never expose raw LLM API keys to frontend

## Scaling AI Agent Systems

**NEW**: Leverage Phase 4 scaling architecture for high-traffic AI agent deployments.

AI agent systems have unique scaling challenges beyond traditional web applications: long-running LLM API calls, stateful conversations, and resource-intensive operations. This section shows how to apply the backend's [Phase 4 scaling architecture](docs/BACKEND_GUIDE.md#phase-4-scaling-architecture-) to AI agent workloads.

### Unique Challenges of Scaling AI Agents

1. **Long-running requests**: LLM API calls can take 5-30 seconds (or more with tool use)
2. **Conversation state**: Multi-turn conversations require session management
3. **Rate limits**: External LLM API quotas and rate limits
4. **Cost management**: Per-request costs for LLM inference
5. **Streaming responses**: Real-time token streaming for better UX
6. **Tool execution**: Async operations that extend request duration

### Scaling Strategy by Traffic Level

#### Low Traffic (< 100 concurrent users)

**Recommended**: Level 1 (Multi-Worker) + Async I/O

```bash
# Single server, 4 workers
uvicorn app.main:create_app --factory --workers 4 --port 8000
```

**Why it works**:
- FastAPI's async/await efficiently handles many concurrent LLM API calls
- Workers utilize multiple CPU cores for non-I/O work
- Simple to deploy and monitor

**Optimization tips**:
- Use streaming responses to provide immediate feedback
- Cache common prompts and responses in Redis (Phase 2)
- Set aggressive timeouts (30-60s) to prevent hung requests

#### Medium Traffic (100-1000 concurrent users)

**Recommended**: Level 2 (Gunicorn) + Level 3 (Background Tasks)

```bash
# gunicorn.conf.py
workers = 8  # Adjust based on CPU cores
timeout = 90  # Allow time for LLM API calls
graceful_timeout = 120  # Extra time for cleanup
```

**Key patterns**:

**1. Offload heavy operations to background tasks:**
```python
# API endpoint (fast response)
@router.post("/agent/analyze")
async def analyze_document(
    document_id: int,
    task_service = Depends(get_task_service)
):
    # Enqueue background task
    task_id = await task_service.enqueue_task(
        "analyze_document",
        document_id=document_id
    )

    return {"task_id": task_id, "status": "processing"}

# Background task (RQ worker)
@register_task("analyze_document")
def analyze_document_task(document_id: int) -> dict:
    # Long-running LLM analysis (minutes)
    document = load_document(document_id)
    analysis = llm_client.analyze(document, timeout=300)
    save_analysis(document_id, analysis)
    return {"document_id": document_id, "analysis": analysis}
```

**2. Separate sync endpoints from async tasks:**
```python
# Quick interactions: Synchronous API
POST /agent/chat          # < 10s response time
GET /agent/history        # < 1s response time

# Heavy processing: Background tasks
POST /agent/analyze       # Returns task_id immediately
POST /agent/summarize     # Long-running operation
GET /tasks/{task_id}      # Check status
```

**3. Implement conversation streaming with timeout protection:**
```python
@router.post("/agent/chat/stream")
async def chat_stream(message: str, session_id: str):
    async def generate():
        try:
            async with asyncio.timeout(30):  # 30s timeout
                async for chunk in agent_service.stream_response(message):
                    yield f"data: {chunk}\n\n"
        except asyncio.TimeoutError:
            yield "data: [TIMEOUT] Response generation exceeded time limit\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

#### High Traffic (1000+ concurrent users)

**Recommended**: Level 4 (Horizontal Scaling) + All Previous Levels

**Architecture**:
```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │   (nginx/k8s)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
         │ Node 1  │    │ Node 2  │   │ Node 3  │
         │ 8 workers│   │ 8 workers│  │ 8 workers│
         └────┬────┘    └────┬────┘   └────┬────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │  Shared Redis   │
                    │  - Sessions     │
                    │  - Cache        │
                    │  - Task Queue   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  RQ Workers     │
                    │  (10+ workers)  │
                    └─────────────────┘
```

**Critical patterns**:

**1. Shared session state (Redis):**
```python
# Don't: In-memory sessions (breaks with multiple nodes)
sessions = {}  # ❌ Not shared across nodes

# Do: Redis-backed sessions
class ConversationManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_conversation(self, session_id: str) -> list:
        data = await self.redis.get(f"conv:{session_id}")
        return json.loads(data) if data else []

    async def add_message(self, session_id: str, message: dict):
        conv = await self.get_conversation(session_id)
        conv.append(message)
        await self.redis.setex(
            f"conv:{session_id}",
            3600,  # 1 hour TTL
            json.dumps(conv)
        )
```

**2. LLM API rate limit management:**
```python
# Distribute requests across multiple API keys
class LLMClientPool:
    def __init__(self, api_keys: list[str]):
        self.clients = [AnthropicClient(key) for key in api_keys]
        self.current_index = 0

    def get_client(self) -> AnthropicClient:
        # Round-robin across API keys
        client = self.clients[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.clients)
        return client

# Usage
llm_pool = LLMClientPool(settings.llm_api_keys)
response = await llm_pool.get_client().chat(message)
```

**3. Response caching for common queries:**
```python
from functools import lru_cache
import hashlib

async def get_agent_response(prompt: str, context: dict) -> str:
    # Generate cache key
    cache_key = f"response:{hashlib.sha256(prompt.encode()).hexdigest()}"

    # Check cache
    cached = await redis.get(cache_key)
    if cached:
        logger.info("agent.cache_hit", prompt_hash=cache_key)
        return cached.decode()

    # Generate response
    response = await llm_client.generate(prompt, context)

    # Cache for 1 hour
    await redis.setex(cache_key, 3600, response)

    return response
```

**4. Database connection pooling adjustment:**
```python
# config.py
import multiprocessing

# Calculate connections per node
workers_per_node = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2))
nodes = int(os.getenv("NODE_COUNT", 1))
total_workers = workers_per_node * nodes

# Adjust pool size to avoid exhausting database connections
# Typical: 100 max connections / (workers × nodes)
database_pool_size = max(3, 100 // total_workers)
database_max_overflow = database_pool_size * 2

DATABASE_URL = (
    f"postgresql+asyncpg://...?"
    f"pool_size={database_pool_size}&"
    f"max_overflow={database_max_overflow}"
)
```

### Deployment Patterns

#### Pattern 1: Dedicated Worker Pools

Separate API servers from background task workers:

```yaml
# docker-compose.prod.yml
services:
  # API servers (handle HTTP requests)
  api:
    image: my-agent-api:latest
    command: gunicorn app.main:create_app --factory -c gunicorn.conf.py
    deploy:
      replicas: 3
    environment:
      - ENABLE_BACKGROUND_TASKS=false  # Don't process tasks

  # Task workers (process background jobs)
  worker:
    image: my-agent-api:latest
    command: rq worker default high priority --url redis://redis:6379/1
    deploy:
      replicas: 10  # More workers for heavy processing
    environment:
      - WORKER_TYPE=background
```

#### Pattern 2: Priority Queues

Prioritize interactive requests over batch processing:

```python
# High priority: Interactive chat (< 10s)
task_service.enqueue_task(
    "chat_response",
    message=message,
    queue="high"  # Processed first
)

# Normal priority: Document analysis (< 1 min)
task_service.enqueue_task(
    "analyze_document",
    document_id=doc_id,
    queue="default"
)

# Low priority: Batch summarization (can take hours)
task_service.enqueue_task(
    "batch_summarize",
    document_ids=doc_ids,
    queue="low"
)
```

Start workers for each queue:
```bash
# High-priority workers (more of these)
rq worker high --url redis://redis:6379/1 &
rq worker high --url redis://redis:6379/1 &
rq worker high --url redis://redis:6379/1 &

# Normal priority workers
rq worker default --url redis://redis:6379/1 &

# Low priority workers
rq worker low --url redis://redis:6379/1 &
```

#### Pattern 3: Kubernetes Auto-Scaling for AI Workloads

```yaml
# deployment/plugins/kubernetes/manifests/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  # Scale based on request queue depth
  - type: Pods
    pods:
      metric:
        name: http_request_queue_depth
      target:
        type: AverageValue
        averageValue: "10"  # Queue depth per pod

  # Also scale on memory (LLM responses can be large)
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70

  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60  # Quick scale-up
    scaleDown:
      stabilizationWindowSeconds: 600  # Slow scale-down (10 min)
```

### Monitoring AI Agent Performance

**Key metrics to track**:

```python
from prometheus_client import Histogram, Counter, Gauge

# LLM API call duration
llm_request_duration = Histogram(
    'agent_llm_request_duration_seconds',
    'Time spent calling LLM API',
    ['model', 'endpoint']
)

# Token usage (cost tracking)
llm_tokens_used = Counter(
    'agent_llm_tokens_total',
    'Total tokens consumed',
    ['model', 'token_type']  # token_type: prompt, completion
)

# Conversation length
conversation_length = Histogram(
    'agent_conversation_length',
    'Number of messages in conversation'
)

# Background task queue depth
task_queue_depth = Gauge(
    'agent_task_queue_depth',
    'Number of pending background tasks',
    ['priority']
)

# Cache hit rate
cache_hits = Counter('agent_cache_hits_total', 'Cache hits')
cache_misses = Counter('agent_cache_misses_total', 'Cache misses')
```

**Alert thresholds**:
- LLM API call duration p95 > 30s → Investigate slow responses
- Task queue depth > 1000 → Add more workers
- Cache hit rate < 30% → Optimize caching strategy
- Token usage spike > 2x baseline → Check for abuse or bugs

### Cost Optimization at Scale

**1. Implement aggressive caching:**
```python
# Cache identical prompts
# Cache system prompts (rarely change)
# Cache tool descriptions and examples
```

**2. Use smaller models for simple tasks:**
```python
class ModelRouter:
    async def route_request(self, message: str, complexity: str) -> str:
        if complexity == "simple":
            # Use faster, cheaper model
            return await self.claude_haiku.generate(message)
        elif complexity == "complex":
            # Use more capable model
            return await self.claude_opus.generate(message)
```

**3. Batch requests when possible:**
```python
# Instead of 100 individual API calls
for doc in documents:
    summary = await llm.summarize(doc)

# Batch into fewer calls
batch_prompt = "Summarize each document:\n" + "\n\n".join(documents)
summaries = await llm.summarize_batch(batch_prompt)
```

### Testing at Scale

**Load testing agent endpoints**:

```python
# tests/load/agent_locustfile.py
from locust import HttpUser, task, between

class AgentUser(HttpUser):
    wait_time = between(1, 3)  # Simulate user think time

    @task(3)  # 3x weight
    def chat_message(self):
        self.client.post("/api/v1/agent/chat", json={
            "message": "Explain quantum computing",
            "session_id": self.session_id
        })

    @task(1)
    def analyze_document(self):
        self.client.post("/api/v1/agent/analyze", json={
            "document_id": 123
        })

    def on_start(self):
        # Authenticate and get session
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test_pass"
        })
        self.session_id = response.json()["session_id"]
```

Run load test:
```bash
# Simulate 100 users, ramp up 10 users/second
locust -f tests/load/agent_locustfile.py \
  --host https://api.example.com \
  --users 100 \
  --spawn-rate 10
```

### Additional Resources

- 📖 **[Phase 4 Scaling Architecture](docs/BACKEND_GUIDE.md#phase-4-scaling-architecture-)** - Backend scaling foundation
- 📖 **[Level 3: Background Tasks](docs/scaling/level3-background-tasks.md)** - Task queue patterns
- 📖 **[Load Testing Guide](docs/scaling/load-testing.md)** - Measure and validate performance
- 📖 **[Troubleshooting](docs/scaling/troubleshooting.md)** - Common scaling issues

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [OpenAI API](https://platform.openai.com/docs/)
- [LangChain](https://python.langchain.com/) - Optional agent framework
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel) - Alternative agent framework

## Support

For issues related to:
- **Template features**: See main [README.md](README.md)
- **Agent implementation**: Check examples and patterns in this document
- **Security concerns**: Review [SECURITY.md](SECURITY.md)

---

Built on the FastAPI Production Starter Template | [GitHub](https://github.com/thesidshah/FastAPI-Backend-Template)
