"""
Full simulation integration test.
Starts mock API and runs a complete simulation with the orchestrator.
"""
import asyncio
import subprocess
import sys
import time
import signal
import os
from typing import List
import uvicorn
from contextlib import asynccontextmanager

# Add src to path so we can import our modules
sys.path.insert(0, 'src')

from aethertest.simulation.orchestrator import SimulationOrchestrator
from aethertest.agents.synthetic_agent import AgentPersona


class MockAPIManager:
    """Manages the mock API server lifecycle."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
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


def create_sample_personas() -> List[AgentPersona]:
    """Create sample personas for infrastructure testing."""
    return [
        AgentPersona(
            name="Cautious DevOps Engineer",
            description="A cautious engineer who validates every step and avoids risks",
            goals=["Validate system reliability", "Ensure data integrity", "Minimize errors"],
            budget=100.0,
            risk_tolerance=0.1,
            technical_expertise=0.8,
            communication_style="formal",
        ),
        AgentPersona(
            name="Aggressive Startup Founder",
            description="A founder focused on rapid growth, willing to take risks",
            goals=["Move fast", "Break things to learn", "Scale quickly"],
            budget=10000.0,
            risk_tolerance=0.9,
            technical_expertise=0.6,
            communication_style="direct",
        ),
        AgentPersona(
            name="SRE / Platform Engineer",
            description="An SRE focused on system performance and availability",
            goals=["Monitor system health", "Optimize performance", "Ensure SLAs"],
            budget=5000.0,
            risk_tolerance=0.3,
            technical_expertise=0.9,
            communication_style="technical",
        ),
        AgentPersona(
            name="QA Engineer",
            description="A QA engineer who tests edge cases and error conditions",
            goals=["Find bugs", "Test error handling", "Verify edge cases"],
            budget=500.0,
            risk_tolerance=0.5,
            technical_expertise=0.7,
            communication_style="detailed",
        ),
    ]


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


async def run_simulation():
    """Run the full simulation test."""
    print("=" * 60)
    print("FULL INFRASTRUCTURE SIMULATION TEST")
    print("=" * 60)

    # Initialize components
    mock_api = MockAPIManager()
    orchestrator = SimulationOrchestrator()

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

        # Create personas and endpoint config
        personas = create_sample_personas()
        endpoint_config = get_endpoint_config()

        print(f"\nConfiguration:")
        print(f"  Target API: {mock_api.base_url}")
        print(f"  Personas: {[p.name for p in personas]}")
        print(f"  Agents per persona: 5")
        print(f"  Interactions per agent: 8")
        print(f"  Total agents: {len(personas) * 5}")

        # Run simulation
        print(f"\nStarting simulation...")
        start_time = time.time()

        results = await orchestrator.run_simulation(
            base_url=mock_api.base_url,
            endpoint_config=endpoint_config,
            personas=personas,
            agents_per_persona=5,
            num_interactions=8,
            save_to_db=True  # Save to database for dashboard
        )

        end_time = time.time()

        # Print results
        print("\n" + orchestrator.get_simulation_summary(results))

        # Show how to access the results
        print(f"\nResults saved to database with simulation ID: {results['simulation_id']}")
        print(f"You can view these results in the analytics dashboard.")
        print(f"To view the API docs, visit: {mock_api.base_url}/docs")

        return results

    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        return None
    except Exception as e:
        print(f"\nError during simulation: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up
        mock_api.stop()


def main():
    """Main entry point."""
    try:
        results = asyncio.run(run_simulation())
        if results:
            print("\n[SUCCESS] Simulation completed successfully!")
            return 0
        else:
            print("\n[FAIL] Simulation failed or was interrupted!")
            return 1
    except Exception as e:
        print(f"\n[FAIL] Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())