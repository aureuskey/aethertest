"""
Base agent class for AetherTest with LangGraph integration.
"""
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from aethertest.agents.synthetic_agent import SyntheticAgent, AgentPersona


class BaseAgentState(Dict[str, Any]):
    """State for the agent workflow."""
    pass


class BaseAgent:
    """Base agent class that integrates with LangGraph."""

    def __init__(self, agent_id: str, persona: AgentPersona):
        self.agent_id = agent_id
        self.persona = persona
        self.synthetic_agent = SyntheticAgent(agent_id, persona)
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create a LangGraph workflow for the agent."""
        workflow = StateGraph(BaseAgentState)

        # Add nodes
        workflow.add_node("think", self._think)
        workflow.add_node("act", self._act)
        workflow.add_node("reflect", self._reflect)

        # Set entry point
        workflow.set_entry_point("think")

        # Add edges
        workflow.add_edge("think", "act")
        workflow.add_edge("act", "reflect")
        workflow.add_edge("reflect", END)

        return workflow.compile()

    async def _think(self, state: BaseAgentState) -> BaseAgentState:
        """Think phase: decide on an action."""
        # This is a placeholder - in a real implementation, this would use the agent's brain
        # to decide on an action based on the current state.
        state["action"] = {
            "type": "noop",
            "description": "No operation",
            "parameters": {}
        }
        return state

    async def _act(self, state: BaseAgentState) -> BaseAgentState:
        """Act phase: perform the decided action."""
        # This is a placeholder - in a real implementation, this would interact with the environment.
        state["action_result"] = {
            "status": "success",
            "data": {}
        }
        return state

    async def _reflect(self, state: BaseAgentState) -> BaseAgentState:
        """Reflect phase: reflect on the action taken."""
        # This is a placeholder - in a real implementation, this would generate a reflection.
        state["reflection"] = {
            "lessons_learned": [],
            "next_steps": []
        }
        return state

    async def interact(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interact with the environment using the LangGraph workflow.

        Args:
            context: The context for the interaction.

        Returns:
            The result of the interaction.
        """
        # Initialize the state
        initial_state: BaseAgentState = {
            "agent_id": self.agent_id,
            "persona": self.persona.__dict__,
            "context": context,
            "action": None,
            "action_result": None,
            "reflection": None
        }

        # Run the workflow
        final_state = await self.workflow.ainvoke(initial_state)
        # Ensure final_state is a dictionary
        if not isinstance(final_state, dict):
            final_state = {}

        return {
            "agent_id": self.agent_id,
            "action": final_state.get("action"),
            "action_result": final_state.get("action_result"),
            "reflection": final_state.get("reflection")
        }

    # For compatibility with existing code, we also provide a direct method to use the synthetic agent
    async def synthetic_interact(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Interact using the underlying synthetic agent (for testing or simple cases)."""
        return await self.synthetic_agent.interact(context)