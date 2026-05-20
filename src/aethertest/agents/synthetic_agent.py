"""
Synthetic agent for AetherTest.
"""
import logging
from typing import Dict, Any
from aethertest.agents.agent_types import AgentPersona

class SyntheticAgent:
    def __init__(self, agent_id: str, persona: AgentPersona):
        self.agent_id = agent_id
        self.persona = persona

def create_synthetic_agent_from_config(config: Dict[str, Any]) -> SyntheticAgent:
    persona = AgentPersona(
        name=config.get("persona_name", "Default Persona"),
        description=config.get("persona_description", ""),
        goals=config.get("persona_goals", []),
        budget=config.get("persona_budget", 0.0)
    )
    return SyntheticAgent(
        agent_id=config.get("agent_id", "unknown"),
        persona=persona
    )

logger = logging.getLogger(__name__)