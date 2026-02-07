"""
Code Processors for DevMind Ingestion System.
Parse code files into logical sections (functions, classes).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import logging

from devmind.ingestion.file_scanner import FileInfo

logger = logging.getLogger(__name__)


@dataclass
class CodeSection:
    """A logical section of code (function, class, method)."""
    content: str
    metadata: dict
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    language: str = ""
    section_type: str = "code"  # function, class, method, module
    
    def __repr__(self) -> str:
        name = self.function_name or self.class_name or "module"
        return f"CodeSection({self.language}.{name}:{self.start_line}-{self.end_line})"


class BaseProcessor(ABC):
    """Abstract base class for all file processors."""
    
    @abstractmethod
    def can_process(self, file_info: FileInfo) -> bool:
        """
        Check if this processor can handle the given file.
        
        Args:
            file_info: File information
            
        Returns:
            True if processor can handle this file
        """
        pass
    
    @abstractmethod
    def process(self, file_info: FileInfo) -> List[CodeSection]:
        """
        Process file into sections.
        
        Args:
            file_info: File to process
            
        Returns:
            List of code sections
        """
        pass


class CodeProcessor(BaseProcessor):
    """
    Abstract base class for language-specific code processors.
    
    Subclasses should implement language-specific parsing logic.
    """
    
    def __init__(self, language: str):
        """
        Initialize processor.
        
        Args:
            language: Programming language name
        """
        self.language = language
        logger.info(f"Initialized {self.language} processor")
    
    def can_process(self, file_info: FileInfo) -> bool:
        """Check if file language matches this processor."""
        return file_info.language == self.language
    
    @abstractmethod
    def process(self, file_info: FileInfo) -> List[CodeSection]:
        """
        Process code file into sections.
        
        TODO: Implement in subclasses
        """
        pass
    
    @abstractmethod
    def extract_functions(self, content: str) -> List[CodeSection]:
        """
        Extract all functions from code.
        
        Args:
            content: Source code content
            
        Returns:
            List of function sections
            
        TODO: Implement AST parsing or regex-based extraction
        """
        pass
    
    @abstractmethod
    def extract_classes(self, content: str) -> List[CodeSection]:
        """
        Extract all classes from code.
        
        Args:
            content: Source code content
            
        Returns:
            List of class sections
            
        TODO: Implement class extraction
        """
        pass
    
    def read_file(self, path: Path) -> str:
        """
        Read file content.
        
        Args:
            path: File path
            
        Returns:
            File content as string
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode {path} as UTF-8, trying latin-1")
            with open(path, "r", encoding="latin-1") as f:
                return f.read()


class PythonProcessor(CodeProcessor):
    """
    Processes Python code files using AST.
    
    Extracts:
    - Functions (with decorators, docstrings)
    - Classes (with methods)
    - Module-level code
    """
    
    def __init__(self):
        super().__init__(language="python")
    
    def process(self, file_info: FileInfo) -> List[CodeSection]:
        """
        Process Python file using AST.
        
        Returns:
            List of CodeSection objects
        """
        logger.info(f"Processing Python file: {file_info.path}")
        
        try:
            content = self.read_file(file_info.path)
            
            # Parse into AST
            import ast
            tree = ast.parse(content, filename=str(file_info.path))
            
            sections = []
            lines = content.split('\n')
            
            # Extract top-level functions and classes
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    section = self._extract_function_node(node, lines, content, file_info.path)
                    sections.append(section)
                    
                elif isinstance(node, ast.ClassDef):
                    # Extract the class itself
                    class_section = self._extract_class_node(node, lines, content, file_info.path)
                    sections.append(class_section)
                    
                    # Extract methods within the class
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_section = self._extract_function_node(
                                item, lines, content, file_info.path, 
                                class_name=node.name
                            )
                            sections.append(method_section)
            
            logger.info(f"Extracted {len(sections)} sections from {file_info.path}")
            return sections
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_info.path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing {file_info.path}: {e}")
            return []
    
    def _extract_function_node(
        self, 
        node, 
        lines: List[str], 
        content: str,
        file_path,
        class_name: Optional[str] = None
    ) -> CodeSection:
        """Extract a function/method node into CodeSection."""
        import ast
        
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        # Get source code for this function
        function_lines = lines[start_line-1:end_line]
        function_content = '\n'.join(function_lines)
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        # Get decorator names
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
        
        section_type = "method" if class_name else "function"
        
        return CodeSection(
            content=function_content,
            metadata={
                "file_path": str(file_path),
                "docstring": docstring or "",
                "decorators": decorators,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "arguments": [arg.arg for arg in node.args.args],
            },
            function_name=node.name,
            class_name=class_name,
            start_line=start_line,
            end_line=end_line,
            language="python",
            section_type=section_type
        )
    
    def _extract_class_node(self, node, lines: List[str], content: str, file_path) -> CodeSection:
        """Extract a class node into CodeSection."""
        import ast
        
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        # Get source code for this class
        class_lines = lines[start_line-1:end_line]
        class_content = '\n'.join(class_lines)
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        # Get base classes
        bases = [self._get_name(base) for base in node.bases]
        
        return CodeSection(
            content=class_content,
            metadata={
                "file_path": str(file_path),
                "docstring": docstring or "",
                "bases": bases,
                "decorators": [self._get_decorator_name(dec) for dec in node.decorator_list],
            },
            class_name=node.name,
            start_line=start_line,
            end_line=end_line,
            language="python",
            section_type="class"
        )
    
    def _get_decorator_name(self, decorator) -> str:
        """Get decorator name from AST node."""
        import ast
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_name(decorator.value)}.{decorator.attr}"
        return str(decorator)
    
    def _get_name(self, node) -> str:
        """Get name from AST node."""
        import ast
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def extract_functions(self, content: str) -> List[CodeSection]:
        """
        Extract functions from Python code.
        """
        import ast
        tree = ast.parse(content)
        sections = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                section = self._extract_function_node(node, lines, content, Path(""))
                sections.append(section)
        
        return sections
    
    def extract_classes(self, content: str) -> List[CodeSection]:
        """
        Extract classes from Python code.
        """
        import ast
        tree = ast.parse(content)
        sections = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                section = self._extract_class_node(node, lines, content, Path(""))
                sections.append(section)
        
        return sections


