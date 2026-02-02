"""
Plugin Loader.

Discovers and loads custom agent implementations from Python modules.
"""

import importlib.util
import inspect
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type

from ..agent_api.base import NegotiationAgent


class PluginLoader:
    """
    Loads custom agent plugins from Python files.
    
    Plugins are Python modules that define a class extending NegotiationAgent.
    """
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = Path(plugin_dir)
        self._loaded_plugins: dict[str, Type[NegotiationAgent]] = {}
    
    def discover(self) -> list[str]:
        """
        Discover available plugins in the plugin directory.
        
        Returns list of plugin names (module names).
        """
        plugins = []
        
        if not self.plugin_dir.exists():
            return plugins
        
        for path in self.plugin_dir.glob("*.py"):
            if path.name.startswith("_"):
                continue
            plugins.append(path.stem)
        
        return plugins
    
    def load(self, plugin_name: str) -> Optional[Type[NegotiationAgent]]:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin (without .py extension)
            
        Returns:
            The NegotiationAgent subclass, or None if not found
        """
        # Check cache
        if plugin_name in self._loaded_plugins:
            return self._loaded_plugins[plugin_name]
        
        # Find plugin file
        plugin_path = self.plugin_dir / f"{plugin_name}.py"
        if not plugin_path.exists():
            print(f"Plugin not found: {plugin_path}")
            return None
        
        # Load module
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find NegotiationAgent subclass
            agent_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, NegotiationAgent) and 
                    obj is not NegotiationAgent and
                    obj.__module__ == module.__name__):
                    agent_class = obj
                    break
            
            if agent_class:
                self._loaded_plugins[plugin_name] = agent_class
                return agent_class
            else:
                print(f"No NegotiationAgent subclass found in {plugin_name}")
                return None
                
        except Exception as e:
            print(f"Error loading plugin {plugin_name}: {e}")
            return None
    
    def create_agent(
        self, 
        plugin_name: str, 
        config: Optional[dict] = None
    ) -> Optional[NegotiationAgent]:
        """
        Load a plugin and create an agent instance.
        
        Args:
            plugin_name: Name of the plugin
            config: Optional configuration dict
            
        Returns:
            Agent instance, or None if loading failed
        """
        agent_class = self.load(plugin_name)
        if agent_class is None:
            return None
        
        try:
            agent = agent_class()
            if config:
                agent.configure(config)
            return agent
        except Exception as e:
            print(f"Error creating agent from {plugin_name}: {e}")
            return None
    
    def list_plugins(self) -> dict[str, str]:
        """
        List available plugins with descriptions.
        
        Returns dict of {plugin_name: description}
        """
        result = {}
        
        for plugin_name in self.discover():
            agent_class = self.load(plugin_name)
            if agent_class:
                # Try to get description
                try:
                    agent = agent_class()
                    result[plugin_name] = agent.get_description()
                except:
                    result[plugin_name] = "No description available"
        
        return result


def discover_plugins(plugin_dir: str = "plugins") -> list[str]:
    """Convenience function to discover plugins."""
    loader = PluginLoader(plugin_dir)
    return loader.discover()


def load_plugin(
    plugin_name: str,
    plugin_dir: str = "plugins",
    config: Optional[dict] = None,
) -> Optional[NegotiationAgent]:
    """Convenience function to load a plugin and create an agent."""
    loader = PluginLoader(plugin_dir)
    return loader.create_agent(plugin_name, config)


@dataclass
class AgentInfo:
    """Information about an available agent."""
    id: str
    name: str
    description: str
    is_builtin: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_builtin": self.is_builtin,
        }


def list_available_agents(plugin_dir: str = "plugins") -> list[AgentInfo]:
    """
    List all available agents from plugins folder.
    
    Returns list of AgentInfo with id, name, description, and is_builtin flag.
    Users must select an agent from plugins or browse for a file.
    """
    agents = []
    
    # Add plugins from plugins/ folder
    loader = PluginLoader(plugin_dir)
    plugin_descriptions = loader.list_plugins()
    
    for plugin_name, description in plugin_descriptions.items():
        agents.append(AgentInfo(
            id=plugin_name,
            name=plugin_name.replace("_", " ").title(),
            description=description,
            is_builtin=False,
        ))
    
    return agents


def create_agent_by_id(agent_id: str, plugin_dir: str = "plugins") -> Optional[NegotiationAgent]:
    """
    Create an agent instance by its ID (plugin name).
    
    Args:
        agent_id: Plugin name from plugins/ directory
        plugin_dir: Directory containing plugins
        
    Returns:
        NegotiationAgent instance or None if not found
    """
    return load_plugin(agent_id, plugin_dir=plugin_dir)


def load_agent_class_from_path(file_path: str) -> Optional[Type[NegotiationAgent]]:
    """
    Load a NegotiationAgent subclass from an arbitrary file path.
    
    Handles both:
    - Standalone files with absolute imports (from negoplatform.agent_api.base import ...)
    - Files within the negoplatform package with relative imports (from ...agent_api.base import ...)
    
    Args:
        file_path: Full path to a Python file containing a NegotiationAgent subclass
        
    Returns:
        The NegotiationAgent subclass, or None if not found/invalid
    """
    path = Path(file_path).resolve()
    
    if not path.exists():
        print(f"File not found: {file_path}")
        return None
    
    if not path.suffix == ".py":
        print(f"Not a Python file: {file_path}")
        return None
    
    # Determine if this file is inside the negoplatform package
    # by looking for negoplatform in the path
    path_parts = path.parts
    negoplatform_idx = None
    for i, part in enumerate(path_parts):
        if part == "negoplatform":
            negoplatform_idx = i
            break
    
    added_to_path = []
    
    try:
        if negoplatform_idx is not None:
            # File is inside negoplatform package
            # Add the project root (parent of negoplatform) to sys.path
            project_root = Path(*path_parts[:negoplatform_idx])
            project_root_str = str(project_root)
            
            if project_root_str not in sys.path:
                sys.path.insert(0, project_root_str)
                added_to_path.append(project_root_str)
            
            # Build the module name as a dotted path from negoplatform
            # e.g., negoplatform.agents.negochat.agent_wrapper
            rel_parts = path_parts[negoplatform_idx:]
            module_name = ".".join(rel_parts)[:-3]  # Remove .py extension
        else:
            # Standalone file - add its directory to path
            file_dir = str(path.parent)
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)
                added_to_path.append(file_dir)
            
            # Also add project root if we can find it (for absolute imports like `from negoplatform...`)
            # Walk up looking for a directory containing negoplatform
            current = path.parent
            for _ in range(10):  # Limit search depth
                if (current / "negoplatform").is_dir():
                    current_str = str(current)
                    if current_str not in sys.path:
                        sys.path.insert(0, current_str)
                        added_to_path.append(current_str)
                    break
                if current.parent == current:
                    break
                current = current.parent
            
            module_name = path.stem
        
        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            print(f"Could not load module spec from: {file_path}")
            return None
        
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules so relative imports work
        sys.modules[module_name] = module
        
        spec.loader.exec_module(module)
        
        # Find NegotiationAgent subclass
        agent_class = None
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, NegotiationAgent) and 
                obj is not NegotiationAgent):
                # Found a valid subclass
                agent_class = obj
                break
        
        if agent_class:
            return agent_class
        else:
            print(f"No NegotiationAgent subclass found in {file_path}")
            return None
            
    except Exception as e:
        print(f"Error loading agent from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up added paths (optional - leave them for now to avoid issues)
        pass


def create_agent_from_path(file_path: str) -> Optional[NegotiationAgent]:
    """
    Load a NegotiationAgent from an arbitrary file path and create an instance.
    
    Args:
        file_path: Full path to a Python file containing a NegotiationAgent subclass
        
    Returns:
        NegotiationAgent instance, or None if loading failed
    """
    agent_class = load_agent_class_from_path(file_path)
    if agent_class is None:
        return None
    
    try:
        return agent_class()
    except Exception as e:
        print(f"Error creating agent instance from {file_path}: {e}")
        return None


def get_agent_info_from_path(file_path: str) -> Optional[AgentInfo]:
    """
    Load agent info from a file path without creating an instance.
    
    Args:
        file_path: Full path to a Python file containing a NegotiationAgent subclass
        
    Returns:
        AgentInfo with details about the agent, or None if invalid
    """
    agent_class = load_agent_class_from_path(file_path)
    if agent_class is None:
        return None
    
    # Use the class name directly
    class_name = agent_class.__name__
    
    try:
        # Create temporary instance to get description
        temp_agent = agent_class()
        description = temp_agent.get_description()
    except Exception as e:
        description = "No description available"
    
    return AgentInfo(
        id=f"file:{file_path}",
        name=class_name,
        description=description,
        is_builtin=False,
    )


def load_agent_from_config(config_path: str) -> Optional[NegotiationAgent]:
    """
    Load an agent based on a JSON configuration file.
    
    Config format:
    {
        "agent_type": "negochat" | "simple" | "<plugin_name>",
        "name": "Agent Name",
        ... other config options
    }
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return None
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    agent_type = config.get("agent_type", "simple")
    
    # Built-in agents
    if agent_type == "negochat":
        from ..agents.negochat import NegoChatAgent
        from ..agents.negochat.negochat_core import StackStrategy
        
        strategy = StackStrategy(config.get("strategy", "balanced"))
        behavior = config.get("behavior", {})
        
        agent = NegoChatAgent(
            strategy=strategy,
            min_acceptable_utility=behavior.get("min_acceptable_utility", 0.4),
            concession_rate=behavior.get("concession_rate", 0.1),
            emotional_mirroring=config.get("personality", {}).get("emotional_mirroring", True),
            response_delay_ms=behavior.get("response_delay_ms", 1000),
            idle_prompt_seconds=behavior.get("idle_prompt_seconds", 30.0),
        )
        agent.configure(config)
        return agent
    
    elif agent_type == "simple":
        from ..agent_api.base import SimpleAgent
        
        behavior = config.get("behavior", {})
        personality = config.get("personality", {})
        
        agent = SimpleAgent(
            min_utility_percent=behavior.get("min_acceptable_utility", 0.4) * 100,
            greeting=personality.get("initial_greeting", "Hello! Let's negotiate."),
        )
        return agent
    
    else:
        # Try to load as plugin
        return load_plugin(agent_type, config=config)

