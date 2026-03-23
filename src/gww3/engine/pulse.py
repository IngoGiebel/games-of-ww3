"""Pulse Engine — Multi-Resolution Time Architecture for GWW3.

The Pulse Engine manages the game clock and triggers system updates
at different frequencies:

- Tactical:    every 60 ticks   (1 game-hour)  — combat, movement, cyber
- Operational: every 1440 ticks (1 game-day)   — casualties, protests
- Diplomatic:  every 10080 ticks (1 game-week) — UN votes, treaties, intel
- Economic:    every 43200 ticks (1 game-month) — GDP, trade, inflation
- Epoch:       every 525600 ticks (1 game-year) — demographics, elections

1 tick = 1 minute of game time (configurable).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Awaitable

# Tick intervals (in ticks, where 1 tick = 1 game-minute)
TICKS_PER_HOUR = 60
TICKS_PER_DAY = 1_440
TICKS_PER_WEEK = 10_080
TICKS_PER_MONTH = 43_200       # ~30 days
TICKS_PER_YEAR = 525_600       # ~365.25 days


class PulseLevel(IntEnum):
    """Update frequency levels, ordered from most to least frequent."""
    TACTICAL = TICKS_PER_HOUR
    OPERATIONAL = TICKS_PER_DAY
    DIPLOMATIC = TICKS_PER_WEEK
    ECONOMIC = TICKS_PER_MONTH
    EPOCH = TICKS_PER_YEAR


# Type alias for update handlers
UpdateHandler = Callable[[int], Awaitable[None]]  # receives current tick


@dataclass
class PulseEngine:
    """Manages the game clock and triggers multi-resolution updates.

    Usage:
        engine = PulseEngine(speed_factor=1.0)
        engine.register(PulseLevel.TACTICAL, handle_combat)
        engine.register(PulseLevel.ECONOMIC, handle_economy)
        await engine.advance()  # advance one tick
    """

    current_tick: int = 0
    speed_factor: float = 1.0  # 1.0 = real-time, 10.0 = 10x speed
    paused: bool = False
    _handlers: dict[PulseLevel, list[UpdateHandler]] = field(default_factory=dict)

    def register(self, level: PulseLevel, handler: UpdateHandler) -> None:
        """Register an update handler at a specific pulse level."""
        self._handlers.setdefault(level, []).append(handler)

    async def advance(self) -> list[PulseLevel]:
        """Advance the game clock by one tick.

        Returns:
            List of PulseLevels that were triggered this tick.
        """
        if self.paused:
            return []

        self.current_tick += 1
        triggered = []

        for level in PulseLevel:
            if self.current_tick % level.value == 0:
                triggered.append(level)
                for handler in self._handlers.get(level, []):
                    await handler(self.current_tick)

        return triggered

    async def advance_to(self, target_tick: int) -> None:
        """Advance the clock to a specific tick, processing all intermediate ticks."""
        while self.current_tick < target_tick:
            await self.advance()

    @property
    def game_minutes(self) -> int:
        return self.current_tick

    @property
    def game_hours(self) -> float:
        return self.current_tick / TICKS_PER_HOUR

    @property
    def game_days(self) -> float:
        return self.current_tick / TICKS_PER_DAY

    @property
    def game_years(self) -> float:
        return self.current_tick / TICKS_PER_YEAR
