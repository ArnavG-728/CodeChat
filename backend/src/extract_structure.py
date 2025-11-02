import ast
from typing import List, Dict, Any
from extract_procedural import ProceduralExtractor, PROCEDURAL_EXTENSIONS, get_language_from_extension
from logger_config import setup_logger

# Setup logger
logger = setup_logger(__name__)


class StructuredExtractor(ast.NodeVisitor):
    def __init__(self, file_name: str, source_code: str):
        self.file_name = file_name
        self.source_code = source_code
        self.current_class = None
        self.current_function = None

    def extract(self) -> Dict[str, Any]:
        tree = ast.parse(self.source_code, filename=self.file_name)
        children = self.visit(tree)
        children = [c for c in children if isinstance(c, dict) and all(k in c for k in ["type", "name", "lineno", "code"])]

        # Ensure only valid structured children are returned
        if not isinstance(children, list):
            children = []

        return {
            "file": self.file_name,
            "code": self.source_code,
            "children": children
        }

    def visit_Module(self, node):
        return [child for child in (self.visit(c) for c in node.body) if child is not None]

    def visit_ClassDef(self, node):
        prev_class = self.current_class
        self.current_class = node.name

        class_node = {
            "type": "class",
            "name": node.name,
            "lineno": node.lineno,
            "code": ast.get_source_segment(self.source_code, node),
            "parameters": [],
            "parent": self.file_name,
            "children": []
        }

        class_node["children"] = [
            c for c in (self.visit(child) for child in node.body)
            if c is not None
        ]

        self.current_class = prev_class  # Restore previous context
        return class_node

    def visit_FunctionDef(self, node):
        return self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_function(node, is_async=True)

    def _visit_function(self, node, is_async: bool):
        prev_function = self.current_function
        self.current_function = node.name

        parent = self.current_class if self.current_class else self.file_name

        func_node = {
            "type": "async_function" if is_async else "function",
            "name": node.name,
            "lineno": node.lineno,
            "code": ast.get_source_segment(self.source_code, node),
            "parameters": [arg.arg for arg in node.args.args],
            "parent": parent,
            "children": []
        }

        func_node["children"] = [
            c for c in (self.visit(child) for child in node.body)
            if c is not None
        ]

        self.current_function = prev_function
        return func_node

    def visit_Call(self, node):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        parent = self.current_function if self.current_function else "module"

        return {
            "type": "call",
            "name": func_name,
            "lineno": node.lineno,
            "code": ast.get_source_segment(self.source_code, node),
            "parent": parent
        }

    def generic_visit(self, node):
        return None


OOP_FILE_EXTENSIONS = (
    ".java", ".cpp", ".cs", ".py", ".rb", ".swift", ".kt", ".scala", ".go",
    ".php", ".m", ".h", ".hpp", ".fs", ".vb", ".vbs", ".cls", ".dart",
    ".groovy", ".jl", ".rs", ".nim"
)


def extract_codebase_structure(documents: List[Any]) -> List[Dict[str, Any]]:
    results = []

    for doc in documents:
        file_name = doc.metadata.get("source", "unknown_file.py")
        source_code = doc.page_content
        
        try:
            # Check if it's a procedural language
            if any(file_name.endswith(ext) for ext in PROCEDURAL_EXTENSIONS.keys()):
                language = get_language_from_extension(file_name)
                print(f"🔧 Processing procedural file ({language}): {file_name}")
                extractor = ProceduralExtractor(file_name, source_code, language)
                result = extractor.extract()
                results.append(result)
            # Check if it's an OOP language (Python-based)
            elif file_name.endswith(OOP_FILE_EXTENSIONS):
                print(f"🐍 Processing OOP file: {file_name}")
                extractor = StructuredExtractor(file_name, source_code)
                result = extractor.extract()
                results.append(result)
            else:
                print(f"⚠️ Skipping unsupported file type: {file_name}")
                
        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}")

    return results
