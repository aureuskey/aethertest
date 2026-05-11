"""
Flexible SyntheticAgent class representing different user personas with goals, budget, memory, and reasoning capabilities.
"""
from typing import Dict, Any, Optional, List, Callable
import json
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from src.aethertest.agents.base_agent import BaseAgent
import logging

# Configure logging (should be called once, but calling multiple times is safe after first call)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


@dataclass
class MemoryItem:
    """Represents a single memory item."""
    timestamp: float
    content: Dict[str, Any]
    memory_type: MemoryType
    importance: float = 1.0  # 0.0 to 1.0


@dataclass
class AgentPersona:
    """Defines a user persona for the synthetic agent."""
    name: str
    description: str
    goals: List[str]
    budget: float
    risk_tolerance: float  # 0.0 (risk-averse) to 1.0 (risk-seeking)
    technical_expertise: float  # 0.0 (non-technical) to 1.0 (expert)
    communication_style: str  # e.g., "formal", "casual", "technical"


class SyntheticAgent(BaseAgent):
    """
    A flexible synthetic agent that can represent different user personas.
    Capable of reasoning, goal-oriented behavior, and learning from interactions.
    """

    # Class-level prompt templates
    PROMPT_TEMPLATES = {
        "reasoning": """
You are {persona_name}, a {persona_description}.

Your goals are:
{goals}

Your budget is ${budget}.
Your risk tolerance is {risk_tolerance}/1.0.
Your technical expertise is {technical_expertise}/1.0.
Your communication style is {communication_style}.

Recent interactions (short-term memory):
{short_term_memory}

Relevant past experiences (long-term memory):
{long_term_memory}

Current situation: You need to interact with an API at {api_endpoint}.
Based on your persona and goals, what is the next best action to take?
Consider:
1. Which endpoint to call and with what method
2. What data to send (if any)
3. What you hope to learn or achieve
4. How this aligns with your budget and risk tolerance

Respond with a JSON object containing:
{{
    "action": "make_api_call",
    "method": "GET|POST|PUT|DELETE|PATCH",
    "endpoint": "/path/to/endpoint",
    "data": {{}} // JSON serializable data for POST/PUT/PATCH, null for others,
    "reasoning": "brief explanation of why this action aligns with your persona and goals"
}}
""",
        "reflection": """
You are {persona_name}. You just performed an action: {action_taken}
The result was: {action_result}

Reflect on:
1. Did this action help you achieve your goals? Why or why not?
2. What did you learn about the API?
3. Should you adjust your approach based on this result and your persona characteristics?
4. What should be your next action?

Provide your reflection and next action recommendation in JSON format:
{{
    "reflection": "your thoughts on the outcome",
    "lessons_learned": ["lesson1", "lesson2"],
    "next_action_suggestion": "suggestion for what to do next",
    "adjust_persona": {{}} // optional adjustments to persona attributes
}}
"""
    }

    def __init__(
        self,
        agent_id: str,
        api_endpoint: str,
        api_key: Optional[str] = None,
        persona: Optional[AgentPersona] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize a SyntheticAgent.

        Args:
            agent_id: Unique identifier for this agent
            api_endpoint: Base URL of the target API
            api_key: Optional API key for the target API
            persona: AgentPersona defining this agent's characteristics
            anthropic_api_key: API key for Anthropic Claude (for reasoning)
        """
        super().__init__(agent_id, api_endpoint, api_key)
        self.persona = persona or self._default_persona()
        self.anthropic_api_key = anthropic_api_key
        self.anthropic_client = None
        if ANTHROPIC_AVAILABLE and anthropic_api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

        # Memory systems
        self.short_term_memory: List[MemoryItem] = []
        self.long_term_memory: List[MemoryItem] = []
        self.max_short_term = 10  # Keep last 10 interactions
        self.max_long_term = 100  # Keep up to 100 important memories

        # Action history for learning
        self.action_history: List[Dict[str, Any]] = []

        # Available tools (methods the agent can call)
        self.available_tools: Dict[str, Callable] = {
            "make_api_call": self._make_api_call_tool,
            "wait": self._wait_tool,
            "reflect": self._reflect_tool,
        }

        logger.info(f"Initialized SyntheticAgent {agent_id} with persona {self.persona.name}")

    def _default_persona(self) -> AgentPersona:
        """Create a default generic persona."""
        return AgentPersona(
            name="Generic User",
            description="A generic API user with no specific characteristics",
            goals=["Explore the API", "Complete basic tasks"],
            budget=100.0,
            risk_tolerance=0.5,
            technical_expertise=0.5,
            communication_style="neutral",
        )

    def _add_memory(self, content: Dict[str, Any], memory_type: MemoryType, importance: float = 1.0):
        """Add a memory item to the appropriate memory store."""
        item = MemoryItem(
            timestamp=time.time(),
            content=content,
            memory_type=memory_type,
            importance=importance,
        )

        if memory_type == MemoryType.SHORT_TERM:
            self.short_term_memory.append(item)
            # Keep short-term memory within limit
            if len(self.short_term_memory) > self.max_short_term:
                # Move oldest to long-term if important enough
                oldest = self.short_term_memory.pop(0)
                if oldest.importance > 0.5:
                    self.long_term_memory.append(oldest)
                    # Trim long-term memory
                    if len(self.long_term_memory) > self.max_long_term:
                        self.long_term_memory.sort(key=lambda x: x.importance, reverse=True)
                        self.long_term_memory = self.long_term_memory[:self.max_long_term]
        else:
            self.long_term_memory.append(item)
            # Keep long-term memory within limit
            if len(self.long_term_memory) > self.max_long_term:
                self.long_term_memory.sort(key=lambda x: x.importance, reverse=True)
                self.long_term_memory = self.long_term_memory[:self.max_long_term]

    def _format_memory_for_prompt(self, memory_list: List[MemoryItem], limit: int = 5) -> str:
        """Format memory items for inclusion in prompts."""
        if not memory_list:
            return "No relevant memories."

        # Take most recent items
        recent = sorted(memory_list, key=lambda x: x.timestamp, reverse=True)[:limit]
        formatted = []
        for item in recent:
            formatted.append(f"- [{time.strftime('%H:%M:%S', time.localtime(item.timestamp))}] {json.dumps(item.content, indent=2)}")
        return "\n".join(formatted)

    async def _reason_and_act(self) -> Dict[str, Any]:
        """
        Use reasoning (via Anthropic API if available, else fallback) to decide next action.
        Returns a dict representing the action to take.
        """
        # Prepare prompt variables
        goals_str = "\n".join([f"- {goal}" for goal in self.persona.goals])
        short_term_str = self._format_memory_for_prompt(self.short_term_memory)
        long_term_str = self._format_memory_for_prompt(self.long_term_memory)

        prompt = self.PROMPT_TEMPLATES["reasoning"].format(
            persona_name=self.persona.name,
            persona_description=self.persona.description,
            goals=goals_str,
            budget=self.persona.budget,
            risk_tolerance=self.persona.risk_tolerance,
            technical_expertise=self.persona.technical_expertise,
            communication_style=self.persona.communication_style,
            short_term_memory=short_term_str,
            long_term_memory=long_term_str,
            api_endpoint=self.api_endpoint,
        )

        # Try to use Anthropic for reasoning
        if self.anthropic_client:
            try:
                message = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",  # or sonnet, depending on availability
                    max_tokens=1000,
                    temperature=0.7,
                    system="You are a helpful AI that helps synthetic agents decide on API interactions.",
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = message.content[0].text if message.content else ""
                # Try to parse JSON from response
                action_dict = self._parse_json_response(response_text)
                if action_dict:
                    return action_dict
            except Exception as e:
                logger.warning(f"Anthropic reasoning failed: {e}, falling back to rule-based")

        # Fallback to rule-based action selection
        return self._rule_based_action()

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to extract and parse JSON from the response text."""
        try:
            # Find JSON-like content
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and start < end:
                json_str = text[start:end+1]
                return json.loads(json_str)
        except Exception as e:
            logger.debug(f"Failed to parse JSON from response: {e}")
        return None

    def _rule_based_action(self) -> Dict[str, Any]:
        """Fallback rule-based action selection when reasoning API is unavailable."""
        # Simple heuristic: choose a random endpoint but bias based on persona
        import random

        # Define some basic endpoints (could be discovered dynamically)
        endpoints = [
            ("GET", "/users"),
            ("GET", "/posts"),
            ("POST", "/posts"),
            ("GET", "/comments"),
            ("GET", "/health"),
        ]

        # Bias selection based on persona traits
        weights = [1.0] * len(endpoints)
        # Adjust weights based on persona (simplified)
        if self.persona.technical_expertise > 0.7:
            # More technical users might try POST/PUT
            weights[2] *= 1.5  # POST /posts
        if self.persona.risk_tolerance < 0.3:
            # Risk-averse users prefer safe GETs
            weights[0] *= 1.5  # GET /users
            weights[1] *= 1.5  # GET /posts
            weights[4] *= 2.0  # GET /health

        # Normalize weights
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]
        else:
            weights = [1.0 / len(endpoints)] * len(endpoints)

        chosen_idx = random.choices(range(len(endpoints)), weights=weights)[0]
        method, path = endpoints[chosen_idx]

        data = None
        if method in ["POST", "PUT", "PATCH"] and "/posts" in path:
            data = {
                "title": f"Post from {self.persona.name} ({self.agent_id})",
                "body": f"Content generated by {self.persona.description}",
                "userId": random.randint(1, 100),
            }

        return {
            "action": "make_api_call",
            "method": method,
            "endpoint": path,
            "data": data,
            "reasoning": f"Rule-based selection for {self.persona.name}",
        }

    async def _make_api_call_tool(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Tool to make an HTTP API call."""
        return await self._make_request(method, endpoint, data=data)

    async def _wait_tool(self, seconds: float = 1.0) -> Dict[str, Any]:
        """Tool to wait for a specified number of seconds."""
        await asyncio.sleep(seconds)
        return {"action": "wait", "seconds": seconds, "completed": True}

    async def _reflect_tool(self, action_taken: Dict[str, Any], action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Tool to reflect on an action and its result."""
        reflection_prompt = self.PROMPT_TEMPLATES["reflection"].format(
            persona_name=self.persona.name,
            action_taken=json.dumps(action_taken),
            action_result=json.dumps(action_result),
        )

        reflection = {}
        if self.anthropic_client:
            try:
                message = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=800,
                    temperature=0.5,
                    system="You are a helpful AI that helps synthetic agents reflect on their actions.",
                    messages=[{"role": "user", "content": reflection_prompt}],
                )
                response_text = message.content[0].text if message.content else ""
                reflection = self._parse_json_response(response_text) or {}
            except Exception as e:
                logger.warning(f"Anthropic reflection failed: {e}")

        # Fallback reflection
        if not reflection:
            success = 200 <= action_result.get("status_code", 0) < 300
            reflection = {
                "reflection": f"The action {'succeeded' if success else 'failed'} with status {action_result.get('status_code')}.",
                "lessons_learned": ["API responded as expected"] if success else ["API returned an error"],
                "next_action_suggestion": "Continue with similar actions" if success else "Try a different approach or endpoint",
            }

        # Optionally update persona based on reflection
        if "adjust_persona" in reflection and isinstance(reflection["adjust_persona"], dict):
            for key, value in reflection["adjust_persona"].items():
                if hasattr(self.persona, key):
                    setattr(self.persona, key, value)
                    logger.info(f"Adjusted persona {key} to {value} based on reflection")

        return reflection

    async def interact(self) -> Dict[str, Any]:
        """
        Perform one interaction cycle: reason, act, reflect, and learn.
        Returns the result of the interaction.
        """
        start_time = time.time()

        # Step 1: Reason and decide on action
        action_decision = await self._reason_and_act()
        action_type = action_decision.get("action", "make_api_call")

        # Step 2: Execute the action using available tools
        action_result = {}
        if action_type in self.available_tools:
            try:
                if action_type == "make_api_call":
                    action_result = await self.available_tools[action_type](
                        method=action_decision.get("method", "GET"),
                        endpoint=action_decision.get("endpoint", "/"),
                        data=action_decision.get("data"),
                    )
                elif action_type == "wait":
                    action_result = await self.available_tools[action_type](
                        seconds=action_decision.get("seconds", 1.0)
                    )
                elif action_type == "reflect":
                    # This would typically be called after an action, not as the main action
                    action_result = await self.available_tools[action_type](
                        action_taken=action_decision,
                        action_result={},  # Would be filled in by caller
                    )
                else:
                    action_result = {"error": f"Unknown action type: {action_type}"}
            except Exception as e:
                logger.error(f"Error executing action {action_type}: {e}")
                action_result = {"error": str(e)}
        else:
            action_result = {"error": f"No tool available for action: {action_type}"}

        # Step 3: Reflect on the action and result
        reflection = await self._reflect_tool(action_decision, action_result)

        # Step 4: Store in memory
        interaction_record = {
            "timestamp": start_time,
            "agent_id": self.agent_id,
            "persona": self.persona.name,
            "action_decision": action_decision,
            "action_result": action_result,
            "reflection": reflection,
        }
        self._add_memory(interaction_record, MemoryType.SHORT_TERM, importance=0.7)

        # Also store in long-term memory if it was particularly important (e.g., learned something)
        if reflection.get("lessons_learned"):
            self._add_memory(
                {
                    "lessons": reflection["lessons_learned"],
                    "action": action_decision,
                },
                MemoryType.LONG_TERM,
                importance=0.9,
            )

        # Update action history
        self.action_history.append(interaction_record)

        # Prepare final result to return
        end_time = time.time()
        result = {
            "agent_id": self.agent_id,
            "persona": self.persona.name,
            "action_taken": action_decision,
            "action_result": action_result,
            "reflection": reflection,
            "interaction_duration_ms": (end_time - start_time) * 1000,
            "short_term_memory_count": len(self.short_term_memory),
            "long_term_memory_count": len(self.long_term_memory),
        }

        logger.debug(f"Agent {self.agent_id} completed interaction: {result['action_taken'].get('method')} {result['action_taken'].get('endpoint')}")
        return result

    # Optional: method to expose agent's current state for inspection
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the agent for debugging/monitoring."""
        return {
            "agent_id": self.agent_id,
            "persona": {
                "name": self.persona.name,
                "description": self.persona.description,
                "goals": self.persona.goals,
                "budget": self.persona.budget,
                "risk_tolerance": self.persona.risk_tolerance,
                "technical_expertise": self.persona.technical_expertise,
                "communication_style": self.persona.communication_style,
            },
            "memory": {
                "short_term_count": len(self.short_term_memory),
                "long_term_count": len(self.long_term_memory),
                "recent_short_term": [
                    {"timestamp": m.timestamp, "content": m.content}
                    for m in sorted(self.short_term_memory, key=lambda x: x.timestamp, reverse=True)[:3]
                ],
            },
            "action_history_count": len(self.action_history),
        }


# Factory function for creating agents from persona definitions
def create_synthetic_agent_from_config(
    agent_id: str,
    api_endpoint: str,
    api_key: Optional[str] = None,
    persona_config: Optional[Dict[str, Any]] = None,
    anthropic_api_key: Optional[str] = None,
) -> SyntheticAgent:
    """
    Create a SyntheticAgent from a configuration dictionary.

    Args:
        agent_id: Unique identifier
        api_endpoint: Target API base URL
        api_key: API key for target API
        persona_config: Dictionary containing persona definition
        anthropic_api_key: API key for Anthropic (for reasoning)

    Returns:
        Configured SyntheticAgent instance
    """
    if persona_config:
        persona = AgentPersona(
            name=persona_config.get("name", "Unknown"),
            description=persona_config.get("description", ""),
            goals=persona_config.get("goals", []),
            budget=float(persona_config.get("budget", 0.0)),
            risk_tolerance=float(persona_config.get("risk_tolerance", 0.5)),
            technical_expertise=float(persona_config.get("technical_expertise", 0.5)),
            communication_style=persona_config.get("communication_style", "neutral"),
        )
    else:
        persona = None

    return SyntheticAgent(
        agent_id=agent_id,
        api_endpoint=api_endpoint,
        api_key=api_key,
        persona=persona,
        anthropic_api_key=anthropic_api_key,
    )


def load_personas_from_json(file_path: str) -> List[Dict[str, Any]]:
    """
    Load persona definitions from a JSON file.

    Expected format:
    [
        {
            "name": "Budget-conscious Freelancer",
            "description": "A freelancer watching every dollar",
            "goals": ["Find cost-effective solutions", "Minimize API usage costs"],
            "budget": 50.0,
            "risk_tolerance": 0.3,
            "technical_expertise": 0.6,
            "communication_style": "casual"
        },
        ...
    ]
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load personas from {file_path}: {e}")
        return []


