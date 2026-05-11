"""
Tests for the AetherTest API.
"""
import pytest
from fastapi.testclient import TestClient
from src.aethertest.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "AetherTest" in response.json()["message"]

def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_simulation():
    """Test creating a new simulation."""
    simulation_data = {
        "api_endpoint": "https://httpbin.org",
        "agent_count": 5,
        "scenario": "basic_interaction",
        "duration_minutes": 1
    }
    response = client.post("/api/v1/simulations", json=simulation_data)
    assert response.status_code == 200
    data = response.json()
    assert "simulation_id" in data
    assert data["status"] == "created"
    # Note: We're not actually running the simulation in this test
    # because it would make external calls. In a full test suite,
    # we would mock the background task.

def get_agent_types():
    """Test getting available agent types."""
    response = client.get("/api/v1/agents/types")
    assert response.status_code == 200
    data = response.json()
    assert "agent_types" in data
    assert isinstance(data["agent_types"], list)
    assert len(data["agent_types"]) > 0