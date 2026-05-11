#!/usr/bin/env python3
"""
Test script to verify that save_simulation_results works correctly.
"""
import os
# Set environment variable BEFORE importing any application modules
os.environ['USE_SQLITE'] = 'true'

import asyncio
import uuid
from datetime import datetime, UTC
from src.aethertest.core.database import SessionLocal
from src.aethertest.core.models import SimulationRun, AgentInteraction
from src.aethertest.simulation.orchestrator import save_simulation_results

async def test_save_simulation_results():
    """Test the save_simulation_results function."""
    print("Starting test of save_simulation_results function...")

    # Create a test simulation ID
    simulation_id = str(uuid.uuid4())
    print(f"Test simulation ID: {simulation_id}")

    # Create a simulation run record
    db = SessionLocal()
    try:
        simulation_run = SimulationRun(
            id=simulation_id,
            api_endpoint="https://httpbin.org/get",
            start_time=datetime.now(UTC),
            status="created",
            config={"test": "configuration"},
            total_interactions=0,
            successful_interactions=0,
            failed_interactions=0
        )
        db.add(simulation_run)
        db.commit()
        print("Created simulation run record")
    except Exception as e:
        print(f"Error creating simulation run: {e}")
        db.rollback()
        return False
    finally:
        db.close()

    # Create mock results data
    mock_results = [
        {
            "agent_id": f"{simulation_id}-agent-1",
            "agent_type": "synthetic",
            "interactions": [
                {
                    "interaction_number": 1,
                    "timestamp": datetime.now(UTC).timestamp(),
                    "action_taken": {"method": "GET", "url": "/test"},
                    "action_result": {"status": 200, "data": {"message": "success"}},
                    "reflection": {"thoughts": "This was a successful interaction"},
                    "duration_ms": 150.5
                },
                {
                    "interaction_number": 2,
                    "timestamp": datetime.now(UTC).timestamp(),
                    "action_taken": {"method": "POST", "url": "/test"},
                    "action_result": {"status": 201, "data": {"id": 123}},
                    "reflection": {"thoughts": "This was also successful"},
                    "duration_ms": 200.3
                }
            ]
        },
        {
            "agent_id": f"{simulation_id}-agent-2",
            "agent_type": "synthetic",
            "interactions": [
                {
                    "interaction_number": 1,
                    "timestamp": datetime.now(UTC).timestamp(),
                    "action_taken": {"method": "GET", "url": "/test"},
                    "action_result": {"status": 500, "data": {"error": "Internal server error"}},
                    "reflection": {"thoughts": "This interaction failed"},
                    "duration_ms": 50.0
                }
            ]
        }
    ]

    # Call the function to save results
    try:
        await save_simulation_results(simulation_id, mock_results)
        print("save_simulation_results executed successfully")
    except Exception as e:
        print(f"Error in save_simulation_results: {e}")
        return False

    # Verify the data was saved correctly
    db = SessionLocal()
    try:
        # Check the simulation run was updated
        simulation_run = db.query(SimulationRun).filter(SimulationRun.id == simulation_id).first()
        if not simulation_run:
            print("ERROR: Simulation run not found after save")
            return False

        print(f"Simulation run status: {simulation_run.status}")
        print(f"Total interactions: {simulation_run.total_interactions}")
        print(f"Successful interactions: {simulation_run.successful_interactions}")
        print(f"Failed interactions: {simulation_run.failed_interactions}")

        # Check that the counts are correct
        expected_total = 3  # 2 interactions from agent-1 + 1 from agent-2
        expected_successful = 2  # First two interactions were successful
        expected_failed = 1  # Last interaction failed

        if simulation_run.total_interactions != expected_total:
            print(f"ERROR: Expected {expected_total} total interactions, got {simulation_run.total_interactions}")
            return False

        if simulation_run.successful_interactions != expected_successful:
            print(f"ERROR: Expected {expected_successful} successful interactions, got {simulation_run.successful_interactions}")
            return False

        if simulation_run.failed_interactions != expected_failed:
            print(f"ERROR: Expected {expected_failed} failed interactions, got {simulation_run.failed_interactions}")
            return False

        # Check that agent interactions were saved
        interactions = db.query(AgentInteraction).filter(AgentInteraction.simulation_id == simulation_id).all()
        print(f"Number of agent interactions saved: {len(interactions)}")

        if len(interactions) != expected_total:
            print(f"ERROR: Expected {expected_total} agent interactions in database, got {len(interactions)}")
            return False

        # Print some details about the saved interactions
        for i, interaction in enumerate(interactions):
            print(f"Interaction {i+1}:")
            print(f"  ID: {interaction.id}")
            print(f"  Agent ID: {interaction.agent_id}")
            print(f"  Interaction number: {interaction.interaction_number}")
            print(f"  Action taken: {interaction.action_taken}")
            print(f"  Action result: {interaction.action_result}")
            if interaction.reflection:
                print(f"  Reflection: {interaction.reflection}")
            print(f"  Duration ms: {interaction.duration_ms}")

        print("All tests passed!")
        return True

    except Exception as e:
        print(f"Error verifying results: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    result = asyncio.run(test_save_simulation_results())
    if result:
        print("\n✅ TEST PASSED: save_simulation_results function works correctly")
    else:
        print("\n❌ TEST FAILED: save_simulation_results function has issues")