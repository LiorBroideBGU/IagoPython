"""
Multi-Issue Bargaining Game.

A configurable negotiation game where parties divide multiple types of items.
Classic IAGO setup: apples, oranges, etc. with different values per party.
"""

import json
from pathlib import Path
from typing import Union

from ..models import Issue, UtilityFunction, ProtocolRules, GameSpec, Party


class MultiIssueBargainingGame:
    """
    Factory for creating multi-issue bargaining games.
    
    Can be configured via:
    - Direct Python instantiation
    - JSON configuration file
    """
    
    @staticmethod
    def create(
        name: str,
        description: str,
        items: list[dict],
        agent_values: dict[str, float],
        human_values: dict[str, float],
        deadline_seconds: int = 300,
        allow_partial: bool = True,
    ) -> GameSpec:
        """
        Create a multi-issue bargaining game.
        
        Args:
            name: Game identifier
            description: Human-readable description
            items: List of dicts with keys: name, display_name, quantity
            agent_values: Map of item name -> value per unit for agent
            human_values: Map of item name -> value per unit for human
            deadline_seconds: Time limit (0 or None for no limit)
            allow_partial: Whether partial agreements are allowed
            
        Returns:
            Configured GameSpec
        """
        issues = [
            Issue(
                name=item["name"],
                display_name=item.get("display_name", item["name"]),
                quantity=item["quantity"],
                divisible=item.get("divisible", False)
            )
            for item in items
        ]
        
        agent_utility = UtilityFunction(
            party=Party.AGENT,
            values=agent_values
        )
        
        human_utility = UtilityFunction(
            party=Party.HUMAN,
            values=human_values
        )
        
        rules = ProtocolRules(
            deadline_seconds=deadline_seconds if deadline_seconds and deadline_seconds > 0 else None,
            allow_partial_agreements=allow_partial,
        )
        
        # Build display name mappings
        singular_names = {item["name"]: item.get("singular_name", item["name"]) for item in items}
        plural_names = {item["name"]: item.get("display_name", item["name"]) for item in items}
        
        return GameSpec(
            name=name,
            description=description,
            issues=issues,
            agent_utility=agent_utility,
            human_utility=human_utility,
            rules=rules,
            issue_singular_names=singular_names,
            issue_plural_names=plural_names,
        )
    
    @staticmethod
    def create_classic_resource_game() -> GameSpec:
        """
        Create a classic IAGO-style resource division game.
        
        Items: Apples (4), Oranges (3), Bananas (2)
        Agent prefers: Apples > Oranges > Bananas
        Human prefers: Bananas > Oranges > Apples (opposing preferences)
        """
        return MultiIssueBargainingGame.create(
            name="classic_resource",
            description="Divide fruits between two parties. Each party values items differently.",
            items=[
                {"name": "apples", "display_name": "Apples", "singular_name": "apple", "quantity": 4},
                {"name": "oranges", "display_name": "Oranges", "singular_name": "orange", "quantity": 3},
                {"name": "bananas", "display_name": "Bananas", "singular_name": "banana", "quantity": 2},
            ],
            agent_values={"apples": 10, "oranges": 6, "bananas": 2},
            human_values={"apples": 2, "oranges": 6, "bananas": 10},
            deadline_seconds=300,
        )
    
    @staticmethod
    def create_job_negotiation_game() -> GameSpec:
        """
        Create a job offer negotiation game.
        
        Issues: Salary (in 10k increments), Vacation Days, Work From Home Days
        """
        return MultiIssueBargainingGame.create(
            name="job_negotiation",
            description="Negotiate job offer terms: salary, vacation, and remote work.",
            items=[
                {"name": "salary", "display_name": "Salary (10k units)", "singular_name": "salary unit", "quantity": 5},
                {"name": "vacation", "display_name": "Vacation Days", "singular_name": "vacation day", "quantity": 10},
                {"name": "remote", "display_name": "Remote Days/Week", "singular_name": "remote day", "quantity": 5},
            ],
            # Employer (agent) prefers lower salary, fewer vacation, less remote
            agent_values={"salary": -8, "vacation": -3, "remote": -5},
            # Employee (human) prefers higher salary, more vacation, more remote
            human_values={"salary": 10, "vacation": 5, "remote": 7},
            deadline_seconds=600,
        )


def load_game_from_json(path: Union[str, Path]) -> GameSpec:
    """
    Load a game configuration from a JSON file.
    
    Expected JSON format:
    {
        "name": "my_game",
        "description": "A custom negotiation game",
        "items": [
            {"name": "item1", "display_name": "Items", "singular_name": "item", "quantity": 5}
        ],
        "agent_values": {"item1": 10},
        "human_values": {"item1": 5},
        "deadline_seconds": 300,
        "allow_partial": true
    }
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return MultiIssueBargainingGame.create(
        name=config["name"],
        description=config.get("description", ""),
        items=config["items"],
        agent_values=config["agent_values"],
        human_values=config["human_values"],
        deadline_seconds=config.get("deadline_seconds", 300),
        allow_partial=config.get("allow_partial", True),
    )


def save_game_to_json(game: GameSpec, path: Union[str, Path]) -> None:
    """Save a game configuration to a JSON file."""
    path = Path(path)
    
    config = {
        "name": game.name,
        "description": game.description,
        "items": [
            {
                "name": issue.name,
                "display_name": issue.display_name,
                "singular_name": game.issue_singular_names.get(issue.name, issue.name),
                "quantity": issue.quantity,
                "divisible": issue.divisible,
            }
            for issue in game.issues
        ],
        "agent_values": game.agent_utility.values,
        "human_values": game.human_utility.values,
        "deadline_seconds": game.rules.deadline_seconds,
        "allow_partial": game.rules.allow_partial_agreements,
    }
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

