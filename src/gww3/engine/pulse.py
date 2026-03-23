"""Pulse Engine — Multi-Resolution Time Architecture for GWW3.

The Pulse Engine manages the game clock and triggers system updates
at different frequencies:

- Tactical:    every 60 ticks   (1 game-hour)  — combat, movement, cyber
- Operational: every 1440 ticks (1 game-day)   — casualties, protests
- Diplomatic:  every 10080 ticks (1 game-week) — UN votes, treaties, intel
- Economic:    every 43200 ticks (1 game-month) — GDP, trade, inflation
- Epoch:       every 525600 ticks (1 game-year) — demographics, elections

1 tick = 1 minute of game time (configurable).

Temporal Snapshot Strategy:
- STATE_AT snapshots are created ONLY on Economic (monthly) and Epoch (annual) ticks.
- Intra-month state changes are logged as lightweight Event nodes.
- This prevents graph explosion in Neo4j.

Event-Driven Interrupts:
- Critical events (invasion, nuclear launch, market crash) trigger immediate
  "Emergency Cabinet" sessions, bypassing the normal pulse schedule.
- Interrupts are processed via an async queue checked every tick.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Awaitable

# Tick intervals (in ticks, where 1 tick = 1 game-minute)
TICKS_PER_HOUR = 60
TICKS_PER_DAY = 1_440
TICKS_PER_WEEK = 10_080
TICKS_PER_MONTH = 43_200       # ~30 days
TICKS_PER_YEAR = 525_600       # ~365.25 days

# Ticks that generate STATE_AT snapshots in Neo4j
SNAPSHOT_TICKS = {TICKS_PER_MONTH, TICKS_PER_YEAR}


class PulseLevel(IntEnum):
    """Update frequency levels, ordered from most to least frequent."""
    TACTICAL = TICKS_PER_HOUR
    OPERATIONAL = TICKS_PER_DAY
    DIPLOMATIC = TICKS_PER_WEEK
    ECONOMIC = TICKS_PER_MONTH
    EPOCH = TICKS_PER_YEAR


class InterruptPriority(IntEnum):
    """Priority levels for event-driven interrupts."""
    CRITICAL = 0    # Nuclear launch, invasion — immediate
    HIGH = 1        # Market crash >10%, revolution in progress
    NORMAL = 2      # Alliance request, diplomatic incident


@dataclass
class Interrupt:
    """An event-driven interrupt that bypasses the normal pulse schedule."""
    event_type: str
    priority: InterruptPriority
    data: dict
    source_nation: str | None = None


# Type alias for update handlers
UpdateHandler = Callable[[int], Awaitable[None]]          # receives current tick
InterruptHandler = Callable[[Interrupt], Awaitable[None]]  # receives the interrupt


@dataclass
class PulseEngine:
    """Manages the game clock and triggers multi-resolution updates.

    Usage:
        engine = PulseEngine(speed_factor=1.0)
        engine.register(PulseLevel.TACTICAL, handle_combat)
        engine.register(PulseLevel.ECONOMIC, handle_economy)
        engine.on_interrupt(handle_emergency_cabinet)
        await engine.advance()  # advance one tick

    Interrupt usage:
        await engine.trigger_interrupt(Interrupt(
            event_type="INVASION_DETECTED",
            priority=InterruptPriority.CRITICAL,
            data={"attacker": "RUS", "target": "UKR"},
        ))
    """

    current_tick: int = 0
    speed_factor: float = 1.0  # 1.0 = real-time, 10.0 = 10x speed
    paused: bool = False
    _handlers: dict[PulseLevel, list[UpdateHandler]] = field(default_factory=dict)
    _interrupt_handlers: list[InterruptHandler] = field(default_factory=list)
    _interrupt_queue: asyncio.Queue[Interrupt] = field(default_factory=asyncio.Queue)

    def register(self, level: PulseLevel, handler: UpdateHandler) -> None:
        """Register an update handler at a specific pulse level."""
        self._handlers.setdefault(level, []).append(handler)

    def on_interrupt(self, handler: InterruptHandler) -> None:
        """Register a handler for event-driven interrupts (e.g., Emergency Cabinet)."""
        self._interrupt_handlers.append(handler)

    async def trigger_interrupt(self, interrupt: Interrupt) -> None:
        """Queue a critical event that bypasses the normal pulse schedule.

        Interrupts are processed at the start of the next tick, before
        regular pulse handlers. Higher priority interrupts are processed first.
        """
        await self._interrupt_queue.put(interrupt)

    async def _process_interrupts(self) -> list[Interrupt]:
        """Drain and process all pending interrupts, sorted by priority."""
        pending: list[Interrupt] = []
        while not self._interrupt_queue.empty():
            try:
                pending.append(self._interrupt_queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        # Process highest priority first
        pending.sort(key=lambda i: i.priority)

        for interrupt in pending:
            for handler in self._interrupt_handlers:
                await handler(interrupt)

        return pending

    async def advance(self) -> list[PulseLevel]:
        """Advance the game clock by one tick.

        Processing order:
        1. Process any pending interrupts (Emergency Cabinet)
        2. Fire pulse-level handlers whose modulo matches

        Returns:
            List of PulseLevels that were triggered this tick.
        """
        if self.paused:
            return []

        self.current_tick += 1

        # 1. Process interrupts first (emergency events)
        await self._process_interrupts()

        # 2. Regular pulse handlers
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

    def should_snapshot(self) -> bool:
        """Check if the current tick should generate a STATE_AT snapshot in Neo4j.

        Snapshots are only created on Monthly (Economic) and Annual (Epoch) ticks
        to prevent graph explosion. Intra-month changes use lightweight Event nodes.
        """
        return any(self.current_tick % interval == 0 for interval in SNAPSHOT_TICKS)

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
