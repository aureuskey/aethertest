"""
Pre-defined simulation scenarios for AetherTest.
"""
from typing import Dict, Any

# Scenario configurations
SCENARIOS = {
    "basic_interaction": {
        "description": "Basic API interaction patterns with mixed agent types",
        "agent_distribution": {
            "api_user": 0.4,
            "stresstest": 0.3,
            "error_testing": 0.2,
            "monitoring": 0.1,
        },
        "duration_minutes": 30,
    },
    "load_test": {
        "description": "High volume load testing to check API performance under stress",
        "agent_distribution": {
            "api_user": 0.2,
            "stresstest": 0.7,
            "error_testing": 0.05,
            "monitoring": 0.05,
        },
        "duration_minutes": 15,
    },
    "reliability_test": {
        "description": "Focus on error handling and API resilience",
        "agent_distribution": {
            "api_user": 0.3,
            "stresstest": 0.1,
            "error_testing": 0.5,
            "monitoring": 0.1,
        },
        "duration_minutes": 20,
    },
    "monitoring_focus": {
        "description": "Emphasis on health checks and performance monitoring",
        "agent_distribution": {
            "api_user": 0.2,
            "stresstest": 0.1,
            "error_testing": 0.1,
            "monitoring": 0.6,
        },
        "duration_minutes": 10,
    },
}

def get_scenario_config(scenario_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific scenario.
    """
    return SCENARIOS.get(scenario_name, SCENARIOS["basic_interaction"])

def list_scenarios() -> List[str]:
    """
    List all available scenario names.
    """
    return list(SCENARIOS.keys())