"""
Chat Panel Widget.

Displays conversation history and allows user to send messages.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Callable, Optional
from datetime import datetime


class ChatPanel(ttk.Frame):
    """
    Chat panel for displaying and sending messages.
    
    Features:
    - Scrollable message history
    - Message input field
    - Visual distinction between human/agent messages
    - Typing indicator support
    """
    
    def __init__(
        self, 
        parent: tk.Widget,
        on_send_message: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self._on_send_message = on_send_message
        self._typing_indicator_visible = False
        
        self._create_widgets()
        self._setup_layout()
        self._bind_events()
    
    def _create_widgets(self):
        """Create chat widgets."""
        # Message display area
        self._chat_frame = ttk.Frame(self)
        
        self._chat_display = scrolledtext.ScrolledText(
            self._chat_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Segoe UI", 10),
            bg="#1e1e2e",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            selectbackground="#45475a",
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        
        # Configure tags for message styling
        self._chat_display.tag_configure(
            "human", 
            foreground="#89b4fa",
            font=("Segoe UI", 10, "bold")
        )
        self._chat_display.tag_configure(
            "agent", 
            foreground="#a6e3a1",
            font=("Segoe UI", 10, "bold")
        )
        self._chat_display.tag_configure(
            "system", 
            foreground="#6c7086",
            font=("Segoe UI", 9, "italic")
        )
        self._chat_display.tag_configure(
            "timestamp", 
            foreground="#585b70",
            font=("Segoe UI", 8)
        )
        self._chat_display.tag_configure(
            "typing",
            foreground="#f9e2af",
            font=("Segoe UI", 9, "italic")
        )
        
        # Input area
        self._input_frame = ttk.Frame(self)
        
        self._message_var = tk.StringVar()
        self._message_entry = ttk.Entry(
            self._input_frame,
            textvariable=self._message_var,
            font=("Segoe UI", 10),
        )
        
        self._send_button = ttk.Button(
            self._input_frame,
            text="Send",
            command=self._send_message,
            width=8,
        )
    
    def _setup_layout(self):
        """Setup widget layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Chat display
        self._chat_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._chat_frame.columnconfigure(0, weight=1)
        self._chat_frame.rowconfigure(0, weight=1)
        self._chat_display.grid(row=0, column=0, sticky="nsew")
        
        # Input area
        self._input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        self._input_frame.columnconfigure(0, weight=1)
        self._message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._send_button.grid(row=0, column=1)
    
    def _bind_events(self):
        """Bind keyboard events."""
        self._message_entry.bind("<Return>", lambda e: self._send_message())
    
    def _send_message(self):
        """Send the current message."""
        text = self._message_var.get().strip()
        if text and self._on_send_message:
            self._on_send_message(text)
            self._message_var.set("")
    
    def add_message(
        self, 
        sender: str, 
        text: str, 
        timestamp: Optional[datetime] = None
    ):
        """
        Add a message to the chat display.
        
        Args:
            sender: 'human', 'agent', or 'system'
            text: Message text
            timestamp: Optional timestamp (default: now)
        """
        self._hide_typing_indicator()
        
        timestamp = timestamp or datetime.now()
        time_str = timestamp.strftime("%H:%M")
        
        self._chat_display.configure(state=tk.NORMAL)
        
        # Add timestamp
        self._chat_display.insert(tk.END, f"[{time_str}] ", "timestamp")
        
        # Add sender name
        if sender == "human":
            self._chat_display.insert(tk.END, "You: ", "human")
        elif sender == "agent":
            self._chat_display.insert(tk.END, "Agent: ", "agent")
        else:
            self._chat_display.insert(tk.END, "System: ", "system")
        
        # Add message text
        self._chat_display.insert(tk.END, f"{text}\n")
        
        self._chat_display.configure(state=tk.DISABLED)
        self._chat_display.see(tk.END)
    
    def show_typing_indicator(self, sender: str = "agent"):
        """Show typing indicator."""
        if self._typing_indicator_visible:
            return
        
        self._typing_indicator_visible = True
        self._chat_display.configure(state=tk.NORMAL)
        self._chat_display.insert(tk.END, f"{sender.capitalize()} is typing...\n", "typing")
        self._chat_display.configure(state=tk.DISABLED)
        self._chat_display.see(tk.END)
    
    def _hide_typing_indicator(self):
        """Hide typing indicator if visible."""
        if not self._typing_indicator_visible:
            return
        
        self._typing_indicator_visible = False
        self._chat_display.configure(state=tk.NORMAL)
        
        # Find and remove typing indicator line
        content = self._chat_display.get("1.0", tk.END)
        lines = content.split("\n")
        
        # Remove last typing indicator line
        for i in range(len(lines) - 1, -1, -1):
            if "is typing..." in lines[i]:
                # Calculate line position
                line_start = f"{i + 1}.0"
                line_end = f"{i + 2}.0"
                self._chat_display.delete(line_start, line_end)
                break
        
        self._chat_display.configure(state=tk.DISABLED)
    
    def clear(self):
        """Clear all messages."""
        self._chat_display.configure(state=tk.NORMAL)
        self._chat_display.delete("1.0", tk.END)
        self._chat_display.configure(state=tk.DISABLED)
        self._typing_indicator_visible = False
    
    def set_on_send_message(self, callback: Callable[[str], None]):
        """Set the message send callback."""
        self._on_send_message = callback
    
    def focus_input(self):
        """Focus the message input field."""
        self._message_entry.focus_set()

