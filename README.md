# AetherTest

**Test your infrastructure in a living digital world before the real world tests you.**

### What is AetherTest?
AetherTest is a realistic AI agent simulation platform that lets infrastructure founders stress-test their APIs, memory systems, orchestration tools, and protocols with thousands of lifelike AI agents — before shipping to real users.

It simulates DevOps engineers, SREs, aggressive startup founders, QA teams, and more — each with their own goals, risk tolerance, workflows, and error-handling behaviors.

## Key Features
- **Real Infrastructure Personalities**: Four distinct user personas with real‑world behaviors, risk tolerances, and goals (Cautious DevOps, Aggressive Founder, SRE, QA Engineer)
- **Stateful Workflow Testing**: Multi‑step API workflows that mimic real usage (authenticate → operate → validate → cleanup) with proper session management
- **Intelligent Error Handling**: Smart retry mechanisms with exponential backoff, jitter, and error classification (including AUTH_RECOVERABLE for 401s)
- **Rate Limit Awareness**: Agents detect 429 responses and implement appropriate back‑off strategies automatically
- **Production‑Grade Observability**: Comprehensive metrics on success rates, failure modes, retry patterns, and performance breakdowns
- **Auth Token Persistence**: Verified session management that maintains authentication across interactions
- **Mock Infrastructure API**: Ready‑to‑use FastAPI server representing common infrastructure patterns for immediate testing
- **Extensible & Customizable**: Easy to add new personas, workflows, and API endpoints to match your specific infrastructure

## 🚀 Quick Start (Beginner-Friendly)

Follow these steps to run your first AetherTest simulation in under 10 minutes:

