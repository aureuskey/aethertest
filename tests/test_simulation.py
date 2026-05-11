"""
Tests for the simulation orchestration.
"""
import pytest
from unittest.mock import Mock, patch
from src.aethertest.simulation.orchestrator import run_simulation
from src.aethertest.agents.agent_types import APIUserAgent

@pytest.mark.asyncio
async def test_run_simulation_basic():
    """Test that the simulation orchestrator can be called."""
    # We'll mock the actual agent interactions to avoid external calls
    with patch('src.aethertest.agents.base_agent.BaseAgent.interact') as mock_interact:
        mock_interact.return_value = {
            "status_code": 200,
            "data": {"message": "success"}
        }

        # Run a small simulation
        await run_simulation(
            simulation_id="test-sim-1",
            api_endpoint="https://example.com",
            api_key=None,
            agent_count=2,
            scenario="basic_interaction",
            duration_minutes=1
        )

        # Verify that interact was called the expected number of times
        # 2 agents * (duration_minutes * 2 interactions per minute) = 2 * 2 = 4
        assert mock_interact.call_count == 4

def test_calculate_metrics():
    """Test the metrics calculation helper."""
    from src.aethertest.utils.helpers import calculate_metrics

    results = [
        {
            "agent_id": "agent1",
            "interactions": [
                {"status_code": 200, "response_time_ms": 100},
                {"status_code": 200, "response_time_ms": 150},
                {"status_code": 400, "response_time_ms": 50},
            ]
        },
        {
            "agent_id": "agent2",
            "interactions": [
                {"status_code": 200, "response_time_ms": 200},
                {"status_code": 500, "response_time_ms": 300},
            ]
        }
    ]

    metrics = calculate_metrics(results)
    assert metrics["total_interactions"] == 5
    assert metrics["successful_interactions"] == 3
    assert metrics["failed_interactions"] == 2
    assert metrics["success_rate"] == 0.6
    assert metrics["average_response_time_ms"] == 150.0  # (100+150+200+300)/4

def test_get_available_agent_types():
    """Test that we can get the list of agent types."""
    from src.aethertest.agents.agent_types import get_available_agent_types
    types = get_available_agent_types()
    assert isinstance(types, list)
    assert "api_user" in types
    assert "stresstest" in types
    assert "error_testing" in types
    assert "monitoring" in types