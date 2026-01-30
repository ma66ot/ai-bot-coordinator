"""
Domain exceptions for ClawBot Coordinator.

All domain errors inherit from DomainError to allow clean separation
between business logic errors and infrastructure errors.
"""


class DomainError(Exception):
    """Base exception for all domain-level errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ResourceNotFound(DomainError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} with id {resource_id} not found")


class InvalidStateTransition(DomainError):
    """Raised when attempting an invalid state machine transition."""

    def __init__(self, entity_type: str, current_state: str, attempted_action: str) -> None:
        self.entity_type = entity_type
        self.current_state = current_state
        self.attempted_action = attempted_action
        super().__init__(
            f"Cannot {attempted_action} {entity_type} in state {current_state}"
        )


class ResourceAlreadyExists(DomainError):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type} with identifier {identifier} already exists")


class ValidationError(DomainError):
    """Raised when domain validation rules are violated."""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"Validation failed for {field}: {reason}")


class AuthorizationError(DomainError):
    """Raised when an operation is not authorized."""

    def __init__(self, operation: str, reason: str) -> None:
        self.operation = operation
        self.reason = reason
        super().__init__(f"Not authorized to {operation}: {reason}")