class JavaScriptProcessor(CodeProcessor):
    """
    Processes JavaScript code files.
    
    Extracts:
    - Functions (regular, arrow, async)
    - Classes
    - Exports
    
    TODO: Consider using tree-sitter for robust parsing
    """
    
    def __init__(self):
        super().__init__(language="javascript")
    
    def process(self, file_info: FileInfo) -> List[CodeSection]:
        """
        Process JavaScript file.
        
        TODO: Implement using regex or tree-sitter
        """
        raise NotImplementedError("JavaScriptProcessor.process() not yet implemented")
    
    def extract_functions(self, content: str) -> List[CodeSection]:
        """Extract JS functions."""
        raise NotImplementedError()
    
    def extract_classes(self, content: str) -> List[CodeSection]:
        """Extract JS classes."""
        raise NotImplementedError()


class TypeScriptProcessor(CodeProcessor):
    """
    Processes TypeScript code files.
    
    Similar to JavaScript but also handles:
    - Type definitions
    - Interfaces
    - Decorators
    """
    
    def __init__(self):
        super().__init__(language="typescript")
    
    def process(self, file_info: FileInfo) -> List[CodeSection]:
        """Process TypeScript file."""
        raise NotImplementedError("TypeScriptProcessor.process() not yet implemented")
    
    def extract_functions(self, content: str) -> List[CodeSection]:
        raise NotImplementedError()
    
    def extract_classes(self, content: str) -> List[CodeSection]:
        raise NotImplementedError()


class GoProcessor(CodeProcessor):
    """Processes Go code files."""
    
    def __init__(self):
        super().__init__(language="go")
    
    def process(self, file_info: FileInfo) -> List[CodeSection]:
        """Process Go file."""
        raise NotImplementedError("GoProcessor.process() not yet implemented")
    
    def extract_functions(self, content: str) -> List[CodeSection]:
        raise NotImplementedError()
    
    def extract_classes(self, content: str) -> List[CodeSection]:
        # Go doesn't have classes, but has structs and methods
        raise NotImplementedError()


class ProcessorFactory:
    """
    Factory for creating appropriate processors.
    
    Maps file types/languages to processor instances.
    """
    
    _processors: dict = {}
    
    @classmethod
    def register(cls, language: str, processor: CodeProcessor):
        """Register a processor for a language."""
        cls._processors[language] = processor
        logger.info(f"Registered processor for {language}")
    
    @classmethod
    def get_processor(cls, file_info: FileInfo) -> Optional[BaseProcessor]:
        """
        Get appropriate processor for a file.
        
        Args:
            file_info: File information
            
        Returns:
            Processor instance or None
        """
        if file_info.language and file_info.language in cls._processors:
            return cls._processors[file_info.language]
        return None
    
    @classmethod
    def initialize_defaults(cls):
        """Initialize default processors."""
        cls.register("python", PythonProcessor())
        cls.register("javascript", JavaScriptProcessor())
        cls.register("typescript", TypeScriptProcessor())
        cls.register("go", GoProcessor())
        logger.info("Initialized default processors")


# Initialize default processors
ProcessorFactory.initialize_defaults()
