"""Tests for the Pulse Engine."""

import pytest

from gww3.engine.pulse import (
    Interrupt,
    InterruptPriority,
    PulseEngine,
    PulseLevel,
    TICKS_PER_HOUR,
    TICKS_PER_MONTH,
)


@pytest.mark.asyncio
async def test_advance_increments_tick():
    engine = PulseEngine()
    assert engine.current_tick == 0
    await engine.advance()
    assert engine.current_tick == 1


@pytest.mark.asyncio
async def test_tactical_triggers_every_hour():
    engine = PulseEngine()
    triggered_at = []

    async def on_tactical(tick: int):
        triggered_at.append(tick)

    engine.register(PulseLevel.TACTICAL, on_tactical)

    for _ in range(TICKS_PER_HOUR + 1):
        await engine.advance()

    assert triggered_at == [TICKS_PER_HOUR]


@pytest.mark.asyncio
async def test_paused_does_not_advance():
    engine = PulseEngine(paused=True)
    result = await engine.advance()
    assert engine.current_tick == 0
    assert result == []


@pytest.mark.asyncio
async def test_game_time_conversions():
    engine = PulseEngine(current_tick=1440)
    assert engine.game_days == 1.0
    assert engine.game_hours == 24.0


@pytest.mark.asyncio
async def test_advance_to():
    engine = PulseEngine()
    await engine.advance_to(100)
    assert engine.current_tick == 100


@pytest.mark.asyncio
async def test_interrupt_triggers_handler():
    engine = PulseEngine()
    received = []

    async def on_interrupt(interrupt: Interrupt):
        received.append(interrupt)

    engine.on_interrupt(on_interrupt)

    await engine.trigger_interrupt(Interrupt(
        event_type="INVASION_DETECTED",
        priority=InterruptPriority.CRITICAL,
        data={"attacker": "RUS", "target": "UKR"},
    ))

    await engine.advance()

    assert len(received) == 1
    assert received[0].event_type == "INVASION_DETECTED"
    assert received[0].priority == InterruptPriority.CRITICAL


@pytest.mark.asyncio
async def test_interrupts_processed_by_priority():
    engine = PulseEngine()
    order = []

    async def on_interrupt(interrupt: Interrupt):
        order.append(interrupt.event_type)

    engine.on_interrupt(on_interrupt)

    # Queue in reverse priority order
    await engine.trigger_interrupt(Interrupt(
        event_type="DIPLOMATIC_INCIDENT",
        priority=InterruptPriority.NORMAL,
        data={},
    ))
    await engine.trigger_interrupt(Interrupt(
        event_type="NUCLEAR_LAUNCH",
        priority=InterruptPriority.CRITICAL,
        data={},
    ))
    await engine.trigger_interrupt(Interrupt(
        event_type="MARKET_CRASH",
        priority=InterruptPriority.HIGH,
        data={},
    ))

    await engine.advance()

    # Should be processed CRITICAL → HIGH → NORMAL
    assert order == ["NUCLEAR_LAUNCH", "MARKET_CRASH", "DIPLOMATIC_INCIDENT"]


@pytest.mark.asyncio
async def test_should_snapshot_monthly():
    engine = PulseEngine(current_tick=TICKS_PER_MONTH)
    assert engine.should_snapshot() is True


@pytest.mark.asyncio
async def test_should_not_snapshot_daily():
    engine = PulseEngine(current_tick=1440)  # 1 day
    assert engine.should_snapshot() is False
