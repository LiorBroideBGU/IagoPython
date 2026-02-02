"""
Status Bar Widget.

Displays negotiation status including timer, scores, and game info.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional


class StatusBar(ttk.Frame):
    """
    Status bar showing negotiation state.
    
    Features:
    - Timer display (elapsed/remaining)
    - Score preview
    - Game info
    - Accept/Reject buttons
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        on_formal_accept: Optional[callable] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self._on_formal_accept = on_formal_accept
        self._deadline_seconds: Optional[int] = None
        self._elapsed_seconds: float = 0
        
        self._create_widgets()
        self._setup_layout()
    
    def _create_widgets(self):
        """Create status bar widgets."""
        # Game info
        self._game_frame = ttk.Frame(self)
        self._game_name_var = tk.StringVar(value="No game loaded")
        self._game_name_label = ttk.Label(
            self._game_frame,
            textvariable=self._game_name_var,
            font=("Segoe UI", 11, "bold"),
        )
        self._game_status_var = tk.StringVar(value="Not started")
        self._game_status_label = ttk.Label(
            self._game_frame,
            textvariable=self._game_status_var,
            font=("Segoe UI", 9),
        )
        
        # Timer
        self._timer_frame = ttk.LabelFrame(self, text="Time")
        self._timer_var = tk.StringVar(value="--:--")
        self._timer_label = ttk.Label(
            self._timer_frame,
            textvariable=self._timer_var,
            font=("Segoe UI", 16, "bold"),
        )
        self._timer_status_var = tk.StringVar(value="")
        self._timer_status_label = ttk.Label(
            self._timer_frame,
            textvariable=self._timer_status_var,
            font=("Segoe UI", 9),
        )
        
        # Scores
        self._score_frame = ttk.LabelFrame(self, text="Current Scores")
        self._human_score_var = tk.StringVar(value="You: --")
        self._human_score_label = ttk.Label(
            self._score_frame,
            textvariable=self._human_score_var,
            font=("Segoe UI", 10),
            foreground="#89b4fa",
        )
        self._agent_score_var = tk.StringVar(value="Agent: --")
        self._agent_score_label = ttk.Label(
            self._score_frame,
            textvariable=self._agent_score_var,
            font=("Segoe UI", 10),
            foreground="#a6e3a1",
        )
        
        # Accept button
        self._action_frame = ttk.Frame(self)
        self._accept_button = ttk.Button(
            self._action_frame,
            text="✓ Accept Deal",
            command=self._formal_accept,
            style="Accent.TButton",
        )
        self._accept_status_var = tk.StringVar(value="")
        self._accept_status_label = ttk.Label(
            self._action_frame,
            textvariable=self._accept_status_var,
            font=("Segoe UI", 9),
        )
    
    def _setup_layout(self):
        """Setup widget layout."""
        self.columnconfigure(1, weight=1)
        
        # Game info (left)
        self._game_frame.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self._game_name_label.pack(anchor="w")
        self._game_status_label.pack(anchor="w")
        
        # Timer (center-left)
        self._timer_frame.grid(row=0, column=1, sticky="w", padx=20, pady=5)
        self._timer_label.pack(padx=15, pady=2)
        self._timer_status_label.pack(pady=(0, 2))
        
        # Scores (center-right)
        self._score_frame.grid(row=0, column=2, sticky="e", padx=20, pady=5)
        self._human_score_label.pack(side=tk.LEFT, padx=10, pady=5)
        self._agent_score_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Accept button (right)
        self._action_frame.grid(row=0, column=3, sticky="e", padx=10, pady=5)
        self._accept_button.pack(pady=2)
        self._accept_status_label.pack()
    
    def set_game_info(self, name: str, description: str = ""):
        """Set game information display."""
        self._game_name_var.set(name)
        if description:
            self._game_status_var.set(description[:50])
    
    def set_game_status(self, status: str):
        """Set game status text."""
        self._game_status_var.set(status)
    
    def set_deadline(self, seconds: Optional[int]):
        """Set the deadline for countdown timer."""
        self._deadline_seconds = seconds
        if seconds:
            self._timer_status_var.set("Time remaining")
        else:
            self._timer_status_var.set("Elapsed time")
    
    def update_time(self, elapsed_seconds: float, remaining_seconds: Optional[float] = None):
        """Update timer display."""
        self._elapsed_seconds = elapsed_seconds
        
        if remaining_seconds is not None:
            # Countdown mode
            mins = int(remaining_seconds // 60)
            secs = int(remaining_seconds % 60)
            self._timer_var.set(f"{mins:02d}:{secs:02d}")
            
            # Warning color when low on time
            if remaining_seconds < 30:
                self._timer_label.configure(foreground="#f38ba8")  # Red
            elif remaining_seconds < 60:
                self._timer_label.configure(foreground="#f9e2af")  # Yellow
            else:
                self._timer_label.configure(foreground="")
        else:
            # Elapsed time mode
            mins = int(elapsed_seconds // 60)
            secs = int(elapsed_seconds % 60)
            self._timer_var.set(f"{mins:02d}:{secs:02d}")
    
    def update_scores(self, human_score: float, agent_score: float):
        """Update score display."""
        self._human_score_var.set(f"You: {human_score:.1f}")
        self._agent_score_var.set(f"Agent: {agent_score:.1f}")
    
    def set_acceptance_status(
        self, 
        human_accepted: bool, 
        agent_accepted: bool,
        can_accept: bool = True
    ):
        """Update acceptance status display."""
        status_parts = []
        if human_accepted:
            status_parts.append("You ✓")
        if agent_accepted:
            status_parts.append("Agent ✓")
        
        if status_parts:
            self._accept_status_var.set(" | ".join(status_parts))
        else:
            self._accept_status_var.set("")
        
        # Enable/disable accept button
        self._accept_button.configure(state=tk.NORMAL if can_accept else tk.DISABLED)
    
    def _formal_accept(self):
        """Handle formal accept button click."""
        if self._on_formal_accept:
            self._on_formal_accept()
    
    def set_on_formal_accept(self, callback: callable):
        """Set formal accept callback."""
        self._on_formal_accept = callback
    
    def reset(self):
        """Reset status bar to initial state."""
        self._timer_var.set("--:--")
        self._timer_status_var.set("")
        self._human_score_var.set("You: --")
        self._agent_score_var.set("Agent: --")
        self._accept_status_var.set("")
        self._game_status_var.set("Not started")
        self._timer_label.configure(foreground="")

