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

## Quick Start (Local Demo)
Experience AetherTest in under 5 minutes:

```bash
# Clone and enter the repository
git clone https://github.com/yourusername/AetherTest.git
cd AetherTest

# Install dependencies
pip install -r requirements.txt

# Launch the complete simulation (starts mock API + runs full test)
python run_full_simulation.py
```

Watch as AetherTest:
1. 🚀 Starts a realistic mock infrastructure API on `http://127.0.0.1:8000`  
2. 👥 Creates 20 infrastructure agents (5 per persona type)  
3. 🔄 Executes 8 interactions per agent (160 total API calls)  
4. 📊 Prints a detailed success report showing performance by persona  
5. 💾 Saves all results to the database for deeper analytics  

While running, explore the live API docs: `http://127.0.0.1:8000/docs`

## How It Works for Founders
As a founder, you don’t need to become a testing expert—AetherTest does the heavy lifting:

1. **Point to your API**: Simply provide your API endpoint URL and basic endpoint mapping (where to find auth, resources, health checks)  
2. **Select your user types**: Choose which infrastructure user types to simulate (or use our battle‑tested defaults)  
3. **Set your scale**: Decide how many virtual users to simulate and how deeply each should test your API  
4. **Let AetherTest run**: Our orchestrator launches agents that behave like real infrastructure teams—they authenticate, workflow through your API, handle errors intelligently, and report everything  
5. **Get actionable insights**: Receive a clear report showing exactly where your API struggles, which user types encounter issues, and what needs fixing before your real users do  

No more guessing if your authentication flow works under load. No more hoping your rate limiting behaves correctly. AetherTest shows you the truth before your users find the problems.

## Project Structure
```
AetherTest/
├── mock_api.py               # Production‑like mock infrastructure API for immediate testing
├── run_full_simulation.py    # One‑command demo: launches API + runs complete simulation
├── run_infrastructure_test.py# Original test harness (evolved to CLI‑driven interface)
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

**Next 4‑6 Weeks Priorities:**
- 🎯 Add 3+ new infrastructure user personas (Security Engineer, Data Engineer, Platform Engineer)  
- 🎯 Support custom workflow definitions via simple YAML/JSON configuration  
- 🎯 Enhanced analytics dashboard with real‑time visualization and filtering  
- 🎯 Distributed testing mode for 1000+ agent simulations (horizontal scaling)  
- 🎯 Pre‑built scenarios for Kubernetes, databases, message queues, and CI/CD patterns  
- 🎯 Performance benchmarking mode with SLA tracking and regression detection  
- 🎯 CI/CD pipeline integrations (GitHub Actions, GitLab CI, Jenkins)  

## Contributing / Getting Early Access
We’re building AetherTest with and for infrastructure API founders who believe testing should be as sophisticated as the systems they’re building.

**If you’re building infrastructure tools, APIs, or platforms:**
1. Star this repository to follow our progress  
2. Join our early access program by opening an Issue with “Early Access Request”  
3. Share your biggest API testing challenges—we’re designing features around real founder needs  
4. Consider contributing: we welcome improvements to personas, workflows, and analytics  

**Let’s make sure your infrastructure API doesn’t just work in theory—it works when thousands of real users are depending on it.**

*AetherTest: Because the best time to find API issues is before your users do.*
