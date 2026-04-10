import customtkinter as ctk
from tool_launcher_gui import ToolLauncherGUI

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = ToolLauncherGUI()
    app.run()