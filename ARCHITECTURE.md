# AetherTest Architecture & Workflow

## Overview
AetherTest enables founders to test their infrastructure APIs with realistic AI agents that mimic actual infrastructure teams—Cautious DevOps, Aggressive Founders, SREs, and QA Engineers—to uncover issues before real users encounter them.

## Simple One-Command Workflow
```bash
aethertest test --url https://your-api.com
```

## System Components

### 1. User Interface Layer
- **CLI Wrapper** (`aethertest.py`): Translates user-friendly flags to underlying script commands
- **Simple Syntax**: `aethertest test|quick [options]`

### 2. Orchestration Layer
- **Simulation Orchestrator**: Manages the entire test lifecycle
- **Agent Creation**: Generates 4 distinct infrastructure personas
- **Workflow Execution**: Coordinates concurrent agent operations

### 3. Agent Personalities (4 Types)
Each persona represents real infrastructure team behaviors:
- **Cautious DevOps Engineer**: Validates every step, avoids risks, focuses on reliability
- **Aggressive Startup Founder**: Moves fast, breaks things to learn, prioritizes speed
- **SRE / Platform Engineer**: Monitors system health, optimizes performance, ensures SLAs
- **QA Engineer**: Tests edge cases, error conditions, verifies boundary conditions

### 4. API Interaction Layer
- **Mock API Server**: Built-in FastAPI server for immediate testing (localhost:8000)
- **External API Support**: Test any real API using `--no-mock` flag
- **Authentication Handling**: Supports none, basic, bearer, and API key auth types
- **Endpoint Mapping**: Configurable via YAML for custom API structures
- **Rate Limit Awareness**: Automatic detection and back-off for 429 responses

### 5. Data & Storage Layer
- **Zero-Configuration SQLite**: Automatic database creation (no PostgreSQL needed)
- **Simulation Results**: Stores detailed interaction data, success/failure metrics
- **Session Management**: Persistent auth tokens across agent interactions
- **Extensible Schema**: Designed for future analytics and reporting features

### 6. Reporting & Observability Layer
- **Real-time Console Output**: Live logging during test execution
- **Simulation Summary**: Post-test report with key metrics
- **Per-Persona Breakdown**: Success rates by agent type
- **Failure Analysis**: Top error modes and retry patterns
- **Performance Metrics**: Execution time, interaction counts, retry statistics

## Data Flow
```
User Command
    ↓
CLI → Orchestrator
    ↓
Creates Agent Personas (4 types)
    ↓
Each Agent Executes Workflow:
    1. Authenticate (login endpoint)
    2. Test API endpoints (resources, batch, ingest, etc.)
    3. Handle errors & implement retries
    4. Validate responses & workflow completion
    ↓
API Interaction (Mock or Real)
    ↓
Results Storage (SQLite Database)
    ↓
Report Generation (Console Summary)
```

## Key Technical Features
- **LangGraph Integration**: Stateful, multi-actor agent workflows
- **Intelligent Error Handling**: AUTH_RECOVERABLE classification, exponential backoff
- **Production-Grade Observability**: Comprehensive metrics and logging
- **Extensible Architecture**: Easy to add new personas, workflows, and API endpoints
- **Built-in Mock API**: Realistic infrastructure API with auth, CRUD, rate limiting
- **Configuration System**: YAML-based with command-line overrides

## Getting Started (Under 5 Minutes)
1. `git clone https://github.com/aureuskey/aethertest.git`
2. `cd AetherTest`
3. `pip install -e .`  # One-time setup
4. `aethertest test --url https://your-api.com`
5. Review results in console output

## Output Example
```
============================================================
INFRASTRUCTURE SIMULATION SUMMARY
============================================================
Simulation ID: a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8
Timestamp: 2026-05-26T11:30:00.000000
Execution Time: 45.2 seconds

Configuration:
  Base URL: https://your-api.com
  Personas: Cautious DevOps Engineer, Aggressive Startup Founder, SRE, QA Engineer
  Agents per Persona: 3
  Interactions per Agent: 5
  Total Agents: 12

Aggregate Metrics:
  Total Interactions: 60
  Successful: 57 (95.0%)
  Failed: 3
  Total Retries: 2
  Avg Retries/Interaction: 0.03

Per-Persona Breakdown:
  Cautious DevOps Engineer: 98.0% success
  Aggressive Startup Founder: 89.0% success
  SRE / Platform Engineer: 100.0% success
  QA Engineer: 92.0% success

Top Failure Modes:
  HTTP 429 (Rate Limited): 2 occurrences
  HTTP 401 (Unauthorized): 1 occurrence
```