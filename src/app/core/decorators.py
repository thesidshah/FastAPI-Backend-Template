"""Decorators for adding logging and other cross-cutting concerns."""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar, cast

import structlog

# Type variables for generic decorator typing
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def with_logger(cls_or_func: type[T] | F) -> type[T] | F:
    """
    Decorator that adds a structlog logger to a class or function.

    For classes:
        Adds a 'logger' attribute to the class that can be accessed via self.logger.
        The logger name is automatically set to the fully qualified class name.

    For functions:
        Adds a 'logger' attribute to the function that can be accessed within the function.
        The logger name is automatically set to the fully qualified function name.

    Example usage with a class:
        @with_logger
        class MyService:
            def process(self):
                self.logger.info("Processing started")
                # ... do work ...
                self.logger.info("Processing completed")

    Example usage with a function:
        @with_logger
        def my_function():
            my_function.logger.info("Function called")
            # ... do work ...
            my_function.logger.info("Function completed")

    Args:
        cls_or_func: The class or function to decorate

    Returns:
        The decorated class or function with a logger attached
    """
    if isinstance(cls_or_func, type):
        # It's a class
        cls = cls_or_func
        logger_name = f"{cls.__module__}.{cls.__qualname__}"
        logger = structlog.get_logger(logger_name)

        # Store the logger as a class attribute
        cls.logger = logger  # type: ignore

        return cast(type[T], cls)
    else:
        # It's a function
        func = cls_or_func
        logger_name = f"{func.__module__}.{func.__qualname__}"
        logger = structlog.get_logger(logger_name)

        # Add logger as a function attribute
        func.logger = logger  # type: ignore

        # Wrap the function to maintain metadata
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Also add logger to the wrapper so it's accessible
        wrapper.logger = logger  # type: ignore

        return cast(F, wrapper)
