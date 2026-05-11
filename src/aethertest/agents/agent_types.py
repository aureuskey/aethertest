"""
Different types of synthetic agents for AetherTest simulations.
"""
from typing import Dict, Any, Optional, List
from src.aethertest.agents.base_agent import BaseAgent, AgentState
from src.aethertest.agents.synthetic_agent import SyntheticAgent, create_synthetic_agent_from_config
from src.aethertest.agents.enhanced_synthetic_agent import EnhancedSyntheticAgent
import random
import asyncio


class APIUserAgent(BaseAgent):
    """
    Simulates a regular user making typical API calls.
    """

    def __init__(self, agent_id: str, api_endpoint: str, api_key: Optional[str] = None):
        super().__init__(agent_id, api_endpoint, api_key)
        self.endpoints = [
            ("GET", "/users"),
            ("GET", "/posts"),
            ("POST", "/posts"),
            ("GET", "/comments"),
        ]

    async def interact(self) -> Dict[str, Any]:
        """
        Make a random API call typical of a user.
        """
        method, path = random.choice(self.endpoints)
        data = None
        if method == "POST" and "/posts" in path:
            data = {
                "title": f"Post from agent {self.agent_id}",
                "body": f"Content from agent {self.agent_id}",
                "userId": random.randint(1, 100),
            }
        return await self._make_request(method, path, data=data)


class StresstestAgent(BaseAgent):
    """
    Agent designed to stress test the API with rapid requests.
    """

    def __init__(self, agent_id: str, api_endpoint: str, api_key: Optional[str] = None):
        super().__init__(agent_id, api_endpoint, api_key)
        self.request_count = 0

    async def interact(self) -> Dict[str, Any]:
        """
        Make a simple GET request to a common endpoint.
        """
        self.request_count += 1
        return await self._make_request("GET", f"/ping?request={self.request_count}")


class ErrorTestingAgent(BaseAgent):
    """
    Agent that deliberately sends malformed requests to test error handling.
    """

    def __init__(self, agent_id: str, api_endpoint: str, api_key: Optional[str] = None):
        super().__init__(agent_id, api_endpoint, api_key)

    async def interact(self) -> Dict[str, Any]:
        """
        Send various malformed requests to test API robustness.
        """
        test_type = random.choice(["invalid_json", "missing_auth", "wrong_method", "large_payload"])

        if test_type == "invalid_json":
            # This would require sending invalid JSON, but our _make_request uses json parameter
            # So we'll simulate by sending a request that will likely cause validation error
            return await self._make_request("POST", "/users", data={"invalid": "data"})
        elif test_type == "missing_auth":
            # Temporarily remove auth header
            original_headers = self.headers.copy()
            if "Authorization" in self.headers:
                del self.headers["Authorization"]
            result = await self._make_request("GET", "/users")
            self.headers = original_headers
            return result
        elif test_type == "wrong_method":
            return await self._make_request("DELETE", "/posts/1")
        else:  # large_payload
            large_data = {"data": "x" * 10000}  # 10KB payload
            return await self._make_request("POST", "/posts", data=large_data)


class MonitoringAgent(BaseAgent):
    """
    Agent that monitors API health and performance.
    """

    def __init__(self, agent_id: str, api_endpoint: str, api_key: Optional[str] = None):
        super().__init__(agent_id, api_endpoint, api_key)

    async def interact(self) -> Dict[str, Any]:
        """
        Perform a health check request and measure response time.
        """
        import time
        start_time = time.time()
        result = await self._make_request("GET", "/health")
        end_time = time.time()
        result["response_time_ms"] = (end_time - start_time) * 1000
        return result


def get_available_agent_types() -> List[str]:
    """
    Return a list of available agent type names.
    """
    return ["api_user", "stresstest", "error_testing", "monitoring", "enhanced_synthetic"]


def create_agent(agent_type: str, agent_id: str, api_endpoint: str, api_key: Optional[str] = None) -> BaseAgent:
    """
    Factory function to create an agent of the specified type.
    """
    agent_types = {
        "api_user": APIUserAgent,
        "stresstest": StresstestAgent,
        "error_testing": ErrorTestingAgent,
        "monitoring": MonitoringAgent,
        "synthetic": SyntheticAgent,  # Will use default persona
        "enhanced_synthetic": EnhancedSyntheticAgent,  # Enhanced version with realistic behavior
    }
    agent_class = agent_types.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    # For synthetic and enhanced_synthetic agents, we need to pass additional optional args but the factory signature doesn't allow it.
    # We'll handle this by creating them with default parameters.
    if agent_type == "synthetic":
        return SyntheticAgent(agent_id, api_endpoint, api_key)
    elif agent_type == "enhanced_synthetic":
        return EnhancedSyntheticAgent(agent_id, api_endpoint, api_key)
    return agent_class(agent_id, api_endpoint, api_key)