### Prerequisites
Before you begin, make sure you have:
- **Python 3.8 or higher** installed ([download Python](https://www.python.org/downloads/))
- **Git** installed ([download Git](https://git-scm.com/downloads))
- **Internet connection** to install dependencies

### Step-by-Step Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AetherTest.git
   cd AetherTest
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   This will install all required packages including FastAPI, Uvicorn, LangGraph, and others.

3. **Run the demonstration**
   ```bash
   python run_full_simulation.py
   ```
   This command does two things:
   - Starts a mock infrastructure API server on `http://127.0.0.1:8000`
   - Runs a simulation with 20 AI agents (5 of each persona type)

### What to Expect During the Demo
While the simulation runs, you'll see:
- 🚀 **Starting up**: The mock API server starts (takes ~5 seconds)
- 👥 **Agent creation**: 20 AI agents are created (5 per persona: Cautious DevOps, Aggressive Founder, SRE, QA Engineer)
- 🔄 **Simulation execution**: Each agent performs 8 API interactions (160 total API calls)
- 📊 **Results display**: A detailed report showing success rates by persona type
- 💾 **Data storage**: All results are saved to a local SQLite database for later analysis

### Verification
To confirm everything worked correctly:
1. Look for the success report printed in your terminal
2. Visit the interactive API docs at: `http://127.0.0.1:8000/docs`
3. Check that a file named `aethertest.db` was created in the project directory

## How It Works for Founders

As a founder, you don't need to become a testing expert—AetherTest does the heavy lifting:

1. **Point to your API**: Simply provide your API endpoint URL and basic endpoint mapping (where to find auth, resources, health checks)
2. **Select your user types**: Choose which infrastructure user types to simulate (or use our battle-tested defaults)
3. **Set your scale**: Decide how many virtual users to simulate and how deeply each should test your API
4. **Let AetherTest run**: Our orchestrator launches agents that behave like real infrastructure teams—they authenticate, workflow through your API, handle errors intelligently, and report everything
5. **Get actionable insights**: Receive a clear report showing exactly where your API struggles, which user types encounter issues, and what needs fixing before your real users do

No more guessing if your authentication flow works under load. No more hoping your rate limiting behaves correctly. AetherTest shows you the truth before your users find the problems.

## Project Structure
```
AetherTest/
├── mock_api.py               # Production-like mock infrastructure API for immediate testing
├── run_full_simulation.py    # One-command demo: launches API + runs complete simulation
├── run_infrastructure_test.py# Original test harness (evolved to CLI-driven interface)
├── src/
│   └── aethertest/
│       ├── agents/           # AI agent implementations (EnhancedSyntheticAgent with auth persistence)
│       ├── api/              # API versioning and endpoints (v1/)
│       ├── core/             # Database, configuration, and data models
│       ├── simulation/       # Workflow orchestrator and scenario definitions
│       ├── utils/            # Helper functions and shared utilities
│       └── main.py           # Application entry point
└── tests/                    # Unit and integration tests ensuring reliability
```

## 🛠️ Troubleshooting Tips

### Common Issues and Solutions

**Problem**: `Command not found: git`
**Solution**: Install Git from https://git-scm.com/downloads and restart your terminal

**Problem**: `Command not found: pip` or `pip: command not found`
**Solution**: Make sure Python is installed and added to your PATH. Try using `python -m pip` instead of `pip`

**Problem**: `Error: externally-managed-environment` (on Linux systems)
**Solution**: Use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Problem**: `ModuleNotFoundError: No module named 'langgraph'`
**Solution**: Reinstall dependencies: `pip install -r requirements.txt`

**Problem**: Port 8000 already in use
**Solution**: Either stop the program using port 8000 or wait a moment and try again. The demo will automatically retry.

**Problem**: Seeing `Connection refused` when trying to access http://127.0.0.1:8000/docs
**Solution**: Wait a few seconds for the API server to fully start, then refresh the page

**Problem**: No output or the program seems to hang
**Solution**: Give it up to 30 seconds to start. If still no output, try pressing Ctrl+C and running again

### Getting Help
If you encounter issues not covered here:
1. Check the [GitHub Issues](https://github.com/yourusername/AetherTest/issues) for similar problems
2. Create a new issue with details about your operating system, Python version, and the exact error message
3. For immediate help, consider reaching out through the project's discussion forums

## Current Status & Roadmap
**What's Working Now:**
- ✅ EnhancedSyntheticAgent with verified auth token persistence (fixes validated)
- ✅ 4 realistic infrastructure user personas with distinct behaviors
- ✅ Stateful workflow testing with proper session management
- ✅ Intelligent error handling and retry mechanisms
- ✅ Rate limit awareness (429 response handling)
- ✅ Mock infrastructure API representing common patterns
- ✅ Database storage for simulation results and analytics
- ✅ Observability and comprehensive reporting
- ✅ Extensible architecture for custom personas and workflows

**Next 4-6 Weeks Priorities:**
- 🎯 Add 3+ new infrastructure user personas (Security Engineer, Data Engineer, Platform Engineer)
- 🎯 Support custom workflow definitions via simple YAML/JSON configuration
- 🎯 Enhanced analytics dashboard with real-time visualization and filtering
- 🎯 Distributed testing mode for 1000+ agent simulations (horizontal scaling)
- 🎯 Pre-built scenarios for Kubernetes, databases, message queues, and CI/CD patterns
- 🎯 Performance benchmarking mode with SLA tracking and regression detection
- 🎯 CI/CD pipeline integrations (GitHub Actions, GitLab CI, Jenkins)

## Contributing / Getting Early Access
We're building AetherTest with and for infrastructure API founders who believe testing should be as sophisticated as the systems they're building.

**If you're building infrastructure tools, APIs, or platforms:**
1. Star this repository to follow our progress
2. Join our early access program by opening an Issue with "Early Access Request"
3. Share your biggest API testing challenges—we're designing features around real founder needs
4. Consider contributing: we welcome improvements to personas, workflows, and analytics

## Let's Make Sure Your Infrastructure Works
Let's make sure your infrastructure API doesn't just work in theory—it works when thousands of real users are depending on it.

*AetherTest: Because the best time to find API issues is before your users do.*