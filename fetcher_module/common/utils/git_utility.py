"""
Git utility for automated code deployment
"""

import os
import git
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from ..config_loader.env_selector import EnvironmentSelector


@dataclass
class GitResult:
    """Result of git operations with comprehensive metadata"""
    
    success: bool
    operation: str
    commit_hash: Optional[str] = None
    branch: Optional[str] = None
    files_processed: Optional[List[str]] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    repo_path: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            "success": self.success,
            "operation": self.operation,
            "commit_hash": self.commit_hash,
            "branch": self.branch,
            "files_processed": self.files_processed,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "repo_path": self.repo_path
        }
    
    def __str__(self) -> str:
        status = "✅ SUCCESS" if self.success else "❌ FAILED"
        return f"{status}: {self.operation} - {self.error_message or 'Completed successfully'}"


class GitUtility:
    """Production-ready git utility for automated deployments"""
    
    def __init__(self, module_name: str, branch: Optional[str] = None):
        """
        Initialize git utility for specific module
        
        Args:
            module_name: Module name (web, api, s3, ftp)
            branch: Target branch (defaults to config default)
        """
        self.module_name = module_name
        
        # Load configuration
        env_selector = EnvironmentSelector()
        config_dict = env_selector.load_config()
        self.git_config = config_dict.get("GIT", {})
        
        # Set branch
        self.branch = branch or self.git_config.get("default_branch", "main")
        
        # Get repository and module paths
        self.repo_path = self._get_module_repo_path()
        self.module_path = self._get_module_folder_path()
        self.repo = None
        
        # Initialize repository connection
        self._connect_to_repo()
    
    def _get_module_repo_path(self) -> Path:
        """Get repository path (base repo, not module subfolder)"""
        base_path = Path(self.git_config.get("base_repo_path", ""))
        
        if not base_path.exists():
            raise ValueError(f"Base repository path does not exist: {base_path}")
        
        return base_path.resolve()
    
    def _get_module_folder_path(self) -> Path:
        """Get module folder path within the repository"""
        module_folder = self.git_config.get("modules", {}).get(self.module_name, self.module_name)
        module_path = self.repo_path / module_folder
        
        if not module_path.exists():
            raise ValueError(f"Module folder does not exist: {module_path}")
        
        return module_path.resolve()
    
    def _connect_to_repo(self) -> None:
        """Connect to git repository and validate"""
        try:
            self.repo = git.Repo(self.repo_path)
            
            if self.repo.bare:
                raise ValueError(f"Repository is bare: {self.repo_path}")
                
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Not a valid git repository: {self.repo_path}")
        except Exception as e:
            raise ValueError(f"Failed to connect to repository: {e}")
    
    def sync_latest(self) -> GitResult:
        """
        Sync latest changes from remote repository
        
        Returns:
            GitResult with operation details
        """
        try:
            # Ensure we're on the correct branch
            if self.repo.active_branch.name != self.branch:
                try:
                    self.repo.git.checkout(self.branch)
                except git.GitCommandError:
                    # Branch might not exist locally, create it
                    self.repo.git.checkout('-b', self.branch, f'origin/{self.branch}')
            
            # Pull latest changes
            origin = self.repo.remotes.origin
            origin.pull(self.branch)
            
            return GitResult(
                success=True,
                operation="sync",
                branch=self.branch,
                commit_hash=str(self.repo.head.commit.hexsha[:8]),
                repo_path=str(self.repo_path)
            )
            
        except Exception as e:
            return GitResult(
                success=False,
                operation="sync",
                branch=self.branch,
                error_message=str(e),
                repo_path=str(self.repo_path)
            )
    
    def push_files(self, file_paths: List[str], commit_message: str) -> GitResult:
        """
        Complete workflow: sync, add, commit, and push files
        
        Args:
            file_paths: List of absolute file paths to push
            commit_message: Commit message
            
        Returns:
            GitResult with comprehensive metadata
        """
        try:
            # Step 1: Sync repository if auto_sync is enabled
            if self.git_config.get("auto_sync", True):
                sync_result = self.sync_latest()
                if not sync_result.success:
                    return GitResult(
                        success=False,
                        operation="push_files",
                        branch=self.branch,
                        files_processed=file_paths,
                        error_message=f"Sync failed: {sync_result.error_message}",
                        repo_path=str(self.repo_path)
                    )
            
            # Step 2: Validate and convert file paths
            relative_files = []
            for file_path in file_paths:
                abs_path = Path(file_path).resolve()
                
                # Validate file exists
                if not abs_path.exists():
                    return GitResult(
                        success=False,
                        operation="push_files",
                        branch=self.branch,
                        files_processed=file_paths,
                        error_message=f"File not found: {abs_path}",
                        repo_path=str(self.repo_path)
                    )
                
                # Convert to relative path from repo root
                try:
                    relative_path = abs_path.relative_to(self.repo_path)
                    relative_files.append(str(relative_path))
                except ValueError:
                    return GitResult(
                        success=False,
                        operation="push_files",
                        branch=self.branch,
                        files_processed=file_paths,
                        error_message=f"File is outside repository: {abs_path}",
                        repo_path=str(self.repo_path)
                    )
            
            # Step 3: Ensure we're on correct branch
            if self.repo.active_branch.name != self.branch:
                self.repo.git.checkout(self.branch)
            
            # Step 4: Add files to staging
            self.repo.index.add(relative_files)
            
            # Step 5: Commit changes
            commit = self.repo.index.commit(commit_message)
            
            # Step 6: Push to remote
            origin = self.repo.remotes.origin
            push_info = origin.push(self.branch)
            
            # Check if push was successful
            if push_info and push_info[0].flags & push_info[0].ERROR:
                return GitResult(
                    success=False,
                    operation="push_files",
                    branch=self.branch,
                    files_processed=relative_files,
                    commit_hash=str(commit.hexsha[:8]),
                    error_message=f"Push failed: {push_info[0].summary}",
                    repo_path=str(self.repo_path)
                )
            
            # Success - return comprehensive result
            return GitResult(
                success=True,
                operation="push_files",
                commit_hash=str(commit.hexsha[:8]),
                branch=self.branch,
                files_processed=relative_files,
                repo_path=str(self.repo_path)
            )
            
        except Exception as e:
            return GitResult(
                success=False,
                operation="push_files",
                branch=self.branch,
                files_processed=file_paths,
                error_message=str(e),
                repo_path=str(self.repo_path)
            )
    
    def get_repo_status(self) -> Dict[str, Any]:
        """
        Get current repository status and metadata
        
        Returns:
            Dictionary with comprehensive repository information
        """
        try:
            return {
                "repo_path": str(self.repo_path),
                "module_name": self.module_name,
                "current_branch": self.repo.active_branch.name,
                "target_branch": self.branch,
                "last_commit_hash": str(self.repo.head.commit.hexsha[:8]),
                "last_commit_full_hash": str(self.repo.head.commit.hexsha),
                "last_commit_message": self.repo.head.commit.message.strip(),
                "last_commit_author": str(self.repo.head.commit.author),
                "last_commit_date": self.repo.head.commit.committed_datetime.isoformat(),
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": self.repo.untracked_files,
                "modified_files": [item.a_path for item in self.repo.index.diff(None)],
                "staged_files": [item.a_path for item in self.repo.index.diff("HEAD")],
                "remote_url": str(self.repo.remotes.origin.url) if self.repo.remotes.origin else None
            }
        except Exception as e:
            return {
                "error": str(e),
                "repo_path": str(self.repo_path),
                "module_name": self.module_name
            }


