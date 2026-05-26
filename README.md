# AetherTest

**Test your infrastructure in a living digital world before the real world tests you.**

## Why AetherTest? The Founder's Edge

Most infrastructure founders launch with uncertainty:
- 🤔 **Will our authentication hold under real load?**
- 🤔 **Do our rate limits actually stop abusive users?**
- 🤔 **Will QA teams find edge cases we missed?**

AetherTest eliminates the guesswork by deploying **realistic AI agents** that behave like actual infrastructure teams—Cautious DevOps, aggressive founders, SREs, and QA engineers—to stress-test your APIs *before* real users encounter issues.

### The Before/After

| Without AetherTest | With AetherTest |
|-------------------|-----------------|
| ❌ Manual testing: inconsistent, doesn't scale | ✅ AI agents: consistent, scalable, realistic |
| ❌ Scripted bots: predictable, miss edge cases | ✅ Human-like behavior: discovers real issues |
| ❌ Load testing: measures throughput, not behavior | ✅ Workflow testing: authenticates, operates, validates |
| ❌ Guess and hope | ✅ Know and fix |

## 🚀 Testing Your Real API in Under 5 Minutes

Get meaningful insights in your first 10 minutes with this foolproof process:

### 1️⃣ One-Time Setup (2 minutes)
```bash
git clone https://github.com/aureuskey/aethertest.git
cd AetherTest
pip install -e .  # Installs AetherTest as editable package
```

### 2️⃣ Test Your API (2 minutes)
```bash
aethertest test --url https://your-api.com [--token YOUR_TOKEN] [--duration 2]
```

That's it! The command will:
- 🚀 Launch realistic AI agents (Cautious DevOps, Aggressive Founder, SRE, QA Engineer)
- 🔄 Test authentication, rate limits, endpoints, and error handling
- 📊 Deliver a clear success report with actionable insights
- 💾 Save detailed results locally (SQLite database—no PostgreSQL needed)

### 3️⃣ Review Results (<1 minute)
- See success rates by persona type
- Identify failure modes and retry patterns
- Get performance metrics and detailed logs

**Example output:**
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

## How It Works for Founders

As a founder, you don't need to become a testing expert—AetherTest does the heavy lifting:

1. **Point to your API**: Simply provide your API endpoint URL and basic authentication
2. **Let AetherTest run**: Our orchestrator launches agents that behave like real infrastructure teams—they authenticate, workflow through your API, handle errors intelligently, and report everything
3. **Get actionable insights**: Receive a clear report showing exactly where your API struggles, which user types encounter issues, and what needs fixing before your real users do

No more guessing if your authentication flow works under load. No more hoping your rate limiting behaves correctly. AetherTest shows you the truth before your users find the problems.

## ⚙️ Configuration System (For Advanced Users)

For more control, AetherTest uses a simple YAML configuration file:

```bash
# Create config file
cp config.yaml.example config.yaml

# Edit config.yaml to customize:
# - Authentication type and credentials
# - Endpoint mapping for your API structure
# - Number of agents and test duration
# - Specific scenarios to run

# Then test with your config
aethertest test --config config.yaml
```

The configuration system makes it easy to test complex APIs with custom endpoints, authentication methods, and testing scenarios—all without changing code.

## 📚 API Reference

AetherTest also provides a REST API for integrating test results into your CI/CD pipeline or custom dashboards. See the API documentation at `http://localhost:8000/docs` when running the local server.

## 🛠️ Troubleshooting

### First-Run Issues

**Problem**: `ModuleNotFoundError: No module named 'langgraph'`
**Solution**: Run `pip install -e .` again to ensure dependencies are installed.

**Problem**: `Error saving simulation results to database: no such table`
**Solution**: This was fixed in v0.2.0—ensure you have the latest version. The system now automatically creates required SQLite tables.

**Problem**: `Port 8000 already in use`
**Solution**: Another process is using the port. Either stop it or use a different port with `--port 8001` (modify config.yaml or use environment variables).

**Problem**: Seeing `Connection refused` when trying to access http://127.0.0.1:8000/docs
**Solution**: Wait a few seconds for the API server to fully start, then refresh the page.

