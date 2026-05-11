"""
Simulation orchestrator managing multiple agents.
Updated to work with EnhancedSyntheticAgent for infrastructure testing.
"""
import asyncio
import datetime
import uuid
import time
import logging
from typing import Dict, Any, List, Optional
from signal import signal, SIGINT
from sys import exit

from src.aethertest.agents.enhanced_synthetic_agent import EnhancedSyntheticAgent
from src.aethertest.agents.agent_types import create_agent
from src.aethertest.agents.synthetic_agent import AgentPersona

logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    """
    Orchestrates simulation runs with EnhancedSyntheticAgents for infrastructure testing.

    Features:
    - Creates agents with different personas
    - Runs agents concurrently using asyncio
    - Collects metrics, logs, and interactions
    - Saves results to database for analytics dashboard
    - Provides clean interface for running simulations
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.running = False
        self.shutdown_requested = False

        # Set up signal handler for graceful shutdown
        signal(SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Shutdown signal received. Finishing current operations...")
        self.shutdown_requested = True

    def create_enhanced_agents(
        self,
        base_url: str,
        endpoint_config: Dict[str, str],
        personas: List[AgentPersona],
        agents_per_persona: int
    ) -> List[EnhancedSyntheticAgent]:
        """
        Create EnhancedSyntheticAgents with specified personas.

        Args:
            base_url: Base URL of the API to test
            endpoint_config: Mapping of logical endpoint names to actual paths
            personas: List of AgentPersona objects to use
            agents_per_persona: Number of agents to create for each persona

        Returns:
            List of created EnhancedSyntheticAgent instances
        """
        agents = []

        for persona in personas:
            for i in range(agents_per_persona):
                agent_id = f"{persona.name.lower().replace(' ', '_')}_{i}"
                agent = EnhancedSyntheticAgent(
                    agent_id=agent_id,
                    api_endpoint=base_url,
                    persona=persona,
                    endpoint_config=endpoint_config
                )
                agents.append(agent)
                logger.debug(f"Created agent: {agent.agent_id} ({persona.name})")

        logger.info(f"Created {len(agents)} agents ({len(personas)} personas, {agents_per_persona} each)")
        return agents

    async def run_agent_simulation(
        self,
        agent: EnhancedSyntheticAgent,
        num_interactions: int
    ) -> List[Dict[str, Any]]:
        """
        Run a single agent for multiple interactions and return results.

        Args:
            agent: EnhancedSyntheticAgent to run
            num_interactions: Number of interactions to perform

        Returns:
            List of interaction results
        """
        results = []
        for i in range(num_interactions):
            # Check for shutdown request
            if self.shutdown_requested:
                logger.info(f"Agent {agent.agent_id} stopping due to shutdown request")
                break

            try:
                result = await agent.interact()
                result["interaction_number"] = i + 1
                result["timestamp"] = time.time()
                results.append(result)

                # Small delay between interactions to simulate realistic timing
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in agent {agent.agent_id} interaction {i+1}: {e}")
                results.append({
                    "agent_id": agent.agent_id,
                    "interaction_number": i + 1,
                    "error": str(e),
                    "timestamp": time.time(),
                })

        return results

    async def run_simulation(
        self,
        base_url: str,
        endpoint_config: Dict[str, str],
        personas: List[AgentPersona],
        agents_per_persona: int = 5,
        num_interactions: int = 10,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Run a full simulation round with multiple agents and personas.

        Args:
            base_url: Base URL of the API to test
            endpoint_config: Mapping of logical endpoint names to actual paths
            personas: List of AgentPersona objects to use
            agents_per_persona: Number of agents to create for each persona (default: 5)
            num_interactions: Number of interactions per agent (default: 10)
            save_to_db: Whether to save results to database (default: True)

        Returns:
            Dictionary containing simulation results and metrics
        """
        if self.running:
            raise RuntimeError("Simulation is already running")

        self.running = True
        self.shutdown_requested = False
        start_time = time.time()

        # Generate simulation ID
        simulation_id = str(uuid.uuid4())
        logger.info(f"Starting simulation {simulation_id}")

        try:
            # Create agents
            agents = self.create_enhanced_agents(
                base_url=base_url,
                endpoint_config=endpoint_config,
                personas=personas,
                agents_per_persona=agents_per_persona
            )

            # Run agents concurrently
            logger.info(f"Running {len(agents)} agents for {num_interactions} interactions each...")
            tasks = []
            for agent in agents:
                task = self.run_agent_simulation(agent, num_interactions)
                tasks.append(task)

            # Wait for all agents to complete
            results_lists = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            agent_results = {}
            all_interactions = []
            total_interactions = 0
            successful_interactions = 0
            failed_interactions = 0
            total_retries = 0

            for i, agent in enumerate(agents):
                persona_name = agent.persona.name

                if isinstance(results_lists[i], Exception):
                    logger.error(f"Agent {agent.agent_id} failed with exception: {results_lists[i]}")
                    agent_results[persona_name] = {
                        "agent_id": agent.agent_id,
                        "error": str(results_lists[i]),
                        "interactions": []
                    }
                else:
                    interactions = results_lists[i]
                    agent_results[persona_name] = {
                        "agent_id": agent.agent_id,
                        "interactions": interactions
                    }

                    # Process interactions for metrics
                    for interaction in interactions:
                        total_interactions += 1
                        all_interactions.append(interaction)

                        # Check if interaction was successful
                        if interaction.get("overall_success", False):
                            successful_interactions += 1
                        else:
                            failed_interactions += 1

                        # Count retries
                        for workflow_result in interaction.get("workflow_results", []):
                            total_retries += workflow_result.get("retry_count", 0)

            # Calculate success rate
            success_rate = (successful_interactions / total_interactions * 100) if total_interactions > 0 else 0

            # Prepare final results
            end_time = time.time()
            execution_time = end_time - start_time

            results = {
                "simulation_id": simulation_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "execution_time_seconds": execution_time,
                "config": {
                    "base_url": base_url,
                    "endpoint_config": endpoint_config,
                    "personas": [p.name for p in personas],
                    "agents_per_persona": agents_per_persona,
                    "num_interactions": num_interactions,
                    "total_agents": len(agents)
                },
                "agents_by_persona": {},
                "aggregate_metrics": {
                    "total_interactions": total_interactions,
                    "successful_interactions": successful_interactions,
                    "failed_interactions": failed_interactions,
                    "success_rate": success_rate,
                    "total_retries": total_retries,
                    "avg_retries_per_interaction": total_retries / total_interactions if total_interactions > 0 else 0
                },
                "failure_modes": {},
                "retry_patterns": [],
                "rate_limit_events": []
            }

            # Process agent-level results
            for persona_name, agent_data in agent_results.items():
                if "error" in agent_data:
                    # Skip agents that had errors
                    continue

                interactions = agent_data["interactions"]
                agent_interactions = len(interactions)
                agent_successful = sum(1 for i in interactions if i.get("overall_success", False))
                agent_failed = agent_interactions - agent_successful
                agent_retries = sum(
                    workflow_result.get("retry_count", 0)
                    for interaction in interactions
                    for workflow_result in interaction.get("workflow_results", [])
                )

                results["agents_by_persona"][persona_name] = {
                    "agent_id": agent_data["agent_id"],
                    "num_interactions": agent_interactions,
                    "successful_interactions": agent_successful,
                    "failed_interactions": agent_failed,
                    "success_rate": (agent_successful / agent_interactions * 100) if agent_interactions > 0 else 0,
                    "avg_retries_per_interaction": agent_retries / agent_interactions if agent_interactions > 0 else 0
                }

                # Collect failure modes
                for interaction in interactions:
                    if not interaction.get("overall_success", False):
                        for workflow_result in interaction.get("workflow_results", []):
                            if not workflow_result.get("success", False):
                                status = workflow_result.get("status_code")
                                error = workflow_result.get("error", "Unknown")
                                failure_key = f"HTTP {status}" if status else error
                                results["failure_modes"][failure_key] = results["failure_modes"].get(failure_key, 0) + 1
                                break

                # Collect retry patterns
                for interaction in interactions:
                    for workflow_result in interaction.get("workflow_results", []):
                        retry_count = workflow_result.get("retry_count", 0)
                        if retry_count > 0:
                            results["retry_patterns"].append({
                                "agent_id": agent_data["agent_id"],
                                "step": workflow_result.get("step_name"),
                                "retry_count": retry_count,
                                "final_status": workflow_result.get("status_code")
                            })

                # Collect rate limit events
                for interaction in interactions:
                    for workflow_result in interaction.get("workflow_results", []):
                        rate_limit_info = workflow_result.get("rate_limit_info", {})
                        if rate_limit_info.get("remaining") is not None and rate_limit_info["remaining"] < 10:
                            results["rate_limit_events"].append({
                                "agent_id": agent_data["agent_id"],
                                "step": workflow_result.get("step_name"),
                                "remaining": rate_limit_info["remaining"],
                                "reset_time": rate_limit_info.get("reset_time")
                            })

            # Sort failure modes by count (descending)
            results["failure_modes"] = dict(
                sorted(results["failure_modes"].items(), key=lambda x: x[1], reverse=True)
            )

            # Save to database if requested
            if save_to_db:
                await self._save_to_database(results)

            logger.info(f"Simulation {simulation_id} completed in {execution_time:.2f}s")
            logger.info(f"Results: {total_interactions} interactions, {successful_interactions} successful ({success_rate:.1f}%), {failed_interactions} failed")

            return results

        finally:
            self.running = False

    async def _save_to_database(self, results: Dict[str, Any]) -> None:
        """
        Save simulation results to the database.

        Args:
            results: Simulation results dictionary
        """
        try:
            from src.aethertest.core.database import SessionLocal
            from src.aethertest.core.models import SimulationRun, AgentInteraction

            db = SessionLocal()
            try:
                # Create simulation run record
                simulation_run = SimulationRun(
                    id=results["simulation_id"],
                    api_endpoint=results["config"]["base_url"],
                    start_time=datetime.datetime.fromisoformat(results["timestamp"].replace("Z", "+00:00")),
                    status="completed",
                    config=results["config"],
                    total_interactions=results["aggregate_metrics"]["total_interactions"],
                    successful_interactions=results["aggregate_metrics"]["successful_interactions"],
                    failed_interactions=results["aggregate_metrics"]["failed_interactions"]
                )
                db.add(simulation_run)

                # Save agent interactions
                # Note: For simplicity, we're not saving every single interaction here
                # In a production system, you might want to save more detailed data
                db.commit()
                logger.info(f"Saved simulation results for {results['simulation_id']} to database")

            except Exception as e:
                logger.error(f"Error saving simulation results to database: {e}")
                db.rollback()
            finally:
                db.close()

        except ImportError as e:
            logger.warning(f"Could not save to database: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving to database: {e}")

    def get_simulation_summary(self, results: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of simulation results.

        Args:
            results: Simulation results dictionary

        Returns:
            Formatted string summary
        """
        config = results["config"]
        metrics = results["aggregate_metrics"]

        summary = []
        summary.append("=" * 60)
        summary.append("INFRASTRUCTURE SIMULATION SUMMARY")
        summary.append("=" * 60)
        summary.append(f"Simulation ID: {results['simulation_id']}")
        summary.append(f"Timestamp: {results['timestamp']}")
        summary.append(f"Execution Time: {results['execution_time_seconds']:.2f} seconds")
        summary.append("")
        summary.append("Configuration:")
        summary.append(f"  Base URL: {config['base_url']}")
        summary.append(f"  Personas: {', '.join(config['personas'])}")
        summary.append(f"  Agents per Persona: {config['agents_per_persona']}")
        summary.append(f"  Interactions per Agent: {config['num_interactions']}")
        summary.append(f"  Total Agents: {config['total_agents']}")
        summary.append("")
        summary.append("Aggregate Metrics:")
        summary.append(f"  Total Interactions: {metrics['total_interactions']}")
        summary.append(f"  Successful: {metrics['successful_interactions']} ({metrics['success_rate']:.1f}%)")
        summary.append(f"  Failed: {metrics['failed_interactions']}")
        summary.append(f"  Total Retries: {metrics['total_retries']}")
        summary.append(f"  Avg Retries/Interaction: {metrics['avg_retries_per_interaction']:.2f}")
        summary.append("")

        if results["agents_by_persona"]:
            summary.append("Per-Persona Breakdown:")
            for persona_name, data in results["agents_by_persona"].items():
                summary.append(f"  {persona_name}:")
                summary.append(f"    Agent ID: {data['agent_id']}")
                summary.append(f"    Interactions: {data['num_interactions']}")
                summary.append(f"    Success Rate: {data['success_rate']:.1f}%")
                summary.append(f"    Avg Retries/Interaction: {data['avg_retries_per_interaction']:.2f}")
            summary.append("")

        if results["failure_modes"]:
            summary.append("Top Failure Modes:")
            for failure, count in list(results["failure_modes"].items())[:5]:
                summary.append(f"  {failure}: {count} occurrences")
            summary.append("")

        if results["retry_patterns"]:
            summary.append("Retry Patterns (showing first 5):")
            for pattern in results["retry_patterns"][:5]:
                summary.append(f"  Agent {pattern['agent_id']} - Step '{pattern['step']}': "
                             f"{pattern['retry_count']} retries, final status {pattern['final_status']}")
            summary.append("")

        if results["rate_limit_events"]:
            summary.append("Rate Limit Events (showing first 5):")
            for event in results["rate_limit_events"][:5]:
                summary.append(f"  Agent {event['agent_id']} - Step '{event['step']}': "
                             f"Remaining {event['remaining']} requests")
            summary.append("")

        summary.append("=" * 60)

        return "\n".join(summary)


# Backward compatibility function
async def run_simulation(
    base_url: str,
    endpoint_config: Dict[str, str],
    personas: List[AgentPersona],
    agents_per_persona: int = 5,
    num_interactions: int = 10,
    save_to_db: bool = True
) -> Dict[str, Any]:
    """
    Backward compatibility function for running simulations.

    Args:
        base_url: Base URL of the API to test
        endpoint_config: Mapping of logical endpoint names to actual paths
        personas: List of AgentPersona objects to use
        agents_per_persona: Number of agents to create for each persona
        num_interactions: Number of interactions per agent
        save_to_db: Whether to save results to database

    Returns:
        Dictionary containing simulation results
    """
    orchestrator = SimulationOrchestrator()
    return await orchestrator.run_simulation(
        base_url=base_url,
        endpoint_config=endpoint_config,
        personas=personas,
        agents_per_persona=agents_per_persona,
        num_interactions=num_interactions,
        save_to_db=save_to_db
    )


if __name__ == "__main__":
    # For direct execution/testing
    import asyncio
    from src.aethertest.agents.synthetic_agent import AgentPersona

    async def main():
        # Create some test personas
        personas = [
            AgentPersona(
                name="Test Engineer 1",
                description="A test engineer",
                goals=["Test APIs"],
                budget=1000.0,
                risk_tolerance=0.5,
                technical_expertise=0.7,
                communication_style="detailed"
            ),
            AgentPersona(
                name="Test Engineer 2",
                description="Another test engineer",
                goals=["Validate systems"],
                budget=500.0,
                risk_tolerance=0.3,
                technical_expertise=0.8,
                communication_style="formal"
            )
        ]

        # Example endpoint config
        endpoint_config = {
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

        # Run simulation
        orchestrator = SimulationOrchestrator()
        results = await orchestrator.run_simulation(
            base_url="https://httpbin.org",  # Using httpbin for testing
            endpoint_config=endpoint_config,
            personas=personas,
            agents_per_persona=2,
            num_interactions=3,
            save_to_db=False  # Don't save to DB for direct execution
        )

        # Print results
        print(orchestrator.get_simulation_summary(results))

    asyncio.run(main())