"""Project structure visualization module.

Creates a hierarchical dictionary representation of the project directory
structure for display in prompts.
"""
import os
from lum.gitignore import *
from typing import List, Dict


def get_project_structure(root_path: str, skipped_folders: List[str]) -> Dict[str, Dict]:
    """Generate a nested dictionary representing the project directory structure.
    
    Respects .gitignore rules and skips hidden folders (starting with '.').
    Folders are marked with a trailing '/' in the dictionary keys.
    
    Args:
        root_path: Root directory to analyze
        skipped_folders: List of folder names/patterns to skip
        
    Returns:
        Nested dictionary with directory structure
    """
    root_path_name = "".join(root_path.split(os.sep)[-1]) + "/"
    structure = {root_path_name: {}}

    if gitignore_exists(""):
        _, skipped_folders = gitignore_skipping()
    
    for root, _, files in os.walk(root_path, topdown=True):
        # Skip folders starting with "."
        relative_dir = os.path.relpath(root, root_path)
        if any(part.startswith('.') for part in relative_dir.split(os.sep) if part != '.'):
            _[:] = []
            continue

        should_skip = False
        for folder_name in skipped_folders:
            # If starts with "*", skip anything that ends with the folder name
            if folder_name.startswith("*"):
                if root.endswith(folder_name[1:]):
                    _[:] = []
                    structure[root_path_name][f"{''.join(root.split(os.sep)[-1])}/"] = {}
                    should_skip = True
                    break

            else:
                element = root.split(os.sep)[-1]
                if element == folder_name:
                    _[:] = []
                    structure[root_path_name][f"{''.join(root.split(os.sep)[-1])}/"] = {}
                    should_skip = True
                    break

        if should_skip:
            continue


        base = structure[root_path_name]
        level = len(root.split(os.sep)) - len(root_path.split(os.sep))

        if level == 0:
            if files:
                for file in files:
                    base[file] = {}

        else:
            for x in range(level, 0, -1):
                folder_subname = root.split(os.sep)[-x]
                if x == 1:
                    base[f"{folder_subname}/"] = {}
                    if files:
                        for file in files:
                            base[f"{folder_subname}/"][file] = {}
                            
                else:
                    base = base[folder_subname + "/"]

    return structure