"""
Main entry point for the IAGO Negotiation Platform.

Usage:
    python -m negoplatform.main [options]
    
Options:
    --game PATH      Path to game config JSON (default: built-in resource game)
    --agent PATH     Path to agent config JSON (default: built-in NegoChat)
    --plugin NAME    Name of plugin agent to use
    --log-dir PATH   Directory for logs (default: ./logs)
    --custom         Launch unified game launcher (agent + game selection)
    --launcher       Alias for --custom
"""

import argparse
import sys
from pathlib import Path

from .domain.games.multi_issue import MultiIssueBargainingGame, load_game_from_json
from .agents.negochat import NegoChatAgent
from .plugins.plugin_loader import load_agent_from_config, load_plugin, list_available_agents
from .gui.app import NegotiationApp, run_negotiation
from .gui.widgets.config_dialog import GameLauncherDialog
from .logging.logger import EventLogger


def main():
    parser = argparse.ArgumentParser(
        description="NegoPlatform - Human-Agent Negotiation System"
    )
    parser.add_argument(
        "--game",
        type=str,
        help="Path to game configuration JSON file",
    )
    parser.add_argument(
        "--custom",
        action="store_true",
        help="Launch unified game launcher (select agent + configure game)",
    )
    parser.add_argument(
        "--launcher",
        action="store_true",
        help="Alias for --custom",
    )
    parser.add_argument(
        "--agent",
        type=str,
        help="Path to agent configuration JSON file",
    )
    parser.add_argument(
        "--plugin",
        type=str,
        help="Name of plugin agent to use (from plugins/ directory)",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory for session logs",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable event logging",
    )
    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List available plugins and exit",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available agents (built-in + plugins) and exit",
    )
    
    args = parser.parse_args()
    
    # List all agents (built-in + plugins) and exit
    if args.list_agents:
        agents = list_available_agents()
        print("Available agents:")
        for agent in agents:
            badge = "[built-in]" if agent.is_builtin else "[plugin]"
            print(f"  {badge} {agent.id}: {agent.description[:60]}...")
        return
    
    # List plugins and exit (legacy)
    if args.list_plugins:
        from .plugins.plugin_loader import PluginLoader
        loader = PluginLoader()
        plugins = loader.list_plugins()
        if plugins:
            print("Available plugins:")
            for name, desc in plugins.items():
                print(f"  {name}: {desc}")
        else:
            print("No plugins found in plugins/ directory")
        return
    
    # Unified launcher mode
    if args.custom or args.launcher:
        # Launch unified launcher dialog
        result = GameLauncherDialog.show()
        
        if not result:
            print("Game launcher cancelled.")
            sys.exit(0)
            
        game = result.game
        agent = result.agent
        
        print(f"Selected agent: {agent.get_name()}")
        print(f"Configured game: {game.name}")
        
    else:
        # Legacy mode: separate game and agent loading
        
        # Load game configuration
        if args.game:
            game_path = Path(args.game)
            if not game_path.exists():
                print(f"Error: Game config not found: {args.game}")
                sys.exit(1)
            game = load_game_from_json(game_path)
            print(f"Loaded game: {game.name}")
        else:
            # Use built-in classic resource game
            game = MultiIssueBargainingGame.create_classic_resource_game()
            print(f"Using default game: {game.name}")
        
        # Load agent
        if args.plugin:
            agent = load_plugin(args.plugin)
            if agent is None:
                print(f"Error: Could not load plugin: {args.plugin}")
                sys.exit(1)
            print(f"Loaded plugin agent: {args.plugin}")
        elif args.agent:
            agent_path = Path(args.agent)
            if not agent_path.exists():
                print(f"Error: Agent config not found: {args.agent}")
                sys.exit(1)
            agent = load_agent_from_config(agent_path)
            if agent is None:
                print(f"Error: Could not load agent from config")
                sys.exit(1)
            print(f"Loaded agent from config: {args.agent}")
        else:
            # Use built-in NegoChat agent
            agent = NegoChatAgent()
            print("Using default NegoChat agent")
    
    # Setup logging
    logger = None
    if not args.no_log:
        logger = EventLogger(output_dir=args.log_dir)
        print(f"Logging to: {logger.file_path}")
    
    # Print game info
    print(f"\n{'='*50}")
    print(f"Game: {game.name}")
    print(f"Description: {game.description}")
    print(f"Issues: {', '.join(i.display_name for i in game.issues)}")
    print(f"Deadline: {game.rules.deadline_seconds}s" if game.rules.deadline_seconds else "No deadline")
    print(f"{'='*50}\n")
    
    # Run negotiation
    try:
        app = NegotiationApp(game, agent, title=f"NegoPlatform - {game.name}")
        
        if logger:
            logger.subscribe_to_bus(app._event_bus)
            logger.log_game_config({
                "name": game.name,
                "description": game.description,
                "issues": [
                    {"name": i.name, "quantity": i.quantity}
                    for i in game.issues
                ],
            })
        
        app.start()
        
    except KeyboardInterrupt:
        print("\nNegotiation interrupted.")
    except Exception as e:
        # Handle case where main loop fails (e.g. if root was destroyed improperly)
        print(f"Error running application: {e}")
    finally:
        if logger:
            logger.close()
            print(f"\nSession log saved to: {logger.file_path}")


if __name__ == "__main__":
    main()
