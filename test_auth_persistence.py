#!/usr/bin/env python3
"""
Test script to verify auth token persistence across interactions.
"""
import asyncio
import sys
import os
import time
import subprocess
import signal
import logging
from typing import List

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aethertest.agents.enhanced_synthetic_agent import EnhancedSyntheticAgent
from aethertest.agents.synthetic_agent import AgentPersona


class MockAPIManager:
    """Manages the mock API server lifecycle."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8003):
        self.host = host
        self.port = port
        self.process = None
        self.base_url = f"http://{host}:{port}"

    async def start(self):
        """Start the mock API server."""
        print(f"Starting mock API server on {self.base_url}...")

        # Start the server as a subprocess
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "mock_api:app",
             "--host", self.host, "--port", str(self.port),
             "--log-level", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait a moment for server to start
        await asyncio.sleep(3)

        # Check if process is still running
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"Failed to start mock API: {stderr}")

        print(f"Mock API server started (PID: {self.process.pid})")

    def stop(self):
        """Stop the mock API server."""
        if self.process:
            print("Stopping mock API server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("Mock API server stopped")


def get_endpoint_config() -> dict:
    """Get endpoint configuration for the mock API."""
    return {
        "auth_login": "/auth/login",
        "resource_base": "/api/v1/resources",
        "health_check": "/health",
        "batch_submit": "/api/v1/batch",
        "batch_status": "/api/v1/batch/{batch_id}",
        "config_get": "/api/v1/config",
        "config_update": "/api/v1/config",
        "ingest": "/api/v1/ingest",
        "process_status": "/api/v1/process/{ingest_id}",
        "results_get": "/api/v1/results/{ingest_id}",
    }


async def run_test():
    """Run the auth persistence test."""
    print("=" * 60)
    print("AUTH TOKEN PERSISTENCE TEST")
    print("=" * 60)

    # Initialize components
    mock_api = MockAPIManager()
    endpoint_config = get_endpoint_config()

    try:
        # Start mock API
        await mock_api.start()

        # Give it a bit more time to be ready
        await asyncio.sleep(2)

        # Test that the API is responding
        import httpx
        try:
            response = httpx.get(f"{mock_api.base_url}/health", timeout=5.0)
            if response.status_code == 200:
                print(f"[OK] Mock API is healthy: {response.json()}")
            else:
                print(f"[WARN] Mock API returned status {response.status_code}")
        except Exception as e:
            print(f"[WARN] Could not connect to mock API: {e}")
            print("Continuing anyway...")

        # Create a single agent with Cautious DevOps persona
        persona = AgentPersona(
            name="Cautious DevOps Engineer",
            description="A cautious engineer who validates every step and avoids risks",
            goals=["Validate system reliability", "Ensure data integrity", "Minimize errors"],
            budget=100.0,
            risk_tolerance=0.1,
            technical_expertise=0.8,
            communication_style="formal",
        )

        agent = EnhancedSyntheticAgent(
            agent_id="test_agent",
            api_endpoint=mock_api.base_url,
            persona=persona,
            endpoint_config=endpoint_config
        )

        print(f"\nCreated agent: {agent.agent_id} ({agent.persona.name})")
        print(f"Initial session auth_token: {agent.session.auth_token}")
        print(f"Initial session authenticated: {agent.session.is_authenticated()}")

        # Check logger levels
        from src.aethertest.agents.enhanced_base_agent import logger as base_logger
        print(f"Base agent logger level: {base_logger.getEffectiveLevel()} (DEBUG={logging.DEBUG})")

        # Run 5 sequential interactions
        num_interactions = 5
        all_successful = True
        token_persisted_across_interactions = True

        for i in range(num_interactions):
            print(f"\n--- Interaction {i+1}/{num_interactions} ---")

            # Before interaction, log session state
            print(f"  Pre-interaction session auth_token: {agent.session.auth_token[:20] if agent.session.auth_token else None}...")
            print(f"  Pre-interaction session authenticated: {agent.session.is_authenticated()}")

            # Run interaction
            result = await agent.interact()

            # After interaction, log results
            print(f"  Interaction success: {result.get('overall_success', False)}")
            if not result.get('overall_success', False):
                all_successful = False
                print(f"  Error: {result.get('error', 'Unknown')}")

            # Log session state after interaction
            print(f"  Post-interaction session auth_token: {agent.session.auth_token[:20] if agent.session.auth_token else None}...")
            print(f"  Post-interaction session authenticated: {agent.session.is_authenticated()}")

            # Check if we have a token after this interaction
            if agent.session.auth_token is None:
                token_persisted_across_interactions = False
                print(f"  [WARNING] No auth token after interaction {i+1}!")

            # Small delay between interactions
            await asyncio.sleep(0.5)

        # Final summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"All interactions successful: {all_successful}")
        print(f"Token persisted across all {num_interactions} interactions: {token_persisted_across_interactions}")

        if all_successful and token_persisted_across_interactions:
            print("RESULT: Token persistence is WORKING CORRECTLY")
            return 0
        else:
            print("RESULT: Token persistence has ISSUES")
            return 1

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up
        mock_api.stop()


if __name__ == "__main__":
    # Set logging to see debug messages
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    exit_code = asyncio.run(run_test())
    sys.exit(exit_code)