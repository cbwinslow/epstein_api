"""
Download management tools for agents.
Uses subprocess/curl to avoid external dependencies.
"""

import subprocess
import json
from typing import List, Dict, Optional


class DownloadTools:
    """Tools for managing downloads."""
    
    API_URL = "http://localhost:8000"
    
    @staticmethod
    def _curl(method: str = "GET", endpoint: str = "", data: Optional[Dict] = None) -> Dict:
        """Make API call using curl."""
        cmd = ["curl", "-s", "-X", method, f"{DownloadTools.API_URL}{endpoint}"]
        
        if data:
            cmd.extend(["-H", "Content-Type: application/json"])
            cmd.extend(["-d", json.dumps(data)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return json.loads(result.stdout) if result.stdout else {}
        except:
            return {"raw": result.stdout, "error": result.stderr}
    
    @staticmethod
    def add_url(url: str) -> Dict:
        """Add a single URL to download queue."""
        return DownloadTools._curl("POST", "/api/ingest/url", {"url": url})
    
    @staticmethod
    def add_urls(urls: List[str]) -> List[Dict]:
        """Add multiple URLs to download queue."""
        return DownloadTools._curl("POST", "/api/ingest/urls", {"urls": urls})
    
    @staticmethod
    def get_tasks(status: Optional[str] = None, limit: int = 100) -> Dict:
        """Get download tasks."""
        endpoint = f"/api/ingest/tasks?limit={limit}"
        if status:
            endpoint += f"&status={status}"
        return DownloadTools._curl(endpoint=endpoint)
    
    @staticmethod
    def get_stats() -> Dict:
        """Get download statistics."""
        tasks = DownloadTools.get_tasks(limit=1000)
        
        statuses = {}
        for task in tasks.get("tasks", []):
            s = task.get("status", "UNKNOWN")
            statuses[s] = statuses.get(s, 0) + 1
        
        return {
            "total": tasks.get("total", 0),
            "statuses": statuses
        }
    
    @staticmethod
    def get_pending_count() -> int:
        """Get count of pending downloads."""
        stats = DownloadTools.get_stats()
        return stats["statuses"].get("PENDING", 0)
    
    @staticmethod
    def get_completed_count() -> int:
        """Get count of completed downloads."""
        stats = DownloadTools.get_stats()
        return stats["statuses"].get("COMPLETED", 0)
    
    @staticmethod
    def queue_doj_files(start: int = 1, count: int = 10, dataset: int = 1) -> List[Dict]:
        """Queue DOJ Epstein files."""
        urls = []
        for i in range(start, start + count):
            file_num = str(i).zfill(8)
            url = f"https://www.justice.gov/epstein/files/DataSet%20{dataset}/EFTA{file_num}.pdf"
            urls.append(url)
        
        return DownloadTools.add_urls(urls)
    
    @staticmethod
    def generate_doj_urls(start: int, count: int, dataset: int = 1) -> List[str]:
        """Generate DOJ file URLs."""
        urls = []
        for i in range(start, start + count):
            file_num = str(i).zfill(8)
            url = f"https://www.justice.gov/epstein/files/DataSet%20{dataset}/EFTA{file_num}.pdf"
            urls.append(url)
        return urls
    
    @staticmethod
    def check_api_health() -> Dict:
        """Check if API is healthy."""
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
             f"{DownloadTools.API_URL}/health"],
            capture_output=True,
            text=True
        )
        code = result.stdout.strip()
        return {
            "healthy": code == "200",
            "status_code": code
        }
    
    @staticmethod
    def download_folder_size() -> Dict:
        """Get download folder size."""
        result = subprocess.run(
            ["du", "-sh", "/home/cbwinslow/Documents/epstein/data/downloads/"],
            capture_output=True,
            text=True
        )
        size = result.stdout.split()[0] if result.stdout else "unknown"
        
        # Count files
        result = subprocess.run(
            ["ls", "-1", "/home/cbwinslow/Documents/epstein/data/downloads/"],
            capture_output=True,
            text=True
        )
        file_count = len([f for f in result.stdout.strip().split('\n') if f])
        
        return {
            "size": size,
            "file_count": file_count
        }
