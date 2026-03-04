"""
Script execution tools for agents.
"""

import subprocess
import json
from typing import Dict, List, Optional


class ScriptTools:
    """Tools for running scripts."""
    
    SCRIPTS_DIR = "/home/cbwinslow/Documents/epstein/app/scripts"
    PROJECT_DIR = "/home/cbwinslow/Documents/epstein"
    
    @staticmethod
    def run_script(script_name: str, args: List[str] = None) -> Dict:
        """Run a Python script."""
        script_path = f"{ScriptTools.SCRIPTS_DIR}/{script_name}"
        
        cmd = ["python3", script_path]
        if args:
            cmd.extend(args)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ScriptTools.PROJECT_DIR
        )
        
        return {
            "script": script_name,
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    
    @staticmethod
    def generate_epstein_urls(start: int = 1, count: int = 10, dataset: int = 1) -> List[str]:
        """Generate DOJ Epstein file URLs."""
        result = ScriptTools.run_script(
            "generate_epstein_urls.py",
            [str(start), str(count), str(dataset)]
        )
        
        if result["success"]:
            return [line for line in result["output"].strip().split('\n') if line]
        return []
    
    @staticmethod
    def generate_report(output_format: str = "json") -> Dict:
        """Generate a report using the report script."""
        return ScriptTools.run_script("generate_report.py", ["--format", output_format])
    
    @staticmethod
    def run_preflight(args: List[str] = None) -> Dict:
        """Run preflight calibration."""
        cmd = ["python3", f"{ScriptTools.SCRIPTS_DIR}/preflight_calibration.py"]
        if args:
            cmd.extend(args)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ScriptTools.PROJECT_DIR
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout[:5000] if result.stdout else "",
            "error": result.stderr[:1000] if result.stderr else ""
        }
    
    @staticmethod
    def list_scripts() -> List[str]:
        """List available scripts."""
        result = subprocess.run(
            ["ls", "-1", ScriptTools.SCRIPTS_DIR],
            capture_output=True,
            text=True
        )
        return [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]


class MakeTools:
    """Tools for Makefile commands."""
    
    PROJECT_DIR = "/home/cbwinslow/Documents/epstein"
    
    @staticmethod
    def run_make(target: str) -> Dict:
        """Run a make target."""
        result = subprocess.run(
            ["make", target],
            capture_output=True,
            text=True,
            cwd=MakeTools.PROJECT_DIR
        )
        
        return {
            "target": target,
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    
    @staticmethod
    def build() -> Dict:
        """Run make build."""
        return MakeTools.run_make("build")
    
    @staticmethod
    def up() -> Dict:
        """Run make up."""
        return MakeTools.run_make("up")
    
    @staticmethod
    def down() -> Dict:
        """Run make down."""
        return MakeTools.run_make("down")
    
    @staticmethod
    def restart() -> Dict:
        """Run make restart."""
        return MakeTools.run_make("restart")
    
    @staticmethod
    def logs(service: Optional[str] = None) -> str:
        """Get logs."""
        if service:
            return MakeTools.run_make(f"logs-{service}")["output"]
        return MakeTools.run_make("logs")["output"]
    
    @staticmethod
    def clean() -> Dict:
        """Run make clean."""
        return MakeTools.run_make("clean")


class ShellTools:
    """Tools for shell commands."""
    
    @staticmethod
    def run(command: str, cwd: str = None) -> Dict:
        """Run a shell command."""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        return {
            "command": command,
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    
    @staticmethod
    def check_port(port: int) -> bool:
        """Check if a port is in use."""
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    
    @staticmethod
    def kill_port(port: int) -> Dict:
        """Kill process on a port."""
        return ShellTools.run(f"lsof -ti:{port} | xargs kill -9")
