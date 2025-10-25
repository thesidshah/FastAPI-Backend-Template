# Production FastAPI Backend: Comprehensive Guide

**The definitive guide to understanding and working with this backend system**

---

## Table of Contents

- [Part I: Essentials](#part-i-essentials-read-this-first)
- [Part II: Core Components](#part-ii-core-components)
- [Part III: Deep Dives](#part-iii-deep-dives)
- [Part IV: Reference](#part-iv-reference)

---

# Part I: Essentials (Read This First)

*Estimated reading time: 15-20 minutes*

## 1. Project Overview & Philosophy

### What Is This Backend?

This is a production-ready FastAPI backend template designed for building scalable, secure APIs. It provides a complete foundation with:

- **Security-first architecture** - Rate limiting, authentication, validation built-in
- **Observability from day one** - Structured logging, request tracing, health checks
- **Progressive enhancement** - Start simple (Phase 1), add features as needed (Phases 2-3)
- **Developer experience** - Type safety, async-first, comprehensive testing

### Core Philosophy

The backend embodies **ruthless simplicity**:

- **KISS principle**: Every component has a clear, single purpose
- **Minimize abstractions**: Direct implementations over complex frameworks
- **Start minimal, grow as needed**: Phase 1 is fully functional with no external dependencies
- **Avoid future-proofing**: Build for current requirements, not hypothetical futures

**Architectural integrity with minimal implementation**:
- Preserve proven patterns (middleware pipeline, dependency injection, factory pattern)
- Implement with dramatically simpler code than typical enterprise solutions
- End-to-end thinking over perfect individual components

### Project Goals

1. **Rapid development**: Get a production-quality API running in minutes
2. **Security by default**: Common vulnerabilities prevented out of the box
3. **Maintainability**: Clear structure, readable code, comprehensive tests
4. **Flexibility**: Easy to extend, modify, and adapt to specific needs

## 2. Architecture at a Glance

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Request                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Middleware Pipeline                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Security   │→ │ Rate Limit   │→ │   Monitoring     │  │
│  │  Headers    │  │              │  │   & Logging      │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │  API Routes  │─────▶│   Services   │                    │
│  │  (Endpoints) │      │   (Business  │                    │
│  │              │      │    Logic)    │                    │
│  └──────────────┘      └──────┬───────┘                    │
│                               │                              │
│                               ▼                              │
│                        ┌──────────────┐                     │
│                        │ Dependencies │                     │
│                        │   (Config,   │                     │
│                        │   Database)  │                     │
│                        └──────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

**Application Factory Pattern**:
- `create_app()` function returns configured FastAPI instance
- Enables different configurations for different environments
- Supports testing with custom settings

**Middleware Pipeline**:
- Ordered stack of request/response processors
- Each middleware has single, focused responsibility
- Order matters: outermost processes requests last, responses first

**Dependency Injection**:
- FastAPI's built-in DI system for sharing resources
- Services, configuration, and database connections injected as needed
- Simplifies testing and modularity

**Phase-Based Feature Set**:
- **Phase 1** (Core): No external dependencies, production-ready
- **Phase 2** (Enhanced): Redis caching, JWT authentication
- **Phase 3** (Advanced): Prometheus metrics, GeoIP blocking, circuit breakers

## 3. Quick Start

For detailed setup instructions, see [QUICKSTART.md](../QUICKSTART.md).

**30-second version**:

```bash
# Clone and setup
git clone <repository-url>
cd production-fastapi-backend
./scripts/setup.sh

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
./scripts/dev.sh
```

Visit http://localhost:8000/docs for interactive API documentation.

## 4. Request Lifecycle Visualization

### Complete Request Flow

```
Client Request
    │
    ▼
[1] Security Headers Middleware
    │ ├─ Add security headers to response
    │ └─ HSTS, CSP, X-Frame-Options, etc.
    ▼
[2] Rate Limit Middleware
    │ ├─ Check request count for client
    │ ├─ Allow or block based on limits
    │ └─ Add rate limit headers
    ▼
[3] Content Validation Middleware
    │ ├─ Validate content-type
    │ ├─ Check payload size
    │ └─ Block suspicious patterns
    ▼
[4] Proxy Headers Middleware (if enabled)
    │ ├─ Trust X-Forwarded-For headers
    │ └─ Fix client IP and scheme
    ▼
[5] JWT Authentication Middleware (if enabled)
    │ ├─ Extract and validate token
    │ ├─ Set user context
    │ └─ 401 if invalid
    ▼
[6] Trusted Host Middleware
    │ ├─ Validate Host header
    │ └─ Block untrusted hosts
    ▼
[7] CORS Middleware (if configured)
    │ ├─ Handle preflight requests
    │ └─ Add CORS headers
    ▼
[8] Request ID Middleware
    │ ├─ Generate or extract request ID
    │ ├─ Bind to logging context
    │ └─ Add X-Request-ID header
    ▼
[9] Request Logging Middleware
    │ ├─ Log request start
    │ ├─ Measure processing time
    │ └─ Log completion with metrics
    ▼
FastAPI Router
    │ ├─ Match route
    │ ├─ Run path operation function
    │ └─ Invoke dependencies
    ▼
Endpoint Handler
    │ ├─ Validate request with Pydantic
    │ ├─ Call service layer
    │ └─ Return response
    ▼
Service Layer
    │ ├─ Execute business logic
    │ ├─ Interact with database
    │ └─ Return data
    ▼
Response Generation
    │ ├─ Serialize with Pydantic
    │ ├─ Set status code
    │ └─ Return to FastAPI
    ▼
Response flows back through middleware (in reverse)
    ▼
Client receives response
```

### Key Points

1. **Middleware order is critical**: Security checks happen before authentication, authentication before business logic
2. **Each layer is independent**: Middleware can be enabled/disabled without affecting others
3. **Observability throughout**: Request ID and logging track the entire journey
4. **Security at every layer**: Multiple defense layers (rate limiting, validation, authentication)

## 5. Further Exploration

### FastAPI Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Official framework docs
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/) - Structuring larger applications
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation library

### Related Patterns
- [Twelve-Factor App](https://12factor.net/) - Cloud-native application principles
- [REST API Design](https://restfulapi.net/) - RESTful API best practices
- [Middleware Pattern](https://en.wikipedia.org/wiki/Middleware) - Request/response processing

### Advanced Topics
- **Part II** below for detailed component explanations
- **Part III** for deep technical dives
- **Part IV** for quick reference materials

---

# Part II: Core Components

*Estimated reading time: 2-3 hours*

## 1. Application Factory & Startup

### The Factory Pattern

The application uses the **factory pattern** via the `create_app()` function in `src/app/main.py:10`. This pattern provides several critical benefits:

**Delayed initialization**: The application is created when uvicorn calls the factory, not at module import time. This prevents issues with global state and allows proper configuration loading.

**Configuration flexibility**: Different settings can be passed for different environments (local, staging, production, testing).

**Testing support**: Fresh app instances can be created for each test with custom configurations, ensuring test isolation.

### Factory Function Anatomy

```python
def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance."""

    # 1. Load configuration
    app_settings = settings or get_app_settings()

    # 2. Configure logging system
    configure_logging(app_settings)

    # 3. Create FastAPI instance
    app = FastAPI(
        title=app_settings.project_name,
        description=app_settings.project_description,
        version=app_settings.project_version,
        debug=app_settings.debug,
        docs_url=app_settings.docs_url,  # Computed property
        redoc_url=app_settings.redoc_url,  # Computed property
        openapi_url=app_settings.openapi_url,  # Computed property
        lifespan=build_lifespan(app_settings),  # Startup/shutdown
    )

    # 4. Register middleware stack
    register_middlewares(app, app_settings)

    # 5. Register API routes
    register_routes(app, app_settings)

    return app
```

### Running with the Factory

**Development with uvicorn**:
```bash
uvicorn app.main:create_app --factory --reload --port 8000
```

The `--factory` flag tells uvicorn that `create_app` is a callable that returns a FastAPI instance.

**Production with gunicorn**:
```bash
gunicorn app.main:create_app --factory \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

**Testing**:
```python
def test_custom_config():
    settings = AppSettings(environment="test", debug=True)
    app = create_app(settings=settings)
    # Test with custom configuration
```

### Lifespan Management

The `build_lifespan()` function in `src/app/core/lifespan.py:14` creates an async context manager that handles application startup and shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    logger.info("application.startup", environment=settings.environment.value)
    engine = await init_database(settings)
    await create_example_schema(engine)

    # Application runs here
    try:
        yield
    finally:
        # Shutdown
        await shutdown_database()
        logger.info("application.shutdown")
```

**Startup tasks**:
- Initialize database connections
- Create database schema
- Load caches or external resources
- Establish connections to external services

**Shutdown tasks**:
- Close database connections
- Flush log buffers
- Clean up temporary resources

### How to Extend

**Adding startup/shutdown logic**:

1. Add your logic to `src/app/core/lifespan.py:14`:
   ```python
   async def lifespan(app: FastAPI):
       # Startup
       await your_init_function()

       try:
           yield
       finally:
           # Shutdown
           await your_cleanup_function()
   ```

2. Keep lifespan fast - slow startup delays deployment

**Creating multiple factories**:

For specialized scenarios (testing, CLI tools):

```python
def create_test_app() -> FastAPI:
    """Factory specifically for testing."""
    settings = AppSettings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
    )
    return create_app(settings=settings)
```

## 2. Configuration Management

### Configuration Architecture

Configuration uses Pydantic settings with environment variable loading. All settings are defined in `src/app/core/config.py:23`.

**Two settings classes**:
- `AppSettings`: Application-level configuration
- `SecuritySettings`: Security-specific configuration

Both load from `.env` file and environment variables, with environment variables taking precedence.

### AppSettings

```python
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_prefix="APP_",
        env_nested_delimiter="__",
    )

    # Core settings
    project_name: str = "CMS Backend API"
    environment: Environment = Environment.LOCAL
    debug: bool = False

    # API configuration
    api_prefix: str = "/api/v1"

    # CORS
    cors_allow_origins: list[str] = Field(default_factory=list)

    # Logging
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.JSON

    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"
```

### SecuritySettings

```python
class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_prefix="SECURITY_",
    )

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # JWT (Phase 2)
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"

    # Redis (Phase 2)
    redis_url: str | None = None
    redis_enabled: bool = False
```

### Environment Variable Loading

Settings automatically load from:

1. `.env` file in project root
2. Environment variables
3. Default values in class definition

**Example `.env` file**:
```bash
APP_ENVIRONMENT=local
APP_DEBUG=true
APP_LOG_LEVEL=DEBUG
APP_CORS_ALLOW_ORIGINS=["http://localhost:3000"]

SECURITY_RATE_LIMIT_ENABLED=true
SECURITY_RATE_LIMIT_PER_MINUTE=100
```

### Accessing Configuration

**In application code**:
```python
from app.core.config import get_app_settings

settings = get_app_settings()  # Cached singleton
print(settings.environment)
```

**In dependencies**:
```python
from fastapi import Depends
from app.dependencies.config import get_config

async def my_endpoint(config: AppSettings = Depends(get_config)):
    # Use config
    return {"env": config.environment}
```

### Computed Properties

Some settings are computed based on environment:

```python
@computed_field
@property
def docs_url(self) -> str | None:
    # API docs only in local/staging
    return "/docs" if self.environment in {Environment.LOCAL, Environment.STAGING} else None
```

This automatically disables Swagger UI in production for security.

### How to Extend

**Adding new settings**:

1. Add to appropriate settings class:
   ```python
   class AppSettings(BaseSettings):
       my_new_setting: str = "default_value"
   ```

2. Add to `.env.example`:
   ```bash
   APP_MY_NEW_SETTING=production_value
   ```

3. Access anywhere:
   ```python
   settings = get_app_settings()
   value = settings.my_new_setting
   ```

**Environment-specific defaults**:
```python
@computed_field
@property
def feature_enabled(self) -> bool:
    return self.environment != Environment.PRODUCTION
```

## 3. Middleware Pipeline

### Middleware Architecture

Middleware forms a layered pipeline that processes every request and response. Each middleware wraps the next layer, creating an "onion" structure.

**Critical concept**: Middleware order matters. The **first registered middleware** is the **outermost layer** (processes requests last, responses first). The **last registered middleware** is the **innermost layer** (processes requests first, responses last).

### Middleware Flow Diagram

```
Request →  [Security Headers] → [Rate Limit] → [Content Val] → ... → [Logging] → Handler
Response ← [Security Headers] ← [Rate Limit] ← [Content Val] ← ... ← [Logging] ← Handler
```

### Complete Middleware Stack

The middleware stack is registered in `src/app/core/middleware.py:92`. Here's the complete order:

```python
def register_middlewares(app: FastAPI, settings: AppSettings):
    # 1. Security Headers (outermost)
    app.add_middleware(SecurityHeadersMiddleware, ...)

    # 2. Rate Limiting
    app.add_middleware(SimpleRateLimitMiddleware, ...)

    # 3. Content Validation
    app.add_middleware(ContentValidationMiddleware, ...)

    # 4. Proxy Headers (if behind load balancer)
    if security_settings.trust_proxy_headers:
        app.add_middleware(ProxyHeadersMiddleware, ...)

    # 5. JWT Authentication (Phase 2, if enabled)
    if security_settings.jwt_secret:
        app.add_middleware(JWTAuthenticationMiddleware, ...)

    # 6. Trusted Host
    if settings.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, ...)

    # 7. CORS (if needed)
    if settings.cors_allow_origins:
        app.add_middleware(CORSMiddleware, ...)

    # 8. Request ID
    app.add_middleware(RequestIDMiddleware)

    # 9. Request Logging (innermost)
    app.add_middleware(RequestLoggingMiddleware, ...)
```

### Core Middleware Details

**SecurityHeadersMiddleware** (`src/app/middleware/security.py:20`):
- Adds security headers to all responses
- Prevents clickjacking (X-Frame-Options)
- Prevents MIME sniffing (X-Content-Type-Options)
- HSTS in production with HTTPS
- Optional Content Security Policy

**SimpleRateLimitMiddleware** (`src/app/middleware/security.py:214`):
- In-memory sliding window rate limiting
- Per-minute and per-hour limits
- Configurable burst allowance
- Client identified by IP + user ID
- Automatic cleanup prevents memory leaks

**ContentValidationMiddleware** (`src/app/middleware/security.py:88`):
- Enforces payload size limits
- Validates content types
- Blocks null bytes (path traversal prevention)
- Different limits for different endpoints

**RequestIDMiddleware** (`src/app/core/middleware.py:16`):
- Generates or extracts request ID
- Binds ID to logging context
- Adds X-Request-ID response header
- Enables request tracing across services

**RequestLoggingMiddleware** (`src/app/core/middleware.py:39`):
- Structured logging for all requests
- Measures processing time
- Optional body logging in debug mode
- Adds X-Process-Time response header

### How Middleware Works

**BaseHTTPMiddleware pattern**:

```python
class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Process request (before handler)
        request_id = request.headers.get("X-Request-ID")

        # Call next middleware/handler
        response = await call_next(request)

        # Process response (after handler)
        response.headers["X-Custom-Header"] = "value"

        return response
```

### Phase-Based Middleware

**Phase 1** (always available):
- Security headers
- In-memory rate limiting
- Content validation
- Request logging

**Phase 2** (requires dependencies):
- Redis rate limiting
- JWT authentication

**Phase 3** (advanced features):
- GeoIP blocking
- Circuit breaker
- DDoS protection
- Prometheus metrics

### How to Extend

**Adding custom middleware**:

1. Create in `src/app/middleware/`:
   ```python
   class MyCustomMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           # Your logic
           response = await call_next(request)
           return response
   ```

2. Register in `src/app/core/middleware.py:92`:
   ```python
   app.add_middleware(MyCustomMiddleware, config=...)
   ```

3. Consider **order carefully** - where should it sit in the pipeline?

**Per-route middleware**:

Use FastAPI dependencies for route-specific behavior:

```python
@router.get("/special", dependencies=[Depends(special_rate_limit)])
async def special_endpoint():
    return {"message": "Special handling"}
```

## 4. API & Routing

### Routing Architecture

The API layer is organized hierarchically:

```
src/app/
├── main.py              # Application factory
├── api/
│   └── routes/          # Route modules
│       ├── __init__.py  # Route registration
│       ├── health.py    # Health check endpoints
│       ├── meta.py      # Metadata endpoints
│       └── database_example.py  # Example CRUD endpoints
```

### Route Registration Flow

**Step 1**: Individual route modules define routers:

```python
# src/app/api/routes/health.py
router = APIRouter()

@router.get("/live")
async def live(health_service: HealthService = Depends(get_health_service)):
    return await health_service.liveness()
```

**Step 2**: Routes module builds API router:

```python
# src/app/api/routes/__init__.py
def build_api_router(settings: AppSettings) -> APIRouter:
    router = APIRouter()
    router.include_router(health_router, prefix="/health", tags=["Health"])
    router.include_router(meta_router, tags=["Meta"])
    return router
```

**Step 3**: Main app includes API router with prefix:

```python
# src/app/main.py via register_routes
api_router = build_api_router(settings)
app.include_router(api_router, prefix=settings.api_prefix)  # /api/v1
```

**Result**: `GET /api/v1/health/live`

### Router Organization

**By feature**, not by method:

```
routes/
├── users.py        # All user-related endpoints
├── posts.py        # All post-related endpoints
└── comments.py     # All comment-related endpoints
```

Each feature module has its own router:

```python
# routes/users.py
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users(): ...

@router.post("/")
async def create_user(): ...

@router.get("/{user_id}")
async def get_user(user_id: int): ...
```

### Dependency Injection

FastAPI's DI system provides services to endpoints:

```python
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: AppSettings = Depends(get_config),
):
    # Dependencies injected automatically
    user = await db.get(User, user_id)
    return user
```

**Common dependencies**:
- `get_db`: Database session
- `get_config`: Application settings
- `get_current_user`: Authenticated user
- `get_health_service`: Health check service

Dependencies defined in `src/app/dependencies/`.

### Request/Response Models

Pydantic models define API contracts:

```python
# src/app/schemas/user.py
class UserCreate(BaseModel):
    username: str
    email: EmailStr

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

# Route uses schemas
@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate):
    # Automatic validation and serialization
    return created_user
```

### Error Handling

FastAPI provides automatic error responses:

- **422 Validation Error**: Invalid request data
- **404 Not Found**: Route doesn't exist
- **500 Internal Server Error**: Unhandled exception

Custom error handlers:

```python
@app.exception_handler(CustomException)
async def custom_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)},
    )
```

### How to Extend

**Adding a new feature**:

1. Create route module `src/app/api/routes/myfeature.py`:
   ```python
   router = APIRouter(prefix="/myfeature", tags=["MyFeature"])

   @router.get("/")
   async def list_items():
       return []
   ```

2. Register in `src/app/api/routes/__init__.py`:
   ```python
   from .myfeature import router as myfeature_router

   def build_api_router(settings):
       router = APIRouter()
       router.include_router(myfeature_router)
       return router
   ```

3. Create schemas in `src/app/schemas/myfeature.py`

4. Create service in `src/app/services/myfeature.py`

5. Write tests in `tests/test_myfeature.py`

## 5. Services & Business Logic

### Service Layer Architecture

The service layer contains business logic, keeping it separate from HTTP concerns. This separation enables:

- **Reusability**: Same logic from CLI, background jobs, or API
- **Testability**: Test business logic without HTTP infrastructure
- **Maintainability**: Change business rules without touching routes

### Service Organization

```
src/app/
├── services/
│   ├── __init__.py
│   ├── health.py              # Health check logic
│   └── database_example.py    # Example CRUD operations
```

### Service Pattern

**Basic service**:

```python
# src/app/services/health.py
class HealthService:
    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._logger = structlog.get_logger(self.__class__.__name__)

    async def liveness(self) -> HealthResponse:
        """Basic liveness check."""
        return HealthResponse(
            environment=self._settings.environment.value,
            version=self._settings.project_version,
        )

    async def readiness(self) -> ReadinessResponse:
        """Check dependencies are ready."""
        checks = {
            "database": await self._check_database(),
            "cache": await self._check_cache(),
        }
        return ReadinessResponse(checks=checks)
```

### Dependency Injection for Services

Services are provided via dependencies:

```python
# src/app/dependencies/services.py
def get_health_service(
    settings: AppSettings = Depends(get_app_settings)
) -> HealthService:
    return HealthService(settings)

# In routes
@router.get("/health/live")
async def live(
    health_service: HealthService = Depends(get_health_service)
):
    return await health_service.liveness()
```

### Service Best Practices

**Single Responsibility**:
Each service handles one domain area:
- `UserService` - User management
- `PostService` - Post operations
- `NotificationService` - Sending notifications

**Async/Await**:
Use async for I/O operations:

```python
class UserService:
    async def get_user(self, user_id: int) -> User:
        async with self.db.session() as session:
            return await session.get(User, user_id)
```

**Dependency Injection**:
Services receive dependencies, don't create them:

```python
class UserService:
    def __init__(
        self,
        db: Database,
        cache: Cache,
        logger: structlog.BoundLogger,
    ):
        self.db = db
        self.cache = cache
        self.logger = logger
```

**Error Handling**:
Raise descriptive exceptions:

```python
class UserService:
    async def get_user(self, user_id: int) -> User:
        user = await self.db.get(User, user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        return user
```

### How to Extend

**Creating a new service**:

1. Create `src/app/services/myservice.py`:
   ```python
   class MyService:
       def __init__(self, settings: AppSettings):
           self.settings = settings

       async def do_something(self) -> Result:
           # Business logic
           return result
   ```

2. Add dependency in `src/app/dependencies/services.py`:
   ```python
   def get_my_service(
       settings: AppSettings = Depends(get_app_settings)
   ) -> MyService:
       return MyService(settings)
   ```

3. Use in routes:
   ```python
   @router.get("/endpoint")
   async def endpoint(
       service: MyService = Depends(get_my_service)
   ):
       return await service.do_something()
   ```

## 6. Testing Strategy

### Test Architecture

The test suite is organized by type and scope:

```
tests/
├── conftest.py                     # Shared fixtures
├── test_health.py                  # Health endpoint tests
├── test_lifespan.py                # Startup/shutdown tests
├── test_security_middleware.py     # Middleware tests
└── integrations/                   # Integration tests
    ├── test_database.py
    └── test_alerting.py
```

### Test Fixtures

**conftest.py** (`tests/conftest.py:18`) provides core fixtures:

```python
@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create test application."""
    settings = AppSettings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
    )
    return create_app(settings=settings)

@pytest.fixture()
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    """Async HTTP client for testing."""
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client
```

**Key points**:
- `app` fixture: Session-scoped test application with test settings
- `async_client` fixture: Function-scoped HTTP client that manages lifespan
- In-memory database for tests (no external dependencies)

### Writing Tests

**Testing endpoints**:

```python
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["environment"] == "test"
    assert "version" in data
```

**Testing with authentication**:

```python
async def test_protected_endpoint(async_client: AsyncClient):
    # Get auth token
    token = await get_test_token()

    # Make authenticated request
    response = await async_client.get(
        "/api/v1/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
```

**Testing services**:

```python
async def test_health_service():
    settings = AppSettings(environment="test")
    service = HealthService(settings)

    result = await service.liveness()

    assert result.environment == "test"
    assert result.version is not None
```

### Test Categories

**Unit Tests** (60% of tests):
- Test individual functions and classes
- Mock external dependencies
- Fast execution (< 1s each)
- Example: `test_security_middleware.py`

**Integration Tests** (30% of tests):
- Test component interactions
- Real database (in-memory)
- Test full request lifecycle
- Example: `tests/integrations/test_database.py`

**End-to-End Tests** (10% of tests):
- Test complete user workflows
- Test with real dependencies
- Slower but comprehensive
- Example: Full CRUD workflow tests

### Running Tests

**All tests**:
```bash
pytest
```

**Specific test file**:
```bash
pytest tests/test_health.py
```

**Specific test function**:
```bash
pytest tests/test_health.py::test_health_endpoint -v
```

**With coverage**:
```bash
pytest --cov=app --cov-report=html
```

**Watch mode** (requires pytest-watch):
```bash
ptw
```

### Test Best Practices

**AAA Pattern** (Arrange-Act-Assert):
```python
async def test_create_user(async_client):
    # Arrange
    user_data = {"username": "test", "email": "test@example.com"}

    # Act
    response = await async_client.post("/api/v1/users", json=user_data)

    # Assert
    assert response.status_code == 201
    assert response.json()["username"] == "test"
```

**Descriptive names**:
```python
# Good
async def test_rate_limit_blocks_excessive_requests()

# Bad
async def test_rate_limit()
```

**Isolated tests**:
Each test should be independent. Don't rely on test execution order.

**Test failures, not just success**:
```python
async def test_invalid_user_returns_400(async_client):
    response = await async_client.post(
        "/api/v1/users",
        json={"invalid": "data"}
    )
    assert response.status_code == 400
```

### How to Extend

**Adding tests for new feature**:

1. Create `tests/test_myfeature.py`:
   ```python
   import pytest

   async def test_myfeature_list(async_client):
       response = await async_client.get("/api/v1/myfeature")
       assert response.status_code == 200
   ```

2. Add integration tests if needed:
   ```python
   async def test_myfeature_database_integration(async_client, db):
       # Test with real database operations
       ...
   ```

3. Mock external dependencies:
   ```python
   @pytest.fixture
   def mock_external_api(monkeypatch):
       async def mock_call(*args, **kwargs):
           return {"mock": "data"}

       monkeypatch.setattr("app.services.myservice.external_api", mock_call)
   ```

## 7. Further Exploration

### Testing Resources
- [pytest Documentation](https://docs.pytest.org/) - Testing framework
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Async test support
- [Testing FastAPI Applications](https://fastapi.tiangolo.com/tutorial/testing/) - Official testing guide
- [TestClient vs AsyncClient](https://fastapi.tiangolo.com/advanced/async-tests/) - When to use which

### Design Patterns
- [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection) - Core pattern for testability
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html) - Data access abstraction
- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html) - Business logic organization

### Next Steps
- **Part III** for deep dives into security, database, logging, and deployment
- **Part IV** for quick reference materials and troubleshooting
- [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines

---

# Part III: Deep Dives

*Estimated reading time: 4-6 hours total (1-1.5 hours per section)*

## 1. Security Implementation

### Security Philosophy

Security is implemented in layers, with each layer providing independent protection:

1. **Network Layer**: Rate limiting prevents abuse
2. **Transport Layer**: HTTPS enforced in production
3. **Application Layer**: Input validation, authentication, authorization
4. **Data Layer**: Parameterized queries prevent injection

**Defense in depth**: If one layer is bypassed, others still protect.

### Phase-Based Security Features

**Phase 1** (No dependencies required):
- Security headers (HSTS, CSP, X-Frame-Options)
- In-memory rate limiting
- Content validation
- Size limits
- Request logging

**Phase 2** (Requires Redis, JWT libraries):
- Redis-backed rate limiting (distributed)
- JWT authentication
- Token refresh mechanism
- Session management

**Phase 3** (Requires GeoIP database, Prometheus):
- GeoIP-based blocking
- Prometheus metrics
- Circuit breaker pattern
- DDoS protection
- Advanced alerting

### Security Headers

Implemented in `src/app/middleware/security.py:20`:

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        response.headers.update({
            "X-Content-Type-Options": "nosniff",           # Prevent MIME sniffing
            "X-Frame-Options": "DENY",                      # Prevent clickjacking
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=()",  # Disable features
            "Cache-Control": "no-store, max-age=0",        # No sensitive data caching
            "Server": "undisclosed",                        # Hide server info
        })

        # HSTS in production with HTTPS
        if self.is_production and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = \
                "max-age=31536000; includeSubDomains; preload"

        # Optional Content Security Policy
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = self.csp_policy

        return response
```

**Key protections**:
- **X-Content-Type-Options**: Prevents browsers from MIME-sniffing responses
- **X-Frame-Options**: Prevents embedding in iframes (clickjacking protection)
- **HSTS**: Forces HTTPS for one year
- **CSP**: Restricts resource loading (XSS protection)

### Rate Limiting

**Phase 1 implementation** (`src/app/middleware/security.py:214`):

Uses in-memory sliding window algorithm:

```python
class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.burst = burst_size

        # Sliding windows
        self.minute_windows: dict[str, list[float]] = defaultdict(list)
        self.hour_windows: dict[str, list[float]] = defaultdict(list)
```

**How it works**:
1. Track timestamps of requests per client
2. Remove old timestamps (outside window)
3. Count requests in current window
4. Allow if under limit, block if over

**Client identification**:
- IP address from request
- X-Forwarded-For header if behind proxy
- User ID if authenticated
- Format: `{ip}:{user_id}`

**Burst allowance**:
Allows brief spikes above the per-minute limit:
- Per-minute limit: 60 requests
- Burst: 10 additional requests
- Total allowed in short burst: 70 requests

**Automatic cleanup**:
Periodically removes old entries to prevent memory leaks:

```python
def _cleanup_old_entries(self, now: float):
    minute_cutoff = now - 60
    hour_cutoff = now - 3600

    # Remove expired timestamps
    for client_id in list(self.minute_windows.keys()):
        self.minute_windows[client_id] = [
            t for t in self.minute_windows[client_id]
            if t > minute_cutoff
        ]
        # Remove empty entries
        if not self.minute_windows[client_id]:
            del self.minute_windows[client_id]
```

**Phase 2 upgrade**: Redis-backed rate limiting provides:
- Distributed rate limiting across multiple servers
- Persistent rate limit state (survives restarts)
- Sliding log algorithm with more precision

### Content Validation

Implemented in `src/app/middleware/security.py:88`:

**Size limits by endpoint**:
```python
DEFAULT_LIMITS = {
    "/api/upload": 50 * 1024 * 1024,   # 50MB for file uploads
    "/api/import": 10 * 1024 * 1024,   # 10MB for data imports
    "/api/": 1 * 1024 * 1024,          # 1MB for API calls
    "/": 64 * 1024,                     # 64KB default
}
```

**Content-type validation**:
```python
ALLOWED_CONTENT_TYPES = {
    "POST": {"application/json", "multipart/form-data", "text/plain"},
    "PUT": {"application/json", "application/octet-stream"},
    "PATCH": {"application/json", "application/merge-patch+json"},
}
```

**Null byte detection**:
Blocks requests with null bytes in URL (path traversal attack prevention):

```python
if self.block_null_bytes and "\x00" in str(request.url):
    return Response(
        content=json.dumps({"error": "Invalid request"}),
        status_code=400,
    )
```

### JWT Authentication (Phase 2)

When enabled, JWT middleware (`src/app/middleware/auth.py`) provides token-based authentication:

**Token structure**:
```json
{
  "sub": "user_id",
  "exp": 1735689600,
  "iat": 1735603200
}
```

**Authentication flow**:
1. Extract token from Authorization header: `Bearer <token>`
2. Validate signature using JWT_SECRET
3. Check expiration time
4. Set user context on request.state
5. Return 401 if invalid

**Usage in routes**:
```python
@router.get("/protected")
async def protected_route(
    current_user: dict = Depends(get_current_user)
):
    return {"user_id": current_user["sub"]}
```

**Token refresh**:
Separate endpoint issues new tokens using refresh token:

```python
@router.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    # Validate refresh token
    # Issue new access token
    return {"access_token": new_token}
```

### Input Validation

Pydantic models provide automatic validation:

```python
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8)

@router.post("/users")
async def create_user(user: UserCreate):
    # user is validated automatically
    # Invalid data returns 422 with details
    ...
```

**Validation features**:
- Type checking
- String length constraints
- Regex patterns
- Email validation
- Custom validators

### SQL Injection Prevention

SQLAlchemy with async provides parameterized queries:

```python
# Safe - parameterized
async def get_user(user_id: int):
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

# Unsafe - never do this
async def get_user_unsafe(user_id: str):
    # DON'T: Direct string interpolation
    query = f"SELECT * FROM users WHERE id = {user_id}"
```

Always use SQLAlchemy's query builder or parameterized queries.

### CORS Configuration

Configure allowed origins in settings:

```python
# .env
APP_CORS_ALLOW_ORIGINS=["http://localhost:3000", "https://app.example.com"]
```

Middleware automatically:
- Handles preflight requests
- Adds CORS headers
- Validates origin

### Security Best Practices

**Do**:
- ✅ Use HTTPS in production
- ✅ Set strong JWT_SECRET
- ✅ Enable rate limiting
- ✅ Validate all inputs
- ✅ Use parameterized queries
- ✅ Keep dependencies updated
- ✅ Enable security headers
- ✅ Log security events

**Don't**:
- ❌ Store secrets in code
- ❌ Disable security features without reason
- ❌ Trust user input
- ❌ Expose detailed error messages in production
- ❌ Use default secrets
- ❌ Disable HTTPS in production

### How to Extend

**Custom authentication**:

1. Create authentication middleware:
   ```python
   class CustomAuthMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           # Validate custom auth
           if not await is_authenticated(request):
               return Response("Unauthorized", status_code=401)
           return await call_next(request)
   ```

2. Register in middleware stack

**API key authentication**:

```python
async def get_api_key(
    api_key: str = Header(None, alias="X-API-Key")
) -> str:
    if not api_key or not await validate_api_key(api_key):
        raise HTTPException(status_code=401)
    return api_key

@router.get("/api-protected")
async def protected(api_key: str = Depends(get_api_key)):
    return {"message": "Authenticated with API key"}
```

## 2. Database Integration

### Database Architecture

The backend uses **SQLAlchemy 2.0** with async support via `asyncio` and `aiosqlite` (or `asyncpg` for PostgreSQL).

**Key design decisions**:
- Async/await for non-blocking I/O
- Connection pooling for efficiency
- Context managers for proper cleanup
- Optional integration (not required for basic functionality)

### Database Configuration

Settings in `src/app/core/config.py:70`:

```python
class AppSettings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./app.db"
    database_pool_size: int = Field(default=5, ge=1)
    database_echo: bool = False  # Log all SQL queries
```

**Supported databases**:
- SQLite: `sqlite+aiosqlite:///path/to/db.db`
- PostgreSQL: `postgresql+asyncpg://user:pass@host/db`
- MySQL: `mysql+aiomysql://user:pass@host/db`

### Database Initialization

Database is initialized in lifespan (`src/app/core/lifespan.py:14`):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    engine = await init_database(settings)
    await create_example_schema(engine)

    try:
        yield
    finally:
        # Shutdown
        await shutdown_database()
```

### Engine and Session Management

Implementation in `src/app/integrations/database.py`:

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

# Global engine and session factory
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None

async def init_database(settings: AppSettings) -> AsyncEngine:
    """Initialize database engine and session factory."""
    global _engine, _async_session_factory

    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        echo=settings.database_echo,
    )

    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return _engine

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized")

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Defining Models

SQLAlchemy declarative models:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

**New SQLAlchemy 2.0 features**:
- `Mapped` type annotations
- `mapped_column` for better type inference
- Async-first design

### Creating Tables

Async table creation:

```python
async def create_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

Called during application startup in lifespan.

### CRUD Operations

**Create**:
```python
async def create_user(
    session: AsyncSession,
    username: str,
    email: str,
) -> User:
    user = User(username=username, email=email)
    session.add(user)
    await session.commit()
    await session.refresh(user)  # Get generated ID
    return user
```

**Read**:
```python
async def get_user(session: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def list_users(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:
    stmt = select(User).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

**Update**:
```python
async def update_user(
    session: AsyncSession,
    user_id: int,
    **updates,
) -> User:
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**updates)
        .returning(User)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()
```

**Delete**:
```python
async def delete_user(session: AsyncSession, user_id: int):
    stmt = delete(User).where(User.id == user_id)
    await session.execute(stmt)
    await session.commit()
```

### Using in Routes

Inject database session via dependency:

```python
@router.get("/users/{user_id}")
async def get_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Transactions

**Explicit transactions**:
```python
async def transfer_funds(
    session: AsyncSession,
    from_account: int,
    to_account: int,
    amount: float,
):
    async with session.begin():
        # Both succeed or both fail
        await debit_account(session, from_account, amount)
        await credit_account(session, to_account, amount)
        # Commits automatically if no exception
```

**Session manages transaction**:
The session from `get_db_session` automatically commits on success, rolls back on exception.

### Query Optimization

**Eager loading** (N+1 query prevention):
```python
stmt = (
    select(User)
    .options(selectinload(User.posts))  # Load related posts
    .where(User.id == user_id)
)
```

**Pagination**:
```python
stmt = select(User).limit(page_size).offset(page * page_size)
```

**Indexing**:
```python
username: Mapped[str] = mapped_column(unique=True, index=True)
```

### Migrations

Use Alembic for database migrations:

**Setup**:
```bash
pip install alembic
alembic init alembic
```

**Configure** `alembic/env.py`:
```python
from app.models import Base
target_metadata = Base.metadata
```

**Create migration**:
```bash
alembic revision --autogenerate -m "Add users table"
```

**Apply migration**:
```bash
alembic upgrade head
```

### Testing with Database

Use in-memory SQLite for tests:

```python
@pytest.fixture
async def test_db():
    settings = AppSettings(database_url="sqlite+aiosqlite:///:memory:")
    engine = await init_database(settings)
    await create_tables(engine)

    yield

    await shutdown_database()
```

### How to Extend

**Adding a new model**:

1. Define model:
   ```python
   class Post(Base):
       __tablename__ = "posts"

       id: Mapped[int] = mapped_column(primary_key=True)
       title: Mapped[str]
       content: Mapped[str]
       user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
   ```

2. Create migration:
   ```bash
   alembic revision --autogenerate -m "Add posts table"
   alembic upgrade head
   ```

3. Add service methods:
   ```python
   async def create_post(session, title, content, user_id):
       ...
   ```

4. Add routes:
   ```python
   @router.post("/posts")
   async def create_post_endpoint(...):
       ...
   ```

## 3. Logging & Observability

### Logging Architecture

The backend uses **structlog** for structured, context-aware logging. Structured logs are JSON-formatted with consistent fields, making them easy to parse and analyze.

**Key benefits**:
- Machine-readable JSON output
- Automatic request correlation
- Performance metrics
- Context propagation
- Easy aggregation

### Logging Configuration

Configuration in `src/app/core/logging.py:26`:

```python
def configure_logging(settings: AppSettings):
    log_level = logging.getLevelName(settings.log_level.upper())

    # Shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # Merge context
        structlog.processors.add_log_level,        # Add level
        structlog.stdlib.add_logger_name,          # Add logger name
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # ISO timestamp
        structlog.processors.StackInfoRenderer(),  # Stack traces
        structlog.processors.format_exc_info,      # Exception formatting
    ]

    # Renderer based on format
    renderer = (
        structlog.processors.JSONRenderer(serializer=orjson_dumps)
        if settings.log_format is LogFormat.JSON
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

**Two output formats**:
- **JSON** (production): Machine-readable, one log per line
- **Console** (development): Human-readable with colors

### Log Levels

Standard Python logging levels:

- **DEBUG**: Detailed diagnostic information
- **INFO**: Confirmation that things are working
- **WARNING**: Something unexpected but not an error
- **ERROR**: Error that prevented a function from completing
- **CRITICAL**: Serious error, application may crash

Configure via `APP_LOG_LEVEL` environment variable.

### Request Logging

RequestLoggingMiddleware (`src/app/core/middleware.py:39`) logs every request:

**Request start**:
```json
{
  "event": "http.request.start",
  "method": "GET",
  "path": "/api/v1/users",
  "query": "limit=10",
  "request_id": "8f7d6e5c-4b3a-2910-8765-4321fedcba98",
  "timestamp": "2025-10-24T14:23:45.123456Z",
  "level": "info"
}
```

**Request complete**:
```json
{
  "event": "http.request.complete",
  "method": "GET",
  "path": "/api/v1/users",
  "status_code": 200,
  "duration_ms": 42.123,
  "request_id": "8f7d6e5c-4b3a-2910-8765-4321fedcba98",
  "timestamp": "2025-10-24T14:23:45.165456Z",
  "level": "info"
}
```

**Body logging**: Enabled in debug mode, logs first 256 bytes of request body.

### Request ID Correlation

RequestIDMiddleware (`src/app/core/middleware.py:16`) ensures every request has a unique ID:

1. Extract from `X-Request-ID` header (if client provides)
2. Or generate new UUID
3. Bind to logging context (all logs from this request include it)
4. Add to response headers

**Correlation across services**:
Client can pass same request ID to multiple services for distributed tracing.

### Logging in Code

**Get logger**:
```python
import structlog

logger = structlog.get_logger(__name__)
```

**Log with context**:
```python
logger.info(
    "user.created",
    user_id=user.id,
    username=user.username,
    email=user.email,
)
```

**Log errors with exceptions**:
```python
try:
    result = await risky_operation()
except Exception:
    logger.exception(
        "operation.failed",
        operation="risky_operation",
        user_id=user_id,
    )
    raise
```

**Bind context for multiple logs**:
```python
logger = logger.bind(user_id=user.id)
logger.info("user.action.start")
# ... do work ...
logger.info("user.action.complete")
# Both logs include user_id
```

### Log Aggregation

**Local development**:
Logs to stdout, view in terminal or redirect to file.

**Production**:
Ship logs to centralized logging system:

**Option 1: Stdout → Log aggregator**
```bash
uvicorn app.main:create_app --factory | vector --config vector.toml
```

**Option 2: Direct to aggregator**
Configure structlog to send to:
- Elasticsearch
- Datadog
- CloudWatch Logs
- Splunk

**Option 3: Sidecar container**
Kubernetes sidecar collects logs from shared volume.

### Metrics

**Request metrics** (automatic):
- Request count
- Response time (in logs as `duration_ms`)
- Status code distribution
- Error rate

**Custom metrics** (Phase 3 with Prometheus):
```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('http_requests_total', 'Total requests')
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def metrics_middleware(request, call_next):
    REQUEST_COUNT.inc()
    with REQUEST_DURATION.time():
        response = await call_next(request)
    return response
```

### Health Checks

Two health endpoints for orchestration platforms:

**Liveness** (`GET /api/v1/health/live`):
- Lightweight check that app is running
- Returns immediately
- Used by Kubernetes liveness probe

**Readiness** (`GET /api/v1/health/ready`):
- Checks dependencies (database, cache, etc.)
- Returns 200 if ready to serve traffic
- Used by Kubernetes readiness probe

Example implementation (`src/app/services/health.py:20`):

```python
async def readiness(self) -> ReadinessResponse:
    checks = {
        "database": await self._check_database(),
        "cache": await self._check_cache(),
    }

    status = ProbeStatus.PASS
    if any(s == ProbeStatus.FAIL for s in checks.values()):
        status = ProbeStatus.FAIL

    return ReadinessResponse(status=status, checks=checks)
```

### Performance Monitoring

**Process time header**:
Every response includes `X-Process-Time` with milliseconds.

**Slow query detection**:
Log queries exceeding threshold:

```python
start = time.time()
result = await session.execute(stmt)
duration = time.time() - start

if duration > 1.0:
    logger.warning(
        "slow.query",
        duration_seconds=duration,
        query=str(stmt),
    )
```

**Memory profiling** (development):
```python
import tracemalloc

tracemalloc.start()
# ... run code ...
current, peak = tracemalloc.get_traced_memory()
logger.info("memory.usage", current_mb=current / 10**6, peak_mb=peak / 10**6)
```

### Distributed Tracing (Advanced)

For multi-service architectures, implement OpenTelemetry:

1. Install dependencies:
   ```bash
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
   ```

2. Configure in main.py:
   ```python
   from opentelemetry import trace
   from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

   app = create_app()
   FastAPIInstrumentor.instrument_app(app)
   ```

3. Traces automatically exported to collector (Jaeger, Zipkin, etc.)

### How to Extend

**Custom log processor**:
```python
def add_custom_context(logger, method_name, event_dict):
    event_dict["environment"] = os.getenv("ENVIRONMENT")
    event_dict["service"] = "my-api"
    return event_dict

structlog.configure(
    processors=[
        add_custom_context,  # Add before other processors
        ...
    ]
)
```

**Sensitive data filtering**:
```python
def filter_sensitive_data(logger, method_name, event_dict):
    if "password" in event_dict:
        event_dict["password"] = "***REDACTED***"
    return event_dict
```

**Error alerting**:
```python
def alert_on_error(logger, method_name, event_dict):
    if event_dict.get("level") == "error":
        await send_alert(event_dict)
    return event_dict
```

## 4. Deployment & Operations

### Deployment Architecture

The backend can be deployed in multiple ways depending on requirements:

1. **Single server**: Uvicorn directly
2. **Multiple workers**: Gunicorn + Uvicorn workers
3. **Containerized**: Docker + orchestration
4. **Serverless**: AWS Lambda, Google Cloud Run (with adaptations)

### Environment Configuration

**Production checklist** from README.md and SECURITY.md:

```bash
# Core settings
APP_ENVIRONMENT=production
APP_DEBUG=false
APP_LOG_FORMAT=json
APP_LOG_LEVEL=INFO

# Security
SECURITY_JWT_SECRET=$(openssl rand -hex 32)  # Generate strong secret
SECURITY_ENABLE_HSTS=true
SECURITY_RATE_LIMIT_ENABLED=true

# CORS
APP_CORS_ALLOW_ORIGINS=["https://app.example.com"]
APP_ALLOWED_HOSTS=["api.example.com"]

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db-host/production
DATABASE_POOL_SIZE=10

# Redis (Phase 2)
SECURITY_REDIS_ENABLED=true
SECURITY_REDIS_URL=redis://redis-host:6379/0
```

### Running with Uvicorn

**Development**:
```bash
uvicorn app.main:create_app --factory --reload --port 8000
```

**Production (single process)**:
```bash
uvicorn app.main:create_app --factory \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-config logging.json
```

### Running with Gunicorn

For production with multiple workers:

```bash
gunicorn app.main:create_app --factory \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

**Worker calculation**:
Common formula: `(2 * CPU cores) + 1`

**Why Gunicorn + Uvicorn**:
- Gunicorn manages worker processes
- Uvicorn provides async ASGI handling
- Process crashes handled gracefully
- Rolling restarts without downtime

### Docker Deployment

**Dockerfile** (included in project):

```dockerfile
# Multi-stage build for efficiency
FROM python:3.11-slim as builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv pip install --system -r pyproject.toml

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY src/ ./src/

# Run with factory pattern
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run**:
```bash
docker build -t my-api:latest .
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name my-api \
  my-api:latest
```

**Docker Compose** (for local development with services):

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENVIRONMENT=local
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/mydb
      - SECURITY_REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes Deployment

**Deployment manifest**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-backend
  template:
    metadata:
      labels:
        app: fastapi-backend
    spec:
      containers:
      - name: api
        image: my-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: APP_ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

**Service manifest**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-backend
spec:
  selector:
    app: fastapi-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Key Kubernetes features**:
- **Liveness probe**: Restarts unhealthy containers
- **Readiness probe**: Removes unready pods from service
- **Resource limits**: Prevents resource exhaustion
- **Replicas**: Horizontal scaling
- **Secrets**: Secure configuration management

### Database Migrations in Production

**Strategy 1: Pre-deployment migration**:
```bash
# Before deploying new version
alembic upgrade head
# Then deploy new code
```

**Strategy 2: Init container**:
```yaml
initContainers:
- name: migrations
  image: my-api:latest
  command: ["alembic", "upgrade", "head"]
  env:
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: url
```

**Blue-Green deployment**:
1. Deploy new version (green) alongside old (blue)
2. Run migrations (backward-compatible)
3. Switch traffic to green
4. Keep blue running briefly for rollback
5. Decommission blue

### Monitoring & Alerting

**Health monitoring**:
```bash
# Check liveness
curl https://api.example.com/api/v1/health/live

# Check readiness
curl https://api.example.com/api/v1/health/ready
```

**Metrics to monitor**:
- Request rate
- Error rate (4xx, 5xx)
- Response time (p50, p95, p99)
- Database connection pool usage
- Memory usage
- CPU usage

**Alerting thresholds**:
- Error rate > 5%
- P95 response time > 1s
- Health check failures
- High memory usage (> 80%)

**Phase 3 Prometheus integration**:
```python
from prometheus_client import make_asgi_app

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

Scrape at `/metrics` endpoint for:
- `http_requests_total`
- `http_request_duration_seconds`
- `http_request_size_bytes`
- `http_response_size_bytes`

### Logging in Production

**Log aggregation**:
Ship JSON logs to centralized system:

**Option 1: Stdout → Log shipper**:
```yaml
# Kubernetes with Fluentd
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      format json
    </source>
    <match **>
      @type elasticsearch
      host elasticsearch
      port 9200
    </match>
```

**Option 2: Direct to cloud**:
```python
# CloudWatch Logs
import boto3

cloudwatch = boto3.client('logs')
cloudwatch.put_log_events(
    logGroupName='/aws/api/production',
    logStreamName='api-logs',
    logEvents=[...],
)
```

### Backup & Disaster Recovery

**Database backups**:
```bash
# Automated daily backups
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/db-$(date +\%Y\%m\%d).sql.gz
```

**Application state**:
- Application is stateless (follows 12-factor)
- Redis persistence (if used) for rate limits
- File uploads to object storage (S3, GCS)

**Disaster recovery plan**:
1. Database: Restore from latest backup
2. Application: Redeploy from git tag
3. Configuration: Restore from secrets manager
4. Verify health checks pass
5. Gradually restore traffic

### Performance Optimization

**Database connection pooling**:
```python
# Already configured in settings
database_pool_size: int = 5  # Adjust based on load
```

**Redis caching** (Phase 2):
```python
@cached(ttl=300)  # 5 minutes
async def expensive_operation():
    return await compute_result()
```

**Response compression**:
```python
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

**CDN for static assets**:
Upload static files to CDN, not served by API.

### Phase 4: Scaling Architecture ⚡

**NEW**: Progressive multi-level scaling from development to enterprise production.

The backend now includes a comprehensive scaling architecture that follows the project's "start minimal, grow as needed" philosophy. Choose the appropriate level based on your traffic requirements:

#### Overview: Four Scaling Levels

```
Level 1: Multi-Worker Uvicorn    →  10-50K req/sec   (Configuration only)
Level 2: Gunicorn + Workers       →  50-100K req/sec  (Process management)
Level 3: Background Tasks (RQ)    →  Async work       (Task queue)
Level 4: Horizontal Scaling       →  100K+ req/sec    (Multi-node)
```

#### Level 1: Multi-Worker Uvicorn

**When to use**: You need to utilize multiple CPU cores on a single machine.

**Installation**: No additional dependencies required.

**Setup**:
```bash
# Development: Single worker with reload
uvicorn app.main:create_app --factory --reload

# Production: Multiple workers
uvicorn app.main:create_app --factory --workers 4 --host 0.0.0.0 --port 8000
```

**Worker calculation**:
- I/O-bound workload: `workers = CPU cores × 2`
- CPU-bound workload: `workers = CPU cores`

**Limitations**:
- No process management (workers don't auto-restart)
- Can't run with `--reload` flag (conflicts with `--workers`)
- In-memory state not shared across workers (use Redis)

**Benefits**:
- Zero configuration changes
- Immediate performance improvement
- Simple to understand and debug

📖 **[Level 1 Complete Guide](docs/scaling/level1-multi-worker.md)**

#### Level 2: Gunicorn Process Management

**When to use**: You need production-grade process management with health monitoring and graceful restarts.

**Installation**:
```bash
pip install -e ".[scaling]"
```

**Setup**:
```bash
# Use included configuration
gunicorn app.main:create_app --factory -c gunicorn.conf.py
```

**Key features**:
- Worker health monitoring and auto-restart
- Graceful shutdown and zero-downtime reloads
- Worker recycling (prevents memory leaks)
- Pre-fork worker model

**Configuration** (`gunicorn.conf.py`):
```python
workers = 4  # Or auto-calculated: multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30
graceful_timeout = 30
max_requests = 1000  # Restart worker after N requests
max_requests_jitter = 100
keepalive = 5
```

**Operations**:
```bash
# Graceful reload (zero downtime)
kill -HUP <gunicorn-master-pid>

# Or with Docker
docker-compose kill -s HUP web
```

**Benefits**:
- Production-ready reliability
- Automatic failure recovery
- Zero-downtime deployments
- Industry-standard solution

📖 **[Level 2 Complete Guide](docs/scaling/level2-gunicorn.md)**

#### Level 3: Background Task Processing

**When to use**: You have long-running operations that shouldn't block request-response cycles.

**Installation**:
```bash
pip install -e ".[scaling]"
```

**Setup**: Uses Redis Queue (RQ) for simplicity and alignment with ruthless simplicity philosophy.

**Configuration** (`.env`):
```bash
ENABLE_BACKGROUND_TASKS=true
TASK_BROKER_URL=redis://localhost:6379/1
TASK_RESULT_BACKEND=redis://localhost:6379/2
```

**Define tasks** (`src/app/tasks/example_tasks.py`):
```python
from app.services.tasks import register_task

@register_task("send_email")
def send_email_task(to: str, subject: str, body: str) -> dict:
    # Task implementation
    send_email(to, subject, body)
    return {"status": "sent", "to": to}
```

**Enqueue tasks** (in your API endpoint):
```python
from app.dependencies.services import get_task_service

@router.post("/users/{user_id}/welcome")
async def send_welcome_email(
    user_id: int,
    task_service = Depends(get_task_service)
):
    task_id = await task_service.enqueue_task(
        "send_email",
        to=user.email,
        subject="Welcome!",
        body="Welcome to our service"
    )
    return {"task_id": task_id}
```

**Start workers**:
```bash
# Using Docker Compose
docker-compose up -d worker

# Or manually
rq worker default --url redis://localhost:6379/1
```

**Monitor tasks**:
```bash
# RQ Dashboard (included)
rq-dashboard --url redis://localhost:6379/1
# Visit http://localhost:9181
```

**Benefits**:
- Offloads long-running work from request handlers
- Simple, battle-tested task queue
- Built-in monitoring dashboard
- Retry logic and failure handling

📖 **[Level 3 Complete Guide](docs/scaling/level3-background-tasks.md)**

#### Level 4: Horizontal Scaling

**When to use**: Single-server capacity exhausted, need to scale across multiple nodes.

**Installation**:
```bash
# Kubernetes plugin
pip install -e ".[k8s]"

# Docker Swarm plugin
pip install -e ".[swarm]"

# Both
pip install -e ".[all-scaling]"
```

**Kubernetes Deployment**:
```bash
# Using included plugin
python -m deployment.plugins.kubernetes deploy \
  --namespace production \
  --replicas 5 \
  --image my-registry.com/api:v1.0

# Scale up/down
python -m deployment.plugins.kubernetes scale --replicas 10

# Status
python -m deployment.plugins.kubernetes status
```

**Docker Swarm Deployment**:
```bash
# Using included plugin
python -m deployment.plugins.swarm deploy \
  --stack-name myapp \
  --replicas 5

# Scale
python -m deployment.plugins.swarm scale --replicas 10

# Status
python -m deployment.plugins.swarm status
```

**Load Balancer Configuration** (nginx example from `deployment/nginx.conf`):
```nginx
upstream backend {
    least_conn;  # Better than round-robin for async apps
    server node1:8000 max_fails=3 fail_timeout=30s;
    server node2:8000 max_fails=3 fail_timeout=30s;
    server node3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://backend/api/v1/health/ready;
    }
}
```

**Key considerations**:
- **Shared state**: Use Redis for sessions, caching, rate limits
- **Session affinity**: Not required (stateless design)
- **Database connections**: Adjust pool size per worker per node
- **Health checks**: Both liveness (`/health/live`) and readiness (`/health/ready`)

**Auto-scaling example** (Kubernetes HPA):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
```

**Benefits**:
- Linear scalability (add nodes = add capacity)
- Geographic distribution possible
- High availability through redundancy
- Auto-scaling based on metrics

📖 **[Level 4 Complete Guide](docs/scaling/level4-horizontal-scaling.md)**

#### Scaling Decision Matrix

| Traffic Level | Scaling Level | Setup Complexity | Monthly Cost* | Recommendation |
|--------------|---------------|------------------|---------------|----------------|
| < 10K req/sec | Level 1 (Multi-worker) | Very Low | $20-50 | Single VPS |
| 10-50K req/sec | Level 2 (Gunicorn) | Low | $50-200 | Single dedicated server |
| 50-100K req/sec | Level 2 + Level 3 | Medium | $200-500 | Add task workers |
| 100K-500K req/sec | Level 4 (3-5 nodes) | High | $500-2000 | Kubernetes/Swarm |
| > 500K req/sec | Level 4 (10+ nodes) | Very High | $2000+ | Enterprise setup |

*Cost estimates are approximate and vary by provider

#### Additional Resources

- 📖 **[Scaling Overview](docs/scaling/README.md)** - Complete introduction to all scaling levels
- 📊 **[Load Testing Guide](docs/scaling/load-testing.md)** - How to measure and validate scaling
- 🔧 **[Troubleshooting](docs/scaling/troubleshooting.md)** - Common scaling issues and solutions
- 🎯 **[Migration Paths](docs/scaling/README.md#migration-paths)** - Moving between scaling levels

#### Philosophy Alignment

This scaling architecture embodies our core principles:

- **Ruthless Simplicity**: Start with Level 1 (configuration only), add complexity only when needed
- **Trust in Emergence**: Complex scalability emerges from simple components (workers + load balancer)
- **Modular Design**: Each level is independent, can be adopted separately
- **Progressive Enhancement**: Clear migration path as requirements grow

### How to Extend

**Adding health checks**:
```python
async def check_external_api(self) -> ProbeStatus:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://external-api.com/health")
            return ProbeStatus.PASS if response.status_code == 200 else ProbeStatus.FAIL
    except Exception:
        return ProbeStatus.FAIL
```

**Custom deployment scripts**:
Create `scripts/deploy.sh`:
```bash
#!/bin/bash
set -e

echo "Running migrations..."
alembic upgrade head

echo "Building Docker image..."
docker build -t my-api:$VERSION .

echo "Pushing to registry..."
docker push my-api:$VERSION

echo "Deploying to Kubernetes..."
kubectl set image deployment/fastapi-backend api=my-api:$VERSION
kubectl rollout status deployment/fastapi-backend

echo "Deployment complete!"
```

## 5. Further Exploration

### Production Operations
- [The Twelve-Factor App](https://12factor.net/) - Modern app methodology
- [Site Reliability Engineering](https://sre.google/books/) - Google's SRE practices
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/) - K8s configuration

### Monitoring & Observability
- [Prometheus Documentation](https://prometheus.io/docs/) - Metrics collection
- [Grafana Dashboards](https://grafana.com/docs/) - Metrics visualization
- [OpenTelemetry](https://opentelemetry.io/) - Distributed tracing standard
- [Structured Logging](https://www.structlog.org/) - Structlog documentation

### Security Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Common vulnerabilities
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725) - JWT security considerations
- [Security Headers](https://securityheaders.com/) - Check your security headers

### Database & Performance
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) - ORM reference
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html) - Query optimization
- [Database Indexing](https://use-the-index-luke.com/) - Index strategies

---

# Part IV: Reference

*Quick lookup reference for configuration, middleware, and best practices*

## 1. Configuration Reference

### Complete Environment Variables

All configuration via environment variables with `APP_` or `SECURITY_` prefix.

#### Core Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_ENVIRONMENT` | enum | `local` | Environment: `local`, `test`, `staging`, `production` |
| `APP_DEBUG` | bool | `false` | Enable debug mode (detailed errors, body logging) |
| `APP_PROJECT_NAME` | string | `"CMS Backend API"` | Application name |
| `APP_PROJECT_VERSION` | string | `"0.1.0"` | Application version |
| `APP_API_PREFIX` | string | `"/api/v1"` | API route prefix |
| `APP_LOG_LEVEL` | string | `"INFO"` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `APP_LOG_FORMAT` | enum | `"json"` | Log format: `json` or `console` |
| `APP_LOG_INCLUDE_CALLER` | bool | `false` | Include caller info in logs |

#### CORS & Security

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_CORS_ALLOW_ORIGINS` | json array | `[]` | Allowed CORS origins: `["http://localhost:3000"]` |
| `APP_CORS_ALLOW_CREDENTIALS` | bool | `true` | Allow credentials in CORS |
| `APP_ALLOWED_HOSTS` | json array | `["*"]` | Trusted host headers |

#### Database

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_DATABASE_URL` | string | `sqlite+aiosqlite:///./app.db` | Async database URL |
| `APP_DATABASE_POOL_SIZE` | int | `5` | Connection pool size |
| `APP_DATABASE_ECHO` | bool | `false` | Log all SQL queries |

#### Security Settings - Phase 1

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECURITY_RATE_LIMIT_ENABLED` | bool | `true` | Enable rate limiting |
| `SECURITY_RATE_LIMIT_PER_MINUTE` | int | `60` | Requests per minute limit |
| `SECURITY_RATE_LIMIT_PER_HOUR` | int | `1000` | Requests per hour limit |
| `SECURITY_RATE_LIMIT_BURST` | int | `10` | Burst allowance above per-minute limit |
| `SECURITY_MAX_UPLOAD_SIZE` | int | `52428800` | Max upload size in bytes (50MB) |
| `SECURITY_MAX_REQUEST_SIZE` | int | `1048576` | Max request size in bytes (1MB) |
| `SECURITY_BLOCK_NULL_BYTES` | bool | `true` | Block null bytes in URLs |
| `SECURITY_ENABLE_HSTS` | bool | `true` | Enable HSTS header in production |
| `SECURITY_ENABLE_CSP` | bool | `false` | Enable Content Security Policy |
| `SECURITY_CSP_POLICY` | string | `"default-src 'self'"` | CSP policy string |
| `SECURITY_TRUSTED_PROXIES` | json set | `["127.0.0.1", "::1"]` | Trusted proxy IPs |
| `SECURITY_TRUST_PROXY_HEADERS` | bool | `false` | Trust X-Forwarded-* headers |

#### Security Settings - Phase 2

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECURITY_REDIS_URL` | string | `null` | Redis connection URL |
| `SECURITY_REDIS_ENABLED` | bool | `false` | Enable Redis features |
| `SECURITY_JWT_SECRET` | string | `null` | JWT signing secret (required in production) |
| `SECURITY_JWT_ALGORITHM` | string | `"HS256"` | JWT signing algorithm |
| `SECURITY_JWT_EXPIRY_MINUTES` | int | `60` | Access token expiry in minutes |
| `SECURITY_API_KEY_HEADER` | string | `"X-API-Key"` | API key header name |

#### Security Settings - Phase 3

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECURITY_ENABLE_GEO_BLOCKING` | bool | `false` | Enable GeoIP blocking |
| `SECURITY_GEOIP_DATABASE_PATH` | string | `null` | Path to GeoIP database |
| `SECURITY_ALLOWED_COUNTRIES` | json set | `null` | Allowed country codes (allowlist) |
| `SECURITY_BLOCKED_COUNTRIES` | json set | `[]` | Blocked country codes (blocklist) |
| `SECURITY_ENABLE_CIRCUIT_BREAKER` | bool | `false` | Enable circuit breaker |
| `SECURITY_CIRCUIT_BREAKER_THRESHOLD` | int | `5` | Failures before opening circuit |
| `SECURITY_CIRCUIT_BREAKER_TIMEOUT` | int | `60` | Circuit recovery timeout in seconds |
| `SECURITY_ENABLE_DDOS_PROTECTION` | bool | `false` | Enable DDoS protection |
| `SECURITY_ENABLE_PROMETHEUS` | bool | `false` | Enable Prometheus metrics |
| `SECURITY_ENABLE_ALERTING` | bool | `false` | Enable security alerting |
| `SECURITY_ALERT_RATE_LIMIT_THRESHOLD` | int | `100` | Alert on rate limit violations |
| `SECURITY_ALERT_AUTH_FAILURE_THRESHOLD` | int | `50` | Alert on auth failures |

### Configuration Examples

**Local development**:
```bash
APP_ENVIRONMENT=local
APP_DEBUG=true
APP_LOG_FORMAT=console
APP_LOG_LEVEL=DEBUG
APP_CORS_ALLOW_ORIGINS=["http://localhost:3000"]
```

**Production**:
```bash
APP_ENVIRONMENT=production
APP_DEBUG=false
APP_LOG_FORMAT=json
APP_LOG_LEVEL=INFO
APP_CORS_ALLOW_ORIGINS=["https://app.example.com"]
APP_ALLOWED_HOSTS=["api.example.com"]

SECURITY_JWT_SECRET=<generated-secret>
SECURITY_ENABLE_HSTS=true
SECURITY_RATE_LIMIT_ENABLED=true
SECURITY_REDIS_ENABLED=true
SECURITY_REDIS_URL=redis://redis:6379/0

APP_DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/production
APP_DATABASE_POOL_SIZE=10
```

## 2. Middleware Reference

### Middleware Execution Order

**Critical**: Order matters. First added = outermost (processes requests last).

```
1. SecurityHeadersMiddleware       (outermost - response headers)
2. SimpleRateLimitMiddleware       (block early if rate limited)
3. ContentValidationMiddleware     (validate before processing)
4. ProxyHeadersMiddleware          (fix client IP if behind proxy)
5. JWTAuthenticationMiddleware     (authenticate if enabled)
6. TrustedHostMiddleware           (validate host header)
7. CORSMiddleware                  (handle CORS if configured)
8. RequestIDMiddleware             (assign request ID)
9. RequestLoggingMiddleware        (innermost - log everything)
```

### Middleware Details Table

| Middleware | Location | Phase | Purpose | Configuration |
|------------|----------|-------|---------|---------------|
| SecurityHeadersMiddleware | `middleware/security.py:20` | 1 | Add security headers | `SECURITY_ENABLE_HSTS`, `SECURITY_ENABLE_CSP` |
| SimpleRateLimitMiddleware | `middleware/security.py:214` | 1 | In-memory rate limiting | `SECURITY_RATE_LIMIT_*` |
| RedisRateLimitMiddleware | `middleware/rate_limit.py` | 2 | Redis-backed rate limiting | `SECURITY_REDIS_URL` |
| ContentValidationMiddleware | `middleware/security.py:88` | 1 | Validate content-type and size | `SECURITY_MAX_*_SIZE` |
| ProxyHeadersMiddleware | `middleware/security.py:383` | 1 | Trust proxy headers | `SECURITY_TRUST_PROXY_HEADERS` |
| JWTAuthenticationMiddleware | `middleware/auth.py` | 2 | JWT authentication | `SECURITY_JWT_SECRET` |
| TrustedHostMiddleware | FastAPI built-in | 1 | Validate Host header | `APP_ALLOWED_HOSTS` |
| CORSMiddleware | FastAPI built-in | 1 | CORS handling | `APP_CORS_ALLOW_ORIGINS` |
| RequestIDMiddleware | `core/middleware.py:16` | 1 | Request ID tracking | Always enabled |
| RequestLoggingMiddleware | `core/middleware.py:39` | 1 | Request/response logging | `APP_DEBUG` for body logging |
| GeoBlockingMiddleware | `middleware/advanced.py` | 3 | GeoIP blocking | `SECURITY_GEOIP_DATABASE_PATH` |
| CircuitBreakerMiddleware | `middleware/advanced.py` | 3 | Circuit breaker | `SECURITY_CIRCUIT_BREAKER_*` |
| MetricsMiddleware | `middleware/monitoring.py` | 3 | Prometheus metrics | `SECURITY_ENABLE_PROMETHEUS` |

### Enabling/Disabling Middleware

**Conditional registration** in `src/app/core/middleware.py:92`:

Middleware is only registered if:
- Settings enable it
- Required dependencies installed
- Environment appropriate

**Example**: Rate limiting
```python
if security_settings.rate_limit_enabled:
    if security_settings.redis_enabled and security_settings.redis_url:
        # Use Redis rate limiter
        app.add_middleware(RedisRateLimitMiddleware, ...)
    else:
        # Use in-memory rate limiter
        app.add_middleware(SimpleRateLimitMiddleware, ...)
```

### Custom Middleware

**Adding custom middleware**:

1. Create `src/app/middleware/custom.py`:
   ```python
   from starlette.middleware.base import BaseHTTPMiddleware

   class CustomMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           # Before request
           response = await call_next(request)
           # After request
           return response
   ```

2. Register in `src/app/core/middleware.py:92`:
   ```python
   app.add_middleware(CustomMiddleware)
   ```

3. **Consider order carefully** - where should it execute in the pipeline?

## 3. Best Practices Checklist

### Development

- [ ] Use type hints everywhere (`def func(x: int) -> str:`)
- [ ] Write docstrings for public functions and classes
- [ ] Keep functions focused (single responsibility)
- [ ] Use async/await for I/O operations
- [ ] Handle errors explicitly (don't use bare `except:`)
- [ ] Log with context (`logger.info("event", key=value)`)
- [ ] Use Pydantic for data validation
- [ ] Inject dependencies via FastAPI DI
- [ ] Write tests for new features
- [ ] Run linter before committing (`ruff check .`)

### Configuration

- [ ] Never hardcode secrets in code
- [ ] Use environment variables for config
- [ ] Provide defaults for non-sensitive values
- [ ] Document all environment variables in `.env.example`
- [ ] Validate configuration on startup
- [ ] Use different configs per environment
- [ ] Keep production config secure

### Security

- [ ] Enable rate limiting in production
- [ ] Set strong `JWT_SECRET` (32+ random bytes)
- [ ] Use HTTPS in production
- [ ] Enable HSTS in production
- [ ] Configure CORS restrictively
- [ ] Validate all user input
- [ ] Use parameterized database queries
- [ ] Keep dependencies updated
- [ ] Review security logs regularly
- [ ] Never log sensitive data (passwords, tokens)

### Database

- [ ] Use async database operations
- [ ] Properly close connections (context managers)
- [ ] Use connection pooling
- [ ] Index frequently queried columns
- [ ] Use transactions for multi-step operations
- [ ] Handle database errors gracefully
- [ ] Test with in-memory database
- [ ] Run migrations before deployment
- [ ] Back up database regularly

### API Design

- [ ] Use consistent naming conventions
- [ ] Version your API (`/api/v1/`)
- [ ] Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- [ ] Return appropriate status codes
- [ ] Use Pydantic for request/response models
- [ ] Document with docstrings (appears in OpenAPI)
- [ ] Handle errors consistently
- [ ] Paginate list endpoints
- [ ] Use dependency injection for shared resources

### Testing

- [ ] Write tests for new features
- [ ] Test happy path and error cases
- [ ] Use pytest fixtures for common setup
- [ ] Mock external dependencies
- [ ] Run tests before committing
- [ ] Maintain test coverage above 70%
- [ ] Test with realistic data
- [ ] Test authentication/authorization

### Deployment

- [ ] Set `APP_ENVIRONMENT=production`
- [ ] Disable debug mode (`APP_DEBUG=false`)
- [ ] Use JSON log format (`APP_LOG_FORMAT=json`)
- [ ] Configure proper CORS origins
- [ ] Set allowed hosts
- [ ] Use strong secrets
- [ ] Run database migrations
- [ ] Configure health checks
- [ ] Set up log aggregation
- [ ] Monitor application metrics
- [ ] Configure auto-scaling
- [ ] Set resource limits
- [ ] Plan disaster recovery

### Operations

- [ ] Monitor error rates
- [ ] Track response times
- [ ] Set up alerting
- [ ] Review logs regularly
- [ ] Keep dependencies updated
- [ ] Back up database
- [ ] Document runbooks
- [ ] Test disaster recovery
- [ ] Rotate secrets periodically
- [ ] Monitor resource usage

## 4. Troubleshooting Guide

### Common Issues

#### Port Already in Use

**Symptom**: `Address already in use` error when starting server

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn app.main:create_app --factory --port 8001
```

#### Import Errors

**Symptom**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```bash
# Ensure virtual environment activated
source .venv/bin/activate

# Reinstall dependencies
pip install -e ".[dev]"

# Verify Python path
python -c "import sys; print(sys.path)"
```

#### Database Connection Errors

**Symptom**: `Cannot connect to database` or `Connection refused`

**Solutions**:
```bash
# Check database URL format
echo $APP_DATABASE_URL

# For PostgreSQL, ensure service running
pg_ctl status

# For SQLite, check file permissions
ls -la app.db

# Test connection manually
python -c "from sqlalchemy import create_engine; engine = create_engine('$APP_DATABASE_URL'); print('Connected')"
```

#### Rate Limit Not Working

**Symptom**: Rate limiting not blocking requests

**Solution**:
```bash
# Verify enabled in settings
echo $SECURITY_RATE_LIMIT_ENABLED

# Check logs for middleware registration
grep "rate.limit" logs/app.log

# Test with curl
for i in {1..100}; do curl http://localhost:8000/api/v1/health/live; done
# Should see 429 responses after hitting limit
```

#### CORS Errors

**Symptom**: Browser shows CORS error

**Solutions**:
```bash
# Check CORS origins configured
echo $APP_CORS_ALLOW_ORIGINS

# Ensure origin matches exactly (including protocol and port)
# Bad: http://localhost
# Good: http://localhost:3000

# Check middleware registered
grep "CORS" logs/app.log

# Test with curl (should see CORS headers)
curl -H "Origin: http://localhost:3000" http://localhost:8000/api/v1/health/live -v
```

#### JWT Authentication Fails

**Symptom**: Always getting 401 Unauthorized

**Solutions**:
```bash
# Verify JWT_SECRET set
echo $SECURITY_JWT_SECRET

# Check token format
# Should be: Authorization: Bearer <token>

# Decode token to check expiry
# Use jwt.io or:
python -c "import jwt; print(jwt.decode('$TOKEN', options={'verify_signature': False}))"

# Check middleware registered
grep "JWT" logs/app.log
```

#### Slow Performance

**Symptoms**: High response times, timeouts

**Diagnostic steps**:
```bash
# Check logs for slow queries
grep "duration_ms" logs/app.log | awk '{if ($NF > 1000) print}'

# Monitor database connections
# For PostgreSQL:
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check worker count
ps aux | grep uvicorn

# Monitor memory usage
free -h

# Check database indexes
# Missing indexes can cause slow queries
```

**Solutions**:
- Add database indexes for frequently queried columns
- Increase worker count
- Enable Redis caching (Phase 2)
- Optimize database queries
- Add connection pooling (already configured)

#### Memory Leaks

**Symptom**: Memory usage grows over time

**Diagnostic steps**:
```bash
# Monitor memory over time
watch -n 5 'ps aux | grep uvicorn'

# Check for rate limiter cleanup
grep "rate_limit.cleanup" logs/app.log

# Profile with tracemalloc
python -c "import tracemalloc; tracemalloc.start(); # run app"
```

**Common causes**:
- Rate limiter not cleaning up old entries (check `_cleanup_old_entries`)
- Database connections not closed (use context managers)
- Large objects in global scope

#### Tests Failing

**Symptom**: Tests pass locally but fail in CI

**Solutions**:
```bash
# Run tests with same environment
APP_ENVIRONMENT=test pytest

# Check for timing issues
pytest -v --log-cli-level=DEBUG

# Run specific failing test
pytest tests/test_module.py::test_function -v

# Check for port conflicts
# Tests might not clean up properly
pkill -f "pytest"
```

### Debug Mode

Enable detailed error messages and body logging:

```bash
APP_DEBUG=true
APP_LOG_LEVEL=DEBUG
```

**In debug mode**:
- Detailed stack traces in responses
- Request body logged (first 256 bytes)
- SQL queries logged (if `DATABASE_ECHO=true`)
- Interactive debugger (if using `--reload`)

**⚠️ Never enable in production** - exposes sensitive information.

### Health Check Status Codes

Understanding health endpoint responses:

**Liveness** (`/api/v1/health/live`):
- `200 OK`: Application is running
- `5xx`: Application not responding (should restart)

**Readiness** (`/api/v1/health/ready`):
- `200 OK`: Ready to serve traffic
- `503 Service Unavailable`: Dependencies not ready (database, cache)
- `5xx`: Application error

**Kubernetes behavior**:
- Liveness failure: Restarts pod
- Readiness failure: Removes from service endpoints

### Getting Help

**Documentation**:
- This guide
- FastAPI docs: https://fastapi.tiangolo.com/
- Project README: [../README.md](../README.md)
- CONTRIBUTING: [../CONTRIBUTING.md](../CONTRIBUTING.md)

**Debugging resources**:
- Check application logs
- Review middleware configuration
- Verify environment variables
- Test with curl for API issues
- Use Python debugger for code issues

**Common commands**:
```bash
# View logs
tail -f logs/app.log

# Test endpoint
curl -v http://localhost:8000/api/v1/health/live

# Check configuration
python -c "from app.core.config import get_app_settings; s = get_app_settings(); print(s.model_dump())"

# Run single test
pytest tests/test_file.py::test_function -vv

# Interactive Python shell
python
>>> from app.main import create_app
>>> app = create_app()
```

## 5. Further Exploration

### Official Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Framework reference
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) - ORM documentation
- [Structlog](https://www.structlog.org/) - Structured logging
- [Uvicorn](https://www.uvicorn.org/) - ASGI server

### Tools & Libraries
- [Ruff](https://docs.astral.sh/ruff/) - Fast Python linter
- [pytest](https://docs.pytest.org/) - Testing framework
- [Docker](https://docs.docker.com/) - Containerization
- [Kubernetes](https://kubernetes.io/docs/) - Orchestration
- [Prometheus](https://prometheus.io/docs/) - Metrics and monitoring

### Best Practices Resources
- [The Twelve-Factor App](https://12factor.net/) - Cloud-native methodology
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Security risks
- [REST API Design](https://restfulapi.net/) - API best practices
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html) - Database optimization

### Community
- [FastAPI GitHub](https://github.com/tiangolo/fastapi) - Source code and issues
- [FastAPI Discord](https://discord.com/invite/VQjSZaeJmf) - Community chat
- [Stack Overflow](https://stackoverflow.com/questions/tagged/fastapi) - Q&A

### Related Projects
- [Full Stack FastAPI Template](https://github.com/tiangolo/full-stack-fastapi-template) - Full-stack template by FastAPI creator
- [FastAPI Users](https://github.com/fastapi-users/fastapi-users) - Authentication system
- [FastAPI Plugins](https://github.com/madkote/fastapi-plugins) - Additional utilities

---

## Document Maintenance

**Last Updated**: 2025-10-24

**Version**: 1.0.0

**Maintained By**: Backend development team

**Feedback**: Report issues or suggest improvements via project repository

---

*This guide is the authoritative reference for the production-fastapi-backend. For quick start instructions, see [QUICKSTART.md](../QUICKSTART.md). For contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).*
