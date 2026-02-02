"""
Action types that agents can return.

Actions represent what the agent wants to do in response to an event.
The platform executes these actions and converts them to Events.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from ..core.events import MessageSubtype, Expression, Preference

if TYPE_CHECKING:
    from ..domain.models import Offer


@dataclass
class Action:
    """Base class for all agent actions."""
    pass


@dataclass
class SendMessage(Action):
    """
    Send a chat message.
    
    Attributes:
        text: The message text to send
        subtype: Message category (for logging/analysis)
        preference: Optional structured preference data
        delay_ms: Delay before sending (simulates typing)
    """
    text: str
    subtype: MessageSubtype = MessageSubtype.GENERIC
    preference: Optional[Preference] = None
    delay_ms: int = 0


@dataclass
class SendOffer(Action):
    """
    Send an offer proposal.
    
    Attributes:
        offer: The offer to send (can be partial)
        delay_ms: Delay before sending
    """
    offer: "Offer"
    delay_ms: int = 0


@dataclass
class SendExpression(Action):
    """
    Display an emotional expression.
    
    Attributes:
        expression: The emotion to display
        duration_ms: How long to show it
        delay_ms: Delay before showing
    """
    expression: Expression
    duration_ms: int = 2000
    delay_ms: int = 0


@dataclass
class Schedule(Action):
    """
    Schedule an action for later execution.
    
    Allows agents to chain delayed responses, like IAGO's
    "wait, then counter-offer, then smile" sequences.
    
    Attributes:
        delay_ms: Delay before executing the inner action
        action: The action to execute after the delay
    """
    delay_ms: int
    action: Action


@dataclass
class FormalAccept(Action):
    """
    Formally accept the current offer.
    
    Only valid if offer is complete (no items in middle).
    """
    delay_ms: int = 0


@dataclass
class FormalReject(Action):
    """
    Formally reject and end negotiation.
    
    Used when agent wants to walk away.
    """
    reason: str = "rejected"
    delay_ms: int = 0


@dataclass
class ShowTyping(Action):
    """
    Show "typing..." indicator.
    
    Used to signal the agent is thinking/composing a response.
    The indicator auto-hides when the next action is sent.
    """
    duration_ms: Optional[int] = None  # None = until next action


def chain_actions(*actions: Action, base_delay_ms: int = 0, gap_ms: int = 500) -> list[Action]:
    """
    Helper to chain multiple actions with delays.
    
    Creates a natural sequence like:
    1. Show typing
    2. Send message
    3. Pause
    4. Send offer
    5. Smile
    
    Args:
        actions: Actions to chain
        base_delay_ms: Initial delay before first action
        gap_ms: Gap between actions
        
    Returns:
        List of Schedule-wrapped actions
    """
    result = []
    current_delay = base_delay_ms
    
    for action in actions:
        if current_delay > 0:
            result.append(Schedule(delay_ms=current_delay, action=action))
        else:
            result.append(action)
        current_delay += gap_ms
    
    return result

