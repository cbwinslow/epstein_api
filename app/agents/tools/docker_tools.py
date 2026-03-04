"""
Docker management tools for agents.
"""

import subprocess
import json
from typing import Dict, List, Optional


class DockerTools:
    """Tools for managing Docker containers."""
    
    @staticmethod
    def ps() -> List[Dict]:
        """List all containers."""
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True
        )
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                containers.append(json.loads(line))
        return containers
    
    @staticmethod
    def ps_all() -> List[Dict]:
        """List all containers including stopped."""
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True,
            text=True
        )
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                containers.append(json.loads(line))
        return containers
    
    @staticmethod
    def logs(container: str, lines: int = 50) -> str:
        """Get container logs."""
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container],
            capture_output=True,
            text=True
        )
        return result.stdout + result.stderr
    
    @staticmethod
    def restart(service: str) -> Dict:
        """Restart a docker-compose service."""
        result = subprocess.run(
            ["docker", "compose", "restart", service],
            capture_output=True,
            text=True,
            cwd="/home/cbwinslow/Documents/epstein"
        )
        return {
            "service": service,
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    
    @staticmethod
    def restart_all() -> Dict:
        """Restart all docker-compose services."""
        result = subprocess.run(
            ["docker", "compose", "restart"],
            capture_output=True,
            text=True,
            cwd="/home/cbwinslow/Documents/epstein"
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    
    @staticmethod
    def build(service: Optional[str] = None) -> Dict:
        """Build docker-compose services."""
        cmd = ["docker", "compose", "build"]
        if service:
            cmd.append(service)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="/home/cbwinslow/Documents/epstein"
        )
        return {
            "service": service or "all",
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    
    @staticmethod
    def up(detach: bool = True) -> Dict:
        """Start docker-compose services."""
        cmd = ["docker", "compose", "up"]
        if detach:
            cmd.append("-d")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="/home/cbwinslow/Documents/epstein"
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    
    @staticmethod
    def down() -> Dict:
        """Stop docker-compose services."""
        result = subprocess.run(
            ["docker", "compose", "down"],
            capture_output=True,
            text=True,
            cwd="/home/cbwinslow/Documents/epstein"
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    
    @staticmethod
    def status() -> Dict:
        """Get status of all services."""
        result = subprocess.run(
            ["docker", "compose", "ps"],
            capture_output=True,
            text=True,
            cwd="/home/cbwinslow/Documents/epstein"
        )
        return {
            "output": result.stdout,
            "services": result.stdout.strip().split('\n')
        }
    
    @staticmethod
    def health_check() -> Dict:
        """Check health of all containers."""
        containers = DockerTools.ps()
        health = {}
        
        for container in containers:
            name = container.get('Names', 'unknown')
            status = container.get('Status', 'unknown')
            
            # Determine health based on status
            if 'Up' in status:
                health[name] = "healthy"
            elif 'Exited' in status:
                health[name] = "stopped"
            else:
                health[name] = status
        
        return {
            "healthy": [k for k, v in health.items() if v == "healthy"],
            "unhealthy": {k: v for k, v in health.items() if v != "healthy"},
            "total": len(containers)
        }
