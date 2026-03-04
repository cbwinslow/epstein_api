"""
Debug and analysis tools for agents.
Uses subprocess/curl to avoid external dependencies.
"""

import subprocess
import json
from typing import Dict, List, Optional


class DebugTools:
    """Tools for debugging and analysis."""
    
    API_URL = "http://localhost:8000"
    
    @staticmethod
    def _curl(endpoint: str = "") -> Dict:
        """Make API call using curl."""
        cmd = ["curl", "-s", f"{DebugTools.API_URL}{endpoint}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return json.loads(result.stdout) if result.stdout else {}
        except:
            return {"raw": result.stdout}
    
    @staticmethod
    def analyze_logs(container: str, lines: int = 100, search: Optional[str] = None) -> Dict:
        """Analyze container logs for errors."""
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container],
            capture_output=True,
            text=True
        )
        
        logs = result.stdout + result.stderr
        
        if search:
            logs = "\n".join([line for line in logs.split('\n') if search.lower() in line.lower()])
        
        # Count errors
        error_lines = [line for line in logs.split('\n') if 'error' in line.lower() or 'exception' in line.lower()]
        warning_lines = [line for line in logs.split('\n') if 'warning' in line.lower()]
        
        return {
            "container": container,
            "total_lines": len(logs.split('\n')),
            "error_count": len(error_lines),
            "warning_count": len(warning_lines),
            "recent_errors": error_lines[-10:] if error_lines else [],
            "recent_warnings": warning_lines[-10:] if warning_lines else []
        }
    
    @staticmethod
    def check_api_endpoints() -> Dict:
        """Check all API endpoints."""
        endpoints = [
            "/health",
            "/",
            "/api/ingest/tasks",
            "/api/graph/stats"
        ]
        
        results = {}
        for endpoint in endpoints:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
                 f"{DebugTools.API_URL}{endpoint}"],
                capture_output=True,
                text=True
            )
            code = result.stdout.strip()
            results[endpoint] = {
                "status": code,
                "working": code == "200"
            }
        
        return {
            "endpoints": results,
            "all_working": all(r.get("working", False) for r in results.values())
        }
    
    @staticmethod
    def check_database() -> Dict:
        """Check database connectivity and state."""
        # Check SQLite
        result = subprocess.run(
            ["docker", "exec", "epstein-worker", "sqlite3", "/data/state.db", 
             "SELECT COUNT(*) FROM download_tasks;"],
            capture_output=True,
            text=True
        )
        
        task_count = result.stdout.strip() if result.returncode == 0 else "error"
        
        # Check status distribution
        result = subprocess.run(
            ["docker", "exec", "epstein-worker", "sqlite3", "/data/state.db",
             "SELECT status, COUNT(*) FROM download_tasks GROUP BY status;"],
            capture_output=True,
            text=True
        )
        
        status_dist = {}
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) == 2:
                        status_dist[parts[0].strip()] = int(parts[1].strip())
        
        return {
            "sqlite_tasks": task_count,
            "status_distribution": status_dist
        }
    
    @staticmethod
    def check_redis() -> Dict:
        """Check Redis connectivity and queues."""
        result = subprocess.run(
            ["docker", "exec", "epstein-redis", "redis-cli", "LLEN", "celery"],
            capture_output=True,
            text=True
        )
        
        queue_len = result.stdout.strip() if result.returncode == 0 else "error"
        
        # Get all keys
        result = subprocess.run(
            ["docker", "exec", "epstein-redis", "redis-cli", "KEYS", "*task*"],
            capture_output=True,
            text=True
        )
        
        task_keys = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        return {
            "queue_length": queue_len,
            "task_keys": len(task_keys),
            "connected": result.returncode == 0
        }
    
    @staticmethod
    def check_neo4j() -> Dict:
        """Check Neo4j connectivity."""
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:7474"],
            capture_output=True,
            text=True
        )
        
        return {
            "connected": result.stdout.strip() == "200",
            "browser_available": result.returncode == 0
        }
    
    @staticmethod
    def check_chromadb() -> Dict:
        """Check ChromaDB connectivity."""
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
             "http://localhost:8001/api/v1/version"],
            capture_output=True,
            text=True
        )
        
        return {
            "connected": result.stdout.strip() == "200",
            "status_code": result.stdout.strip()
        }
    
    @staticmethod
    def full_diagnostic() -> Dict:
        """Run full system diagnostic."""
        return {
            "docker": DebugTools._check_docker(),
            "api": DebugTools.check_api_endpoints(),
            "database": DebugTools.check_database(),
            "redis": DebugTools.check_redis(),
            "neo4j": DebugTools.check_neo4j(),
            "chromadb": DebugTools.check_chromadb()
        }
    
    @staticmethod
    def _check_docker() -> Dict:
        """Check Docker status."""
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        return {
            "running": containers,
            "count": len(containers)
        }
    
    @staticmethod
    def analyze_download_failures() -> Dict:
        """Analyze any failed downloads."""
        tasks = DebugTools._curl("/api/ingest/tasks?limit=1000")
        
        failed = [t for t in tasks.get("tasks", []) if t.get("status") == "FAILED"]
        pending = [t for t in tasks.get("tasks", []) if t.get("status") == "PENDING"]
        
        return {
            "total_tasks": tasks.get("total", 0),
            "failed_count": len(failed),
            "pending_count": len(pending),
            "recent_failures": [
                {
                    "url": t.get("url", "")[:60],
                    "error": t.get("error_message", "unknown")
                }
                for t in failed[-5:]
            ]
        }
