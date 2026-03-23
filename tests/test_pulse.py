"""Tests for the Pulse Engine."""

import pytest

from gww3.engine.pulse import PulseEngine, PulseLevel, TICKS_PER_HOUR


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
