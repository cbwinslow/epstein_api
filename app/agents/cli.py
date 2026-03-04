#!/usr/bin/env python3
"""
CLI interface for agents.
"""

import sys
import json
from roles import AgentFactory


def main():
    if len(sys.argv) < 2:
        print("Usage: agent.py <agent> <action> [args...]")
        print("\nAvailable agents:")
        print("  docker   - Docker container management")
        print("  download - Download management")
        print("  debug    - Debug and diagnostics")
        print("  execution - Build and deployment")
        print("\nExamples:")
        print("  agent.py docker status")
        print("  agent.py docker restart worker")
        print("  agent.py download queue 10")
        print("  agent.py download progress")
        print("  agent.py debug diagnose")
        print("  agent.py execution git-status")
        sys.exit(1)
    
    agent_type = sys.argv[1].lower()
    action = sys.argv[2].lower() if len(sys.argv) > 2 else "status"
    
    try:
        agent = AgentFactory.get_agent(agent_type)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    result = {}
    
    # Docker agent actions
    if agent_type == "docker":
        if action == "status":
            result = agent.docker.status()
        elif action == "health":
            result = agent.health_report()
        elif action == "restart":
            service = sys.argv[3] if len(sys.argv) > 3 else None
            if service:
                result = agent.restart_service(service)
            else:
                result = agent.full_restart()
        elif action == "logs":
            container = sys.argv[3] if len(sys.argv) > 3 else "epstein-worker"
            lines = int(sys.argv[4]) if len(sys.argv) > 4 else 50
            result = {"logs": agent.get_logs(container, lines)}
        elif action == "rebuild":
            service = sys.argv[3] if len(sys.argv) > 3 else None
            result = agent.rebuild(service)
    
    # Download agent actions
    elif agent_type == "download":
        if action == "progress" or action == "status":
            result = agent.progress()
        elif action == "queue":
            count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            start = int(sys.argv[4]) if len(sys.argv) > 4 else 1
            dataset = int(sys.argv[5]) if len(sys.argv) > 5 else 1
            result = agent.queue_files(count, start, dataset)
        elif action == "add":
            url = sys.argv[3] if len(sys.argv) > 3 else ""
            if url:
                result = agent.add_url(url)
    
    # Debug agent actions
    elif agent_type == "debug":
        if action == "diagnose":
            result = agent.diagnose()
        elif action == "logs":
            container = sys.argv[3] if len(sys.argv) > 3 else "epstein-worker"
            result = agent.analyze_logs(container)
        elif action == "endpoints":
            result = agent.check_endpoints()
        elif action == "services":
            result = agent.check_services()
        elif action == "failures":
            result = agent.analyze_failures()
    
    # Execution agent actions
    elif agent_type == "execution":
        if action == "git-status":
            result = agent.git_status()
        elif action == "git-commit":
            message = sys.argv[3] if len(sys.argv) > 3 else "Auto commit"
            result = agent.git_commit_and_push(message)
        elif action == "cleanup":
            keep = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            result = agent.cleanup_old_downloads(keep)
        elif action == "disk":
            result = agent.disk_report()
        elif action == "deploy":
            service = sys.argv[3] if len(sys.argv) > 3 else None
            result = agent.build_and_deploy(service)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
