"""
Game Launcher Dialog.

Combined dialog for configuring both:
- Agent selection (NegoChat or custom plugin)
- Game configuration (issues and quantities)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

from ...domain.models import GameSpec
from ...domain.games.multi_issue import MultiIssueBargainingGame
from ...plugins.plugin_loader import (
    AgentInfo,
    get_agent_info_from_path,
    create_agent_from_path,
)
from ...agent_api.base import NegotiationAgent


@dataclass
class LauncherResult:
    """Result from the game launcher dialog."""
    agent: NegotiationAgent
    game: GameSpec


class GameLauncherDialog:
    """
    Unified launcher dialog for IAGO Negotiation Platform.
    
    Handles both agent selection and game configuration in one interface.
    """
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("IAGO Negotiation Platform")
        self.root.geometry("580x720")
        self.root.resizable(True, True)
        
        # Result storage
        self.result: Optional[LauncherResult] = None
        self._cancelled = False
        
        # Agent data - will be set when user browses for a file
        self._selected_agent_info: Optional[AgentInfo] = None
        
        # Game config state
        self._issue_frames: List[tk.Frame] = []
        self._issue_widgets: List[Dict[str, Any]] = []
        
        self._setup_ui()
        
        # Center dialog
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
    def _setup_ui(self):
        """Create dialog UI elements."""
        # Main container with padding
        main_frame = tk.Frame(self.root, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title Header
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title = tk.Label(
            title_frame, 
            text="🎯 IAGO Negotiation Platform", 
            font=("Helvetica", 20, "bold"),
            fg="#2c3e50"
        )
        title.pack()
        
        subtitle = tk.Label(
            title_frame,
            text="Configure your negotiation session",
            font=("Helvetica", 11),
            fg="#7f8c8d"
        )
        subtitle.pack()
        
        # ═══════════════════════════════════════════════════════════
        # AGENT SELECTION SECTION
        # ═══════════════════════════════════════════════════════════
        agent_frame = tk.LabelFrame(
            main_frame, 
            text=" 🤖 Agent Selection ", 
            padx=15, 
            pady=10,
            font=("Helvetica", 11, "bold")
        )
        agent_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Selected agent info (no dropdown, just current selection)
        self._selected_agent_info: Optional[AgentInfo] = None
        
        # Agent selection row
        selection_frame = tk.Frame(agent_frame)
        selection_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            selection_frame, 
            text="Opponent Agent:", 
            font=("Helvetica", 11)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Agent name label (shows currently selected agent)
        self._agent_name_label = tk.Label(
            selection_frame,
            text="(None selected)",
            font=("Helvetica", 11, "bold"),
            fg="#e74c3c"
        )
        self._agent_name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Browse button to load agent from file
        browse_btn = tk.Button(
            selection_frame,
            text="Browse...",
            command=self._on_browse_agent,
            font=("Helvetica", 10),
            width=10
        )
        browse_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Agent description
        desc_frame = tk.Frame(agent_frame)
        desc_frame.pack(fill=tk.X, pady=(10, 5))
        
        self._agent_desc_label = tk.Label(
            desc_frame,
            text="Click 'Browse...' to select an agent Python file.",
            font=("Helvetica", 10),
            fg="#7f8c8d",
            wraplength=500,
            justify=tk.LEFT
        )
        self._agent_desc_label.pack(anchor="w")
        
        # ═══════════════════════════════════════════════════════════
        # GAME CONFIGURATION SECTION
        # ═══════════════════════════════════════════════════════════
        game_outer_frame = tk.LabelFrame(
            main_frame, 
            text=" 🎮 Game Configuration ", 
            padx=15, 
            pady=10,
            font=("Helvetica", 11, "bold")
        )
        game_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Use Default vs Custom toggle
        toggle_frame = tk.Frame(game_outer_frame)
        toggle_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._use_default_var = tk.BooleanVar(value=False)
        
        default_radio = tk.Radiobutton(
            toggle_frame,
            text="Use default game (3 fruits: Apples, Oranges, Bananas)",
            variable=self._use_default_var,
            value=True,
            command=self._on_game_mode_changed,
            font=("Helvetica", 10)
        )
        default_radio.pack(anchor="w")
        
        custom_radio = tk.Radiobutton(
            toggle_frame,
            text="Configure custom game",
            variable=self._use_default_var,
            value=False,
            command=self._on_game_mode_changed,
            font=("Helvetica", 10)
        )
        custom_radio.pack(anchor="w")
        
        # Custom game config container
        self._custom_config_frame = tk.Frame(game_outer_frame)
        self._custom_config_frame.pack(fill=tk.BOTH, expand=True)
        
        # Number of Issues Selection
        config_row = tk.Frame(self._custom_config_frame)
        config_row.pack(fill=tk.X, pady=(5, 10))
        
        tk.Label(
            config_row, 
            text="Number of Issues (1-10):", 
            font=("Helvetica", 10)
        ).pack(side=tk.LEFT, padx=5)
        
        self._num_issues_var = tk.IntVar(value=3)
        
        self._num_scale = tk.Scale(
            config_row,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            variable=self._num_issues_var,
            command=lambda v: self._refresh_issue_inputs(),
            length=180
        )
        self._num_scale.pack(side=tk.LEFT, padx=10)
        
        # Issues Container with scrollbar
        issues_container = tk.Frame(self._custom_config_frame)
        issues_container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbar
        self._canvas = tk.Canvas(issues_container, highlightthickness=0, bg='#fafafa', height=200)
        scrollbar = tk.Scrollbar(issues_container, orient="vertical", command=self._canvas.yview)
        
        self._issues_frame = tk.Frame(self._canvas, bg='#fafafa')
        
        self._canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._canvas_window = self._canvas.create_window((0, 0), window=self._issues_frame, anchor="nw")
        
        # Bind resize events
        self._issues_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mouse wheel scrolling
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)
        
        # Generate initial issue inputs
        self._refresh_issue_inputs()
        
        # ═══════════════════════════════════════════════════════════
        # BUTTONS
        # ═══════════════════════════════════════════════════════════
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        cancel_btn = tk.Button(
            btn_frame, 
            text="Cancel", 
            command=self._on_cancel,
            width=12,
            font=("Helvetica", 11)
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        start_btn = tk.Button(
            btn_frame, 
            text="Start Game", 
            command=self._on_submit,
            width=14,
            font=("Helvetica", 11, "bold"),
            bg="#27ae60",
            fg="white",
            activebackground="#2ecc71",
            activeforeground="white"
        )
        start_btn.pack(side=tk.RIGHT, padx=5)
        
    def _on_browse_agent(self):
        """Open file dialog to select an agent Python file."""
        file_path = filedialog.askopenfilename(
            parent=self.root,
            title="Select Agent Python File",
            filetypes=[
                ("Python files", "*.py"),
                ("All files", "*.*")
            ],
            initialdir="."
        )
        
        if not file_path:
            return  # User cancelled
        
        # Try to load agent info from the selected file
        agent_info = get_agent_info_from_path(file_path)
        
        if agent_info is None:
            messagebox.showerror(
                "Invalid Agent File",
                f"Could not load a valid NegotiationAgent from:\n{file_path}\n\n"
                "Make sure the file contains a class that extends NegotiationAgent.",
                parent=self.root
            )
            return
        
        # Set as the selected agent (replaces any previous selection)
        self._selected_agent_info = agent_info
        
        # Update the UI
        self._agent_name_label.config(
            text=agent_info.name,
            fg="#27ae60"  # Green color to indicate valid selection
        )
        self._agent_desc_label.config(
            text=f"📁 {agent_info.description}",
            fg="#555555"
        )
                
    def _on_game_mode_changed(self):
        """Show/hide custom config based on selection."""
        if self._use_default_var.get():
            # Hide custom config
            for child in self._custom_config_frame.winfo_children():
                child.pack_forget()
        else:
            # Show custom config - re-pack all children
            for child in self._custom_config_frame.winfo_children():
                if child.winfo_class() == 'Frame':
                    child.pack(fill=tk.BOTH, expand=True)
            self._refresh_issue_inputs()
        
    def _on_frame_configure(self, event):
        """Reset scroll region when frame size changes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        """Resize frame to canvas width."""
        self._canvas.itemconfig(self._canvas_window, width=event.width)
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    def _refresh_issue_inputs(self):
        """Re-generate input fields based on number of issues."""
        try:
            num = self._num_issues_var.get()
            if num < 1: 
                num = 1
            if num > 10: 
                num = 10
        except (ValueError, tk.TclError):
            return

        # Clear existing
        for widget in self._issues_frame.winfo_children():
            widget.destroy()
        self._issue_widgets.clear()
        self._issue_frames.clear()
        
        # Create header row
        header_frame = tk.Frame(self._issues_frame, bg='#fafafa')
        header_frame.pack(fill=tk.X, pady=(5, 10))
        
        tk.Label(
            header_frame, 
            text="Issue Name", 
            font=("Helvetica", 10, "bold"), 
            bg='#fafafa', 
            width=20, 
            anchor='w'
        ).pack(side=tk.LEFT, padx=(10, 20))
        
        tk.Label(
            header_frame, 
            text="Quantity (1-20)", 
            font=("Helvetica", 10, "bold"), 
            bg='#fafafa', 
            anchor='w'
        ).pack(side=tk.LEFT)
        
        # Default names
        defaults = [
            "Apples", "Oranges", "Bananas", "Pears", "Grapes", 
            "Melons", "Berries", "Kiwis", "Mangos", "Plums"
        ]
        
        for i in range(num):
            default_name = defaults[i] if i < len(defaults) else f"Item {i+1}"
            default_qty = random.randint(3, 8)
            
            row_frame = tk.Frame(self._issues_frame, bg='#fafafa')
            row_frame.pack(fill=tk.X, pady=3)
            
            # Name Entry
            name_var = tk.StringVar(value=default_name)
            name_entry = tk.Entry(
                row_frame, 
                textvariable=name_var, 
                width=22, 
                font=("Helvetica", 10)
            )
            name_entry.pack(side=tk.LEFT, padx=(10, 20))
            
            # Quantity Spinbox
            qty_var = tk.IntVar(value=default_qty)
            qty_spin = tk.Spinbox(
                row_frame, 
                from_=1, 
                to=20, 
                textvariable=qty_var, 
                width=5, 
                font=("Helvetica", 10)
            )
            qty_spin.pack(side=tk.LEFT)
            
            self._issue_widgets.append({
                "name": name_var,
                "qty": qty_var
            })
            self._issue_frames.append(row_frame)
        
        # Force update
        self._issues_frame.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _create_default_game(self) -> GameSpec:
        """Create the default 3-fruit game."""
        return MultiIssueBargainingGame.create(
            name="default_game",
            description="Classic resource exchange negotiation",
            items=[
                {"name": "apples", "display_name": "Apples", "singular_name": "Apple", "quantity": 5},
                {"name": "oranges", "display_name": "Oranges", "singular_name": "Orange", "quantity": 3},
                {"name": "bananas", "display_name": "Bananas", "singular_name": "Banana", "quantity": 4},
            ],
            agent_values={"apples": 10, "oranges": 4, "bananas": 2},
            human_values={"apples": 2, "oranges": 4, "bananas": 10},
            deadline_seconds=300,
            allow_partial=True
        )
        
    def _create_custom_game(self) -> Optional[GameSpec]:
        """Create game from custom configuration."""
        items = []
        seen_names = set()
        
        for i, widgets in enumerate(self._issue_widgets):
            name = widgets["name"].get().strip()
            try:
                qty = widgets["qty"].get()
            except (ValueError, tk.TclError):
                messagebox.showerror(
                    "Error", 
                    f"Invalid quantity for issue {i+1}", 
                    parent=self.root
                )
                return None
                
            if not name:
                messagebox.showerror(
                    "Error", 
                    f"Issue {i+1} must have a name", 
                    parent=self.root
                )
                return None
            if qty < 1 or qty > 20:
                messagebox.showerror(
                    "Error", 
                    f"Quantity for '{name}' must be between 1 and 20", 
                    parent=self.root
                )
                return None
            
            # Check for duplicate names
            name_key = name.lower().replace(" ", "_")
            if name_key in seen_names:
                messagebox.showerror(
                    "Error", 
                    f"Duplicate issue name: '{name}'", 
                    parent=self.root
                )
                return None
            seen_names.add(name_key)
                
            items.append({
                "name": name_key,
                "display_name": name,
                "singular_name": name.rstrip('s') if name.endswith('s') else name,
                "quantity": qty
            })
            
        # Generate Utilities with opposing preferences
        agent_values = {}
        human_values = {}
        
        num_items = len(items)
        
        # Shuffle indices to randomize which party prefers what
        indices = list(range(num_items))
        random.shuffle(indices)
        
        # Split: first half agent prefers, second half human prefers
        mid = num_items // 2
        if mid == 0:
            mid = 1  # Ensure at least some split for 1-2 items
        
        agent_preferred = set(indices[:mid])
        
        for idx, item in enumerate(items):
            item_name = item["name"]
            
            # Generate values
            high_val = random.randint(8, 12)
            low_val = random.randint(2, 5)
            
            if idx in agent_preferred:
                agent_values[item_name] = high_val
                human_values[item_name] = low_val
            else:
                agent_values[item_name] = low_val
                human_values[item_name] = high_val
                
        try:
            return MultiIssueBargainingGame.create(
                name="custom_game",
                description="Custom user-configured negotiation",
                items=items,
                agent_values=agent_values,
                human_values=human_values,
                deadline_seconds=300,
                allow_partial=True
            )
        except Exception as e:
            messagebox.showerror(
                "Error", 
                f"Failed to create game: {str(e)}", 
                parent=self.root
            )
            return None

    def _on_submit(self):
        """Validate and create the agent + game."""
        # Check if agent is selected
        if self._selected_agent_info is None:
            messagebox.showerror(
                "No Agent Selected", 
                "Please select an agent first.\n\n"
                "Click 'Browse...' to load an agent from a Python file.", 
                parent=self.root
            )
            return
        
        # Load agent from file path
        file_path = self._selected_agent_info.id[5:]  # Remove "file:" prefix
        agent = create_agent_from_path(file_path)
        
        if agent is None:
            messagebox.showerror(
                "Error", 
                f"Failed to load agent: {self._selected_agent_info.name}", 
                parent=self.root
            )
            return
        
        # Create game
        if self._use_default_var.get():
            game = self._create_default_game()
        else:
            game = self._create_custom_game()
            
        if game is None:
            return  # Error already shown
            
        self.result = LauncherResult(agent=agent, game=game)
        self.root.quit()

    def _on_cancel(self):
        """Handle cancel/close."""
        self._cancelled = True
        self.result = None
        self.root.quit()
    
    def run(self) -> Optional[LauncherResult]:
        """Run the dialog and return the result."""
        self.root.mainloop()
        
        # Unbind mousewheel events before destroying
        try:
            self.root.unbind_all("<MouseWheel>")
            self.root.unbind_all("<Button-4>")
            self.root.unbind_all("<Button-5>")
        except:
            pass
            
        self.root.destroy()
        return self.result

    @classmethod
    def show(cls, plugin_dir: str = "plugins") -> Optional[LauncherResult]:
        """Show the dialog and return the result if submitted."""
        dialog = cls(plugin_dir=plugin_dir)
        return dialog.run()


# Keep backward compatibility alias
GameConfigDialog = GameLauncherDialog