def create_agent_batch(
    base_agent_id: str,
    api_endpoint: str,
    api_key: Optional[str] = None,
    personas: Optional[List[Dict[str, Any]]] = None,
    anthropic_api_key: Optional[str] = None,
    count_per_persona: int = 1,
) -> List[SyntheticAgent]:
    """
    Create a batch of agents with varied personas.

    Args:
        base_agent_id: Base ID for agents (will be appended with index)
        api_endpoint: Target API base URL
        api_key: API key for target API
        personas: List of persona configurations; if None, uses default varied personas
        anthropic_api_key: API key for Anthropic reasoning
        count_per_persona: Number of agents to create for each persona

    Returns:
        List of created SyntheticAgent instances
    """
    if personas is None:
        # Generate some default varied personas
        personas = [
            {
                "name": "Budget-conscious Freelancer",
                "description": "A freelancer watching every dollar, prefers free tiers and low-cost options",
                "goals": ["Minimize costs", "Find cost-effective solutions", "Complete essential tasks"],
                "budget": 20.0,
                "risk_tolerance": 0.2,
                "technical_expertise": 0.5,
                "communication_style": "casual",
            },
            {
                "name": "Aggressive Startup Founder",
                "description": "A founder focused on rapid growth and market domination, willing to spend and take risks",
                "goals": ["Acquire users quickly", "Outperform competitors", "Scale rapidly"],
                "budget": 5000.0,
                "risk_tolerance": 0.8,
                "technical_expertise": 0.7,
                "communication_style": "direct",
            },
            {
                "name": "Cautious Enterprise Buyer",
                "description": "An enterprise procurement officer focused on security, compliance, and long-term value",
                "goals": ["Ensure security and compliance", "Minimize risk", "Negotiate best long-term terms"],
                "budget": 50000.0,
                "risk_tolerance": 0.1,
                "technical_expertise": 0.6,
                "communication_style": "formal",
            },
            {
                "name": "Curious Student",
                "description": "A student learning about APIs and web development, exploring with limited resources",
                "goals": ["Learn how APIs work", "Build a small project", "Stay within free limits"],
                "budget": 5.0,
                "risk_tolerance": 0.4,
                "technical_expertise": 0.3,
                "communication_style": "enthusiastic",
            },
            {
                "name": "Data-driven Analyst",
                "description": "An analyst who makes decisions based on metrics and performance data",
                "goals": ["Optimize performance", "Reduce latency", "Maximize throughput"],
                "budget": 1000.0,
                "risk_tolerance": 0.5,
                "technical_expertise": 0.8,
                "communication_style": "technical",
            },
        ]

    agents = []
    for i, persona in enumerate(personas):
        for j in range(count_per_persona):
            agent_id = f"{base_agent_id}_{persona['name'].lower().replace(' ', '_')}_{i}_{j}"
            agent = create_synthetic_agent_from_config(
                agent_id=agent_id,
                api_endpoint=api_endpoint,
                api_key=api_key,
                persona_config=persona,
                anthropic_api_key=anthropic_api_key,
            )
            agents.append(agent)

    logger.info(f"Created batch of {len(agents)} agents with {len(personas)} different personas")
    return agents