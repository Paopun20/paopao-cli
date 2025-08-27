import inspect
import asyncio
from typing import get_type_hints, Callable, Any

global_registry = []

class Runtime:
    registry = {}       # global registry
    _fast = {}          # direct call cache (speed boost)
    
    def __init__(self):
        global global_registry
        global_registry.append(self)

    # ─────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────
    @classmethod
    def add(cls, name: str):
        """Decorator to register a function globally."""
        def decorator(func: Callable):
            cls._register(name, func)
            return func
        return decorator

    @classmethod
    def import_callable(cls, func: Callable, name: str = None):
        """Import any callable into the registry."""
        cmd_name = name or getattr(func, "__name__", "unnamed")
        cls._register(cmd_name, func)
        return func

    @classmethod
    def _register(cls, name: str, func: Callable):
        """Internal registration logic with auto-wrap + speed optimization."""
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or "No documentation."
        hints = get_type_hints(func)
        is_async = asyncio.iscoroutinefunction(func)

        # Fast path: direct function reference if it accepts *args (no self injection needed)
        if "self" not in sig.parameters:
            if is_async:
                async def fast(self, *a, **kw): return await func(*a, **kw)
            else:
                def fast(self, *a, **kw): return func(*a, **kw)
            cls._fast[name] = fast
            wrapper = fast
        else:
            # Normal wrapper, inject self
            if is_async:
                async def wrapper(self, *a, **kw): return await func(self, *a, **kw)
            else:
                def wrapper(self, *a, **kw): return func(self, *a, **kw)

        cls.registry[name] = {
            "func": wrapper,
            "signature": sig,
            "annotations": hints,
            "doc": doc,
            "async": is_async,
        }

    # ─────────────────────────────────────────────
    # Runtime execution
    # ─────────────────────────────────────────────
    def run(self, name: str, *args, **kwargs) -> Any:
        """Run a registered command by name. Supports sync + async."""
        if name in self._fast:  # fast-path (skip registry lookup)
            return self._fast[name](self, *args, **kwargs)

        if name not in self.registry:
            raise ValueError(f"No function registered under '{name}'")

        entry = self.registry[name]
        func = entry["func"]

        if entry["async"]:
            try:
                loop = asyncio.get_running_loop()
                return loop.create_task(func(self, *args, **kwargs))
            except RuntimeError:
                return asyncio.run(func(self, *args, **kwargs))
        else:
            return func(self, *args, **kwargs)

    # ─────────────────────────────────────────────
    # Docs & Tools
    # ─────────────────────────────────────────────
    def list(self):
        """List all registered commands."""
        return list(self.registry.keys())

    def doc(self, name: str):
        """Get documentation for a command."""
        if name not in self.registry:
            raise ValueError(f"No docs for unknown command '{name}'")
        e = self.registry[name]
        return {
            "name": name,
            "signature": str(e["signature"]),
            "annotations": e["annotations"],
            "doc": e["doc"],
            "async": e["async"],
        }