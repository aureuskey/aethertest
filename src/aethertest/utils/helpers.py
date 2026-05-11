"""
Utility functions for AetherTest.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary metrics from simulation results.
    """
    total_interactions = 0
    successful_interactions = 0
    failed_interactions = 0
    response_times = []

    for agent_result in results:
        for interaction in agent_result.get("interactions", []):
            total_interactions += 1
            status_code = interaction.get("status_code", 0)
            if 200 <= status_code < 300:
                successful_interactions += 1
                if "response_time_ms" in interaction:
                    response_times.append(interaction["response_time_ms"])
            else:
                failed_interactions += 1

    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

    return {
        "total_interactions": total_interactions,
        "successful_interactions": successful_interactions,
        "failed_interactions": failed_interactions,
        "success_rate": successful_interactions / total_interactions if total_interactions > 0 else 0,
        "average_response_time_ms": avg_response_time,
    }

def validate_api_endpoint(endpoint: str) -> bool:
    """
    Basic validation for API endpoint URL.
    """
    return endpoint.startswith(("http://", "https://"))

def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: List[str]) -> Dict[str, Any]:
    """
    Create a copy of a dictionary with sensitive values masked.
    """
    masked = data.copy()
    for key in sensitive_keys:
        if key in masked:
            masked[key] = "***MASKED***"
    return masked