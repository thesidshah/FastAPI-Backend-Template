# Contributing to FastAPI Production Starter

First off, thank you for considering contributing to this project! It's people like you that make this template better for everyone.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Process](#development-process)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Our Standards

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- A GitHub account

### Setting Up Your Development Environment

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/PROJECT_NAME.git
   cd PROJECT_NAME
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/PROJECT_NAME.git
   ```

4. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

5. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

6. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, etc.)
- Any relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- A clear and descriptive title
- A detailed description of the proposed feature
- Explain why this enhancement would be useful
- Provide examples of how it would be used
- List any alternative solutions you've considered

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:

- `good first issue` - Simple issues for beginners
- `help wanted` - Issues where we need community help
- `documentation` - Documentation improvements

### Pull Requests

1. Ensure your code follows the [Style Guidelines](#style-guidelines)
2. Update documentation as needed
3. Add tests for new functionality
4. Ensure all tests pass
5. Update the CHANGELOG.md if applicable

## Development Process

### Running Tests

Always run tests before submitting a pull request:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific tests
pytest tests/test_health.py -v
```

### Code Quality Checks

Run these checks before committing:

```bash
# Format code with Black
black src tests

# Lint with Ruff
ruff check src tests --fix

# Type checking with MyPy
mypy src

# Run all checks together
black src tests && ruff check src tests --fix && mypy src && pytest
```

### Testing Guidelines

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Test both success and failure cases
- Use async tests for async code

Example test structure:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_feature_success(client: AsyncClient):
    """Test successful feature behavior."""
    response = await client.get("/api/v1/feature")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_feature_validation_error(client: AsyncClient):
    """Test feature with invalid input."""
    response = await client.post("/api/v1/feature", json={})
    assert response.status_code == 422
```

## Style Guidelines

### Python Style Guide

We follow PEP 8 with some modifications:

- Line length: 88 characters (Black default)
- Use type hints for all function signatures
- Use descriptive variable names
- Prefer explicit over implicit

### Code Organization

- Keep functions focused and single-purpose
- Use dependency injection via FastAPI's `Depends`
- Separate business logic from API routes
- Place business logic in `services/`
- Use Pydantic models for validation

Example structure:

```python
# src/app/api/routes/example.py
from fastapi import APIRouter, Depends
from app.schemas.example import ExampleResponse
from app.services.example import ExampleService

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/", response_model=ExampleResponse)
async def get_example(
    service: ExampleService = Depends()
) -> ExampleResponse:
    """Get example data."""
    return await service.get_data()
```

### Documentation

- Use docstrings for all public functions/classes
- Follow Google-style docstrings
- Include type hints
- Document exceptions raised

Example:

```python
async def process_data(data: dict, user_id: str) -> ProcessedData:
    """Process user data and return results.

    Args:
        data: Raw data dictionary to process
        user_id: Unique identifier for the user

    Returns:
        ProcessedData: Validated and processed data

    Raises:
        ValidationError: If data is invalid
        ProcessingError: If processing fails
    """
    pass
```

## Commit Messages

Write clear, meaningful commit messages:

### Format

```
type(scope): brief description

Detailed explanation if needed.

- Bullet points for multiple changes
- Reference issues: Fixes #123
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(auth): add JWT refresh token support

Implement refresh token mechanism for extended sessions.
Tokens expire after 7 days and can be refreshed.

Fixes #45
```

```
fix(middleware): correct rate limit window calculation

The sliding window was incorrectly calculating timestamps,
causing premature resets. Now uses proper UTC timestamps.
```

## Pull Request Process

### Before Submitting

1. Update your fork:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Run all checks:
   ```bash
   black src tests
   ruff check src tests --fix
   mypy src
   pytest --cov=app
   ```

3. Update documentation
4. Add your changes to CHANGELOG.md (if it exists)

### Submitting

1. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a Pull Request on GitHub

3. Fill out the PR template completely

4. Link related issues

### PR Title Format

```
[Type] Brief description

Examples:
[Feature] Add user authentication
[Fix] Correct rate limiting calculation
[Docs] Update installation guide
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] Added new tests
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
```

### Review Process

1. Maintainers will review your PR
2. Address any feedback
3. Once approved, your PR will be merged
4. Your contribution will be recognized

## Questions?

Feel free to:
- Open an issue for questions
- Start a discussion
- Reach out to maintainers

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing!
