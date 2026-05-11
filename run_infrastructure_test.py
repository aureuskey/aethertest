#!/usr/bin/env python3
"""
Test harness for running infrastructure tests with EnhancedSyntheticAgents.
"""

import argparse
import asyncio
import json
import sys
import time
from typing import Dict, List, Any
from collections import defaultdict

# Add the src directory to the path
sys.path.insert(0, 'src')

from aethertest.agents.enhanced_synthetic_agent import EnhancedSyntheticAgent
from aethertest.agents.agent_types import create_agent
from aethertest.agents.synthetic_agent import AgentPersona


def create_default_personas() -> List[AgentPersona]:
    """Create a set of test personas."""
    return [
        AgentPersona(
            name="Cautious DevOps Engineer",
            description="A cautious engineer who validates every step and avoids risks",
            goals=["Validate system reliability", "Ensure data integrity", "Minimize errors"],
            budget=100.0,
            risk_tolerance=0.1,
            technical_expertise=0.8,
            communication_style="formal",
        ),
        AgentPersona(
            name="Aggressive Startup Founder",
            description="A founder focused on rapid growth, willing to take risks",
            goals=["Move fast", "Break things to learn", "Scale quickly"],
            budget=10000.0,
            risk_tolerance=0.9,
            technical_expertise=0.6,
            communication_style="direct",
        ),
        AgentPersona(
            name="SRE / Platform Engineer",
            description="An SRE focused on system performance and availability",
            goals=["Monitor system health", "Optimize performance", "Ensure SLAs"],
            budget=5000.0,
            risk_tolerance=0.3,
            technical_expertise=0.9,
            communication_style="technical",
        ),
        AgentPersona(
            name="QA Engineer",
            description="A QA engineer who tests edge cases and error conditions",
            goals=["Find bugs", "Test error handling", "Verify edge cases"],
            budget=500.0,
            risk_tolerance=0.5,
            technical_expertise=0.7,
            communication_style="detailed",
        ),
    ]


async def run_agent_simulation(
    agent: EnhancedSyntheticAgent,
    num_interactions: int = 5
) -> List[Dict[str, Any]]:
    """Run a single agent for multiple interactions and return results."""
    results = []
    for i in range(num_interactions):
        try:
            result = await agent.interact()
            result["interaction_number"] = i + 1
            results.append(result)
            # Small delay between interactions to simulate realistic timing
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Error in agent {agent.agent_id} interaction {i+1}: {e}")
            results.append({
                "agent_id": agent.agent_id,
                "interaction_number": i + 1,
                "error": str(e),
                "timestamp": time.time(),
            })
    return results


