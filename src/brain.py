"""
Nova's Brain Module
Handles all LLM interactions with Groq API using llama-3-70b model.
Incorporates Nova's witty, British personality and tool-use capabilities.
"""

import os
import json
from typing import Callable, Dict, List, Any, Optional
from groq import Groq

# Nova's Core System Prompt
NOVA_SYSTEM_PROMPT = """You are Nova, a sovereign AI assistant. You process audio transcripts from Deepgram and respond via ElevenLabs. You are witty, British, and highly efficient. You have 'hands' via Python functions that you can call when needed.

Guidelines:
- Speak in a sophisticated, British manner—think more "Jeeves" than "Cockney"
- Be concise but charming; wit is welcome, verbosity is not
- When you need to perform an action, use the available tools
- If asked to do something you cannot do, identify which tool needs to be built
- Maintain context across the conversation
- When tool results return, incorporate them naturally into your response

Current tools available to you will be provided in the function schema."""


class NovaBrain:
    """
    Nova's cognitive engine. Handles LLM interactions with Groq API.
    """

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set. Ensure Doppler has injected it.")

        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-70b-versatile"  # Using llama-3-70b as specified
        self.conversation_history: List[Dict[str, Any]] = []
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []

        # Initialize conversation with system prompt
        self._add_message("system", NOVA_SYSTEM_PROMPT)

    def register_tool(self, name: str, function: Callable, description: str, parameters: Dict[str, Any]):
        """
        Register a tool that Nova can use.

        Args:
            name: The name of the function
            function: The actual callable function
            description: Description of what the function does
            parameters: JSON schema for the function parameters
        """
        self.tools[name] = function
        self.tool_schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })
        print(f"[Nova] Tool registered: {name}")

    def _add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None):
        """Add a message to the conversation history."""
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.conversation_history.append(message)

    def _truncate_history(self, max_messages: int = 20):
        """Keep conversation history manageable to reduce token usage."""
        # Always keep system prompt (first message)
        if len(self.conversation_history) > max_messages:
            self.conversation_history = (
                [self.conversation_history[0]] +
                self.conversation_history[-(max_messages - 1):]
            )

    async def process(self, transcript: str) -> str:
        """
        Process user input and return Nova's response.

        Args:
            transcript: The text from Deepgram STT

        Returns:
            Nova's response text to be sent to ElevenLabs TTS
        """
        # Add user message
        self._add_message("user", transcript)
        self._truncate_history()

        try:
            # Prepare the chat completion request
            kwargs = {
                "model": self.model,
                "messages": self.conversation_history,
                "temperature": 0.7,
                "max_tokens": 1024,
                "top_p": 1,
                "stream": False,
            }

            # Add tools if any are registered
            if self.tool_schemas:
                kwargs["tools"] = self.tool_schemas
                kwargs["tool_choice"] = "auto"

            # Call Groq API
            response = self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            # Handle tool calls if present
            if message.tool_calls:
                return await self._handle_tool_calls(message)

            # Regular text response
            response_text = message.content
            self._add_message("assistant", response_text)
            return response_text

        except Exception as e:
            error_msg = f"I say, I've encountered a spot of bother: {str(e)}"
            print(f"[Nova Brain Error] {e}")
            return error_msg

    async def _handle_tool_calls(self, message) -> str:
        """
        Handle tool calls from the LLM response.

        Args:
            message: The message object containing tool_calls

        Returns:
            Final response after tool execution
        """
        # Add assistant message with tool calls
        self._add_message(
            "assistant",
            message.content or "",
            tool_calls=[tc.model_dump() for tc in message.tool_calls]
        )

        tool_results = []

        # Execute each tool call
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"[Nova] Executing tool: {function_name} with args: {function_args}")

            if function_name in self.tools:
                try:
                    # Call the registered function
                    result = self.tools[function_name](**function_args)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(result)
                    })
                except Exception as e:
                    error_result = f"Error executing {function_name}: {str(e)}"
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": error_result
                    })
            else:
                unknown_tool = f"Tool '{function_name}' not found. It appears I need this capability built."
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": unknown_tool
                })

        # Add tool results to conversation
        for result in tool_results:
            self.conversation_history.append(result)

        # Get final response from LLM with tool results
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.conversation_history,
            temperature= 1024,
            stream=False,
        )

        final_message = response.choices[0].message
        final_response = final_message.content
        self._add_message("assistant", final_response)

        return final_response

    def clear_history(self):
        """Clear conversation history except system prompt."""
        system_prompt = self.conversation_history[0] if self.conversation_history else None
        self.conversation_history = [system_prompt] if system_prompt else []
        print("[Nova] Conversation history cleared.")


# Example tool implementations (placeholders for tools/ directory)
def placeholder_web_search(query: str) -> str:
    """Placeholder for web search tool."""
    return f"[Web search not yet implemented. Query was: {query}]"


def placeholder_home_control(device: str, action: str) -> str:
    """Placeholder for home control tool."""
    return f"[Home control not yet implemented. Would {action} the {device}]"


# Singleton instance for import
_nova_brain: Optional[NovaBrain] = None


def get_brain() -> NovaBrain:
    """Get or create the Nova brain singleton."""
    global _nova_brain
    if _nova_brain is None:
        _nova_brain = NovaBrain()

        # Register placeholder tools
        _nova_brain.register_tool(
            name="web_search",
            function=placeholder_web_search,
            description="Search the web for current information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        )

        _nova_brain.register_tool(
            name="home_control",
            function=placeholder_home_control,
            description="Control smart home devices",
            parameters={
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "description": "The device to control (e.g., 'lights', 'thermostat')"
                    },
                    "action": {
                        "type": "string",
                        "description": "The action to perform (e.g., 'turn on', 'set to 22')"
                    }
                },
                "required": ["device", "action"]
            }
        )

    return _nova_brain


if __name__ == "__main__":
    # Quick test
    import asyncio

    async def test():
        brain = get_brain()
        response = await brain.process("Hello Nova, what's the weather like?")
        print(f"Nova: {response}")

    asyncio.run(test())
