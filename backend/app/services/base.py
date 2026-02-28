"""
Base Service Interface

All services inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseService(ABC, Generic[InputT, OutputT]):
    """
    Base class for all services.

    Each service:
    - Has a defined input type
    - Has a defined output type
    - Can validate its inputs
    - Can check its health
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Service name for logging."""
        pass

    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """
        Execute the service's main function.

        Args:
            input_data: Validated input conforming to InputT schema

        Returns:
            Output conforming to OutputT schema

        Raises:
            ServiceError: If execution fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy and can process requests."""
        pass

    async def validate_input(self, input_data: InputT) -> InputT:
        """
        Validate input data.
        Default implementation returns input as-is (Pydantic handles validation).
        Override for custom validation logic.
        """
        return input_data


class ServiceError(Exception):
    """Base exception for service errors."""

    def __init__(self, service_name: str, message: str, details: dict = None):
        self.service_name = service_name
        self.message = message
        self.details = details or {}
        super().__init__(f"[{service_name}] {message}")


class ValidationError(ServiceError):
    """Input validation error."""
    pass


class ExternalAPIError(ServiceError):
    """External API call failed."""
    pass


class RateLimitError(ServiceError):
    """Rate limit exceeded."""
    pass
