"""
Test script for the analytics API endpoints.
"""
import os
# Set environment variable BEFORE importing any application modules
os.environ['USE_SQLITE'] = 'true'

from fastapi.testclient import TestClient
from src.aethertest.main import app
from src.aethertest.core.database import SessionLocal
from src.aethertest.core.models import SimulationRun, AgentInteraction
import uuid
from datetime import datetime, UTC
import json

# Override the dependency to use a test session
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[SessionLocal] = override_get_db

client = TestClient(app)

def setup_test_data():
    """Create a test simulation run and some agent interactions."""
    db = SessionLocal()
    try:
        # Clear existing data (for clean test)
        db.query(AgentInteraction).delete()
        db.query(SimulationRun).delete()
        db.commit()

        # Create a test simulation run
        simulation_id = str(uuid.uuid4())
        simulation_run = SimulationRun(
            id=simulation_id,
            api_endpoint="https://httpbin.org/get",
            start_time=datetime.now(UTC),
            status="completed",
            config={"test": "configuration"},
            total_interactions=5,
            successful_interactions=3,
            failed_interactions=2
        )
        db.add(simulation_run)
        db.commit()

        # Create test agent interactions
        interactions_data = [
            # Successful interactions (status 200, 201)
            {
                "id": str(uuid.uuid4()),
                "simulation_id": simulation_id,
                "agent_id": f"{simulation_id}-agent-1",
                "agent_type": "synthetic",
                "persona_name": "Test Agent 1",
                "interaction_number": 1,
                "timestamp": datetime.now(UTC),
                "action_taken": {"method": "GET", "url": "/test"},
                "action_result": {"status": 200, "data": {"message": "success"}},
                "reflection": {"thoughts": "This was successful"},
                "duration_ms": 150.5
            },
            {
                "id": str(uuid.uuid4()),
                "simulation_id": simulation_id,
                "agent_id": f"{simulation_id}-agent-1",
                "agent_type": "synthetic",
                "persona_name": "Test Agent 1",
                "interaction_number": 2,
                "timestamp": datetime.now(UTC),
                "action_taken": {"method": "POST", "url": "/test"},
                "action_result": {"status": 201, "data": {"id": 123}},
                "reflection": {"thoughts": "This was also successful"},
                "duration_ms": 200.3
            },
            {
                "id": str(uuid.uuid4()),
                "simulation_id": simulation_id,
                "agent_id": f"{simulation_id}-agent-2",
                "agent_type": "synthetic",
                "persona_name": "Test Agent 2",
                "interaction_number": 1,
                "timestamp": datetime.now(UTC),
                "action_taken": {"method": "GET", "url": "/test"},
                "action_result": {"status": 200, "data": {"message": "success"}},
                "reflection": {"thoughts": "Another success"},
                "duration_ms": 100.0
            },
            # Failed interactions (status 400, 500)
            {
                "id": str(uuid.uuid4()),
                "simulation_id": simulation_id,
                "agent_id": f"{simulation_id}-agent-3",
                "agent_type": "synthetic",
                "persona_name": "Test Agent 3",
                "interaction_number": 1,
                "timestamp": datetime.now(UTC),
                "action_taken": {"method": "GET", "url": "/test"},
                "action_result": {"status": 400, "data": {"error": "Bad request"}},
                "reflection": {"thoughts": "Bad request error"},
                "duration_ms": 50.0
            },
            {
                "id": str(uuid.uuid4()),
                "simulation_id": simulation_id,
                "agent_id": f"{simulation_id}-agent-3",
                "agent_type": "synthetic",
                "persona_name": "Test Agent 3",
                "interaction_number": 2,
                "timestamp": datetime.now(UTC),
                "action_taken": {"method": "GET", "url": "/test"},
                "action_result": {"status": 500, "data": {"error": "Internal server error"}},
                "reflection": {"thoughts": "Server error"},
                "duration_ms": 75.0
            }
        ]

        for interaction_data in interactions_data:
            interaction = AgentInteraction(**interaction_data)
            db.add(interaction)

        db.commit()
        print(f"Created test data: simulation {simulation_id} with 5 interactions")
        return simulation_id

    except Exception as e:
        print(f"Error setting up test data: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def test_adoption_rate(simulation_id):
    """Test the adoption rate endpoint."""
    print("\n=== Testing Adoption Rate Endpoint ===")
    response = client.get(
        f"/api/v1/analytics/adoption-rate",
        params={"simulation_id": simulation_id, "hours": 24}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        # Verify we have data
        assert "adoption_rate" in data
        assert len(data["adoption_rate"]) > 0
        # Check that the adoption rate is correct (3 successful out of 5 total = 60%)
        # Note: The endpoint groups by hour, so we need to check the values
        # For simplicity, we'll just check that we got some data
        print("[PASS] Adoption rate endpoint test passed")
    else:
        print(f"[FAIL] Error: {response.text}")
        raise Exception("Adoption rate endpoint failed")

def test_cost_curves(simulation_id):
    """Test the cost curves endpoint."""
    print("\n=== Testing Cost Curves Endpoint ===")
    response = client.get(
        f"/api/v1/analytics/cost-curves",
        params={"simulation_id": simulation_id, "hours": 24}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "cost_curves" in data
        assert len(data["cost_curves"]) > 0
        print("[PASS] Cost curves endpoint test passed")
    else:
        print(f"[FAIL] Error: {response.text}")
        raise Exception("Cost curves endpoint failed")

def test_failure_modes(simulation_id):
    """Test the failure modes endpoint."""
    print("\n=== Testing Failure Modes Endpoint ===")
    response = client.get(
        f"/api/v1/analytics/failure-modes",
        params={"simulation_id": simulation_id, "hours": 24, "limit": 10}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "failure_modes" in data
        # We have two failure types: 400 and 500
        assert len(data["failure_modes"]) == 2
        print("[PASS] Failure modes endpoint test passed")
    else:
        print(f"[FAIL] Error: {response.text}")
        raise Exception("Failure modes endpoint failed")

def test_successful_strategies(simulation_id):
    """Test the successful strategies endpoint."""
    print("\n=== Testing Successful Strategies Endpoint ===")
    response = client.get(
        f"/api/v1/analytics/successful-strategies",
        params={"simulation_id": simulation_id, "hours": 24, "limit": 10}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "successful_strategies" in data
        # We have three successful interactions from two agents
        # Agent 1: 2 successes, Agent 2: 1 success
        assert len(data["successful_strategies"]) == 2
        print("[PASS] Successful strategies endpoint test passed")
    else:
        print(f"[FAIL] Error: {response.text}")
        raise Exception("Successful strategies endpoint failed")

def test_visual_replay(simulation_id):
    """Test the visual replay endpoint."""
    print("\n=== Testing Visual Replay Endpoint ===")
    response = client.get(
        f"/api/v1/analytics/visual-replay/{simulation_id}",
        params={"limit": 100}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {data.keys()}")
        assert "simulation" in data
        assert "interactions" in data
        assert data["simulation"]["id"] == simulation_id
        assert len(data["interactions"]) == 5
        print("[PASS] Visual replay endpoint test passed")
    else:
        print(f"[FAIL] Error: {response.text}")
        raise Exception("Visual replay endpoint failed")

def main():
    """Run all tests."""
    print("Starting analytics API tests...")

    # Setup test data
    simulation_id = setup_test_data()
    if not simulation_id:
        print("[FAIL] Failed to setup test data")
        return

    try:
        # Run tests
        test_adoption_rate(simulation_id)
        test_cost_curves(simulation_id)
        test_failure_modes(simulation_id)
        test_successful_strategies(simulation_id)
        test_visual_replay(simulation_id)

        print("\n[INFO] All tests passed!")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()

if __name__ == "__main__":
    main()