import unittest

from tiny_deadline_ctx import DeadlineCtx, CancellationError
from tiny_deadline_ctx.core import DeadlineCtx as CoreDeadlineCtx


class Clock:
    """A mutable clock so tests can advance time deterministically."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t


class TestDeadlineCtx(unittest.TestCase):
    def test_exported_name_matches_core(self) -> None:
        self.assertIs(DeadlineCtx, CoreDeadlineCtx)

    def test_infinite_deadline_never_expires(self) -> None:
        clk = Clock(1000.0)
        ctx = DeadlineCtx(deadline_ms=None, now_ms=clk)
        self.assertFalse(ctx.expired())
        self.assertIsNone(ctx.remaining_ms())

    def test_deadline_not_yet_expired(self) -> None:
        clk = Clock(100.0)
        ctx = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        self.assertFalse(ctx.expired())
        self.assertEqual(ctx.remaining_ms(), 4900.0)

    def test_deadline_exact_boundary_expired(self) -> None:
        # now_ms == deadline_ms must count as expired.
        clk = Clock(5000.0)
        ctx = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        self.assertTrue(ctx.expired())
        self.assertEqual(ctx.remaining_ms(), 0.0)

    def test_deadline_past_expired(self) -> None:
        clk = Clock(6000.0)
        ctx = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        self.assertTrue(ctx.expired())
        self.assertEqual(ctx.remaining_ms(), -1000.0)

    def test_remaining_updates_with_clock(self) -> None:
        clk = Clock(100.0)
        ctx = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        self.assertEqual(ctx.remaining_ms(), 4900.0)
        clk.t = 4600.0
        self.assertEqual(ctx.remaining_ms(), 400.0)
        self.assertFalse(ctx.expired())
        clk.t = 5000.0
        self.assertTrue(ctx.expired())

    def test_cancel_mark(self) -> None:
        clk = Clock(0.0)
        ctx = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        self.assertFalse(ctx.expired())
        ctx.cancel()
        self.assertTrue(ctx.cancelled)
        self.assertTrue(ctx.expired())

    def test_from_parent_tightens_deadline(self) -> None:
        clk = Clock(0.0)
        parent = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        child = DeadlineCtx.from_parent(parent, deadline_ms=2000.0)
        self.assertEqual(child.deadline_ms, 2000.0)
        clk.t = 2500.0
        self.assertTrue(child.expired())
        self.assertFalse(parent.expired())

    def test_from_parent_cannot_loosen_deadline(self) -> None:
        clk = Clock(0.0)
        parent = DeadlineCtx(deadline_ms=2000.0, now_ms=clk)
        # Child tries to request a later deadline than the parent allows.
        child = DeadlineCtx.from_parent(parent, deadline_ms=5000.0)
        self.assertEqual(child.deadline_ms, 2000.0)
        clk.t = 3000.0
        self.assertTrue(child.expired())
        self.assertTrue(parent.expired())

    def test_from_parent_none_inherits_parent_deadline(self) -> None:
        clk = Clock(0.0)
        parent = DeadlineCtx(deadline_ms=2000.0, now_ms=clk)
        child = DeadlineCtx.from_parent(parent, deadline_ms=None)
        self.assertEqual(child.deadline_ms, 2000.0)

    def test_from_parent_inherits_infinite_deadline(self) -> None:
        clk = Clock(0.0)
        parent = DeadlineCtx(deadline_ms=None, now_ms=clk)
        child = DeadlineCtx.from_parent(parent, deadline_ms=2000.0)
        self.assertEqual(child.deadline_ms, 2000.0)
        self.assertFalse(child.expired())
        child2 = DeadlineCtx.from_parent(parent)
        self.assertIsNone(child2.deadline_ms)

    def test_from_parent_inherits_cancellation(self) -> None:
        clk = Clock(0.0)
        parent = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        parent.cancel()
        child = DeadlineCtx.from_parent(parent, deadline_ms=10000.0)
        self.assertTrue(child.cancelled)
        self.assertTrue(child.expired())

    def test_from_parent_uses_parent_clock(self) -> None:
        clk = Clock(100.0)
        parent = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        child = DeadlineCtx.from_parent(parent, deadline_ms=2000.0)
        # remaining_ms on the child is measured against the same clock.
        self.assertEqual(child.remaining_ms(), 1900.0)

    def test_cancellation_error_is_exception(self) -> None:
        self.assertTrue(issubclass(CancellationError, Exception))

    def test_raise_on_expired(self) -> None:
        clk = Clock(6000.0)
        ctx = DeadlineCtx(deadline_ms=5000.0, now_ms=clk)
        with self.assertRaises(CancellationError):
            if ctx.expired():
                raise CancellationError("deadline exceeded")


if __name__ == "__main__":
    unittest.main()
