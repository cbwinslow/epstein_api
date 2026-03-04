"""
System management tools for agents.
"""

import subprocess
import os
from typing import Dict, List, Optional


class SystemTools:
    """Tools for system operations."""
    
    PROJECT_DIR = "/home/cbwinslow/Documents/epstein"
    
    @staticmethod
    def git_status() -> Dict:
        """Get git status."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=SystemTools.PROJECT_DIR
        )
        return {
            "changed_files": result.stdout.strip().split('\n') if result.stdout.strip() else [],
            "has_changes": bool(result.stdout.strip())
        }
    
    @staticmethod
    def git_diff() -> str:
        """Get git diff."""
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True,
            text=True,
            cwd=SystemTools.PROJECT_DIR
        )
        return result.stdout
    
    @staticmethod
    def git_commit(message: str) -> Dict:
        """Commit changes."""
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            capture_output=True,
            cwd=SystemTools.PROJECT_DIR
        )
        
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            cwd=SystemTools.PROJECT_DIR
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    
    @staticmethod
    def git_push() -> Dict:
        """Push to remote."""
        result = subprocess.run(
            ["git", "push", "origin", "master"],
            capture_output=True,
            text=True,
            cwd=SystemTools.PROJECT_DIR
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    
    @staticmethod
    def disk_usage() -> Dict:
        """Get disk usage."""
        result = subprocess.run(
            ["df", "-h", SystemTools.PROJECT_DIR],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            return {
                "total": parts[1],
                "used": parts[2],
                "available": parts[3],
                "use_percent": parts[4]
            }
        return {}
    
    @staticmethod
    def memory_usage() -> Dict:
        """Get memory usage."""
        result = subprocess.run(
            ["free", "-h"],
            capture_output=True,
            text=True
        )
        return {"output": result.stdout}
    
    @staticmethod
    def project_size() -> Dict:
        """Get project directory size."""
        result = subprocess.run(
            ["du", "-sh", SystemTools.PROJECT_DIR],
            capture_output=True,
            text=True
        )
        size = result.stdout.split()[0] if result.stdout else "unknown"
        
        # Get subdirectories
        result = subprocess.run(
            ["du", "-sh", f"{SystemTools.PROJECT_DIR}/*"],
            capture_output=True,
            text=True,
            shell=True
        )
        dirs = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    dirs[parts[1].replace(SystemTools.PROJECT_DIR + "/", "")] = parts[0]
        
        return {
            "total": size,
            "directories": dirs
        }
    
    @staticmethod
    def cleanup_downloads(keep_recent: int = 50) -> Dict:
        """Clean up old downloads, keeping most recent."""
        downloads_dir = f"{SystemTools.PROJECT_DIR}/data/downloads"
        
        # List files sorted by modification time
        result = subprocess.run(
            ["ls", "-t", downloads_dir],
            capture_output=True,
            text=True
        )
        
        files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        files_to_delete = files[keep_recent:]
        
        deleted = []
        for f in files_to_delete:
            path = f"{downloads_dir}/{f}"
            subprocess.run(["rm", "-f", path])
            deleted.append(f)
        
        return {
            "deleted_count": len(deleted),
            "kept_count": len(files) - len(deleted),
            "deleted_files": deleted[:10]  # Show first 10
        }
