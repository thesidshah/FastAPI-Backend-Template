# Code reading

This document is a guide to help you understand the structure of the Commission Management System (CMS) backend codebase.

# Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [What to expect?](#what-to-expect)
- [Where to find it?](#where-to-find-it)
- [How to use it?](#how-to-use-it)
- [Code Style and Linting](#code-style-and-linting)
- [Type Checking](#type-checking)
- [Troubleshooting](#troubleshooting)

# Quick Start

```bash
# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env  # Edit with your configuration

# Run the application
uvicorn src.app.main:app --reload

# Access the API documentation
# Open http://localhost:8000/docs in your browser
```

# Prerequisites

Before working with this project, ensure you have:
- **Python 3.11+** installed
- **uv** package manager installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Basic knowledge of FastAPI and async Python
- A code editor with Python support (VS Code, PyCharm, etc.)

# Sections
## What to expect?

This project is a Python-based backend built with the [FastAPI](https://fastapi.tiangolo.com/) framework. It serves as the API for the Commission Management System (CMS) application.

Here's a quick overview of the technologies used:
- **FastAPI:** For building the high-performance API.
- **Pydantic:** For data validation and settings management.
- **uv:** For package management.
- **pytest:** For running tests.
- **ruff:** For linting and code formatting.

The codebase is structured to have a clear separation of concerns, making it easier to navigate and maintain.

## Where to find it?

The code is organized into several directories, each with a specific purpose.

-   `pyproject.toml`: This file contains all the project metadata, dependencies, and tool configurations (like `pytest`, `ruff`, and `mypy`). Start here to understand what packages are used in the project.

-   `src/app/`: This is the main application package.
    -   `main.py`: The entry point of the application. It contains the `create_app` factory function which initializes the FastAPI app, configures logging, registers middleware, and includes API routers.
    -   `api/`: This is the API layer.
        -   `routes/`: Each file in this directory corresponds to a set of related API endpoints (e.g., `health.py` for health checks). Routers from here are included in the main app.
    -   `core/`: This directory holds the core application logic and configuration.
        -   `config.py`: Defines the application settings using Pydantic's `BaseSettings`.
        -   `lifespan.py`: Manages application startup and shutdown events.
        -   `logging.py`: Configures application-wide logging.
        -   `middleware.py`: Contains custom middleware for processing requests and responses.
    -   `dependencies/`: For FastAPI's dependency injection system. This is where you'd put dependencies that need to be shared across different parts of the application.
    -   `schemas/`: Contains Pydantic models (schemas) that define the data shape for API requests and responses.
    -   `services/`: This is the business logic layer. Functions here are called by the API routes to perform the actual work.
    -   `utils/`: A place for miscellaneous utility functions that can be used anywhere in the application.

-   `tests/`: This directory contains all the automated tests for the application. Tests are written using `pytest`.

## How to use it?

Here are some common development workflows:

### Installing Dependencies

Install all project dependencies using `uv`:
```bash
uv sync
```

This will create a virtual environment and install all dependencies specified in `pyproject.toml`.

### Environment Configuration

The application uses environment variables for configuration. Create a `.env` file in the project root:

```bash
# Copy the example file (if available)
cp .env.example .env

# Edit the .env file with your settings
```

Common environment variables include:
- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT`: Current environment (development, staging, production)
- Database connection settings (if applicable)
- API keys and secrets

### Running the application

To run the application locally for development, you can use `uvicorn`:
```bash
uvicorn src.app.main:app --reload
```
This will start a development server on `http://localhost:8000` that automatically reloads when you make changes to the code.

**Accessing API Documentation:**
FastAPI automatically generates interactive API documentation:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Running tests

To run the test suite, simply run `pytest` from the root of the project:
```bash
pytest
```

**Run tests with coverage:**
```bash
pytest --cov=src --cov-report=html
```
This generates a coverage report in `htmlcov/index.html`.

**Run specific tests:**
```bash
# Run a specific test file
pytest tests/test_health.py

# Run a specific test function
pytest tests/test_health.py::test_health_endpoint
```

### Adding a new feature (e.g., a new API endpoint)

A typical workflow for adding a new feature would be:

1.  **Define the data shape:** Create or update a Pydantic schema in the `src/app/schemas/` directory. This will define the structure of your request and response bodies.

    ```python
    # src/app/schemas/user.py
    from pydantic import BaseModel

    class UserCreate(BaseModel):
        username: str
        email: str

    class UserResponse(BaseModel):
        id: int
        username: str
        email: str
    ```

2.  **Implement the business logic:** Add a new function to a relevant file in the `src/app/services/` directory. This function will contain the core logic for your feature.

    ```python
    # src/app/services/user.py
    async def create_user(user_data: UserCreate) -> UserResponse:
        # Your business logic here
        pass
    ```

3.  **Create the API endpoint:** Add a new route in the `src/app/api/routes/` directory. This route will use the service function you created and the schema for request/response validation.

    ```python
    # src/app/api/routes/user.py
    from fastapi import APIRouter
    from app.schemas.user import UserCreate, UserResponse
    from app.services.user import create_user

    router = APIRouter(prefix="/users", tags=["users"])

    @router.post("/", response_model=UserResponse)
    async def create_user_endpoint(user: UserCreate):
        return await create_user(user)
    ```

4.  **Register the router:** Include the new router in `src/app/main.py`:

    ```python
    from app.api.routes import user

    app.include_router(user.router)
    ```

5.  **Write a test:** Add a new test file in the `tests/` directory to ensure your new endpoint works as expected.

    ```python
    # tests/test_user.py
    def test_create_user(client):
        response = client.post("/users/", json={
            "username": "testuser",
            "email": "test@example.com"
        })
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"
    ```

## Code Style and Linting

The project uses `ruff` for both linting and code formatting.

**Run the linter:**
```bash
ruff check .
```

**Auto-fix linting issues:**
```bash
ruff check --fix .
```

**Format code:**
```bash
ruff format .
```

**Check formatting without making changes:**
```bash
ruff format --check .
```

## Type Checking

The project uses `mypy` for static type checking. Run type checks with:

```bash
mypy src/
```

Type checking configuration is defined in `pyproject.toml`.

## Troubleshooting

### Common Issues

**Import errors when running the application:**
- Ensure you've activated the virtual environment created by `uv`
- Run `uv sync` to ensure all dependencies are installed

**Port already in use:**
- Change the port: `uvicorn src.app.main:app --reload --port 8001`
- Or kill the process using port 8000

**Tests failing:**
- Ensure test database is properly configured (if using a database)
- Check that all test dependencies are installed
- Run tests with verbose output: `pytest -v`

**Environment variables not loading:**
- Verify `.env` file exists in the project root
- Check that variable names match those expected in `src/app/core/config.py`
- Ensure no typos in environment variable names

### Getting Help

- Check FastAPI documentation: https://fastapi.tiangolo.com/
- Review Pydantic documentation: https://docs.pydantic.dev/
- Check project-specific issues in the issue tracker
