#!/usr/bin/env python3
"""
Debug test to see what's happening with auth token.
"""
import asyncio
import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aethertest.agents.enhanced_synthetic_agent import EnhancedSyntheticAgent
from aethertest.agents.synthetic_agent import AgentPersona


class MockAPIManager:
    def __init__(self, host="127.0.0.1", port=8003):
        self.host = host
        self.port = port
        self.process = None
        self.base_url = f"http://{host}:{port}"

    async def start(self):
        import subprocess
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "mock_api:app",
             "--host", self.host, "--port", str(self.port),
             "--log-level", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        await asyncio.sleep(3)
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"Failed to start mock API: {stderr}")
        print(f"Mock API server started (PID: {self.process.pid})")

    def stop(self):
        if self.process:
            print("Stopping mock API server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("Mock API server stopped")


def get_endpoint_config():
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


async def run_debug():
    # Clear verify token debug log
    if os.path.exists("verify_token_debug.log"):
        os.remove("verify_token_debug.log")

    mock_api = MockAPIManager()
    endpoint_config = get_endpoint_config()

    try:
        await mock_api.start()
        await asyncio.sleep(2)

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
            agent_id="debug_agent",
            api_endpoint=mock_api.base_url,
            persona=persona,
            endpoint_config=endpoint_config
        )

        print(f"Initial session auth_token: {agent.session.auth_token}")

        # Run one interaction
        result = await agent.interact()
        print(f"Interaction result: {result.get('overall_success')}")
        if not result.get('overall_success'):
            print(f"Error: {result.get('error')}")
            # Print workflow results for debugging
            if 'workflow_results' in result:
                for i, wr in enumerate(result['workflow_results']):
                    print(f"  Step {i}: {wr.get('step_name')} - success: {wr.get('success')} - status: {wr.get('status_code')} - error: {wr.get('error')}")

        print(f"Session auth_token after interaction: {agent.session.auth_token}")

        # Print the last 20 lines of verify_token_debug.log
        if os.path.exists("verify_token_debug.log"):
            print("\n--- Last 20 lines of verify_token_debug.log ---")
            with open("verify_token_debug.log", "r") as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
        else:
            print("verify_token_debug.log not found")

    finally:
        mock_api.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(run_debug())