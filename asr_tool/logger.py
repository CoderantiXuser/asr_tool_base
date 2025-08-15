from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text

# --- Global Console Object ---
custom_theme = Theme({
    "info": "cyan", "warning": "yellow", "error": "bold red",
    "critical": "bold white on red", "debug": "dim"
})
console = Console(theme=custom_theme)

# --- General Logging ---
def log_message(message, level="info"):
    console.log(message, style=level)

# --- Live Status Display ---
class StatusDisplay:
    def __init__(self):
        self._status_text = "Initializing..."
        self._partial_text = ""
        self._predictions = []
        self._live = Live(self._generate_layout(), console=console, auto_refresh=False, vertical_overflow="visible")

    def _generate_layout(self):
        """Generates the rich layout with status, partial text, and predictions."""
        grid = Table.grid(expand=True)
        grid.add_column(min_width=28) # Status column
        grid.add_column(ratio=1)    # Main content column
        
        # Status Panel
        status_panel = Panel(self._status_text, title="[b]Status[/b]", border_style="blue", width=30)
        
        # Main Content (Partial Text + Predictions)
        main_content_grid = Table.grid(expand=True)
        main_content_grid.add_row(Panel(self._partial_text, title="[b]Live Text[/b]", border_style="green"))
        
        if self._predictions:
            prediction_text = Text(" ".join(self._predictions), style="dim")
            main_content_grid.add_row(Panel(prediction_text, title="[b]Suggestions[/b]", border_style="yellow"))
        
        grid.add_row(status_panel, main_content_grid)
        return grid

    def start(self):
        self._live.start()
        log_message("Rich display initialized.", level="info")

    def stop(self):
        self._live.stop()
        console.print("[bold green]Display stopped.[/bold green]")

    def update(self, status_text=None, partial_text=None, predictions=None):
        """Updates the live display with new data."""
        if status_text is not None:
            self._status_text = status_text
        if partial_text is not None:
            self._partial_text = partial_text
        if predictions is not None:
            self._predictions = predictions
        
        self._live.update(self._generate_layout(), refresh=True)

# These are now obsolete but kept for backward compatibility if needed.
def display_partial(text, *args, **kwargs): pass
def clear_partial(): pass

# Global instance for the status display
status_display = StatusDisplay()
