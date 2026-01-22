"""GitIgnore parsing and handling module.

Reads and parses .gitignore files to determine which files and folders
should be skipped during codebase analysis.
"""
import os
from typing import List, Tuple
from lum.config import *


def gitignore_exists(root: str) -> bool:
    """Check if a .gitignore file exists in the specified directory.
    
    Args:
        root: Root directory to check
        
    Returns:
        True if .gitignore exists, False otherwise
    """
    path = os.path.join(root, ".gitignore")
    return os.path.exists(path = path)


def gitignore_read(root: str) -> Tuple[List[str], List[str]]:
    """Parse .gitignore file and extract files and folders to skip.
    
    Ignores comments (lines starting with #) and negation patterns (lines starting with !).
    Separates patterns ending with / as folders, others as files.
    
    Args:
        root: Root directory containing .gitignore
        
    Returns:
        Tuple of (skipped_files, skipped_folders)
    """
    path = os.path.join(root, ".gitignore")
    skipped_files, skipped_folders = [], []

    try:
        with open(path, "r", encoding="utf-8") as d:
            lines = d.readlines()

    except Exception as e:
        print(f"Error reading .gitignore: {e}.")
        return skipped_files, skipped_folders
    
    for line_raw in lines:
        line = line_raw.strip()

        # Skip non-readable or useless lines
        if not line:
            continue
        if line.startswith("#"):  # Comments
            continue
        if line.startswith("!"):  # Negation patterns
            continue

        if line.endswith("/") or line.endswith("\\"):
            folder_name = line.rstrip('/\\')
            
            if folder_name and folder_name != "." and folder_name != "..":
                skipped_folders.append(folder_name)

        else:
            if line != "." and line != "..":
                 skipped_files.append(line)
    
    return skipped_files, skipped_folders


def gitignore_skipping() -> Tuple[List[str], List[str]]:
    """Merge .gitignore patterns with configuration skip lists.
    
    Combines files and folders from both .gitignore and user configuration,
    removing duplicates.
    
    Returns:
        Tuple of (merged_skipped_files, merged_skipped_folders)
    """
    # Get skipped files and folders from configuration
    skipped_files, skipped_folders = get_skipped_files(), get_skipped_folders()
    # Parse .gitignore
    skipped_files_git, skipped_folders_git = gitignore_read("")

    # Merge and deduplicate
    skipped_files = list(set(skipped_files + skipped_files_git))
    skipped_folders = list(set(skipped_folders + skipped_folders_git))

    return skipped_files, skipped_folders