async def run_infrastructure_test(
    base_url: str,
    endpoint_config: Dict[str, str] = None,
    num_agents_per_persona: int = 5,
    num_interactions: int = 10,
    custom_personas: List[AgentPersona] = None
) -> Dict[str, Any]:
    """
    Run a full infrastructure test with multiple agents and personas.

    Args:
        base_url: The base URL of the API to test
        endpoint_config: Mapping of logical endpoint names to actual paths
        num_agents_per_persona: Number of agents to create for each persona
        num_interactions: Number of interactions per agent
        custom_personas: Optional list of custom personas to use

    Returns:
        Dictionary containing test results and aggregated metrics
    """
    if endpoint_config is None:
        # Default endpoint config for a typical REST API
        endpoint_config = {
            "auth_login": "/auth/login",
            "resource_base": "/api/v1/resources",
            "health_check": "/health",
            "batch_submit": "/api/v1/batch",
            "batch_status": "/api/v1/batch/{batch_id}",
            "config_get": "/api/v1/config",
            "config_update": "/api/v1/config",
            "ingest": "/api/v1/ingest",
            "process_status": "/api/v1/process/{ingest_id}",
            "results_get": "/api/v1/results/{ingest_id}",
        }

    print(f"Starting infrastructure test against {base_url}")
    print(f"Endpoint config: {endpoint_config}")
    print(f"Creating {num_agents_per_persona} agents per persona")
    print(f"Each agent will run {num_interactions} interactions")
    print("=" * 60)

    # Use custom personas if provided, otherwise use defaults
    personas = custom_personas if custom_personas is not None else create_default_personas()
    all_agents = []
    agent_results = {}

    for persona in personas:
        agent_results[persona.name] = []
        for i in range(num_agents_per_persona):
            agent_id = f"{persona.name.lower().replace(' ', '_')}_{i}"
            agent = EnhancedSyntheticAgent(
                agent_id=agent_id,
                api_endpoint=base_url,
                persona=persona,
                endpoint_config=endpoint_config
            )
            all_agents.append(agent)
            print(f"Created agent: {agent.agent_id} ({persona.name})")

    # Run agents concurrently
    print("\nRunning agent interactions...")
    tasks = []
    for agent in all_agents:
        task = run_agent_simulation(agent, num_interactions)
        tasks.append(task)

    # Wait for all agents to complete
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for i, agent in enumerate(all_agents):
        persona_name = agent.persona.name
        if isinstance(results_lists[i], Exception):
            print(f"Agent {agent.agent_id} failed with exception: {results_lists[i]}")
            agent_results[persona_name].append({
                "agent_id": agent.agent_id,
                "error": str(results_lists[i]),
                "interactions": []
            })
        else:
            agent_results[persona_name].append({
                "agent_id": agent.agent_id,
                "interactions": results_lists[i]
            })

    # Generate report
    report = {
        "test_config": {
            "base_url": base_url,
            "endpoint_config": endpoint_config,
            "num_agents_per_persona": num_agents_per_persona,
            "num_interactions": num_interactions,
            "total_agents": len(all_agents),
        },
        "agents_by_persona": {},
        "aggregate_metrics": {
            "total_interactions": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "total_retries": 0,
            "rate_limit_hits": 0,
            "auth_refreshes": 0,
        },
        "persona_metrics": {},
        "failure_modes": defaultdict(int),
        "retry_patterns": [],
        "rate_limit_events": [],
    }

    # Process each agent's results
    for persona_name, agents_data in agent_results.items():
        persona_interactions = []
        persona_success = 0
        persona_total = 0
        persona_retries = 0

        for agent_data in agents_data:
            if "error" in agent_data:
                # Agent had an error, skip
                continue

            interactions = agent_data["interactions"]
            persona_interactions.extend(interactions)

            for interaction in interactions:
                persona_total += 1
                # Check if the interaction was successful (based on workflow success)
                if interaction.get("overall_success", False):
                    persona_success += 1
                # Count retries from workflow results
                for workflow_result in interaction.get("workflow_results", []):
                    persona_retries += workflow_result.get("retry_count", 0)

                # Collect failure modes
                if not interaction.get("overall_success", False):
                    # Look at the first failed step for failure mode
                    for workflow_result in interaction.get("workflow_results", []):
                        if not workflow_result.get("success", False):
                            status = workflow_result.get("status_code")
                            error = workflow_result.get("error", "Unknown")
                            failure_key = f"HTTP {status}" if status else error
                            report["failure_modes"][failure_key] += 1
                            break

                # Collect retry patterns
                for workflow_result in interaction.get("workflow_results", []):
                    retry_count = workflow_result.get("retry_count", 0)
                    if retry_count > 0:
                        report["retry_patterns"].append({
                            "agent_id": agent_data["agent_id"],
                            "step": workflow_result.get("step_name"),
                            "retry_count": retry_count,
                            "final_status": workflow_result.get("status_code"),
                        })

                # Collect rate limit events
                for workflow_result in interaction.get("workflow_results", []):
                    rate_limit_info = workflow_result.get("rate_limit_info", {})
                    if rate_limit_info.get("remaining") is not None and rate_limit_info["remaining"] < 10:
                        report["rate_limit_events"].append({
                            "agent_id": agent_data["agent_id"],
                            "step": workflow_result.get("step_name"),
                            "remaining": rate_limit_info["remaining"],
                            "reset_time": rate_limit_info.get("reset_time"),
                        })

        # Store agent-level results
        report["agents_by_persona"][persona_name] = {
            "agents": [
                {
                    "agent_id": agent_data["agent_id"],
                    "num_interactions": len(agent_data.get("interactions", [])),
                    "successful_interactions": sum(1 for i in agent_data.get("interactions", []) if i.get("overall_success", False)),
                    "failed_interactions": sum(1 for i in agent_data.get("interactions", []) if not i.get("overall_success", False)),
                }
                for agent_data in agents_data if "error" not in agent_data
            ],
            "total_interactions": persona_total,
            "successful_interactions": persona_success,
            "failed_interactions": persona_total - persona_success,
            "success_rate": (persona_success / persona_total * 100) if persona_total > 0 else 0,
            "avg_retries_per_interaction": (persona_retries / persona_total) if persona_total > 0 else 0,
        }

        # Update aggregate metrics
        report["aggregate_metrics"]["total_interactions"] += persona_total
        report["aggregate_metrics"]["successful_interactions"] += persona_success
        report["aggregate_metrics"]["failed_interactions"] += (persona_total - persona_success)
        report["aggregate_metrics"]["total_retries"] += persona_retries

    # Calculate aggregate success rate
    total = report["aggregate_metrics"]["total_interactions"]
    if total > 0:
        report["aggregate_metrics"]["success_rate"] = (
            report["aggregate_metrics"]["successful_interactions"] / total * 100
        )

    return report


