# NegoPlatform - Negotiation Platform

A Python implementation of NegoPlatform, inspired by IAGO's (Interactive Arbitration Guide Online) negotiation platform for human-agent negotiation research.

[Demo Link]([https://example.com](https://drive.google.com/file/d/1_ehidpGIKrt3PU9zoV9x_blzA1jvYo8o/view?usp=sharing))


## Features

- **Event-Driven Architecture**: Mirrors IAGO's multi-channel event system (messages, offers, expressions, timing)
- **NegoChat Agent**: Issue-by-issue negotiation strategy with configurable behavior
- **Tkinter GUI**: Desktop interface with chat, offer builder, emotion bar, and status display
- **Plugin System**: Create custom agents by extending `NegotiationAgent`
- **JSON Configuration**: Define games and agent personalities via config files
- **Session Logging**: JSONL event logs for analysis and replay

## Quick Start

```bash
# Run with default settings (classic resource game + NegoChat agent)
python -m negoplatform.main

# Use custom game configuration
python -m negoplatform.main --game path/to/game.json

# Use custom agent configuration
python -m negoplatform.main --agent path/to/agent_config.json

# Use a plugin agent
python -m negoplatform.main --plugin example_agent

# List available plugins
python -m negoplatform.main --list-plugins
```

## Project Structure

```
negoplatform/
├── domain/           # Game definitions and models
│   ├── models.py     # Issue, Offer, UtilityFunction, GameSpec
│   └── games/        # Pre-defined games (multi-issue bargaining)
├── core/             # Event system and session management
│   ├── events.py     # Event types and payloads
│   ├── bus.py        # EventBus for publish/subscribe
│   ├── session.py    # NegotiationSession state machine
│   └── scheduler.py  # TIME ticks and delayed actions
├── agent_api/        # Agent interface
│   ├── base.py       # NegotiationAgent abstract class
│   ├── actions.py    # Action types (SendMessage, SendOffer, etc.)
│   └── context.py    # AgentContext (read-only session view)
├── agents/           # Built-in agents
│   └── negochat/     # NegoChat implementation
├── gui/              # Tkinter interface
│   ├── app.py        # Main application window
│   └── widgets/      # Chat, OfferBuilder, EmotionBar, StatusBar
├── logging/          # Session logging and replay
├── config/           # JSON configuration files
└── plugins/          # Custom agent plugins
```

## Creating Custom Agents

### Option 1: JSON Configuration

Edit `config/agent_config.json` to customize the NegoChat agent:

```json
{
  "agent_type": "negochat",
  "strategy": "balanced",  // aggressive, balanced, cooperative
  "behavior": {
    "min_acceptable_utility": 0.4,
    "concession_rate": 0.1
  }
}
```

### Option 2: Python Plugin

Create a new file in `plugins/` directory:

```python
# plugins/my_agent.py
from negoplatform.agent_api.base import NegotiationAgent
from negoplatform.agent_api.actions import SendMessage, SendOffer, FormalAccept
from negoplatform.agent_api.context import AgentContext
from negoplatform.core.events import Event

class MyCustomAgent(NegotiationAgent):
    def on_game_start(self, ctx: AgentContext, event: Event):
        return [SendMessage("Hello! Let's negotiate.")]
    
    def on_send_offer(self, ctx: AgentContext, event: Event):
        if ctx.get_agent_utility_percent() > 50:
            return [FormalAccept()]
        return [SendMessage("I need a better deal.")]
```

Run with: `python -m negoplatform.main --plugin my_agent`

## Creating Custom Games

Create a JSON file with game configuration:

```json
{
  "name": "job_negotiation",
  "description": "Negotiate job offer terms",
  "items": [
    {"name": "salary", "display_name": "Salary Units", "quantity": 5},
    {"name": "vacation", "display_name": "Vacation Days", "quantity": 10}
  ],
  "agent_values": {"salary": -8, "vacation": -3},
  "human_values": {"salary": 10, "vacation": 5},
  "deadline_seconds": 300
}
```

## Event Types

| Event | Description |
|-------|-------------|
| `SEND_MESSAGE` | Chat message with optional preference data |
| `SEND_OFFER` | Proposal with item allocations |
| `SEND_EXPRESSION` | Emotional expression (happy, sad, angry, etc.) |
| `OFFER_IN_PROGRESS` | User is editing an offer |
| `TIME` | Periodic time tick (every 5 seconds) |
| `FORMAL_ACCEPT` | Binding acceptance of complete offer |
| `GAME_START` | Negotiation begins |
| `GAME_END` | Negotiation ends |

## Agent Actions

| Action | Description |
|--------|-------------|
| `SendMessage(text)` | Send a chat message |
| `SendOffer(offer)` | Propose an allocation |
| `SendExpression(emotion)` | Display an emotion |
| `FormalAccept()` | Formally accept current offer |
| `Schedule(delay_ms, action)` | Execute action after delay |

## References

- Mell, J., & Gratch, J. "Grumpy & Pinocchio: Answering Human-Agent Negotiation Questions through Realistic Agent Design" (IAGO Platform)
- Rosenfeld, A., et al. "NegoChat: A Chat-Based Negotiation Agent" (NegoChat algorithm)

## License

MIT License

