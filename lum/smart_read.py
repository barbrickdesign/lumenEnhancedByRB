"""Smart file reading module with encoding detection and token counting."""
from typing import List, Dict, Tuple, Iterator, IO
from lum.config import *
from lum.gitignore import *
import json
import chardet
import tiktoken


def get_files_parameters() -> Dict[str, List[str]]:
    """Get file parameters from configuration.
    
    Returns:
        Dictionary containing allowed file types and files to skip
    """
    base_parameters = {
        "allowed_files": get_allowed_file_types(),
        "non_allowed_read": get_skipped_files()
    }
    return base_parameters


def chunk_read(file_path: IO, chunk_size: int = 1024) -> Iterator[str]:
    """Read file in chunks for memory efficiency.
    
    Args:
        file_path: File object to read from
        chunk_size: Size of each chunk in bytes (default: 1024)
        
    Yields:
        Chunks of file data
    """
    while True:
        data = file_path.read(chunk_size)
        if not data:
            break
        yield data


def read_ipynb(file_path: str, cell_seperator: str = None) -> str:
    """Read and parse Jupyter Notebook files (.ipynb).
    
    Args:
        file_path: Path to the .ipynb file
        cell_seperator: Optional custom separator between cells
        
    Returns:
        String containing all cell contents from the notebook
        
    Raises:
        json.JSONDecodeError: If the notebook file is not valid JSON
        FileNotFoundError: If the file doesn't exist
    """
    output_lines = []
    with open(file_path, 'r', encoding='utf-8') as f:  # ipynb files are UTF-8
        data = json.load(f)
    
    for cell in data.get('cells', []):
        cell_type = cell.get('cell_type')
        if cell_type in ['markdown', 'code']:
            output_lines.append("--- CELL ---\n" if not cell_seperator else cell_seperator)
            source_content = cell.get('source', [])
            output_lines.append("".join(source_content) + "\n")
            
    return "\n".join(output_lines)


def detect_encoding(file_path: str) -> str:
    """Automatically detect file encoding using chardet.
    
    Reads only the first 1KB of the file for performance.
    Falls back to UTF-8 if encoding detection fails or returns ASCII.
    
    Args:
        file_path: Path to the file to detect encoding for
        
    Returns:
        Detected encoding name (e.g., 'utf-8', 'latin-1')
        
    Note:
        Can be used as a separate utility function
    """
    with open(file_path, 'rb') as f:
        sample = f.read(1 * 1024)  # Read first 1KB for performance
    
    result = chardet.detect(sample)
    encoding = result['encoding']
        
    return 'utf-8' if encoding is None or encoding.lower() == 'ascii' else encoding


def rank_tokens(files_root: Dict[str, str], top: int, allowed_files: List[str] = None, skipped_files: List[str] = None) -> None:
    """Calculate and display token counts for files, showing top consumers.
    
    Used when calling -l or --leaderboard parameter. Shows by default the top 20
    most token-consuming files, with tokens calculated via tiktoken module.
    
    Args:
        files_root: Dictionary mapping file names to file paths
        top: Number of top files to display
        allowed_files: List of allowed file extensions
        skipped_files: List of files to skip
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    token_counts = []

    print("\nCalculating token counts...")

    for file_name, file_path in files_root.items():
        content = read_file(file_path, allowed_files=allowed_files, skipped_files=skipped_files)

        try:
            tokens = encoding.encode(content)
            token_count = len(tokens)
            token_counts.append((token_count, file_name))
        except Exception as e:
            print(f"Error encoding file {file_name}: {e}")

    token_counts.sort(key=lambda item: item[0], reverse=True)

    print(f"\nTop {min(top, len(token_counts))} Most Token-Consuming Files:")

    if not token_counts:
        print("No readable files found to rank.")
    else:
        for i, (count, name) in enumerate(token_counts[:top]):
            print(f"{i + 1}. {name}: {count} tokens")


def read_file(file_path: str, allowed_files: List[str] = None, skipped_files: List[str] = None) -> str:
    """Read and process a file with intelligent encoding detection.
    
    Supports multiple file types including Jupyter notebooks (.ipynb).
    Attempts UTF-8 first for performance, falls back to encoding detection if needed.
    
    Args:
        file_path: Path to the file to read
        allowed_files: List of allowed file extensions
        skipped_files: List of file patterns to skip
        
    Returns:
        File contents as a string, or a status message if file cannot be read
        
    Note:
        Special handling for .ipynb files to extract cell contents
    """
    if not allowed_files:
        allowed_files = get_files_parameters()["allowed_files"]
    
    if not skipped_files:
        skipped_files = get_files_parameters()["non_allowed_read"]

    if not any(file_path.endswith(allowed_file) for allowed_file in allowed_files):
        return "--- NON READABLE FILE ---"
    
    content = ""
    LARGE_OUTPUT = "--- FILE TOO LARGE / NO NEED TO READ ---"
    ERROR_OUTPUT = "--- ERROR READING FILE ---"
    EMPNR_OUTPUT = "--- EMPTY / NON READABLE FILE ---"

    # Handle Jupyter notebooks
    if file_path.endswith(".ipynb"):
        try:
            content += read_ipynb(file_path = file_path)
            return content if content else EMPNR_OUTPUT

        except Exception as e:
            print(f"Error while reading the ipynb file: {file_path}. Skipping file. Error: {e}")
            return ERROR_OUTPUT

    # Skip large files or files that don't need to be read
    if any(file_path.endswith(dont_read) for dont_read in skipped_files):
        return LARGE_OUTPUT
    
    # Handle all other allowed files
    try:
        with open(file_path, "r", encoding='utf-8') as file:  # Try UTF-8 first for performance
            for chunk in chunk_read(file):
                content += chunk

    except UnicodeDecodeError:  # Fallback to encoding detection (rare case)
        try:
            detected_encoding = detect_encoding(file_path=file_path)
            with open(file_path, "r", encoding=detected_encoding) as file:
                for chunk in chunk_read(file):
                    content += chunk

        except Exception as e:
            print(f"Error: Unexpected error while reading {file_path} with encoding detection. "
                  f"Please report this issue on GitHub. Skipping file. Error: {e}")
            return ERROR_OUTPUT
        
    except Exception as e:
        print(f"Error: Unexpected error while reading {file_path}. Skipping file. Error: {e}")
        return ERROR_OUTPUT
    
    return content if content else EMPNR_OUTPUT