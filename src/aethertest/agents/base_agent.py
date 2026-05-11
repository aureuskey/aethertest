"""
Base class for all synthetic agents in AetherTest.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
import json
from langgraph.graph import StateGraph, END

class BaseAgent(ABC):
    """
    Abstract base class for synthetic agents.
    Each agent simulates a user or system interacting with the infrastructure API.
    """

    def __init__(self, agent_id: str, api_endpoint: str, api_key: Optional[str] = None):
        self.agent_id = agent_id
        self.api_endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": f"AetherTest-Agent/{self.agent_id}",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    @abstractmethod
    async def interact(self) -> Dict[str, Any]:
        """
        Perform an interaction with the target API and return the result.
        Must be implemented by each agent type.
        """
        pass

    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the target API.
        """
        url = f"{self.api_endpoint}{path}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.content else {},
                }
            except httpx.HTTPStatusError as e:
                return {
                    "status_code": e.response.status_code,
                    "error": str(e),
                    "data": e.response.json() if e.response.content else {},
                }
            except Exception as e:
                return {
                    "status_code": 0,
                    "error": str(e),
                    "data": {},
                }

class AgentState(dict):
    """
    State object for LangGraph agent workflow.
    """
    agent_id: str
    interaction_count: int
    last_result: Optional[Dict[str, Any]]
    metrics: Dict[str, Any]

def create_agent_workflow(agent: BaseAgent) -> StateGraph:
    """
    Create a LangGraph workflow for an agent's behavior.
    This is a simple example - can be extended for complex behaviors.
    """
    workflow = StateGraph(AgentState)

    # Define the interaction node
    async def interact_node(state: AgentState) -> AgentState:
        result = await agent.interact()
        state["interaction_count"] += 1
        state["last_result"] = result
        # Update metrics based on result
        state["metrics"]["total_interactions"] = state["interaction_count"]
        if result.get("status_code", 0) == 200:
            state["metrics"]["successful_interactions"] = state["metrics"].get("successful_interactions", 0) + 1
        else:
            state["metrics"]["failed_interactions"] = state["metrics"].get("failed_interactions", 0) + 1
        return state

    workflow.add_node("interact", interact_node)
    workflow.set_entry_point("interact")
    # For simplicity, we'll just do one interaction per agent in this example
    # In a real simulation, you might have loops or more complex logic
    workflow.add_edge("interact", END)

    return workflow.compile()