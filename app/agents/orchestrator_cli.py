#!/usr/bin/env python3
"""
Comprehensive CLI for the agent system.
"""

import sys
import json
import os

# Add project to path
sys.path.insert(0, '/home/cbwinslow/Documents/epstein/app')

from agents.orchestrator import Orchestrator, quick_status, quick_deploy, quick_download
from agents.roles import AgentFactory


def print_json(data):
    print(json.dumps(data, indent=2))


def main():
    if len(sys.argv) < 2:
        print("""
Epstein OSINT Pipeline - Agent System
====================================

Usage: orchestrator.py <command> [args...]

Commands:
  status              - Quick system status
  deploy              - Build and deploy
  diagnose            - Full diagnostic
  
  docker <action>     - Docker operations
    health, restart, logs, rebuild
  
  download <action>   - Download operations
    progress, queue, add
  
  debug <action>     - Debug operations
    diagnose, logs, endpoints, failures
  
  execute <action>   - Execution operations
    git-status, cleanup, disk
  
  script <name>      - Run scripts
    generate_epstein_urls, generate_report
  
  make <target>      - Run make targets
    build, up, down, restart, clean
  
  orch <action>      - Orchestrator
    plan, incident, report

Examples:
  orchestrator.py status
  orchestrator.py docker health
  orchestrator.py download queue 20 1000
  orchestrator.py diagnose
  orchestrator.py make build
""")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    args = sys.argv[2:]
    
    orch = Orchestrator()
    
    # Quick commands
    if command == "status":
        print_json(quick_status())
        return
    
    if command == "deploy":
        print_json(quick_deploy())
        return
    
    if command == "diagnose":
        print_json(orch.full_diagnostic())
        return
    
    # Docker commands
    if command == "docker":
        action = args[0] if args else "health"
        
        if action == "health":
            print_json(orch.docker.health_report())
        elif action == "restart":
            service = args[1] if len(args) > 1 else None
            if service:
                print_json(orch.docker.restart_service(service))
            else:
                print_json(orch.docker.restart_all())
        elif action == "logs":
            container = args[1] if len(args) > 1 else "epstein-worker"
            lines = int(args[2]) if len(args) > 2 else 50
            print(orch.docker.logs(container, lines))
        elif action == "rebuild":
            service = args[1] if len(args) > 1 else None
            print_json(orch.docker.build(service))
        else:
            print(f"Unknown docker action: {action}")
    
    # Download commands
    elif command == "download":
        action = args[0] if args else "progress"
        
        if action == "progress":
            print_json(orch.download.progress())
        elif action == "queue":
            count = int(args[1]) if len(args) > 1 else 10
            start = int(args[2]) if len(args) > 2 else 1
            dataset = int(args[3]) if len(args) > 3 else 1
            print_json(orch.download.queue_files(count, start, dataset))
        elif action == "add":
            url = args[1] if len(args) > 1 else ""
            if url:
                print_json(orch.download.add_url(url))
        elif action == "urls":
            count = int(args[1]) if len(args) > 1 else 10
            start = int(args[2]) if len(args) > 2 else 1
            urls = orch.download.generate_urls(start, count)
            print_json({"urls": urls})
    
    # Debug commands
    elif command == "debug":
        action = args[0] if args else "diagnose"
        
        if action == "diagnose":
            print_json(orch.full_diagnostic())
        elif action == "logs":
            container = args[1] if len(args) > 1 else "epstein-worker"
            print_json(orch.debug.analyze_logs(container))
        elif action == "endpoints":
            print_json(orch.debug.check_endpoints())
        elif action == "failures":
            print_json(orch.debug.analyze_download_failures())
        elif action == "services":
            print_json({
                "redis": orch.debug.check_redis(),
                "neo4j": orch.debug.check_neo4j(),
                "chromadb": orch.debug.check_chromadb()
            })
    
    # Execution commands
    elif command == "execute":
        action = args[0] if args else "git-status"
        
        if action == "git-status":
            print_json(orch.execution.git_status())
        elif action == "git-commit":
            message = args[1] if len(args) > 1 else "Auto commit"
            print_json(orch.execution.git_commit_and_push(message))
        elif action == "cleanup":
            keep = int(args[1]) if len(args) > 1 else 50
            print_json(orch.execution.cleanup_old_downloads(keep))
        elif action == "disk":
            print_json(orch.execution.disk_report())
        elif action == "deploy":
            service = args[1] if len(args) > 1 else None
            print_json(orch.execution.build_and_deploy(service))
    
    # Script commands
    elif command == "script":
        script = args[0] if args else ""
        
        if script == "generate_epstein_urls":
            count = int(args[1]) if len(args) > 1 else 10
            start = int(args[2]) if len(args) > 2 else 1
            urls = orch.scripts.generate_epstein_urls(start, count)
            print_json({"urls": urls[:5], "total": len(urls)})
        elif script == "list":
            print_json({"scripts": orch.scripts.list_scripts()})
        else:
            result = orch.run_script(script, args[1:] if len(args) > 1 else None)
            print_json(result)
    
    # Make commands
    elif command == "make":
        target = args[0] if args else "help"
        
        if target == "help":
            print("make targets: build, up, down, restart, clean, logs")
        else:
            print_json(orch.make.run_make(target))
    
    # Orchestrator commands
    elif command == "orch":
        action = args[0] if args else "report"
        
        if action == "report":
            print_json(orch.system_report())
        elif action == "incident":
            incident = args[1] if len(args) > 1 else "download_stalled"
            print_json(orch.handle_incident(incident))
        elif action == "download-report":
            print_json(orch.download_report())
    
    else:
        print(f"Unknown command: {command}")
        print("Run orchestrator.py for help")


if __name__ == "__main__":
    main()
