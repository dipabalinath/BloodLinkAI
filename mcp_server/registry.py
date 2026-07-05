"""
Tool Registry for BloodLink MCP Server.
"""

from typing import Callable, Dict, List, Optional, Any
import inspect

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: Optional[str] = None) -> Callable:
        """
        Decorator to register a tool function in the registry.
        If name is not provided, the function's name is used.
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            self._tools[tool_name] = func
            return func
        return decorator

    def register_class(self, cls: type) -> type:
        """
        Decorator to automatically register every public method in a tool class.
        """
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):
                self._tools[name] = method
        return cls

    def register_instance(self, instance: Any) -> None:
        """
        Register every public method of an instantiated object.
        """
        for name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
            if not name.startswith('_'):
                self._tools[name] = method

    def get_tool(self, name: str) -> Callable:
        """
        Retrieve a registered tool by its name.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> List[str]:
        """
        Returns a list of all registered tool names.
        """
        return list(self._tools.keys())

    def tool_description(self, name: str) -> Optional[str]:
        """
        Get the description (docstring) of a registered tool.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        
        tool = self._tools[name]
        return inspect.getdoc(tool)

# Global registry instance to automatically register tools
registry = ToolRegistry()
# Auto-load all MCP tools
import mcp_server.tools
