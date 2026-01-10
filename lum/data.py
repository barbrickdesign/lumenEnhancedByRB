"""Code sanitization module.

Provides functionality to remove comments, detect and redact secrets,
and remove personally identifiable information (PII) from code before
network submission.
"""
import re
import os
import tempfile
from pygments import lex
from pygments.lexers import guess_lexer
from pygments.token import Comment
from pygments.util import ClassNotFound


def _remove_comments(content: str) -> str:
    """Remove comments from code using Pygments lexer.
    
    Automatically detects the programming language and removes
    language-specific comments.
    
    Args:
        content: Source code string
        
    Returns:
        Code with comments removed, or original content if language unknown
    """
    try:
        lexer = guess_lexer(content, stripall=True)
        tokens = lex(content, lexer)
        return "".join(token[1] for token in tokens if not token[0] in Comment)
    except ClassNotFound:
        return content

def _redact_secrets(content: str) -> str:
    """Detect and redact secrets using TruffleHog.
    
    Scans code for API keys, tokens, passwords, and other secrets,
    replacing them with [REDACTED_SECRET].
    
    Args:
        content: Source code string
        
    Returns:
        Code with secrets redacted
        
    Note:
        Uses temporary files for TruffleHog processing
    """
    from trufflehog3.core import scan, load_config, load_rules, DEFAULT_RULES_FILE

    sanitized_content = content
    tmp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8', suffix='.tmp') as tmp_file:
            tmp_file.write(content)
            tmp_filepath = tmp_file.name

        dummy_config_path = os.path.join(tempfile.gettempdir(), ".trufflehog3.yml")
        config = load_config(dummy_config_path)
        rules = load_rules(DEFAULT_RULES_FILE)
        
        found_issues = scan(target=tmp_filepath, config=config, rules=rules, processes=1)

        for issue in found_issues:
            for secret_string in issue.get("stringsFound", []):
                if secret_string:
                    sanitized_content = sanitized_content.replace(secret_string.strip(), "[REDACTED_SECRET]")

    except Exception as e:
        print(f"Warning: An unexpected error occurred during secret scanning with trufflehog3. Error: {e}")
    finally:
        if tmp_filepath and os.path.exists(tmp_filepath):
            os.unlink(tmp_filepath)

    return sanitized_content

def _redact_pii(content: str) -> str:
    """Remove personally identifiable information from code.
    
    Uses scrubadub to detect and replace names, emails, phone numbers,
    and other PII. Also removes IP addresses.
    
    Args:
        content: Source code string
        
    Returns:
        Code with PII redacted
    """
    import scrubadub
    sanitized_content = scrubadub.clean(content, replace_with='placeholder')

    # Additional IP address removal
    sanitized_content = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]', sanitized_content)
    return sanitized_content

def sanitize_code(content: str) -> str:
    """Comprehensive code sanitization pipeline.
    
    Applies three sanitization steps in order:
    1. Remove comments
    2. Redact secrets (API keys, tokens, etc.)
    3. Redact PII (names, emails, etc.)
    
    Also normalizes whitespace by removing excessive blank lines.
    
    Args:
        content: Source code string
        
    Returns:
        Sanitized code ready for network submission
    """
    if not content or not isinstance(content, str):
        return ""

    uncommented_code = _remove_comments(content)
    unsecreted_code = _redact_secrets(uncommented_code)
    sanitized_code = _redact_pii(unsecreted_code)

    # Normalize whitespace
    final_code = re.sub(r'\n\s*\n', '\n\n', sanitized_code).strip()
    return final_code