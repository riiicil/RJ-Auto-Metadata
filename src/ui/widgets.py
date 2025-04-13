# RJ Auto Metadata
# Copyright (C) 2025 Riiicil
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# src/ui/widgets.py
import customtkinter as ctk
import tkinter as tk

class ToolTip:
    """
    Kelas untuk menampilkan tooltip pada widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#2d2d30" if is_dark else "#f0f0f5"
        fg_color = "#ffffff" if is_dark else "#000000"
        
        frame = tk.Frame(self.tooltip_window, background=bg_color, borderwidth=1, relief="solid")
        frame.pack(ipadx=5, ipady=5)
        
        label = tk.Label(frame, text=self.text, background=bg_color, foreground=fg_color, 
                        wraplength=250, justify="left", font=("Segoe UI", 9))
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None