#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced agent functionality.
"""
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aethertest.agents.enhanced_synthetic_agent import EnhancedSyntheticAgent
from aethertest.agents.agent_types import create_agent

async def test_enhanced_agent():
    """Test the enhanced agent functionality."""
    print("Testing EnhancedSyntheticAgent...")

    # Create an enhanced agent
    agent = EnhancedSyntheticAgent(
        agent_id="test_agent_001",
        api_endpoint="https://httpbin.org",  # Using httpbin for testing
        api_key=None  # No API key needed for httpbin
    )

    print(f"Created agent: {agent.agent_id}")
    print(f"Persona: {agent.persona.name}")
    print(f"Available workflows: {len(agent.workflow_library)}")

    # Show some workflow examples
    print("\nSample workflows:")
    for i, workflow in enumerate(agent.workflow_library[:3]):
        print(f"  {i+1}. {workflow.name} ({workflow.workflow_type.value})")

    # Test a single interaction (will make actual HTTP requests)
    print("\nExecuting interaction...")
    try:
        result = await agent.interact()
        print(f"Interaction completed:")
        print(f"  Success: {result.get('overall_success', False)}")
        print(f"  Workflow: {result.get('workflow_name', 'Unknown')}")
        print(f"  Steps: {result.get('steps_succeeded', 0)}/{result.get('steps_attempted', 0)}")
        print(f"  Duration: {result.get('duration_ms', 0):.2f}ms")

        # Show detailed state
        state = agent.get_detailed_state()
        print(f"\nAgent state:")
        print(f"  Discovered endpoints: {state['infrastructure_state']['discovered_endpoints_count']}")
        print(f"  Failed endpoints: {state['infrastructure_state']['failed_endpoints_count']}")
        print(f"  Rate limited endpoints: {state['infrastructure_state']['rate_limited_endpoints_count']}")

    except Exception as e:
        print(f"Error during interaction: {e}")
        import traceback
        traceback.print_exc()

    # Test the factory function
    print("\nTesting factory function...")
    try:
        agent2 = create_agent(
            agent_type="enhanced_synthetic",
            agent_id="factory_agent_001",
            api_endpoint="https://httpbin.org"
        )
        print(f"Created agent via factory: {agent2.agent_id}")
        print(f"Agent type: {type(agent2).__name__}")
    except Exception as e:
        print(f"Error creating agent via factory: {e}")

async def test_agent_types():
    """Test that our enhanced type is available."""
    from aethertest.agents.agent_types import get_available_agent_types

    types = get_available_agent_types()
    print(f"Available agent types: {types}")

    if "enhanced_synthetic" in types:
        print("[OK] Enhanced synthetic agent type is available")
    else:
        print("[ERROR] Enhanced synthetic agent type is missing")

async def main():
    """Main test function."""
    print("=" * 60)
    print("Enhanced Agent System Test")
    print("=" * 60)

    await test_agent_types()
    print()
    await test_enhanced_agent()

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())