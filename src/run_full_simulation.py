#!/usr/bin/env python3
"""
Full simulation runner for AetherTest.
"""
import asyncio
import argparse
import logging
import sys
import os
import uuid  # Added for generating simulation ID

# Add the src directory to the path so we can import from aethertest
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from aethertest.simulation.orchestrator import run_simulation
from aethertest.simulation.scenarios import get_scenario_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the simulation."""
    parser = argparse.ArgumentParser(description="Run a full AetherTest simulation")
    parser.add_argument(
        "--simulation-id",
        type=str,
        default=None,
        help="Unique identifier for the simulation (default: random UUID)"
    )
    parser.add_argument(
        "--api-endpoint",
        type=str,
        required=True,
        help="API endpoint to simulate against"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for authentication (optional)"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="basic_interaction",
        help="Scenario to run (default: basic_interaction)"
    )
    parser.add_argument(
        "--agent-count",
        type=int,
        default=None,
        help="Number of agents to simulate (default: from scenario)"
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        default=None,
        help="Type of agents to simulate (default: from scenario)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Duration of simulation in minutes (default: from scenario)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Generate simulation ID if not provided
    simulation_id = args.simulation_id
    if simulation_id is None:
        simulation_id = str(uuid.uuid4())

    # Get scenario configuration
    scenario_config = get_scenario_config(args.scenario)

    # Override scenario config with command line arguments
    agent_count = args.agent_count if args.agent_count is not None else scenario_config.get("agent_count", 10)
    agent_type = args.agent_type if args.agent_type is not None else scenario_config.get("agent_type", "synthetic")
    duration_minutes = args.duration if args.duration is not None else scenario_config.get("duration_minutes", 5)

    # Get additional scenario-specific parameters
    synthetic_personas = scenario_config.get("synthetic_personas")
    num_clients = scenario_config.get("num_clients")
    num_freelancers = scenario_config.get("num_freelancers")
    client_personas = scenario_config.get("client_personas")
    freelancer_personas = scenario_config.get("freelancer_personas")

    logger.info(f"Starting simulation {simulation_id}")
    logger.info(f"Scenario: {args.scenario}")
    logger.info(f"Agent count: {agent_count}")
    logger.info(f"Agent type: {agent_type}")
    logger.info(f"Duration: {duration_minutes} minutes")
    logger.info(f"API endpoint: {args.api_endpoint}")

    # Run the simulation
    result = await run_simulation(
        simulation_id=simulation_id,
        api_endpoint=args.api_endpoint,
        api_key=args.api_key,
        agent_count=agent_count,
        scenario=args.scenario,
        duration_minutes=duration_minutes,
        agent_type=agent_type,
        synthetic_personas=synthetic_personas,
        num_clients=num_clients,
        num_freelancers=num_freelancers,
        client_personas=client_personas,
        freelancer_personas=freelancer_personas
    )

    # Print results
    print("\n" + "="*50)
    print(f"Simulation {simulation_id} Results")
    print("="*50)
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")
    print(f"Total Interactions: {result.get('total_interactions', 0)}")
    print(f"Agents Count: {result.get('agents_count', 0)}")
    print("="*50)

    # Save results if needed (optional)
    # from aethertest.simulation.orchestrator import save_simulation_results
    # await save_simulation_results(simulation_id, result.get("results", []))

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        sys.exit(1)