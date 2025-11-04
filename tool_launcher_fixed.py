"""
Tool Launcher Application
Main entry point - separates GUI from business logic
"""
import customtkinter as ctk
from tool_launcher_gui import ToolLauncherGUI

if __name__ == "__main__":
    app = ToolLauncherGUI()
    app.run()