def create_git_utility(module_name: str, branch: Optional[str] = None) -> GitUtility:
    """
    Factory function to create GitUtility instance
    
    Args:
        module_name: Module name (web, api, s3, ftp)
        branch: Target branch (optional)
        
    Returns:
        GitUtility instance
        
    Raises:
        ValueError: If module or repository is invalid
    """
    return GitUtility(module_name, branch)


# Convenience functions for common operations
def push_to_module(module_name: str, file_paths: List[str], commit_message: str, 
                   branch: Optional[str] = None) -> GitResult:
    """
    Convenience function to push files to a module repository
    
    Args:
        module_name: Module name (web, api, s3, ftp)
        file_paths: List of absolute file paths to push
        commit_message: Commit message
        branch: Target branch (optional)
        
    Returns:
        GitResult with operation details
    """
    git_util = create_git_utility(module_name, branch)
    return git_util.push_files(file_paths, commit_message)


def sync_module(module_name: str, branch: Optional[str] = None) -> GitResult:
    """
    Convenience function to sync latest changes for a module
    
    Args:
        module_name: Module name (web, api, s3, ftp)
        branch: Target branch (optional)
        
    Returns:
        GitResult with operation details
    """
    git_util = create_git_utility(module_name, branch)
    return git_util.sync_latest()


def get_module_status(module_name: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get module repository status
    
    Args:
        module_name: Module name (web, api, s3, ftp)
        branch: Target branch (optional)
        
    Returns:
        Dictionary with repository status
    """
    git_util = create_git_utility(module_name, branch)
    return git_util.get_repo_status()
