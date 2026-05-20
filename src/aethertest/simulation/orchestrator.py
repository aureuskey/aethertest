"""
Simulation orchestrator managing multiple agents with LangGraph integration.
"""
import asyncio
import uuid
import time
from typing import Dict, Any, List, Optional
from aethertest.agents.agent_types import create_agent, get_available_agent_types
from aethertest.agents.synthetic_agent import AgentPersona
from aethertest.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Default personas for Freelance Marketplace
DEFAULT_CLIENT_PERSONAS = [
    AgentPersona(
        name="Startup Client",
        description="A startup founder needing to build an MVP quickly and affordably",
        goals=["Build MVP", "Keep costs low"],
        budget=5000.0
    ),
    AgentPersona(
        name="Enterprise Client",
        description="An enterprise client looking for a reliable solution",
        goals=["Implement solution", "Ensure reliability"],
        budget=50000.0
    )
]

DEFAULT_FREELANCER_PERSONAS = [
    AgentPersona(
        name="Junior Freelancer",
        description="A junior freelancer looking to gain experience",
        goals=["Gain experience", "Earn money"],
        budget=0.0
    ),
    AgentPersona(
        name="Senior Freelancer",
        description="A senior freelancer looking for high-paying projects",
        goals=["Earn high income", "Work on challenging projects"],
        budget=0.0
    )
]

async def run_simulation(
    simulation_id: str,
    api_endpoint: str,
    api_key: Optional[str] = None,
    agent_count: int = 100,
    scenario: str = "basic_interaction",
    duration_minutes: int = 30,
    agent_type: Optional[str] = None,
    synthetic_personas: Optional[List[Dict[str, Any]]] = None,
    anthropic_api_key: Optional[str] = None,
    # Freelance Marketplace specific parameters
    num_clients: Optional[int] = None,
    num_freelancers: Optional[int] = None,
    client_personas: Optional[List[Dict[str, Any]]] = None,
    freelancer_personas: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Run a simulation with synthetic agents interacting with the provided API.
    Uses LangGraph-based agents for internal processing.
    """
    logger.info(f"Starting simulation {simulation_id} with {agent_count} agents")

    # Determine agent types and counts
    if agent_type is None:
        # Default to synthetic agents for backward compatibility
        agent_type = "synthetic"

    # Create agents
    agents = []
    for i in range(agent_count):
        agent_id = f"{agent_type}_{simulation_id}_{i}"

        # Determine persona based on agent type and available persona lists
        persona = None
        if agent_type == "synthetic":
            if synthetic_personas and i < len(synthetic_personas):
                persona_data = synthetic_personas[i]
                persona = AgentPersona(
                    name=persona_data.get("name", "Synthetic Agent"),
                    description=persona_data.get("description", ""),
                    goals=persona_data.get("goals", []),
                    budget=persona_data.get("budget", 0.0)
                )
            elif agent_count <= len(DEFAULT_FREELANCER_PERSONAS):
                persona = DEFAULT_FREELANCER_PERSONAS[i % len(DEFAULT_FREELANCER_PERSONAS)]
            else:
                persona = AgentPersona(
                    name=f"Synthetic Agent {i}",
                    description="A synthetic agent",
                    goals=["Complete tasks"],
                    budget=0.0
                )
        else:
            # For other agent types, use a generic persona
            persona = AgentPersona(
                name=f"{agent_type} Agent {i}",
                description=f"An {agent_type} agent",
                goals=["Complete tasks"],
                budget=0.0
            )

        # Create the agent
        agent = create_agent(agent_type, agent_id, persona)
        agents.append(agent)

    # Run simulation for the specified duration
    results = []
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    interaction_number = 0
    while time.time() < end_time:
        interaction_number += 1
        logger.info(f"Simulation {simulation_id}: Interaction round {interaction_number}")

        # Have each agent interact with the environment
        interaction_tasks = []
        for agent in agents:
            context = {
                "simulation_id": simulation_id,
                "api_endpoint": api_endpoint,
                "api_key": api_key,
                "scenario": scenario,
                "interaction_number": interaction_number,
                "timestamp": time.time(),
                # Include any other relevant context
            }
            task = agent.interact(context)
            interaction_tasks.append(task)

        # Wait for all agents to complete their interaction
        interaction_results = await asyncio.gather(*interaction_tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(interaction_results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agents[i].agent_id} failed in interaction {interaction_number}: {result}")
                result = {
                    "agent_id": agents[i].agent_id,
                    "error": str(result),
                    "action": None,
                    "action_result": None,
                    "reflection": None
                }
            elif not isinstance(result, dict):
                logger.error(f"Agent {agents[i].agent_id} returned non-dict result: {result}")
                result = {
                    "agent_id": agents[i].agent_id,
                    "error": "Invalid result type",
                    "action": None,
                    "action_result": None,
                    "reflection": None
                }

            # Add to results
            results.append({
                "simulation_id": simulation_id,
                "interaction_number": interaction_number,
                "agent_id": result.get("agent_id", agents[i].agent_id),
                "timestamp": result.get("timestamp", time.time()),
                "action": result.get("action"),
                "action_result": result.get("action_result"),
                "reflection": result.get("reflection")
            })

        # Sleep briefly to avoid overwhelming the system
        await asyncio.sleep(0.1)

    # Calculate simulation duration
    actual_duration = time.time() - start_time

    logger.info(f"Simulation {simulation_id} completed in {actual_duration:.2f} seconds")

    return {
        "simulation_id": simulation_id,
        "status": "completed",
        "message": f"Simulation completed after {duration_minutes} minutes",
        "duration_seconds": actual_duration,
        "total_interactions": len(results),
        "agents_count": len(agents),
        "results": results
    }

async def save_simulation_results(simulation_id: str, results: List[Dict[str, Any]]) -> None:
    """
    Save simulation results to the database.
    Implementation would depend on your database schema.
    """
    # This is a placeholder - implement based on your actual DB models
    # For now, we'll just log the results
    logger.info(f"Saving results for simulation {simulation_id}: {len(results)} interactions")
    # In a real implementation, you would save to a database here
    pass