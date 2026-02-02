"""Plugin system for custom agents."""

from .plugin_loader import (
    PluginLoader, 
    discover_plugins, 
    load_plugin, 
    list_available_agents,
    create_agent_by_id,
    AgentInfo,
    load_agent_class_from_path,
    create_agent_from_path,
    get_agent_info_from_path,
)

__all__ = [
    "PluginLoader", 
    "discover_plugins", 
    "load_plugin",
    "list_available_agents",
    "create_agent_by_id",
    "AgentInfo",
    "load_agent_class_from_path",
    "create_agent_from_path",
    "get_agent_info_from_path",
]

