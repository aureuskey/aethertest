# AetherTest - AI Infrastructure Simulation Platform

AI Infrastructure Simulation Platform for testing and validating AI-driven systems under various load and stress conditions.

## Overview

AetherTest is a platform designed to simulate complex interactions between AI agents and infrastructure systems. It helps developers and DevOps teams test how their APIs, microservices, and AI-powered applications behave under different conditions, including:

- High load scenarios
- Stress testing with error-prone agents
- Mixed agent types simulating real-world usage
- Customizable scenarios for specific use cases

The platform uses LangGraph for agent orchestration, providing sophisticated agent behavior with thinking, acting, and reflection cycles.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   If there's no requirements.txt, install these packages:
   ```bash
   pip install langgraph pydantic pydantic-settings fastapi uvicorn sqlalchemy
   ```

3. Set up environment variables:
   Create a `.env` file in the project root with:
   ```
   # API settings
   API_V1_STR=/api/v1
   PROJECT_NAME=AetherTest

   # Database settings (SQLite for simplicity)
   USE_SQLITE=true

   # Anthropic (Claude) API settings (optional, for Claude-powered agents)
   # ANTHROPIC_API_KEY=your_anthropic_api_key_here

   # Simulation settings
   DEFAULT_AGENT_COUNT=100
   MAX_AGENT_COUNT=2000
   DEFAULT_SIMULATION_DURATION_MINUTES=30
   ```

### Run Your First Simulation

```bash
python src/run_full_simulation.py --api-endpoint http://localhost:8000 --scenario basic_interaction
```

#### Common Command-Line Options

- `--api-endpoint`: Target API URL (required)
- `--scenario`: Scenario to run (default: `basic_interaction`)
  - Available: `basic_interaction`, `load_test`, `stress_test`, `mixed_agents`, `freelance_marketplace`
- `--agent-count`: Number of agents (default: from scenario)
- `--agent-type`: Agent type (default: from scenario)
- `--duration`: Duration in minutes (default: from scenario)
- `--verbose`: Enable detailed logging

#### Example Commands

Run a load test with 30 agents for 5 minutes:
```bash
python src/run_full_simulation.py --api-endpoint http://localhost:8000 --scenario load_test --agent-count 30 --duration 5
```

Run a freelance marketplace scenario:
```bash
python src/run_full_simulation.py --api-endpoint http://localhost:8000 --scenario freelance_marketplace
```

Run a custom test with specific parameters:
```bash
python src/run_full_simulation.py --api-endpoint http://localhost:8000 --api-key your-key --agent-count 50 --agent-type synthetic --duration 10
```

## How It Works

### 1. Agent Creation
Based on your scenario, AetherTest creates AI agents with specific roles:
- **Synthetic Agents**: General-purpose agents for various tasks
- **API User Agents**: Simulate real users making API requests
- **Stress Test Agents**: Designed to provoke errors and edge cases
- **Monitoring Agents**: Observe system behavior and report metrics

### 2. Agent Behavior (LangGraph-Powered)
Each agent follows a Think-Act-Reflect cycle:
- **Think**: Analyzes context and decides on an action
- **Act**: Executes the action against your API
- **Reflect**: Learns from outcomes to adjust future behavior

This creates realistic, adaptive agent behavior that mimics real users and systems.

### 3. Simulation Execution
Agents interact with your API endpoint concurrently, simulating realistic load patterns. You can:
- Monitor real-time metrics and logs
- Track success/failure rates
- Observe system performance under stress
- Identify bottlenecks and failure points

### 4. Results Analysis
After the simulation, you receive detailed results including:
- Agent actions and outcomes
- Performance metrics
- Error rates and types
- Timing information
- Reflection insights from agents

Use this data to:
- Validate system resilience
- Optimize performance
- Improve error handling
- Prepare for production deployment

## Project Structure

```
├── src/
│   ├── aethertest/                 # Core simulation engine
│   │   ├── agents/                 # Agent definitions and behaviors
│   │   │   ├── base_agent.py       # Base agent with LangGraph integration
│   │   │   ├── agent_types.py      # Agent type definitions
│   │   │   └── synthetic_agent.py  # Synthetic agent implementation
│   │   ├── simulation/             # Simulation orchestration and scenarios
│   │   │   ├── orchestrator.py     # Main simulation orchestrator
│   │   │   └── scenarios.py        # Predefined simulation scenarios
│   │   ├── core/                   # Core configuration and utilities
│   │   │   ├── config.py           # Configuration management
│   │   │   ├── database.py         # Database setup
│   │   │   └── models.py           # Data models
│   │   ├── api/                    # API interface (FastAPI)
│   │   │   └── v1/
│   │   │       ├── routes.py       # API routes
│   │   │       └── analytics.py    # Analytics endpoints
│   │   ├── main.py                 # API entry point
│   │   └── __init__.py
│   ├── run_full_simulation.py      # Standalone simulation runner
│   ├── main.py                     # Nova AI Assistant (separate project)
│   ├── brain.py                    # Nova's AI brain
│   ├── stt.py                      # Speech-to-text for Nova
│   ├── tts.py                      # Text-to-speech for Nova
│   └── tools/                      # Utility functions for Nova
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (create this)
└── .gitignore                      # Git ignore rules
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'langgraph'**
   - Solution: `pip install langgraph`

2. **Connection errors to API endpoint**
   - Verify the API URL is correct and accessible
   - Check network connectivity and firewall settings
   - Ensure the API is running and accepting connections

3. **Authentication errors (401/403)**
   - Verify your API key is correct and has necessary permissions
   - Check that the API key is passed correctly in request headers

4. **Performance issues or slow simulations**
   - Reduce agent count or duration
   - Check your API's performance and consider scaling
   - Monitor system resources during simulation

5. **Database connection errors**
   - If using PostgreSQL, verify connection details in `.env`
   - Ensure the database is running and accessible
   - For simpler setup, use SQLite (set `USE_SQLITE=true`)

### Getting Help

If you encounter issues not covered here:
1. Check the logs for detailed error messages
2. Verify your environment variables and configuration
3. Ensure all dependencies are installed correctly
4. For additional support, please open an issue in the repository

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- LangGraph team for the excellent agent orchestration library
- The open-source AI community for inspiration and tools