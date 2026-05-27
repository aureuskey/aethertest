"""
Full simulation integration test.
Starts mock API and runs a complete simulation with the orchestrator.
Can be configured via YAML file or command line arguments.
"""
import asyncio
import subprocess
import sys
import time
import signal
import os
import argparse
from typing import List, Dict, Any
import uvicorn
from contextlib import asynccontextmanager

# Add src to path so we can import our modules
sys.path.insert(0, 'src')

from aethertest.simulation.orchestrator import SimulationOrchestrator
from aethertest.agents.synthetic_agent import AgentPersona
from aethertest.core.yaml_config import YAMLConfigLoader


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
            [r"C:\Users\HP\AppData\Local\Programs\Python\Python313\python.exe", "-m", "uvicorn", "mock_api:app",
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


def get_mock_endpoint_config() -> dict:
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


def load_configuration() -> YAMLConfigLoader:
    """Load configuration from YAML file or create default."""
    config_loader = YAMLConfigLoader()
    return config_loader


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run AetherTest simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration (uses config.yaml or creates one)
  python run_full_simulation.py

  # Test a specific API
  python run_full_simulation.py --api-url https://api.example.com

  # Run a quick test
  python run_full_simulation.py --quick

  # Run with custom agent count
  python run_full_simulation.py --agents-per-persona 10 --num-interactions 5

  # Run for a specific duration
  python run_full_simulation.py --duration-minutes 5
        """
    )

    parser.add_argument(
        "--api-url",
        type=str,
        help="Base URL of the API to test (overrides config.yaml)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration YAML file (default: config.yaml)"
    )

    parser.add_argument(
        "--agents-per-persona",
        type=int,
        help="Number of agents per persona type (overrides config.yaml)"
    )

    parser.add_argument(
        "--num-interactions",
        type=int,
        help="Number of interactions per agent (overrides config.yaml)"
    )

    parser.add_argument(
        "--duration-minutes",
        type=float,
        help="Test duration in minutes (overrides num_interactions)"
    )

    parser.add_argument(
        "--scenario",
        type=str,
        choices=["basic_interaction", "load_test", "reliability_test", "monitoring_focus"],
        help="Specific scenario to run (overrides config.yaml)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a quick test with reduced parameters (2 personas, 2 agents each, 2 interactions)"
    )

    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Don't start mock API - use only the --api-url"
    )

    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Don't save results to database"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def create_personas_from_config(config: YAMLConfigLoader, quick: bool = False) -> List[AgentPersona]:
    """Create personas based on configuration."""
    all_personas = create_sample_personas()
    agents_config = config.get_agents_config()
    persona_enabled = agents_config.get("personas", {})

    # Filter personas based on configuration
    filtered_personas = []
    for persona in all_personas:
        persona_key = persona.name.lower().replace(' ', '_').replace('/', '_')
        if persona_enabled.get(persona_key, True):  # Default to enabled
            filtered_personas.append(persona)

    # For quick test, use only first 2 personas
    if quick:
        return filtered_personas[:2]

    return filtered_personas


async def run_simulation_with_config() -> Dict[str, Any]:
    """Run the full simulation test with configuration."""
    # Parse command line arguments
    args = parse_arguments()

    # Load configuration
    config = YAMLConfigLoader(args.config)

    # Override config with command line arguments
    updates = {}
    if args.api_url:
        updates["api.base_url"] = args.api_url
    if args.agents_per_persona is not None:
        updates["simulation.agents_per_persona"] = args.agents_per_persona
    if args.num_interactions is not None:
        updates["simulation.num_interactions"] = args.num_interactions
    if args.duration_minutes is not None:
        updates["simulation.duration_minutes"] = args.duration_minutes
    if args.scenario:
        updates["simulation.scenarios"] = [args.scenario]
    if args.no_db:
        updates["simulation.save_to_db"] = False

    if updates:
        config.update(updates)

    # Get configuration values
    api_base_url = config.get_api_base_url() if not args.no_mock else args.api_url
    endpoint_config = config.get_endpoint_config()
    simulation_config = config.get_simulation_config()
    output_config = config.get_output_config()

    # Set logging level
    if args.verbose or output_config.get("level") == "verbose":
        import logging
        logging.basicConfig(level=logging.INFO)
    elif output_config.get("level") == "debug":
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Determine test parameters
    quick_test = args.quick
    agents_per_persona = (
        2 if quick_test
        else (args.agents_per_persona if args.agents_per_persona is not None
              else simulation_config.get("agents_per_persona", 5))
    )
    num_interactions = (
        2 if quick_test
        else (args.num_interactions if args.num_interactions is not None
              else simulation_config.get("num_interactions", 8))
    )
    save_to_db = (
        False if args.no_db
        else simulation_config.get("save_to_db", True)
    )

    # Handle duration-based testing
    duration_minutes = args.duration_minutes or simulation_config.get("duration_minutes", 0)
    if duration_minutes > 0:
        # Calculate interactions based on duration and estimated time per interaction
        # Assume ~2 seconds per interaction as a rough estimate
        estimated_time_per_interaction = 2.0  # seconds
        max_interactions = int((duration_minutes * 60) / estimated_time_per_interaction)
        num_interactions = max(1, min(num_interactions, max_interactions))
        print(f"Duration-based testing: {duration_minutes} minutes ≈ {num_interactions} interactions per agent")

    # Print configuration summary
    print("=" * 60)
    print("AETHERTEST FULL SIMULATION")
    print("=" * 60)
    print(f"Configuration file: {args.config}")
    print(f"Target API: {api_base_url}")
    print(f"Quick test mode: {quick_test}")
    print(f"Agents per persona: {agents_per_persona}")
    print(f"Interactions per agent: {num_interactions}")
    print(f"Save to database: {save_to_db}")

    if not args.no_mock:
        print("\nStarting mock API server...")
    else:
        print("\nUsing external API (mock API disabled)")

    # Initialize components
    mock_api = None
    orchestrator = SimulationOrchestrator()

    try:
        # Start mock API if not disabled
        if not args.no_mock:
            mock_api = MockAPIManager()
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
        else:
            # Validate that we have an API URL for external testing
            if not api_base_url or api_base_url == "http://127.0.0.1:8000":
                print("[ERROR] External API testing requires --api-url to be set")
                return None

        # Create personas and get endpoint config
        personas = create_personas_from_config(config, quick_test)

        # If using external API, we might need to adjust endpoint config
        # For now, we'll use the configured endpoint mapping
        # In a more advanced version, we'd allow mapping to external endpoints
        final_endpoint_config = endpoint_config

        print(f"\nConfiguration:")
        print(f"  Target API: {api_base_url if not args.no_mock else 'EXTERNAL API'}")
        print(f"  Personas: {[p.name for p in personas]}")
        print(f"  Agents per persona: {agents_per_persona}")
        print(f"  Interactions per agent: {num_interactions}")
        print(f"  Total agents: {len(personas) * agents_per_persona}")

        # Run simulation
        print(f"\nStarting simulation...")
        start_time = time.time()

        results = await orchestrator.run_simulation(
            base_url=api_base_url if not args.no_mock else api_base_url,
            endpoint_config=final_endpoint_config,
            personas=personas,
            agents_per_persona=agents_per_persona,
            num_interactions=num_interactions,
            save_to_db=save_to_db
        )

        end_time = time.time()

        # Print results
        print("\n" + orchestrator.get_simulation_summary(results))

        # Show how to access the results
        print(f"\nResults saved to database with simulation ID: {results['simulation_id']}")
        if not args.no_mock:
            print(f"You can view these results in the analytics dashboard.")
            print(f"To view the API docs, visit: {api_base_url}/docs")
        else:
            print(f"API tested: {api_base_url}")

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
        if mock_api and not args.no_mock:
            mock_api.stop()


def main():
    """Main entry point."""
    try:
        results = asyncio.run(run_simulation_with_config())
        if results:
            print("\n[SUCCESS] Simulation completed successfully!")
            return 0
        else:
            print("\n[FAIL] Simulation failed or was interrupted!")
            return 1
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())