"""
API routes for simulation management.
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from src.aethertest.simulation.orchestrator import run_simulation
from src.aethertest.core.database import SessionLocal
from src.aethertest.core.models import SimulationRun
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

class SimulationCreate(BaseModel):
    api_endpoint: str
    api_key: Optional[str] = None
    agent_count: int = 100
    scenario: str = "basic_interaction"
    duration_minutes: int = 30
    # Optional synthetic agent configuration
    agent_type: Optional[str] = None  # Override agent type distribution; if set, all agents will be this type
    synthetic_personas: Optional[List[Dict[str, Any]]] = None  # List of persona configs for synthetic agents
    anthropic_api_key: Optional[str] = None  # For enabling reasoning in synthetic agents
    # Freelance Marketplace specific parameters
    num_clients: Optional[int] = None  # Number of Client agents (if specified, overrides agent_count)
    num_freelancers: Optional[int] = None  # Number of Freelancer agents (if specified, overrides agent_count)
    client_personas: Optional[List[Dict[str, Any]]] = None  # Personas for Client agents
    freelancer_personas: Optional[List[Dict[str, Any]]] = None  # Personas for Freelancer agents

class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    message: str

# In-memory store for simulations (in production, use database)
simulations: Dict[str, Dict[str, Any]] = {}

@router.post("/simulations", response_model=SimulationResponse)
async def create_simulation(
    simulation: SimulationCreate,
    background_tasks: BackgroundTasks
):
    """
    Create a new simulation with synthetic agents interacting with the provided API.
    """
    simulation_id = str(uuid.uuid4())

    # Store initial simulation state in memory
    simulations[simulation_id] = {
        "id": simulation_id,
        "status": "created",
        "config": simulation.dict(),
        "results": None,
    }

    # Also create simulation run record in database
    db = SessionLocal()
    try:
        simulation_run = SimulationRun(
            id=simulation_id,
            api_endpoint=simulation.api_endpoint,
            start_time=datetime.utcnow(),
            status="created",
            config=simulation.dict(),  # Store the simulation configuration
            total_interactions=0,
            successful_interactions=0,
            failed_interactions=0
        )
        db.add(simulation_run)
        db.commit()
        logger.info(f"Created simulation run record in database for {simulation_id}")
    except Exception as e:
        logger.error(f"Error creating simulation run record in database: {e}")
        db.rollback()
    finally:
        db.close()

    # Run simulation in background
    background_tasks.add_task(
        run_simulation,
        simulation_id=simulation_id,
        api_endpoint=simulation.api_endpoint,
        api_key=simulation.api_key,
        agent_count=simulation.agent_count,
        scenario=simulation.scenario,
        duration_minutes=simulation.duration_minutes,
        agent_type=simulation.agent_type,
        synthetic_personas=simulation.synthetic_personas,
        anthropic_api_key=simulation.anthropic_api_key,
        # Freelance Marketplace specific parameters
        num_clients=simulation.num_clients,
        num_freelancers=simulation.num_freelancers,
        client_personas=simulation.client_personas,
        freelancer_personas=simulation.freelancer_personas,
    )

    logger.info(f"Created simulation {simulation_id} with config: {simulation.dict()}")

    return SimulationResponse(
        simulation_id=simulation_id,
        status="created",
        message="Simulation started in background",
    )

@router.get("/simulations/{simulation_id}", response_model=Dict[str, Any])
async def get_simulation(simulation_id: str):
    """
    Get the status and results of a simulation.
    """
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return simulations[simulation_id]

@router.get("/agents/types")
async def get_agent_types():
    """
    Get available agent types for simulations.
    """
    from src.aethertest.agents.agent_types import get_available_agent_types
    return {"agent_types": get_available_agent_types()}