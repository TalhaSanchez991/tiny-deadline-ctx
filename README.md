# tiny-deadline-ctx

Propagate a deadline through nested Python calls without a framework: carry a monotonic deadline and a cancellation token through plain function calls so deep callees can check `expired()` without an explicit context argument at every level.

```python
from tiny_deadline_ctx import DeadlineCtx, CancellationError

def clock() -> float:
    return 100.0

def deep(ctx):
    if ctx.expired():
        raise CancellationError("deadline exceeded")
    return ctx.remaining_ms()  # e.g. 5000.0

parent = DeadlineCtx(deadline_ms=5000, now_ms=clock)
child = DeadlineCtx.from_parent(parent)
print(deep(child))  # remaining_ms based on clock() at call time
```

The library exists because threading `timeout` parameters through every layer of a call graph is noisy and error-prone, and pulling in a full context framework for a small library is overkill. Here you thread one small object through the layers that need it and check `.expired()` where it matters.

`remaining_ms()` evaluates `now_fn()` fresh on every call, so its value depends on the clock at call time — tests must pass a deterministic `now_fn` (as above) rather than relying on wall-clock time. `expired()` is `True` when `now_ms() >= deadline_ms`. When `deadline_ms` is `None` the deadline is treated as infinite: `expired()` is always `False` and `remaining_ms()` returns `None`.
