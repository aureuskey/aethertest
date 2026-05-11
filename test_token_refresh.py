#!/usr/bin/env python3
"""
Test script to verify token refresh functionality in EnhancedSyntheticAgent.
"""
import asyncio
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aethertest.agents.enhanced_synthetic_agent import EnhancedSyntheticAgent
from aethertest.agents.synthetic_agent import AgentPersona


async def test_token_refresh():
    """Test that token refresh works correctly."""
    print("Testing token refresh functionality...")

    # Create a test agent
    agent = EnhancedSyntheticAgent(
        agent_id="test_agent",
        api_endpoint="http://127.0.0.1:8003",  # Assuming mock API is running on this port
        persona=AgentPersona(
            name="Tester",
            description="A test agent",
            goals=["Test token refresh"],
            budget=100.0,
            risk_tolerance=0.5,
            technical_expertise=0.5,
            communication_style="technical",
        )
    )

    # Initially, no auth token should be present
    print(f"Initial auth token: {agent.session.auth_token}")
    print(f"Initial authenticated: {agent.session.is_authenticated()}")

    # Try to refresh token (should fail since we're not connected to a real API)
    # But we can still test the mechanism
    print("\nAttempting token refresh...")
    refreshed = await agent._try_refresh_token()
    print(f"Token refresh result: {refreshed}")
    print(f"Auth token after refresh attempt: {agent.session.auth_token}")
    print(f"Authenticated after refresh attempt: {agent.session.is_authenticated()}")

    # Test that we can at least call the method without errors
    print("\nTest completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_token_refresh())