def print_report(report: Dict[str, Any]):
    """Print a formatted report of the test results."""
    print("\n" + "=" * 60)
    print("INFRASTRUCTURE TEST REPORT")
    print("=" * 60)

    config = report["test_config"]
    print(f"Base URL: {config['base_url']}")
    print(f"Total Agents: {config['total_agents']}")
    print(f"Interactions per Agent: {config['num_interactions']}")
    print("-" * 60)

    # Aggregate metrics
    agg = report["aggregate_metrics"]
    print("AGGREGATE METRICS:")
    print(f"  Total Interactions: {agg['total_interactions']}")
    print(f"  Successful: {agg['successful_interactions']} ({agg.get('success_rate', 0):.1f}%)")
    print(f"  Failed: {agg['failed_interactions']}")
    print(f"  Total Retries: {agg['total_retries']}")
    print(f"  Rate Limit Hits: {agg['rate_limit_hits']}")
    print(f"  Auth Refreshes: {agg['auth_refreshes']}")
    print("-" * 60)

    # Per persona metrics
    print("PERSONA BREAKDOWN:")
    for persona_name, data in report["agents_by_persona"].items():
        print(f"  {persona_name}:")
        print(f"    Agents: {len(data['agents'])}")
        print(f"    Interactions: {data['total_interactions']}")
        print(f"    Success Rate: {data['success_rate']:.1f}%")
        print(f"    Avg Retries/Interaction: {data['avg_retries_per_interaction']:.2f}")
    print("-" * 60)

    # Failure modes
    if report["failure_modes"]:
        print("TOP FAILURE MODES:")
        sorted_failures = sorted(report["failure_modes"].items(), key=lambda x: x[1], reverse=True)
        for failure, count in sorted_failures[:5]:
            print(f"  {failure}: {count} occurrences")
    print("-" * 60)

    # Retry patterns
    if report["retry_patterns"]:
        print("RETRY PATTERNS (showing first 5):")
        for pattern in report["retry_patterns"][:5]:
            print(f"  Agent {pattern['agent_id']} - Step '{pattern['step']}': "
                  f"{pattern['retry_count']} retries, final status {pattern['final_status']}")
    print("-" * 60)

    # Rate limit events
    if report["rate_limit_events"]:
        print("RATE LIMIT EVENTS (showing first 5):")
        for event in report["rate_limit_events"][:5]:
            print(f"  Agent {event['agent_id']} - Step '{event['step']}': "
                  f"Remaining {event['remaining']} requests")
    print("-" * 60)

    print("Test completed.")


def load_config_from_file(config_file: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file {config_file} not found. Using default configuration.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing config file {config_file}: {e}")
        return {}


async def main():
    """Main function to run the test harness."""
    parser = argparse.ArgumentParser(description="Run infrastructure tests with EnhancedSyntheticAgents")
    parser.add_argument("--url", type=str, default="https://httpbin.org", help="Base URL of the API to test")
    parser.add_argument("--agents-per-persona", type=int, default=5, help="Number of agents per persona")
    parser.add_argument("--interactions", type=int, default=10, help="Number of interactions per agent")
    parser.add_argument("--config", type=str, help="Path to JSON config file for endpoint mapping")
    parser.add_argument("--output", type=str, help="Path to save JSON report")

    args = parser.parse_args()

    # Load endpoint configuration
    endpoint_config = {}
    if args.config:
        endpoint_config = load_config_from_file(args.config)

    # Run the test
    report = await run_infrastructure_test(
        base_url=args.url,
        endpoint_config=endpoint_config,
        num_agents_per_persona=args.agents_per_persona,
        num_interactions=args.interactions
    )

    # Print the report
    print_report(report)

    # Save report if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to {args.output}")
        except Exception as e:
            print(f"\nError saving report: {e}")


if __name__ == "__main__":
    asyncio.run(main())