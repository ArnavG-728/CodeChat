import re
from typing import List, Dict, Any
from logger_config import setup_logger

# Setup logger
logger = setup_logger(__name__)

class ProceduralExtractor:
    """Extractor for procedural languages like C, Go, Rust, etc."""
    
    def __init__(self, file_name: str, source_code: str, language: str = "c"):
        self.file_name = file_name
        self.source_code = source_code
        self.language = language.lower()
        
    def extract(self) -> Dict[str, Any]:
        """Extract functions and global variables from procedural code."""
        children = []
        
        if self.language in ["c", "cpp", "c++"]:
            children = self._extract_c_functions()
        elif self.language == "go":
            children = self._extract_go_functions()
        elif self.language == "rust":
            children = self._extract_rust_functions()
        else:
            children = self._extract_generic_functions()
        
        return {
            "file": self.file_name,
            "code": self.source_code,
            "children": children
        }
    
    def _extract_c_functions(self) -> List[Dict[str, Any]]:
        """Extract functions from C/C++ code."""
        functions = []
        lines = self.source_code.split('\n')
        
        # Pattern for C/C++ function definitions
        # Matches: return_type function_name(parameters) {
        func_pattern = re.compile(
            r'^\s*(?:(?:static|inline|extern|virtual|const)\s+)*'  # Optional modifiers
            r'(\w+(?:\s*\*+)?)\s+'  # Return type (with possible pointers)
            r'(\w+)\s*'  # Function name
            r'\(([^)]*)\)\s*'  # Parameters
            r'(?:const\s*)?'  # Optional const after params
            r'\{'  # Opening brace
        )
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.search(line)
            
            if match:
                return_type = match.group(1).strip()
                func_name = match.group(2).strip()
                params_str = match.group(3).strip()
                
                # Extract parameters
                parameters = []
                if params_str and params_str != 'void':
                    param_parts = params_str.split(',')
                    for param in param_parts:
                        param = param.strip()
                        if param:
                            # Extract parameter name (last word)
                            parts = param.split()
                            if parts:
                                parameters.append(parts[-1].strip('*'))
                
                # Find function body end
                brace_count = 1
                start_line = i
                i += 1
                
                while i < len(lines) and brace_count > 0:
                    for char in lines[i]:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                    if brace_count > 0:
                        i += 1
                
                end_line = i
                func_code = '\n'.join(lines[start_line:end_line + 1])
                
                functions.append({
                    "type": "function",
                    "name": func_name,
                    "lineno": start_line + 1,
                    "code": func_code,
                    "parameters": parameters,
                    "parent": self.file_name,
                    "children": []
                })
            
            i += 1
        
        return functions
    
    def _extract_go_functions(self) -> List[Dict[str, Any]]:
        """Extract functions from Go code."""
        functions = []
        lines = self.source_code.split('\n')
        
        # Pattern for Go function definitions
        # Matches: func (receiver) name(params) returns {
        func_pattern = re.compile(
            r'^\s*func\s+'
            r'(?:\([^)]*\)\s+)?'  # Optional receiver
            r'(\w+)\s*'  # Function name
            r'\(([^)]*)\)'  # Parameters
        )
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.search(line)
            
            if match:
                func_name = match.group(1).strip()
                params_str = match.group(2).strip()
                
                # Extract parameters
                parameters = []
                if params_str:
                    param_parts = params_str.split(',')
                    for param in param_parts:
                        param = param.strip()
                        if param:
                            parts = param.split()
                            if parts:
                                parameters.append(parts[0])
                
                # Find function body end
                if '{' in line:
                    brace_count = line.count('{') - line.count('}')
                    start_line = i
                    i += 1
                    
                    while i < len(lines) and brace_count > 0:
                        brace_count += lines[i].count('{') - lines[i].count('}')
                        i += 1
                    
                    end_line = i - 1
                    func_code = '\n'.join(lines[start_line:end_line + 1])
                    
                    functions.append({
                        "type": "function",
                        "name": func_name,
                        "lineno": start_line + 1,
                        "code": func_code,
                        "parameters": parameters,
                        "parent": self.file_name,
                        "children": []
                    })
            
            i += 1
        
        return functions
    
    def _extract_rust_functions(self) -> List[Dict[str, Any]]:
        """Extract functions from Rust code."""
        functions = []
        lines = self.source_code.split('\n')
        
        # Pattern for Rust function definitions
        # Matches: pub fn name(params) -> return_type {
        func_pattern = re.compile(
            r'^\s*(?:pub\s+)?'  # Optional pub
            r'(?:async\s+)?'  # Optional async
            r'(?:unsafe\s+)?'  # Optional unsafe
            r'fn\s+'  # fn keyword
            r'(\w+)\s*'  # Function name
            r'\(([^)]*)\)'  # Parameters
        )
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.search(line)
            
            if match:
                func_name = match.group(1).strip()
                params_str = match.group(2).strip()
                
                # Extract parameters
                parameters = []
                if params_str:
                    param_parts = params_str.split(',')
                    for param in param_parts:
                        param = param.strip()
                        if param and ':' in param:
                            param_name = param.split(':')[0].strip()
                            parameters.append(param_name)
                
                # Find function body end
                if '{' in lines[i:i+3]:  # Check next few lines for opening brace
                    for j in range(i, min(i+3, len(lines))):
                        if '{' in lines[j]:
                            start_line = i
                            brace_count = lines[j].count('{') - lines[j].count('}')
                            i = j + 1
                            
                            while i < len(lines) and brace_count > 0:
                                brace_count += lines[i].count('{') - lines[i].count('}')
                                i += 1
                            
                            end_line = i - 1
                            func_code = '\n'.join(lines[start_line:end_line + 1])
                            
                            functions.append({
                                "type": "function",
                                "name": func_name,
                                "lineno": start_line + 1,
                                "code": func_code,
                                "parameters": parameters,
                                "parent": self.file_name,
                                "children": []
                            })
                            break
            
            i += 1
        
        return functions
    
    def _extract_generic_functions(self) -> List[Dict[str, Any]]:
        """Generic function extractor for other procedural languages."""
        functions = []
        lines = self.source_code.split('\n')
        
        # Generic pattern - looks for function/func/def keyword
        func_pattern = re.compile(
            r'^\s*(?:function|func|def|fn|sub|procedure)\s+'
            r'(\w+)\s*'
            r'\(([^)]*)\)'
        )
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.search(line)
            
            if match:
                func_name = match.group(1).strip()
                params_str = match.group(2).strip()
                
                parameters = [p.strip().split()[0] if p.strip() else '' 
                             for p in params_str.split(',') if p.strip()]
                
                # Try to find function body
                if '{' in line or ':' in line:
                    start_line = i
                    # Estimate 50 lines per function as fallback
                    end_line = min(i + 50, len(lines) - 1)
                    func_code = '\n'.join(lines[start_line:end_line + 1])
                    
                    functions.append({
                        "type": "function",
                        "name": func_name,
                        "lineno": start_line + 1,
                        "code": func_code,
                        "parameters": parameters,
                        "parent": self.file_name,
                        "children": []
                    })
            
            i += 1
        
        return functions


PROCEDURAL_EXTENSIONS = {
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".go": "go",
    ".rs": "rust",
}


def get_language_from_extension(filename: str) -> str:
    """Get language type from file extension."""
    for ext, lang in PROCEDURAL_EXTENSIONS.items():
        if filename.endswith(ext):
            return lang
    return "generic"
