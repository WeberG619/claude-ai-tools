"""Python-specific code parser using AST."""

import ast
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from .base import CodeParser
from ..core.models import CodeEntityInfo

logger = logging.getLogger(__name__)


class PythonParser(CodeParser):
    """Parser for Python code using the built-in AST module."""
    
    def parse_file(self, file_path: Path) -> List[CodeEntityInfo]:
        """Parse a Python file and extract code entities."""
        entities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            
            # Extract entities
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    entity = self._extract_function(node, file_path, content)
                    if entity:
                        entities.append(entity)
                elif isinstance(node, ast.ClassDef):
                    entity = self._extract_class(node, file_path, content)
                    if entity:
                        entities.append(entity)
                        
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            
        return entities
        
    def get_dependencies(self, file_path: Path) -> List[str]:
        """Extract import statements from a Python file."""
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)
                        
        except Exception as e:
            logger.error(f"Error extracting dependencies from {file_path}: {e}")
            
        return list(set(dependencies))
        
    def _extract_function(self, node: ast.FunctionDef, file_path: Path, content: str) -> Optional[CodeEntityInfo]:
        """Extract function information from AST node."""
        try:
            # Get function signature
            args = []
            for arg in node.args.args:
                arg_name = arg.arg
                if arg.annotation:
                    arg_type = ast.unparse(arg.annotation)
                    args.append(f"{arg_name}: {arg_type}")
                else:
                    args.append(arg_name)
                    
            signature = f"def {node.name}({', '.join(args)})"
            if node.returns:
                signature += f" -> {ast.unparse(node.returns)}"
                
            # Get docstring
            docstring = ast.get_docstring(node)
            
            # Get dependencies within function
            func_deps = self._extract_function_dependencies(node)
            
            return CodeEntityInfo(
                name=node.name,
                entity_type="function",
                file_path=str(file_path),
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=signature,
                docstring=docstring,
                dependencies=func_deps
            )
        except Exception as e:
            logger.debug(f"Error extracting function {node.name}: {e}")
            return None
            
    def _extract_class(self, node: ast.ClassDef, file_path: Path, content: str) -> Optional[CodeEntityInfo]:
        """Extract class information from AST node."""
        try:
            # Get base classes
            bases = [ast.unparse(base) for base in node.bases]
            signature = f"class {node.name}"
            if bases:
                signature += f"({', '.join(bases)})"
                
            # Get docstring
            docstring = ast.get_docstring(node)
            
            # Get methods
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
                    
            return CodeEntityInfo(
                name=node.name,
                entity_type="class",
                file_path=str(file_path),
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=signature,
                docstring=docstring,
                dependencies=methods  # Store methods as dependencies
            )
        except Exception as e:
            logger.debug(f"Error extracting class {node.name}: {e}")
            return None
            
    def _extract_function_dependencies(self, node: ast.FunctionDef) -> List[str]:
        """Extract function/method calls within a function."""
        deps = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    deps.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # Handle method calls like obj.method()
                    if isinstance(child.func.value, ast.Name):
                        deps.add(f"{child.func.value.id}.{child.func.attr}")
                        
        return list(deps)