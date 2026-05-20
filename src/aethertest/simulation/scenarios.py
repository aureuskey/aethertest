"""
Simulation scenarios for AetherTest.
"""
from typing import List, Dict, Any
from aethertest.agents.agent_types import AgentType


def get_scenario_config(scenario_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific scenario.

    Args:
        scenario_name: Name of the scenario

    Returns:
        Dictionary containing scenario configuration
    """
    scenarios = {
        "basic_interaction": {
            "description": "Basic agent interaction with the API",
            "agent_type": AgentType.SYNTHETIC.value,
            "agent_count": 10,
            "duration_minutes": 5
        },
        "load_test": {
            "description": "High volume agent interactions to test system limits",
            "agent_type": AgentType.API_USER.value,
            "agent_count": 100,
            "duration_minutes": 10
        },
        "stress_test": {
            "description": "Stress test with error-prone agents",
            "agent_type": AgentType.ERROR_TESTING.value,
            "agent_count": 50,
            "duration_minutes": 15
        },
        "mixed_agents": {
            "description": "Mixed agent types simulating real-world usage",
            "agent_type": "mixed",
            "agent_count": 50,
            "duration_minutes": 10,
            "agent_distribution": {
                AgentType.SYNTHETIC.value: 0.4,
                AgentType.API_USER.value: 0.3,
                AgentType.STRESS_TEST.value: 0.2,
                AgentType.MONITORING.value: 0.1
            }
        },
        "freelance_marketplace": {
            "description": "Freelance marketplace scenario with clients and freelancers",
            "agent_type": "mixed",
            "agent_count": 20,
            "duration_minutes": 20,
            "num_clients": 5,
            "num_freelancers": 15,
            "client_personas": [
                {
                    "name": "Startup Client",
                    "description": "A startup founder needing to build an MVP quickly and affordably",
                    "goals": ["Build MVP", "Keep costs low"],
                    "budget": 5000.0
                },
                {
                    "name": "Enterprise Client",
                    "description": "An enterprise client looking for a reliable solution",
                    "goals": ["Implement solution", "Ensure reliability"],
                    "budget": 50000.0
                }
            ],
            "freelancer_personas": [
                {
                    "name": "Junior Freelancer",
                    "description": "A junior freelancer looking to gain experience",
                    "goals": ["Gain experience", "Earn money"],
                    "budget": 0.0
                },
                {
                    "name": "Senior Freelancer",
                    "description": "A senior freelancer looking for high-paying projects",
                    "goals": ["Earn high income", "Work on challenging projects"],
                    "budget": 0.0
                }
            ]
        }
    }

    if scenario_name not in scenarios:
        # Return a default scenario
        return {
            "description": "Default scenario",
            "agent_type": AgentType.SYNTHETIC.value,
            "agent_count": 10,
            "duration_minutes": 5
        }

    return scenarios[scenario_name]


def get_available_scenarios() -> List[str]:
    """
    Get a list of available scenario names.

    Returns:
        List of scenario names
    """
    return list(get_scenario_config.__defaults__[0].keys()) if get_scenario_config.__defaults__ else ["basic_interaction", "load_test", "stress_test", "mixed_agents", "freelance_marketplace"]