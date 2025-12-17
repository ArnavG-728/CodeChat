"""
Automatic language detection for code files
"""
import os
from pathlib import Path
from typing import Dict, List
import logging
from .logger_config import setup_logger

# Setup logger
logger = setup_logger(__name__)

# Language detection patterns
LANGUAGE_PATTERNS = {
    # Object-Oriented Languages
    "python": [".py", ".pyw", ".pyx"],
    "javascript": [".js", ".jsx", ".mjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "csharp": [".cs"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
    "c": [".c", ".h"],
    "ruby": [".rb"],
    "swift": [".swift"],
    "kotlin": [".kt", ".kts"],
    "scala": [".scala"],
    "php": [".php"],
    "go": [".go"],
    "rust": [".rs"],
    "dart": [".dart"],
    "perl": [".pl", ".pm"],
    "lua": [".lua"],
    "r": [".r", ".R"],
    "julia": [".jl"],
    "groovy": [".groovy"],
    "elixir": [".ex", ".exs"],
    "clojure": [".clj", ".cljs"],
    "haskell": [".hs"],
    "ocaml": [".ml", ".mli"],
    "fsharp": [".fs", ".fsx"],
    "visualbasic": [".vb"],
    
    # Web Technologies
    "html": [".html", ".htm"],
    "css": [".css", ".scss", ".sass", ".less"],
    "vue": [".vue"],
    "svelte": [".svelte"],
    
    # Configuration & Data
    "json": [".json"],
    "yaml": [".yaml", ".yml"],
    "xml": [".xml"],
    "toml": [".toml"],
    "ini": [".ini"],
    "properties": [".properties"],
    
    # Shell & Scripts
    "shell": [".sh", ".bash", ".zsh", ".fish"],
    "powershell": [".ps1", ".psm1"],
    "batch": [".bat", ".cmd"],
    
    # Database
    "sql": [".sql"],
    
    # Documentation
    "markdown": [".md", ".markdown"],
    "rst": [".rst"],
    "tex": [".tex"],
}

# Language paradigms
OOP_LANGUAGES = {
    "python", "javascript", "typescript", "java", "csharp", "cpp",
    "ruby", "swift", "kotlin", "scala", "php", "dart", "groovy"
}

PROCEDURAL_LANGUAGES = {
    "c", "go", "rust"
}

FUNCTIONAL_LANGUAGES = {
    "haskell", "ocaml", "fsharp", "clojure", "elixir"
}

SCRIPTING_LANGUAGES = {
    "python", "javascript", "ruby", "php", "perl", "lua", "shell", "powershell"
}


def detect_language(filename: str) -> str:
    """Detect programming language from filename"""
    ext = Path(filename).suffix.lower()
    
    for lang, extensions in LANGUAGE_PATTERNS.items():
        if ext in extensions:
            return lang
    
    return "unknown"


def get_language_paradigm(language: str) -> str:
    """Get the paradigm of a language (OOP, Procedural, Functional)"""
    if language in OOP_LANGUAGES:
        return "oop"
    elif language in PROCEDURAL_LANGUAGES:
        return "procedural"
    elif language in FUNCTIONAL_LANGUAGES:
        return "functional"
    else:
        return "other"


def analyze_repository(files: List[str]) -> Dict[str, any]:
    """Analyze languages in a repository"""
    language_counts = {}
    total_files = 0
    
    for filename in files:
        lang = detect_language(filename)
        if lang != "unknown":
            language_counts[lang] = language_counts.get(lang, 0) + 1
            total_files += 1
    
    # Calculate percentages
    language_percentages = {
        lang: (count / total_files * 100) if total_files > 0 else 0
        for lang, count in language_counts.items()
    }
    
    # Sort by count
    sorted_languages = sorted(
        language_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Get primary language (most common)
    primary_language = sorted_languages[0][0] if sorted_languages else "unknown"
    
    # Detect if multi-language project
    is_multi_language = len(language_counts) > 1
    
    # Detect project type
    project_types = []
    if any(lang in language_counts for lang in ["javascript", "typescript", "html", "css"]):
        project_types.append("frontend")
    if any(lang in language_counts for lang in ["python", "java", "go", "rust", "php"]):
        project_types.append("backend")
    if any(lang in language_counts for lang in ["swift", "kotlin", "dart"]):
        project_types.append("mobile")
    
    return {
        "total_files": total_files,
        "languages": language_counts,
        "language_percentages": language_percentages,
        "primary_language": primary_language,
        "is_multi_language": is_multi_language,
        "project_types": project_types,
        "supported_languages": list(language_counts.keys())
    }


def is_supported_for_parsing(language: str) -> bool:
    """Check if language is supported for structure parsing"""
    supported = {
        "python", "javascript", "typescript", "java", "csharp",
        "cpp", "c", "go", "rust", "ruby", "php", "swift", "kotlin"
    }
    return language in supported


def get_parser_type(language: str) -> str:
    """Get the parser type for a language"""
    if language in OOP_LANGUAGES:
        return "oop"
    elif language in PROCEDURAL_LANGUAGES:
        return "procedural"
    else:
        return "generic"