**Problem**: Authentication fails when testing real API
**Solution**:
1. Verify your token/credentials are correct
2. Ensure the auth_login endpoint is properly mapped in config.yaml
3. Try with `--verbose` flag to see detailed authentication logs

**Problem**: Endpoints not found (404 errors)
**Solution**:
1. Check your endpoint mapping in config.yaml
2. Verify the base URL is correct
3. Use `--verbose` to see exactly which endpoints are being called
4. Adjust the endpoint mappings to match your API's actual paths

### Getting Help

If you encounter issues not covered here:
1. Check the [GitHub Issues](https://github.com/aureuskey/aethertest/issues) for similar problems
2. Create a new issue with details about your operating system, Python version, and the exact error message
3. For immediate help, consider reaching out through the project's discussion forums

## 🔑 Key Features

- **Real Infrastructure Personalities**: Four distinct user personas with real‑world behaviors, risk tolerances, and goals (Cautious DevOps, Aggressive Founder, SRE, QA Engineer)
- **Stateful Workflow Testing**: Multi‑step API workflows that mimic real usage (authenticate → operate → validate → cleanup) with proper session management
- **Intelligent Error Handling**: Smart retry mechanisms with exponential backoff, jitter, and error classification (including AUTH_RECOVERABLE for 401s)
- **Rate Limit Awareness**: Agents detect 429 responses and implement appropriate back‑off strategies automatically
- **Production‑Grade Observability**: Comprehensive metrics on success rates, failure modes, retry patterns, and performance breakdowns
- **Auth Token Persistence**: Verified session management that maintains authentication across interactions
- **Mock Infrastructure API**: Ready‑to‑use FastAPI server representing common infrastructure patterns for immediate testing
- **Extensible & Customizable**: Easy to add new personas, workflows, and API endpoints to match your specific infrastructure
- **Real API Testing**: Test your actual APIs with configurable endpoint mapping and authentication
- **Zero-Configuration Database**: SQLite database created automatically—no PostgreSQL required for basic use

## 📈 Current Status & Roadmap

**What's Working Now:**
- ✅ EnhancedSyntheticAgent with verified auth token persistence (fixes validated)
- ✅ 4 realistic infrastructure user personas with distinct behaviors
- ✅ Stateful workflow testing with proper session management
- ✅ Intelligent error handling and retry mechanisms
- ✅ Rate limit awareness (429 response handling)
- ✅ Mock infrastructure API representing common patterns
- ✅ Database storage for simulation results and analytics (SQLite default)
- ✅ Observability and comprehensive reporting
- ✅ Extensible architecture for custom personas and workflows
- ✅ Real API testing via configuration system
- ✅ Command-line configuration overrides
- ✅ One-command CLI for founder-friendly testing

**Next 4-6 Weeks Priorities:**
- 🎯 Add 3+ new infrastructure user personas (Security Engineer, Data Engineer, Platform Engineer)
- 🎯 Support custom workflow definitions via simple YAML/JSON configuration
- 🎯 Enhanced analytics dashboard with real-time visualization and filtering
- 🎯 Distributed testing mode for 1000+ agent simulations (horizontal scaling)
- 🎯 Pre-built scenarios for Kubernetes, databases, message queues, and CI/CD patterns
- 🎯 Performance benchmarking mode with SLA tracking and regression detection
- 🎯 CI/CD pipeline integrations (GitHub Actions, GitLab CI, Jenkins)

## 🤝 Contributing / Getting Early Access

We're building AetherTest with and for infrastructure API founders who believe testing should be as sophisticated as the systems they're building.

**If you're building infrastructure tools, APIs, or platforms:**
1. Star this repository to follow our progress
2. Join our early access program by opening an Issue with "Early Access Request"
3. Share your biggest API testing challenges—we're designing features around real founder needs
4. Consider contributing: we welcome improvements to personas, workflows, and analytics

## 💡 Let's Make Sure Your Infrastructure Works

Let's make sure your infrastructure API doesn't just work in theory—it works when thousands of real users are depending on it.

*AetherTest: Because the best time to find API issues is before your users do.*