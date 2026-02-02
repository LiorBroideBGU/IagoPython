"""
NLG Templates for NegoChat agent.

Simple template-based response generation without NLU.
Maps negotiation actions to natural language responses.
"""

import random
from typing import Optional
from ...domain.models import Offer, GameSpec


class NegoChatTemplates:
    """Template-based Natural Language Generation for NegoChat."""
    
    # Greetings
    GREETINGS = [
        "Hello! I'm looking forward to finding a deal that works for both of us.",
        "Hi there! Let's see if we can reach an agreement.",
        "Hello! I hope we can work something out together.",
        "Hi! Ready to negotiate?",
    ]
    
    # Offer proposals
    PROPOSE_OPENING = [
        "Let me start with a proposal.",
        "Here's my opening offer.",
        "What do you think about this to start?",
        "How about we begin with this?",
    ]
    
    PROPOSE_COUNTER = [
        "How about this instead?",
        "Let me make a counter-offer.",
        "What if we tried this?",
        "Here's what I'm thinking.",
        "Consider this alternative.",
    ]
    
    PROPOSE_CONCESSION = [
        "I can move a bit on this.",
        "Let me adjust my offer.",
        "I'm willing to give a little.",
        "Here's a revised proposal.",
    ]
    
    # Acceptance
    ACCEPT_OFFER = [
        "That works for me!",
        "I can agree to that.",
        "Deal!",
        "That's acceptable.",
        "I'm happy with that.",
    ]
    
    ACCEPT_PARTIAL = [
        "I like the direction, let's finalize the details.",
        "Good progress! Let's sort out the remaining items.",
        "We're getting there! What about the rest?",
    ]
    
    # Rejection
    REJECT_MILD = [
        "I'll need a bit more than that.",
        "Can you do better on your side?",
        "That's not quite enough for me.",
        "I was hoping for a better deal.",
    ]
    
    REJECT_STRONG = [
        "I can't accept that.",
        "That's really not going to work for me.",
        "We're too far apart on that.",
        "I need you to reconsider.",
    ]
    
    # Issue-specific
    WANT_ISSUE = [
        "I really need the {item}.",
        "The {item} are important to me.",
        "I'd like to keep the {item}.",
    ]
    
    OFFER_ISSUE = [
        "You can have the {item}.",
        "I'll give you the {item}.",
        "Take the {item} if you want.",
    ]
    
    # Emotional responses
    RESPOND_HAPPY = [
        "I'm glad you're happy!",
        "Great, let's keep this positive energy!",
        "Nice! :)",
    ]
    
    RESPOND_SAD = [
        "I'm sorry you feel that way.",
        "Let's try to find something that makes us both happy.",
        "Don't worry, we can work this out.",
    ]
    
    RESPOND_ANGRY = [
        "Let's stay calm and work through this.",
        "I understand you're frustrated.",
        "Let's focus on finding a solution.",
    ]
    
    RESPOND_SURPRISED = [
        "Unexpected, right?",
        "I know, let me explain...",
        "Yes, hear me out!",
    ]
    
    # Time pressure
    TIME_PRESSURE = [
        "We're running low on time.",
        "Clock's ticking...",
        "We should try to wrap this up.",
    ]
    
    TIME_PROMPT = [
        "Any thoughts on my last offer?",
        "What do you think?",
        "I'm waiting to hear from you.",
    ]
    
    # Farewells
    FAREWELL_SUCCESS = [
        "Great negotiating with you!",
        "Pleasure doing business!",
        "Thanks for the deal!",
    ]
    
    FAREWELL_FAIL = [
        "Maybe next time.",
        "Sorry we couldn't reach an agreement.",
        "Too bad we couldn't work it out.",
    ]
    
    def __init__(self, game: GameSpec):
        self.game = game
    
    def get_greeting(self) -> str:
        return random.choice(self.GREETINGS)
    
    def get_opening_proposal(self) -> str:
        return random.choice(self.PROPOSE_OPENING)
    
    def get_counter_proposal(self) -> str:
        return random.choice(self.PROPOSE_COUNTER)
    
    def get_concession_text(self) -> str:
        return random.choice(self.PROPOSE_CONCESSION)
    
    def get_accept_text(self, is_complete: bool = True) -> str:
        if is_complete:
            return random.choice(self.ACCEPT_OFFER)
        return random.choice(self.ACCEPT_PARTIAL)
    
    def get_reject_text(self, strong: bool = False) -> str:
        if strong:
            return random.choice(self.REJECT_STRONG)
        return random.choice(self.REJECT_MILD)
    
    def get_want_issue_text(self, issue_name: str) -> str:
        display_name = self.game.issue_plural_names.get(issue_name, issue_name)
        template = random.choice(self.WANT_ISSUE)
        return template.format(item=display_name.lower())
    
    def get_offer_issue_text(self, issue_name: str) -> str:
        display_name = self.game.issue_plural_names.get(issue_name, issue_name)
        template = random.choice(self.OFFER_ISSUE)
        return template.format(item=display_name.lower())
    
    def get_emotion_response(self, emotion: str) -> str:
        responses = {
            "happy": self.RESPOND_HAPPY,
            "sad": self.RESPOND_SAD,
            "angry": self.RESPOND_ANGRY,
            "surprised": self.RESPOND_SURPRISED,
        }
        templates = responses.get(emotion, self.RESPOND_HAPPY)
        return random.choice(templates)
    
    def get_time_pressure_text(self) -> str:
        return random.choice(self.TIME_PRESSURE)
    
    def get_prompt_text(self) -> str:
        return random.choice(self.TIME_PROMPT)
    
    def get_farewell(self, success: bool) -> str:
        if success:
            return random.choice(self.FAREWELL_SUCCESS)
        return random.choice(self.FAREWELL_FAIL)
    
    def describe_offer(self, offer: Offer) -> str:
        """Generate a natural language description of an offer."""
        parts = []
        
        for issue in self.game.issues:
            alloc = offer[issue.name]
            if alloc is None:
                continue
            
            singular = self.game.issue_singular_names.get(issue.name, issue.name)
            plural = self.game.issue_plural_names.get(issue.name, issue.name)
            
            if alloc.agent > 0 and alloc.human == 0:
                if alloc.agent == 1:
                    parts.append(f"I get the {singular}")
                else:
                    parts.append(f"I get all {alloc.agent} {plural.lower()}")
            elif alloc.human > 0 and alloc.agent == 0:
                if alloc.human == 1:
                    parts.append(f"you get the {singular}")
                else:
                    parts.append(f"you get all {alloc.human} {plural.lower()}")
            elif alloc.agent > 0 and alloc.human > 0:
                parts.append(f"we split the {plural.lower()} ({alloc.agent} for me, {alloc.human} for you)")
        
        if not parts:
            return "Let's discuss the items."
        
        return ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1] if len(parts) > 1 else parts[0]

