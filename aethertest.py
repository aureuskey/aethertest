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

    # Convert user-friendly --url to --api-url for underlying scripts
    processed_args = []
    i = 0
    while i < len(args):
        if args[i] == "--url":
            # Handle --url value format
            processed_args.append("--api-url")
            if i + 1 < len(args):
                processed_args.append(args[i + 1])
                i += 2
            else:
                print("Error: --url requires a value")
                sys.exit(1)
        elif args[i].startswith("--url="):
            # Handle --url=value format
            processed_args.append("--api-url" + args[i][5:])
            i += 1
        else:
            processed_args.append(args[i])
            i += 1

    # Base command - use the Python interpreter that has langgraph installed
    base = [r"C:\Users\HP\AppData\Local\Programs\Python\Python313\python.exe"]

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
    subprocess.run(base + processed_args)

if __name__ == "__main__":
    main()