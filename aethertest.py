#!/usr/bin/env python
"""
Aethertest CLI - One-command interface for testing APIs
"""
import sys
import subprocess
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: aethertest <command> [options]")
        print("Commands:")
        print("  test    Run a test against an API")
        print("  quick   Run a quick test (faster feedback)")
        print("  help    Show this help")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    # Base command - use the same Python interpreter
    base = [sys.executable]

    if command == "test":
        base.append("run_full_simulation.py")
    elif command == "quick":
        base.append("quick_test.py")
    elif command == "help":
        print("Aethertest CLI - Test your APIs with AI agents")
        print("")
        print("Commands:")
        print("  test    Run a test against an API")
        print("          aethertest test --url https://api.example.com")
        print("  quick   Run a quick test (faster feedback)")
        print("          aethertest quick --url https://api.example.com")
        print("  help    Show this help")
        sys.exit(0)
    else:
        print(f"Unknown command: {command}")
        print("Use 'aethertest help' for usage information")
        sys.exit(1)

    # Execute the selected script with all remaining arguments
    subprocess.run(base + args)

if __name__ == "__main__":
    main()