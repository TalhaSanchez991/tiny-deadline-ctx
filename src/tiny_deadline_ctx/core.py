"""Deadline propagation context with no third-party dependencies."""

from __future__ import annotations

from typing import Callable, Optional


class CancellationError(Exception):
    """Raised when an operation is attempted past its deadline."""


class DeadlineCtx:
    """Carry a monotonic deadline and optional cancel flag through nested calls.

    The deadline is expressed in milliseconds against a caller-supplied clock
    function (``now_ms``). Keeping the clock injectable makes timeouts
    deterministic in tests — no code path here ever reads wall-clock time.

    A ``DeadlineCtx`` may be derived from a parent via :meth:`from_parent`.
    The child inherits the parent's clock and cancel flag and may tighten the
    deadline but never loosen it: ``deadline_ms`` is the minimum of the
    parent's deadline and any new value. This guarantees a callee can never
    extend a deadline its caller did not authorize.
    """

    __slots__ = ("_deadline_ms", "_now_fn", "_cancelled")

    def __init__(
        self,
        deadline_ms: Optional[float] = None,
        now_ms: Callable[[], float] = lambda: 0.0,
        cancelled: bool = False,
    ) -> None:
        self._deadline_ms = deadline_ms
        self._now_fn = now_ms
        self._cancelled = cancelled

    @property
    def deadline_ms(self) -> Optional[float]:
        """The configured deadline in ``now_ms`` units, or ``None`` for infinite."""
        return self._deadline_ms

    @property
    def cancelled(self) -> bool:
        """Whether this context has been explicitly cancelled."""
        return self._cancelled

    def cancel(self) -> None:
        """Mark this context as cancelled so :meth:`expired` returns ``True``."""
        self._cancelled = True

    def expired(self) -> bool:
        """Return ``True`` if the deadline has passed or the context is cancelled."""
        if self._cancelled:
            return True
        if self._deadline_ms is None:
            return False
        # >= rather than > so a deadline of 0 immediately reports expired.
        return self._now_fn() >= self._deadline_ms

    def remaining_ms(self) -> Optional[float]:
        """Milliseconds remaining until expiry, or ``None`` if the deadline is infinite.

        Returns a negative number when the deadline has already passed, so
        callers can distinguish "no deadline" from "overrun by N ms".
        """
        if self._deadline_ms is None:
            return None
        return self._deadline_ms - self._now_fn()

    @classmethod
    def from_parent(
        cls,
        parent: "DeadlineCtx",
        deadline_ms: Optional[float] = None,
    ) -> "DeadlineCtx":
        """Derive a child context that cannot outlive its parent.

        The child shares the parent's clock and inherits its cancellation. The
        effective deadline is the tighter of the parent's deadline and the
        new ``deadline_ms``; passing ``None`` (the default) inherits the
        parent's deadline unchanged.
        """
        parent_deadline = parent._deadline_ms
        if deadline_ms is None:
            effective = parent_deadline
        elif parent_deadline is None:
            effective = deadline_ms
        else:
            effective = min(parent_deadline, deadline_ms)
        return cls(
            deadline_ms=effective,
            now_ms=parent._now_fn,
            cancelled=parent._cancelled,
        )
