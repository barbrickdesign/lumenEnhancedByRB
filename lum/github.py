"""GitHub repository handling module.

Provides functionality to validate GitHub repository URLs, clone repositories,
and manage temporary repository downloads for analysis.
"""
import os
import shutil
import sys
import stat
import subprocess
from typing import Tuple, Optional
import requests
from lum.config import *


def make_github_api_link(repo_link: str = None) -> Tuple[Optional[str], Optional[str]]:
    """Convert GitHub repository URL to API link and clone link.
    
    Handles multiple GitHub URL formats:
    - https://github.com/user/repo
    - github.com/user/repo
    - https://www.github.com/user/repo
    - URLs with or without .git extension
    
    Args:
        repo_link: GitHub repository URL
        
    Returns:
        Tuple of (api_link, clone_link) or (False, False) if invalid
    """
    if repo_link is None:
        return False, False
    
    if repo_link.startswith("http://"):
        print("Use a secured link please (https:// and not http://)")
        return False, False

    clone_link = repo_link if repo_link.endswith(".git") else repo_link + ".git"
    api_proc_link = repo_link[:-4] if repo_link.endswith(".git") else repo_link

    for link_prefix in ["https://github.com/", "https://www.github.com/", "github.com/", "www.github.com/"]:
        if api_proc_link.startswith(link_prefix):
            rest = api_proc_link.split(link_prefix, 1)[-1]

            if '/' in rest and not rest.startswith('/') and not rest.endswith('/'):
                 return "https://api.github.com/repos/" + rest, clone_link

    print("Link does not appear to be a standard GitHub repository link.")
    return False, False


def check_repo(repo_link: str = None) -> bool:
    """Check if a GitHub repository exists and is accessible.
    
    Args:
        repo_link: GitHub repository URL
        
    Returns:
        True if repository exists and is public, False otherwise
    """
    api_link, _ = make_github_api_link(repo_link=repo_link)
    if api_link:
        try:
            headers = {'User-Agent': 'LUM-Python-Script'}
            response = requests.get(url=api_link, timeout=10, headers=headers)
            return response.status_code == 200
        
        except requests.exceptions.RequestException as e:
            print(f"ERROR checking repository API: {e}")

    return False


def check_git() -> bool:
    """Check if Git is installed on the system.
    
    Provides platform-specific installation instructions if Git is not found.
    
    Returns:
        True if Git is installed, False otherwise
    """
    if shutil.which('git') is None:
        print("Git is not installed. Please install it manually.")

        if sys.platform.startswith('win'):
            print("On Windows: https://git-scm.com/download/win")
        elif sys.platform.startswith('linux'):
            print("On Linux: Use package manager (e.g., 'sudo apt install git' or 'sudo yum install git').")
        elif sys.platform.startswith('darwin'):
            print("On macOS: https://git-scm.com/download/mac or 'brew install git'.")

        return False
    return True


def remove_readonly(func, path, excinfo):
    """Callback for removing read-only files during directory deletion.
    
    Handles permission errors when deleting Git repositories on Windows.
    
    Args:
        func: Function that raised the error
        path: Path to the problematic file
        excinfo: Exception information tuple
        
    Raises:
        Original exception if not a permission error
    """
    exc_value = excinfo[1]
    if isinstance(exc_value, PermissionError) or (hasattr(exc_value, 'winerror') and exc_value.winerror == 5):
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            func(path)
        except Exception as e:
            raise exc_value from e
    else:
        raise exc_value


def download_repo(repo_link: str = None) -> str:
    """Clone a GitHub repository to the Lumen config directory.
    
    Downloads repository to ~/.lum/{repo_name}. Removes existing directory
    if it already exists.
    
    Args:
        repo_link: GitHub repository URL
        
    Returns:
        Path to the cloned repository
        
    Raises:
        SystemExit: If repo_link is invalid or clone fails
        subprocess.CalledProcessError: If git clone command fails
    """
    if not repo_link:
        print("Repository link is required.")
        sys.exit(1)

    _, clone_link = make_github_api_link(repo_link=repo_link)
    if not clone_link:
        print("Invalid or unsupported GitHub repository link format.")
        sys.exit(1)

    # Navigate to Lumen config directory
    lum_repo = get_config_directory()
    repo_name = clone_link.split("/")[-1].replace(".git", "")

    if not repo_name:
        repo_name = clone_link.split("/")[-2]  # Handle trailing slash case
    lum_repo_name = os.path.join(lum_repo, repo_name)

    # Remove existing folder if it exists
    if os.path.exists(lum_repo_name):
        print(f"Removing existing directory: {lum_repo_name}")
        remove_repo(lum_repo_name)

    # Clone repository using git
    command = ["git", "clone", clone_link, lum_repo_name]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return lum_repo_name

    except subprocess.CalledProcessError as e:
        print(f"Git clone failed. Error: {e.stderr}")

        if os.path.exists(lum_repo_name):
            print("Attempting cleanup of partially cloned folder...")
            remove_repo(lum_repo_name)

        raise


def remove_repo(repo_root: str = None) -> None:
    """Remove a cloned repository directory.
    
    Handles read-only file permissions that may prevent deletion.
    
    Args:
        repo_root: Path to the repository directory to remove
    """
    if not repo_root or not isinstance(repo_root, str) or not os.path.isdir(repo_root):
        print(f"Path not found or not a directory: {repo_root}")
        return

    try:
        shutil.rmtree(repo_root, onerror=remove_readonly)

    except Exception as e:
        print(f"ERROR deleting folder {repo_root}: {e}")