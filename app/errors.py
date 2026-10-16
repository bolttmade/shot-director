"""Friendly engine errors. Adapters translate SDK exceptions into these."""

from __future__ import annotations


class EngineError(Exception):
    """Something the UI can show verbatim. `code` is stable, `hint` says what to do next."""

    code = "engine_error"
    http_status = 400

    def __init__(self, message: str, *, hint: str = "", retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.retryable = retryable

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "hint": self.hint, "retryable": self.retryable}


class InsufficientCredits(EngineError):
    code = "insufficient_credits"
    http_status = 402


class Unauthorized(EngineError):
    code = "unauthorized"
    http_status = 401


class QueueFull(EngineError):
    code = "queue_full"
    http_status = 429


class CapExceeded(EngineError):
    code = "cap_exceeded"
    http_status = 409


class NotConfigured(EngineError):
    code = "not_configured"
    http_status = 412


class ContentPolicy(EngineError):
    code = "content_policy_violation"
    http_status = 422


class JobFailed(EngineError):
    code = "job_failed"
    http_status = 502
