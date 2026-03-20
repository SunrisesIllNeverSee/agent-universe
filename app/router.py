from __future__ import annotations

from .models import SystemRuntime


class SequenceRouter:
    def ordered_systems(self, systems: dict[str, SystemRuntime]) -> list[tuple[str, SystemRuntime]]:
        active = [(system_id, runtime) for system_id, runtime in systems.items() if runtime.active]

        def sort_key(item: tuple[str, SystemRuntime]) -> tuple[int, int, str]:
            system_id, runtime = item
            role_rank = {"primary": 0, "secondary": 1, "observer": 2, "none": 3}
            seq = runtime.seq if runtime.seq is not None else 999
            return (role_rank.get(runtime.role, 3), seq, system_id)

        return sorted(active, key=sort_key)

    def sequence_map(self, systems: dict[str, SystemRuntime]) -> dict[str, int]:
        ordered = self.ordered_systems(systems)
        return {system_id: index + 1 for index, (system_id, _runtime) in enumerate(ordered)}
