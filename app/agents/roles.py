"""
Agent roles for the Epstein OSINT Pipeline.
"""

from typing import Dict, List, Optional
from .tools import DockerTools, DownloadTools, SystemTools, DebugTools


class BaseAgent:
    """Base agent class."""
    
    name: str = "Base Agent"
    description: str = "Base agent"
    
    def __init__(self):
        self.docker = DockerTools()
        self.downloads = DownloadTools()
        self.system = SystemTools()
        self.debug = DebugTools()
    
    def status(self) -> Dict:
        """Get agent status."""
        return {
            "name": self.name,
            "description": self.description
        }


class DockerAgent(BaseAgent):
    """Agent for Docker container management."""
    
    name = "Docker Agent"
    description = "Manages Docker containers, builds, restarts, and health checks"
    
    def health_report(self) -> Dict:
        """Get comprehensive health report."""
        return self.docker.health_check()
    
    def restart_service(self, service: str) -> Dict:
        """Restart a specific service."""
        return self.docker.restart(service)
    
    def full_restart(self) -> Dict:
        """Restart all services."""
        return self.docker.restart_all()
    
    def rebuild(self, service: Optional[str] = None) -> Dict:
        """Rebuild services."""
        return self.docker.build(service)
    
    def get_logs(self, container: str, lines: int = 50) -> str:
        """Get container logs."""
        return self.docker.logs(container, lines)


class DownloadAgent(BaseAgent):
    """Agent for managing downloads."""
    
    name = "Download Agent"
    description = "Manages file downloads, queues URLs, monitors progress"
    
    def queue_files(self, count: int = 10, start: int = 1, dataset: int = 1) -> Dict:
        """Queue DOJ files for download."""
        results = self.downloads.queue_doj_files(start, count, dataset)
        return {
            "queued": len(results),
            "files": [r.get("url", "") for r in results[:5]]
        }
    
    def progress(self) -> Dict:
        """Get download progress."""
        stats = self.downloads.get_stats()
        folder = self.downloads.download_folder_size()
        
        return {
            "total": stats["total"],
            "statuses": stats["statuses"],
            "folder_size": folder["size"],
            "file_count": folder["file_count"]
        }
    
    def add_url(self, url: str) -> Dict:
        """Add single URL."""
        return self.downloads.add_url(url)
    
    def add_urls(self, urls: List[str]) -> List[Dict]:
        """Add multiple URLs."""
        return self.downloads.add_urls(urls)
    
    def generate_urls(self, start: int, count: int, dataset: int = 1) -> List[str]:
        """Generate DOJ file URLs."""
        return self.downloads.generate_doj_urls(start, count, dataset)


class DebugAgent(BaseAgent):
    """Agent for debugging and analysis."""
    
    name = "Debug Agent"
    description = "Analyzes logs, checks system health, diagnoses issues"
    
    def diagnose(self) -> Dict:
        """Run full diagnostic."""
        return self.debug.full_diagnostic()
    
    def analyze_logs(self, container: str = "epstein-worker", lines: int = 100) -> Dict:
        """Analyze container logs."""
        return self.debug.analyze_logs(container, lines)
    
    def check_endpoints(self) -> Dict:
        """Check API endpoints."""
        return self.debug.check_api_endpoints()
    
    def check_services(self) -> Dict:
        """Check all external services."""
        return {
            "redis": self.debug.check_redis(),
            "neo4j": self.debug.check_neo4j(),
            "chromadb": self.debug.check_chromadb()
        }
    
    def analyze_failures(self) -> Dict:
        """Analyze download failures."""
        return self.debug.analyze_download_failures()


class ExecutionAgent(BaseAgent):
    """Agent for execution and deployment."""
    
    name = "Execution Agent"
    description = "Executes commands, builds, deploys, manages git workflow"
    
    def build_and_deploy(self, service: Optional[str] = None) -> Dict:
        """Build and deploy services."""
        # Build
        build_result = self.docker.build(service)
        if not build_result["success"]:
            return {"error": "Build failed", "details": build_result}
        
        # Restart
        restart_result = self.docker.restart_all()
        
        return {
            "build": build_result,
            "restart": restart_result
        }
    
    def git_status(self) -> Dict:
        """Check git status."""
        return self.system.git_status()
    
    def git_commit_and_push(self, message: str) -> Dict:
        """Commit and push changes."""
        commit_result = self.system.git_commit(message)
        if not commit_result["success"]:
            return commit_result
        
        push_result = self.system.git_push()
        
        return {
            "commit": commit_result,
            "push": push_result
        }
    
    def cleanup_old_downloads(self, keep_recent: int = 50) -> Dict:
        """Clean up old downloads."""
        return self.system.cleanup_downloads(keep_recent)
    
    def disk_report(self) -> Dict:
        """Get disk usage report."""
        return self.system.disk_usage()


class ResearchAgent(BaseAgent):
    """Agent for research and web searches."""
    
    name = "Research Agent"
    description = "Searches for information, finds resources"
    
    def __init__(self):
        super().__init__()
        # Will add web search capabilities
        pass


# Agent factory
class AgentFactory:
    """Factory for creating agents."""
    
    @staticmethod
    def get_agent(agent_type: str) -> BaseAgent:
        """Get an agent by type."""
        agents = {
            "docker": DockerAgent,
            "download": DownloadAgent,
            "debug": DebugAgent,
            "execution": ExecutionAgent,
            "research": ResearchAgent,
        }
        
        agent_class = agents.get(agent_type.lower())
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return agent_class()
    
    @staticmethod
    def get_all_agents() -> Dict[str, BaseAgent]:
        """Get all available agents."""
        return {
            "docker": DockerAgent(),
            "download": DownloadAgent(),
            "debug": DebugAgent(),
            "execution": ExecutionAgent(),
            "research": ResearchAgent(),
        }
