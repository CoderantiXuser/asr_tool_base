import tkinter as tk
import threading
import time

class NotificationOverlay:
    def __init__(self):
        self.root = None
        self.label = None
        self.thread = None
        self.message_queue = []
        self.queue_lock = threading.Lock()
        self.running = False
        self.fade_job = None

        self.themes = {
            'dark': {'bg': '#282c34', 'fg': '#abb2bf'},
            'light': {'bg': '#f0f0f0', 'fg': '#333333'},
            'colorful': {'bg': '#003366', 'fg': '#ffcc00'}
        }
        self.positions = {'top': self._pos_top, 'bottom': self._pos_bottom, 'center': self._pos_center}
        self.current_theme = 'dark'
        self.current_position = 'top'

    def _run_tk(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.0) # Start fully transparent

        theme_colors = self.themes[self.current_theme]
        self.label = tk.Label(self.root, text="", font=("Arial", 20, "bold"), fg=theme_colors['fg'], bg=theme_colors['bg'], padx=20, pady=10)
        self.label.pack()

        self._update_position()
        self.root.deiconify()
        self.running = True
        self._process_queue()
        self.root.mainloop()

    def _fade(self, alpha_target, duration=300, steps=20):
        """Generic fade function."""
        if self.fade_job:
            self.root.after_cancel(self.fade_job)

        current_alpha = self.root.attributes('-alpha')
        delta = (alpha_target - current_alpha) / steps
        step_duration = duration // steps

        def _animate_step(current_step):
            if current_step > steps:
                self.root.attributes('-alpha', alpha_target)
                return

            new_alpha = current_alpha + delta * current_step
            self.root.attributes('-alpha', new_alpha)
            self.fade_job = self.root.after(step_duration, lambda: _animate_step(current_step + 1))

        _animate_step(1)

    def _update_position(self):
        pos_func = self.positions.get(self.current_position, self._pos_top)
        pos_func()

    def _pos_top(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = 50
        self.root.geometry(f"+{x}+{y}")

    def _pos_bottom(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = self.root.winfo_screenheight() - self.root.winfo_height() - 50
        self.root.geometry(f"+{x}+{y}")

    def _pos_center(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

    def set_theme(self, theme_name):
        if theme_name in self.themes:
            self.current_theme = theme_name
            if self.label:
                theme_colors = self.themes[self.current_theme]
                self.label.config(fg=theme_colors['fg'], bg=theme_colors['bg'])

    def set_position(self, position_name):
        if position_name in self.positions:
            self.current_position = position_name
            if self.root:
                self._update_position()

    def _process_queue(self):
        if not self.running: return
        with self.queue_lock:
            if self.message_queue:
                message, color, duration = self.message_queue.pop(0)
                self._update_label(message, color)
                if duration > 0:
                    self.root.after(int(duration * 1000), self._clear_after_delay)
        self.root.after(100, self._process_queue)

    def _update_label(self, message, color):
        if self.label and self.running:
            self.label.config(text=message)
            theme_fg = self.themes[self.current_theme]['fg']
            self.label.config(fg=color if color != "white" else theme_fg)
            self._update_position()
            if message:
                self._fade(0.9)
            else:
                self._fade(0.0)

    def _clear_after_delay(self):
        if self.label and self.running:
            with self.queue_lock:
                if not self.message_queue:
                    self._update_label("", "white")

    def start(self):
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run_tk, daemon=True)
            self.thread.start()
            time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except tk.TclError:
                # This can happen if the window is already destroyed, which is fine.
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)

    def show_message(self, message, color="white", duration=0):
        if not self.running: self.start()
        with self.queue_lock:
            if duration == 0: self.message_queue.clear()
            self.message_queue.append((message, color, duration))

    def hide_message(self):
        self.show_message("", duration=0)

overlay = NotificationOverlay()
