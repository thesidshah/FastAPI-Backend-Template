# Logging Decorator Guide

## Overview

The `@with_logger` decorator provides an easy way to add structured logging to any class or function in your application. It automatically creates a logger instance with the fully qualified name of the class or function.

## Installation

The decorator is available in `app.core.decorators` and can be imported as:

```python
from app.core import with_logger
```

## Usage

### Using with Classes

When applied to a class, the decorator adds a `logger` attribute that can be accessed via `self.logger`:

```python
from app.core import with_logger

@with_logger
class UserService:
    def create_user(self, username: str) -> dict:
        self.logger.info("Creating user", username=username)

        user = {"id": 1, "username": username}

        self.logger.info("User created successfully", user_id=user["id"])
        return user

    def delete_user(self, user_id: int) -> None:
        self.logger.warning("Deleting user", user_id=user_id)
        # Deletion logic here
        self.logger.info("User deleted", user_id=user_id)
```

**Logger name format:** `module.path.ClassName`
**Example:** `app.services.user.UserService`

### Using with Functions

When applied to a function, the decorator adds a `logger` attribute to the function itself:

```python
from app.core import with_logger

@with_logger
def process_payment(amount: float, currency: str = "USD") -> bool:
    process_payment.logger.info("Processing payment", amount=amount, currency=currency)

    if amount <= 0:
        process_payment.logger.error("Invalid payment amount", amount=amount)
        return False

    process_payment.logger.info("Payment processed successfully", amount=amount)
    return True
```

**Logger name format:** `module.path.function_name`
**Example:** `app.services.payment.process_payment`

## Logging Levels

The decorator uses structlog, which supports standard Python logging levels:

```python
@with_logger
class ExampleService:
    def example_method(self):
        self.logger.debug("Detailed debug information")
        self.logger.info("General information")
        self.logger.warning("Warning message")
        self.logger.error("Error occurred", error_code=500)
        self.logger.critical("Critical system failure")
```

## Structured Logging

All logs are structured and support key-value pairs:

```python
@with_logger
class OrderService:
    def place_order(self, order_id: str, items: list[str], total: float):
        self.logger.info(
            "Order placed",
            order_id=order_id,
            item_count=len(items),
            total_amount=total,
            currency="USD"
        )
```

**JSON Output:**
```json
{
  "event": "Order placed",
  "order_id": "ORD-12345",
  "item_count": 3,
  "total_amount": 150.50,
  "currency": "USD",
  "level": "info",
  "logger": "app.services.order.OrderService",
  "timestamp": "2025-10-16T16:38:19.547039Z"
}
```

**Console Output:**
```
2025-10-16T16:38:19.547039Z [info     ] Order placed              [app.services.order.OrderService] order_id=ORD-12345 item_count=3 total_amount=150.5 currency=USD
```

## Exception Logging

The decorator integrates with structlog's exception handling:

```python
@with_logger
class DataProcessor:
    def process_data(self, data: dict):
        try:
            # Processing logic
            result = self._validate_data(data)
            self.logger.info("Data processed successfully", record_count=len(result))
        except ValueError as e:
            self.logger.error(
                "Data validation failed",
                error=str(e),
                exc_info=True  # Includes full traceback
            )
            raise
```

## Advanced Usage

### Combining with Other Decorators

The `@with_logger` decorator works well with other decorators:

```python
from functools import lru_cache
from app.core import with_logger

@with_logger
class ConfigService:
    @lru_cache(maxsize=1)
    def get_config(self):
        self.logger.info("Loading configuration")
        # Configuration loading logic
        return {"setting": "value"}
```

### Using in Async Functions/Methods

The decorator fully supports async code:

```python
@with_logger
class AsyncService:
    async def fetch_data(self, url: str) -> dict:
        self.logger.info("Fetching data", url=url)
        # Async fetch logic
        self.logger.info("Data fetched successfully")
        return {}

@with_logger
async def async_function():
    async_function.logger.info("Async function called")
    # Async logic here
```

## Configuration

The logger behavior is controlled by the application settings:

- `APP_LOG_LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `APP_LOG_FORMAT`: Choose format (json or console)
- `APP_LOG_INCLUDE_CALLER`: Include caller information (true/false)

Example `.env` configuration:
```env
APP_LOG_LEVEL=INFO
APP_LOG_FORMAT=json
APP_LOG_INCLUDE_CALLER=false
```

## Best Practices

1. **Apply to classes that need logging**: Use `@with_logger` on service classes, repositories, and business logic components.

2. **Use structured logging**: Pass context as key-value pairs rather than formatting strings:
   ```python
   # Good
   self.logger.info("User created", user_id=user_id, username=username)

   # Avoid
   self.logger.info(f"User {user_id} created with username {username}")
   ```

3. **Choose appropriate log levels**:
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General operational messages
   - `WARNING`: Warning messages for potentially harmful situations
   - `ERROR`: Error messages for serious problems
   - `CRITICAL`: Critical messages for severe errors

4. **Include relevant context**: Add meaningful key-value pairs that help with debugging:
   ```python
   self.logger.error(
       "Database connection failed",
       host=db_host,
       port=db_port,
       retry_count=retry_count,
       max_retries=max_retries
   )
   ```

5. **Don't log sensitive information**: Never log passwords, tokens, or other sensitive data:
   ```python
   # Bad
   self.logger.info("User logged in", password=password)

   # Good
   self.logger.info("User logged in", user_id=user_id)
   ```

## Examples

See [examples/logging_decorator_example.py](../examples/logging_decorator_example.py) for complete working examples.

## Implementation Details

The decorator is implemented in [src/app/core/decorators.py](../src/app/core/decorators.py) and uses:
- **structlog** for structured logging
- **Python's standard logging** as the backend
- Automatic logger naming based on module and class/function name

The logger name format ensures:
- Easy filtering of logs by module or class
- Clear identification of log sources
- Consistent naming across the application
