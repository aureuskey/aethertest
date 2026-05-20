"""
Agent types for AetherTest.
"""
from enum import Enum
from typing import Optional
import uuid

class AgentPersona:
    def __init__(self, name: str, description: str, goals: list, budget: float):
        self.name = name
        self.description = description
        self.goals = goals
        self.budget = budget

class AgentType(str, Enum):
    API_USER = "api_user"
    STRESS_TEST = "stresstest"
    ERROR_TESTING = "error_testing"
    MONITORING = "monitoring"
    SYNTHETIC = "synthetic"


def create_agent(agent_type: str, agent_id: Optional[str] = None, persona: Optional[AgentPersona] = None):
    """Create an agent based on the agent type."""
    from aethertest.agents.base_agent import BaseAgent

    if agent_id is None:
        agent_id = str(uuid.uuid4())

    if persona is None:
        persona = AgentPersona(
            name=f"{agent_type} Agent",
            description=f"An {agent_type} agent",
            goals=["Complete tasks"],
            budget=0.0
        )
    return BaseAgent(agent_id, persona)


def get_available_agent_types():
    return [e.value for e in AgentType]