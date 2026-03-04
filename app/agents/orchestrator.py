"""
Orchestrator agent that coordinates all sub-agents.
"""

import json
from typing import Dict, List, Optional, Any
from .roles import AgentFactory, BaseAgent, DockerAgent, DownloadAgent, DebugAgent, ExecutionAgent
from .tools import ScriptTools, MakeTools, ShellTools


class Orchestrator:
    """
    Main orchestrator that coordinates all agents and tools.
    Can delegate tasks to specialized agents or use tools directly.
    """
    
    def __init__(self):
        self.docker = DockerAgent()
        self.download = DownloadAgent()
        self.debug = DebugAgent()
        self.execution = ExecutionAgent()
        self.scripts = ScriptTools()
        self.make = MakeTools()
        self.shell = ShellTools()
        
        # Agent registry for quick access
        self.agents = {
            "docker": self.docker,
            "download": self.download,
            "debug": self.debug,
            "execution": self.execution,
        }
    
    def status(self) -> Dict:
        """Get overall system status."""
        return {
            "docker": self.docker.health_report(),
            "download": self.download.progress(),
            "debug": self.debug.check_endpoints()
        }
    
    def full_diagnostic(self) -> Dict:
        """Run full diagnostic."""
        return self.debug.diagnose()
    
    # === HIGH-LEVEL WORKFLOWS ===
    
    def deploy_service(self, service: Optional[str] = None) -> Dict:
        """Build and deploy services."""
        return self.execution.build_and_deploy(service)
    
    def restart_all(self) -> Dict:
        """Restart all services."""
        return self.docker.restart_all()
    
    def queue_downloads(self, count: int = 10, start: int = 1, dataset: int = 1) -> Dict:
        """Queue downloads."""
        return self.download.queue_files(count, start, dataset)
    
    def monitor_progress(self) -> Dict:
        """Monitor download progress."""
        return self.download.progress()
    
    # === COORDINATION METHODS ===
    
    def execute_plan(self, plan: Dict) -> Dict:
        """
        Execute a plan with multiple steps.
        
        Example plan:
        {
            "steps": [
                {"action": "docker.restart", "args": ["worker"]},
                {"action": "download.queue", "args": [10, 1000]},
                {"action": "wait", "seconds": 30},
                {"action": "download.progress"}
            ]
        }
        """
        results = []
        
        for step in plan.get("steps", []):
            action = step.get("action", "")
            args = step.get("args", [])
            
            result = {"step": action, "success": False}
            
            if action == "wait":
                import time
                time.sleep(int(args[0]) if args else 10)
                result["success"] = True
            
            elif "." in action:
                # Delegate to agent
                agent_name, method = action.split(".", 1)
                agent = self.agents.get(agent_name)
                if agent and hasattr(agent, method):
                    method_func = getattr(agent, method)
                    result["result"] = method_func(*args) if args else method_func()
                    result["success"] = True
            
            elif hasattr(self, action):
                method = getattr(self, action)
                result["result"] = method(*args) if args else method()
                result["success"] = True
            
            results.append(result)
        
        return {
            "plan_executed": True,
            "steps": results,
            "all_success": all(r.get("success", False) for r in results)
        }
    
    def handle_incident(self, incident_type: str) -> Dict:
        """Handle a specific incident type."""
        if incident_type == "download_stalled":
            # Restart worker and retry
            return self.execute_plan({
                "steps": [
                    {"action": "docker.restart", "args": ["worker"]},
                    {"action": "wait", "args": ["10"]},
                    {"action": "debug.analyze_failures"}
                ]
            })
        
        elif incident_type == "api_down":
            # Check and restart API
            return self.execute_plan({
                "steps": [
                    {"action": "docker.restart", "args": ["api"]},
                    {"action": "wait", "args": ["10"]},
                    {"action": "debug.check_endpoints"}
                ]
            })
        
        elif incident_type == "low_disk":
            # Clean up old downloads
            return self.execution.cleanup_old_downloads(100)
        
        return {"error": f"Unknown incident type: {incident_type}"}
    
    # === REPORTING ===
    
    def system_report(self) -> Dict:
        """Generate comprehensive system report."""
        return {
            "status": self.status(),
            "diagnostic": self.full_diagnostic(),
            "disk": self.execution.disk_report(),
            "project_size": self.execution.system.project_size()
        }
    
    def download_report(self) -> Dict:
        """Generate download report."""
        progress = self.download.progress()
        failures = self.debug.analyze_failures()
        
        return {
            "progress": progress,
            "failures": failures
        }
    
    # === DIRECT TOOL ACCESS ===
    
    def run_script(self, script: str, args: List[str] = None) -> Dict:
        """Run a script directly."""
        return self.scripts.run_script(script, args)
    
    def run_make(self, target: str) -> Dict:
        """Run make target."""
        return self.make.run_make(target)
    
    def run_shell(self, command: str) -> Dict:
        """Run shell command."""
        return self.shell.run(command)


# === CONVENIENCE FUNCTIONS ===

def quick_status() -> Dict:
    """Quick status check."""
    orch = Orchestrator()
    return orch.status()

def quick_deploy() -> Dict:
    """Quick deploy."""
    orch = Orchestrator()
    return orch.deploy_service()

def quick_download(count: int = 10) -> Dict:
    """Quick download queue."""
    orch = Orchestrator()
    return orch.queue_downloads(count)
