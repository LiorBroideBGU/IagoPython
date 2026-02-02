"""
Emotion Bar Widget.

Allows users to send emotional expressions during negotiation.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ...core.events import Expression


class EmotionBar(ttk.Frame):
    """
    Bar of emotion buttons for expressing emotions.
    
    Features:
    - 5 emotion buttons matching IAGO
    - Visual feedback on selection
    - Agent emotion display
    """
    
    # Emoji representations for each emotion
    EMOTION_EMOJIS = {
        Expression.HAPPY: "😊",
        Expression.SAD: "😢",
        Expression.ANGRY: "😠",
        Expression.SURPRISED: "😲",
        Expression.NEUTRAL: "😐",
    }
    
    EMOTION_LABELS = {
        Expression.HAPPY: "Happy",
        Expression.SAD: "Sad",
        Expression.ANGRY: "Angry",
        Expression.SURPRISED: "Surprised",
        Expression.NEUTRAL: "Neutral",
    }
    
    def __init__(
        self,
        parent: tk.Widget,
        on_send_expression: Optional[Callable[[Expression], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self._on_send_expression = on_send_expression
        self._buttons: dict[Expression, ttk.Button] = {}
        self._current_agent_emotion: Optional[Expression] = None
        
        self._create_widgets()
        self._setup_layout()
    
    def _create_widgets(self):
        """Create emotion bar widgets."""
        # User emotions section
        self._user_frame = ttk.LabelFrame(self, text="Express Emotion")
        
        # Create emotion buttons
        for expr in Expression.human_expressions():
            emoji = self.EMOTION_EMOJIS.get(expr, "🙂")
            label = self.EMOTION_LABELS.get(expr, expr.value)
            
            btn = ttk.Button(
                self._user_frame,
                text=f"{emoji}\n{label}",
                width=10,
                command=lambda e=expr: self._send_expression(e),
            )
            self._buttons[expr] = btn
        
        # Agent emotion display
        self._agent_frame = ttk.LabelFrame(self, text="Agent Emotion")
        self._agent_emoji_var = tk.StringVar(value="😐")
        self._agent_emoji_label = ttk.Label(
            self._agent_frame,
            textvariable=self._agent_emoji_var,
            font=("Segoe UI Emoji", 32),
        )
        self._agent_emotion_var = tk.StringVar(value="Neutral")
        self._agent_emotion_label = ttk.Label(
            self._agent_frame,
            textvariable=self._agent_emotion_var,
            font=("Segoe UI", 10),
        )
    
    def _setup_layout(self):
        """Setup widget layout."""
        self.columnconfigure(0, weight=1)
        
        # User emotions
        self._user_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        for i, btn in enumerate(self._buttons.values()):
            btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Agent emotion
        self._agent_frame.grid(row=0, column=1, sticky="e", padx=5, pady=5)
        self._agent_emoji_label.pack(padx=10, pady=5)
        self._agent_emotion_label.pack(padx=10, pady=(0, 5))
    
    def _send_expression(self, expression: Expression):
        """Send an expression."""
        if self._on_send_expression:
            self._on_send_expression(expression)
    
    def set_agent_emotion(self, expression: Expression, duration_ms: int = 2000):
        """
        Display agent's current emotion.
        
        Args:
            expression: The emotion to display
            duration_ms: How long to show (then revert to neutral)
        """
        self._current_agent_emotion = expression
        
        emoji = self.EMOTION_EMOJIS.get(expression, "😐")
        label = self.EMOTION_LABELS.get(expression, expression.value)
        
        self._agent_emoji_var.set(emoji)
        self._agent_emotion_var.set(label)
        
        # Schedule revert to neutral
        if expression != Expression.NEUTRAL:
            self.after(duration_ms, self._revert_agent_emotion)
    
    def _revert_agent_emotion(self):
        """Revert agent emotion to neutral."""
        self._current_agent_emotion = Expression.NEUTRAL
        self._agent_emoji_var.set(self.EMOTION_EMOJIS[Expression.NEUTRAL])
        self._agent_emotion_var.set(self.EMOTION_LABELS[Expression.NEUTRAL])
    
    def set_on_send_expression(self, callback: Callable[[Expression], None]):
        """Set the expression send callback."""
        self._on_send_expression = callback
    
    def get_agent_emotion(self) -> Optional[Expression]:
        """Get the current agent emotion."""
        return self._current_agent_emotion

