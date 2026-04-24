from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CallRecorder:
    calls: list[tuple[str, dict]] = field(default_factory=list)
    return_values: dict[str, object] = field(default_factory=dict)
    side_effects: dict[str, Exception] = field(default_factory=dict)

    def record(self, method: str, kwargs: dict) -> None:
        self.calls.append((method, kwargs))

    def maybe_raise(self, method: str) -> None:
        exc = self.side_effects.get(method)
        if exc is not None:
            raise exc

    def value(self, method: str) -> object:
        return self.return_values.get(method)

