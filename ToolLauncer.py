import customtkinter as ctk
import json
import os
import sys
import subprocess
import webbrowser
import platform
from typing import Dict, List, Optional, Any, Tuple

# Set appearance mode and color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ToolLauncher:
    """
    A GUI application for launching and managing various tools including folders,
    Python projects, batch files, and web pages. Supports multiple configurations
    with add, edit, delete, and search functionality.
    """
    
    def __init__(self) -> None:
        """Initialize the Tool Launcher application with GUI components and data structures."""
        self.root = ctk.CTk()
        self.root.title("Tool Launcher")
        self.root.geometry("350x600")  # Initial size
        self.root.resizable(True, True)  # Make resizable
        self.root.minsize(200, 400)  # Minimum size to prevent too small
        
        # Configs list file path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.configs_list_file = os.path.join(script_dir, "configs_list.json")
        print(f"Looking for configs_list.json in: {self.configs_list_file}")  # Debug
        
        # Initialize default configs if first run (files don't exist)
        self.initialize_defaults(script_dir)
        
        # Load configs list
        self.configs_list: List[Dict[str, str]] = self.load_configs_list()
        self.current_config: Optional[Dict[str, str]] = None
        self.json_file: Optional[str] = None
        self.raw_data: Dict[str, Any] = {}  # Initialize empty
        self.grouped_data: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        self.search_query: str = ""
        
        # Main content frame (takes full space)
        self.content_frame = ctk.CTkFrame(self.root)
        self.content_frame.pack(side="left", fill="both", expand=True)
        
        # Create header frame inside content_frame with grid layout
        self.header_frame = ctk.CTkFrame(self.content_frame)
        self.header_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        # Configure grid for dynamic wrapping
        self.header_frame.grid_columnconfigure(0, weight=0)  # Title
        self.header_frame.grid_columnconfigure(1, weight=1)  # Config combo (expandable)
        self.header_frame.grid_columnconfigure(2, weight=0)  # Toggle button
        self.header_frame.grid_columnconfigure(3, weight=0)  # Refresh button
        self.header_frame.grid_columnconfigure(4, weight=0)  # Add button
        self.header_frame.grid_rowconfigure(0, weight=0)
        self.header_frame.grid_rowconfigure(1, weight=0)  # For search bar
        

        # Config selector combobox
        config_names = [config['name'] for config in self.configs_list if 'name' in config] or ["No Configs"]
        self.config_combo = ctk.CTkComboBox(
            self.header_frame,
            values=config_names,
            width=150,
            command=self.on_config_select
        )
        self.config_combo.grid(row=0, column=0, pady=10, padx=5, sticky="ew")
        
        # Toggle sidebar button (now for adding new config)
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="📝",
            width=40,
            height=30,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.show_sidebar_for_add_config
        )
        self.toggle_btn.grid(row=0, column=1, pady=10, padx=2)
        
        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            self.header_frame,
            text="↻",
            width=40,
            height=30,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.refresh_data
        )
        self.refresh_btn.grid(row=0, column=2, pady=10, padx=2)
        
        # Add new button
        self.add_btn = ctk.CTkButton(
            self.header_frame,
            text="➕",
            width=40,
            height=30,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.show_sidebar_for_add
        )
        self.add_btn.grid(row=0, column=3, pady=10, padx=(2, 10))
        
        # Search bar (spans all columns)
        self.search_entry = ctk.CTkEntry(
            self.header_frame,
            placeholder_text="Search by name or path...",
            height=30
        )
        self.search_entry.grid(row=1, column=0, columnspan=5, pady=(0, 10), padx=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # Create scrollable frame inside content_frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self.content_frame)
        self.scrollable_frame.pack(pady=(0, 20), padx=10, fill="both", expand=True)
        
        # Sidebar (not packed, only placed, parented to root)
        self.sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        self.sidebar_visible = False
        
        # Sidebar content (dynamic based on mode)
        self.sidebar_title = ctk.CTkLabel(self.sidebar, text="Add/Edit Item", font=ctk.CTkFont(size=16, weight="bold"))
        self.sidebar_title.pack(pady=10)
        
        # Message label
        self.msg_label = ctk.CTkLabel(self.sidebar, text="")
        self.msg_label.pack(pady=5)
        
        # Config name field (for add config mode)
        self.config_name_entry = ctk.CTkEntry(self.sidebar, width=230, placeholder_text="Config Name")
        self.config_name_entry.pack(pady=5)
        
        # Config path field (for add config mode)
        self.config_path_entry = ctk.CTkEntry(self.sidebar, width=230, placeholder_text="Config Path (optional)")
        self.config_path_entry.pack(pady=5)
        
        # Category field (for add/edit item)
        self.cat_label = ctk.CTkLabel(self.sidebar, text="Category:")
        self.cat_entry = ctk.CTkEntry(self.sidebar, width=230)
        self.cat_label.pack(pady=5)
        self.cat_entry.pack(pady=5)
        
        # Type field (for add/edit item)
        self.type_label = ctk.CTkLabel(self.sidebar, text="Type:")
        self.type_combo = ctk.CTkComboBox(self.sidebar, values=["folder", "python project", "bat file", "web page"], width=230)
        self.type_label.pack(pady=5)
        self.type_combo.pack(pady=5)
        self.type_combo.set("folder")  # Default
        
        # Name field (for add/edit item)
        self.name_label = ctk.CTkLabel(self.sidebar, text="Name:")
        self.name_entry = ctk.CTkEntry(self.sidebar, width=230)
        self.name_label.pack(pady=5)
        self.name_entry.pack(pady=5)
        
        # Path field (for add/edit item)
        self.path_label = ctk.CTkLabel(self.sidebar, text="Path:")
        self.path_entry = ctk.CTkEntry(self.sidebar, width=230)
        self.path_label.pack(pady=5)
        self.path_entry.pack(pady=5)
        
        # Sidebar buttons
        sidebar_button_frame = ctk.CTkFrame(self.sidebar)
        sidebar_button_frame.pack(pady=10, fill="x", padx=10)
        self.save_btn = ctk.CTkButton(sidebar_button_frame, text="Save", command=self.submit_sidebar)
        self.save_btn.pack(side="left", padx=5)
        self.cancel_btn = ctk.CTkButton(sidebar_button_frame, text="Cancel", command=self.hide_sidebar)
        self.cancel_btn.pack(side="left", padx=5)
        
        # Mode for sidebar
        self.sidebar_mode: str = "item_add"  # 'item_add', 'item_edit', 'config_add'
        
        # Editing mode flags
        self.editing_mode: bool = False
        self.edit_category: Optional[str] = None
        self.edit_type: Optional[str] = None
        self.edit_index: Optional[int] = None
        self.edit_item: Optional[Dict[str, str]] = None
        
        # Deleting mode flags
        self.deleting_mode: bool = False
        self.delete_category: Optional[str] = None
        self.delete_type: Optional[str] = None
        self.delete_index: Optional[int] = None
        
        # Load initial config
        if config_names and config_names[0] != "No Configs":
            self.config_combo.set(config_names[0])
            self.on_config_select(config_names[0])
        else:
            self.current_config = {"name": "No Configs", "config_path": None}
            self.json_file = None
            self.root.title("Tool Launcher - No Configs")
            self.refresh_data()  # Load empty for No Configs
        
        # Bind window resize to check for button wrapping
        self.root.bind("<Configure>", self.on_window_resize)
        
    def on_window_resize(self, event: Any) -> None:
        """
        Handle window resize events to adjust header layout.
        
        Args:
            event: The configure event from tkinter
        """
        # This is called on every resize; grid handles wrapping automatically
        # with proper weight configuration, so no manual intervention needed
        pass
    
    def show_sidebar_for_add_config(self) -> None:
        """Show the sidebar in 'add new config' mode with empty fields."""
        self.sidebar_mode = "config_add"
        self.sidebar_title.configure(text="Add New Config")
        self.msg_label.configure(text="")
        self.config_name_entry.delete(0, "end")
        self.config_path_entry.delete(0, "end")
        # Hide item fields
        self.cat_label.pack_forget()
        self.cat_entry.pack_forget()
        self.type_label.pack_forget()
        self.type_combo.pack_forget()
        self.name_label.pack_forget()
        self.name_entry.pack_forget()
        self.path_label.pack_forget()
        self.path_entry.pack_forget()
        # Show config fields
        self.config_name_entry.pack(pady=5)
        self.config_path_entry.pack(pady=5)
        self.save_btn.configure(command=self.submit_add_config)
        self.animate_sidebar_in()
    
    def toggle_sidebar(self) -> None:
        """Toggle the visibility of the sidebar for adding/editing items."""
        if self.sidebar_visible:
            self.hide_sidebar()
        else:
            self.show_sidebar_for_add()
    
    def show_sidebar_for_add(self) -> None:
        """Show the sidebar in 'add new item' mode with empty fields."""
        if not self.json_file:
            ctk.CTkMessageBox(self.root, title="Error", message="No config selected. Please select a config first.", icon="warning")
            return
        self.sidebar_mode = "item_add"
        self.sidebar_title.configure(text="Add New Item")
        self.msg_label.configure(text="")
        self.cat_entry.delete(0, "end")
        self.type_combo.set("folder")
        self.name_entry.delete(0, "end")
        self.path_entry.delete(0, "end")
        self.cat_entry.configure(state="normal")
        self.type_combo.configure(state="normal")
        # Hide config fields
        self.config_name_entry.pack_forget()
        self.config_path_entry.pack_forget()
        # Show item fields
        self.cat_label.pack(pady=5)
        self.cat_entry.pack(pady=5)
        self.type_label.pack(pady=5)
        self.type_combo.pack(pady=5)
        self.name_label.pack(pady=5)
        self.name_entry.pack(pady=5)
        self.path_label.pack(pady=5)
        self.path_entry.pack(pady=5)
        self.save_btn.configure(command=self.submit_sidebar)
        self.animate_sidebar_in()
    
    def show_sidebar_for_edit(self, category: str, item_type: str, item_index: int, current_item: Dict[str, str]) -> None:
        """
        Show the sidebar in 'edit item' mode with pre-filled fields.
        
        Args:
            category: The category of the item to edit
            item_type: The type of the item to edit
            item_index: The index of the item in its type list
            current_item: The current item data dictionary
        """
        if not self.json_file:
            return  # Safety check
        
        # Ensure raw_data is loaded
        if not self.raw_data:
            self.refresh_data()
        
        self.sidebar_mode = "item_edit"
        self.editing_mode = True
        self.deleting_mode = False
        self.edit_category = category
        self.edit_type = item_type
        self.edit_index = item_index
        self.edit_item = current_item
        self.sidebar_title.configure(text="Edit Item")
        self.msg_label.configure(text="")
        self.cat_entry.delete(0, "end")
        self.cat_entry.insert(0, category)
        self.cat_entry.configure(state="disabled")
        self.type_combo.set(item_type)
        self.type_combo.configure(state="disabled")
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, current_item.get('name', 'Unnamed'))
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, current_item.get('path', ''))
        # Hide config fields
        self.config_name_entry.pack_forget()
        self.config_path_entry.pack_forget()
        # Show item fields
        self.cat_label.pack(pady=5)
        self.cat_entry.pack(pady=5)
        self.type_label.pack(pady=5)
        self.type_combo.pack(pady=5)
        self.name_label.pack(pady=5)
        self.name_entry.pack(pady=5)
        self.path_label.pack(pady=5)
        self.path_entry.pack(pady=5)
        self.save_btn.configure(command=self.submit_sidebar)
        self.animate_sidebar_in()
    
    def confirm_delete(self, category: str, item_type: str, item_index: int, item: Dict[str, str]) -> None:
        """
        Show a confirmation dialog for deleting an item.
        
        Args:
            category: The category of the item to delete
            item_type: The type of the item to delete
            item_index: The index of the item in its type list
            item: The item data dictionary
        """
        # Create a simple dialog for confirmation
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Confirm Deletion")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(
            dialog,
            text=f"Delete '{item.get('name', 'Unnamed')}'?",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.pack(pady=20)
        
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)
        
        def on_confirm() -> None:
            """Handle confirmation of deletion."""
            self.delete_item(category, item_type, item_index)
            dialog.destroy()
        
        def on_cancel() -> None:
            """Handle cancellation of deletion."""
            dialog.destroy()
        
        confirm_btn = ctk.CTkButton(button_frame, text="Delete", command=on_confirm, fg_color="red", hover_color="darkred")
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side="left", padx=10)
    
    def delete_item(self, category: str, item_type: str, item_index: int) -> None:
        """
        Delete an item from the configuration and update the UI.
        
        Args:
            category: The category of the item to delete
            item_type: The type of the item to delete
            item_index: The index of the item in its type list
        """
        if not self.json_file:
            print("No config file selected to delete from.")
            return
        
        # Ensure raw_data is loaded
        if not self.raw_data:
            self.raw_data = self.load_json()
        
        # Delete the item from raw_data
        if isinstance(self.raw_data, list):
            # For flat list, find and remove
            cat_lower = category.lower()
            typ_lower = item_type.lower()
            count = 0
            for i in range(len(self.raw_data) - 1, -1, -1):
                item = self.raw_data[i]
                if (item.get('category', '').lower() == cat_lower and
                    item.get('type', '').lower() == typ_lower):
                    if count == item_index:
                        del self.raw_data[i]
                        break
                    count += 1
            nested = self.to_nested(self.raw_data)
        else:  # Nested dict
            cat_lower = category.lower()
            typ_lower = item_type.lower()
            if cat_lower in self.raw_data and typ_lower in self.raw_data[cat_lower]:
                items_list = self.raw_data[cat_lower][typ_lower]
                if isinstance(items_list, list):
                    if 0 <= item_index < len(items_list):
                        del items_list[item_index]
                        # Clean up empty structures
                        if not items_list:
                            del self.raw_data[cat_lower][typ_lower]
                        if not self.raw_data[cat_lower]:
                            del self.raw_data[cat_lower]
                else:  # Single dict
                    del self.raw_data[cat_lower][typ_lower]
                    if not self.raw_data[cat_lower]:
                        del self.raw_data[cat_lower]
            nested = self.raw_data
        
        self.save_json(nested)
        self.refresh_data()
        print(f"Item deleted from {category}/{item_type}")
    
    def hide_sidebar(self) -> None:
        """Hide the sidebar and reset its state."""
        self.animate_sidebar_out()
        # Reset readonly states
        self.cat_entry.configure(state="normal")
        self.type_combo.configure(state="normal")
        self.editing_mode = False
        self.deleting_mode = False
        self.edit_category = None
        self.edit_type = None
        self.edit_index = None
        self.edit_item = None
        self.sidebar_mode = "item_add"
    
    def animate_sidebar_in(self) -> None:
        """Animate the sidebar sliding in from the left."""
        self.sidebar.place(x=0, y=0, relheight=1)
        self.sidebar_visible = True
    
    def animate_sidebar_out(self) -> None:
        """Animate the sidebar sliding out to the left."""
        self.sidebar.place_forget()
        self.sidebar_visible = False
    
    def submit_sidebar(self) -> None:
        """Submit the sidebar form, either adding a new item or editing an existing one."""
        if self.sidebar_mode == "config_add":
            self.submit_add_config()
        elif self.editing_mode:
            self.submit_edit()
        else:
            self.submit_add()
    
    def submit_add_config(self) -> None:
        """Add a new configuration to configs_list.json and create empty config file."""
        config_name = self.config_name_entry.get().strip()
        config_path_input = self.config_path_entry.get().strip()
        
        if not config_name:
            self.msg_label.configure(text="Please enter a config name!", text_color="red")
            return
        
        # Generate default path if not provided
        if not config_path_input:
            safe_name = config_name.lower().replace(" ", "_")
            config_path = os.path.join(os.path.dirname(self.configs_list_file), f"config_{safe_name}.json")
        else:
            config_path = config_path_input
        
        # Use forward slashes for JSON
        config_path = config_path.replace("\\", "/")
        
        # Check if config already exists
        if any(cfg['name'] == config_name for cfg in self.configs_list):
            self.msg_label.configure(text="Config name already exists!", text_color="red")
            return
        
        # Create empty config file
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
        except Exception as e:
            self.msg_label.configure(text=f"Error creating config file: {e}", text_color="red")
            return
        
        # Add to configs_list
        new_config = {"name": config_name, "config_path": config_path}
        self.configs_list.append(new_config)
        
        # Save updated configs_list.json
        try:
            with open(self.configs_list_file, 'w', encoding='utf-8') as f:
                json.dump(self.configs_list, f, indent=2)
        except Exception as e:
            self.msg_label.configure(text=f"Error saving configs list: {e}", text_color="red")
            return
        
        # Update combobox and select new config
        self.config_combo.configure(values=[cfg['name'] for cfg in self.configs_list])
        self.config_combo.set(config_name)
        self.on_config_select(config_name)
        
        self.msg_label.configure(text="New config added successfully!", text_color="green")
        self.after_sidebar_action()
    
    def submit_add(self) -> None:
        """Add a new item to the configuration based on sidebar form data."""
        cat = self.cat_entry.get().strip()
        typ = self.type_combo.get().strip()
        name = self.name_entry.get().strip()
        path = self.path_entry.get().strip()
        
        if not all([cat, typ, name, path]):
            self.msg_label.configure(text="Please fill all fields!", text_color="red")
            return
        
        new_item = {'name': name, 'path': path}
        
        # Ensure raw_data is loaded
        if not self.raw_data:
            self.raw_data = self.load_json()
        
        # Handle raw_data as list or convert dict to list for appending
        if isinstance(self.raw_data, list):
            flat_item = {'category': cat, 'type': typ, 'name': name, 'path': path}
            self.raw_data.append(flat_item)
            nested = self.to_nested(self.raw_data)
        else:  # Nested dict
            cat_lower = cat.lower()
            typ_lower = typ.lower()
            if cat_lower not in self.raw_data:
                self.raw_data[cat_lower] = {}
            if typ_lower not in self.raw_data[cat_lower]:
                self.raw_data[cat_lower][typ_lower] = []
            # Append to list if exists, or set as single dict
            existing = self.raw_data[cat_lower][typ_lower]
            if isinstance(existing, list):
                existing.append(new_item)
            else:
                self.raw_data[cat_lower][typ_lower] = [existing, new_item] if existing else [new_item]
            nested = self.raw_data
        
        self.save_json(nested)
        
        self.msg_label.configure(text="Item added successfully!", text_color="green")
        self.after_sidebar_action()
    
    def submit_edit(self) -> None:
        """Update an existing item in the configuration based on sidebar form data."""
        name = self.name_entry.get().strip()
        path = self.path_entry.get().strip()
        
        if not name or not path:
            self.msg_label.configure(text="Please fill name and path!", text_color="red")
            return
        
        # Ensure raw_data is loaded
        if not self.raw_data:
            self.raw_data = self.load_json()
        
        # Update the item in raw_data
        if isinstance(self.raw_data, list):
            # For flat list, find and update
            for i, flat_item in enumerate(self.raw_data):
                if (flat_item.get('category', '').lower() == self.edit_category.lower() and
                    flat_item.get('type', '').lower() == self.edit_type.lower() and
                    flat_item.get('name') == self.edit_item.get('name') and
                    flat_item.get('path') == self.edit_item.get('path')):
                    self.raw_data[i]['name'] = name
                    self.raw_data[i]['path'] = path
                    break
            nested = self.to_nested(self.raw_data)
        else:  # Nested dict
            cat_lower = self.edit_category.lower()
            typ_lower = self.edit_type.lower()
            items_list = self.raw_data[cat_lower][typ_lower]
            if isinstance(items_list, list):
                items_list[self.edit_index]['name'] = name
                items_list[self.edit_index]['path'] = path
            else:  # Single dict
                self.raw_data[cat_lower][typ_lower]['name'] = name
                self.raw_data[cat_lower][typ_lower]['path'] = path
            nested = self.raw_data
        
        self.save_json(nested)
        
        self.msg_label.configure(text="Item updated successfully!", text_color="green")
        self.after_sidebar_action()
    
    def after_sidebar_action(self) -> None:
        """Perform cleanup actions after a successful sidebar submission."""
        self.refresh_data()
        self.root.after(1000, self.hide_sidebar)  # Hide after 1s
    
    def initialize_defaults(self, script_dir: str) -> None:
        """
        Initialize default configuration files if they don't exist.
        
        Args:
            script_dir: The directory where the script is located
        """
        if os.path.exists(self.configs_list_file):
            return  # Already exists, no need to create
        
        print("First run detected: Creating default configs_list.json and config_default.json")
        
        # Default configs_list.json with one entry
        default_configs_list = [
            {
                "name": "Default Tools",
                "config_path": os.path.join(script_dir, "config_default.json").replace("\\", "/")
            }
        ]
        with open(self.configs_list_file, 'w', encoding='utf-8') as f:
            json.dump(default_configs_list, f, indent=2)
        
        # Default config_default.json with minimal example
        default_config = {
            "example": {
                "web page": {
                    "name": "Sample Site",
                    "path": "https://example.com"
                }
            }
        }
        default_config_path = os.path.join(script_dir, "config_default.json")
        with open(default_config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        
        print("Defaults created successfully.")
    
    def load_configs_list(self) -> List[Dict[str, str]]:
        """
        Load the list of available configurations from configs_list.json.
        
        Returns:
            A list of configuration dictionaries with 'name' and 'config_path' keys
        """
        try:
            with open(self.configs_list_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"Error: {self.configs_list_file} must contain a list.")
                    return []
                return [item for item in data if item and 'name' in item and 'config_path' in item]
        except FileNotFoundError:
            print(f"Error: {self.configs_list_file} not found.")
            return []
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {self.configs_list_file}. Details: {e}")
            return []
    
    def on_config_select(self, selection: str) -> None:
        """
        Handle selection of a configuration from the dropdown.
        
        Args:
            selection: The name of the selected configuration
        """
        for config in self.configs_list:
            if config['name'] == selection:
                self.current_config = config
                self.json_file = config['config_path']
                self.root.title(f"Tool Launcher - {config['name']}")
                self.refresh_data()
                break
    
    def load_json(self) -> Dict[str, Any]:
        """
        Load the current configuration JSON file.
        
        Returns:
            The parsed JSON data as a dictionary or list
        """
        if not self.json_file:
            return {}
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Successfully loaded data from {self.json_file}.")
                return data
        except FileNotFoundError:
            print(f"Error: {self.json_file} not found. Creating empty file.")
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {self.json_file}. Details: {e}")
            return {}
    
    def normalize_grouped(self, data: Any) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """
        Normalize configuration data into a grouped structure.
        
        Args:
            data: Raw configuration data (list or dict format)
            
        Returns:
            A nested dictionary grouped by category and type
        """
        grouped: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        if isinstance(data, list):
            # Backward-compatible: flat array of items
            filtered_data = [item for item in data if item]
            for item in filtered_data:
                category = item.get('category', 'Uncategorized').lower()
                item_type = item.get('type', '').lower()
                if category not in grouped:
                    grouped[category] = {}
                if item_type not in grouped[category]:
                    grouped[category][item_type] = []
                grouped[category][item_type].append(item)
        elif isinstance(data, dict):
            # New dynamic nested structure: {category: {type: {name, path} or [items]}}
            for category, types_dict in data.items():
                category = category.lower()
                if category not in grouped:
                    grouped[category] = {}
                for item_type, type_value in types_dict.items():
                    item_type = item_type.lower()
                    if item_type not in grouped[category]:
                        grouped[category][item_type] = []
                    if isinstance(type_value, dict):
                        # Single item as dict
                        if type_value:  # Ignore empty {}
                            grouped[category][item_type].append(type_value)
                    elif isinstance(type_value, list):
                        # Multiple items as list
                        filtered_items = [item for item in type_value if item]
                        grouped[category][item_type].extend(filtered_items)
        return grouped
    
    def to_nested(self, data_list: List[Dict[str, str]]) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """
        Convert a flat list of items to nested dictionary format.
        
        Args:
            data_list: A list of item dictionaries with category and type keys
            
        Returns:
            A nested dictionary grouped by category and type
        """
        grouped: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        filtered_data = [item for item in data_list if item]
        for item in filtered_data:
            category = item.get('category', 'Uncategorized').lower()
            item_type = item.get('type', '').lower()
            if category not in grouped:
                grouped[category] = {}
            if item_type not in grouped[category]:
                grouped[category][item_type] = []
            grouped[category][item_type].append(item)
        return grouped
    
    def save_json(self, data: Dict[str, Any]) -> None:
        """
        Save configuration data to the current JSON file.
        
        Args:
            data: The configuration data to save
        """
        if not self.json_file:
            print("No config file selected to save.")
            return
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"JSON saved successfully to {self.json_file}.")
        except Exception as e:
            print(f"Error saving JSON to {self.json_file}: {e}")
    
    def save_configs_list(self) -> None:
        """Save the current configs_list to configs_list.json."""
        try:
            with open(self.configs_list_file, 'w', encoding='utf-8') as f:
                json.dump(self.configs_list, f, indent=2)
            print(f"Configs list saved successfully to {self.configs_list_file}.")
        except Exception as e:
            print(f"Error saving configs list: {e}")
    
    def on_search(self, event: Any) -> None:
        """
        Handle search input changes and filter the displayed items.
        
        Args:
            event: The key release event from tkinter
        """
        self.search_query = self.search_entry.get().strip().lower()
        self.populate_ui()
    
    def matches_search(self, item: Dict[str, str]) -> bool:
        """
        Check if an item matches the current search query.
        
        Args:
            item: The item dictionary to check
            
        Returns:
            True if the item matches the search query, False otherwise
        """
        if not self.search_query:
            return True
        name = item.get('name', '').lower()
        path = item.get('path', '').lower()
        return self.search_query in name or self.search_query in path
    
    def highlight_text(self, text: str, query: str) -> str:
        """
        Add visual emphasis to search query matches in text.
        
        Args:
            text: The text to highlight
            query: The search query to highlight
            
        Returns:
            The text with highlighted query matches
        """
        if not query:
            return text
        # Simple highlight by adding brackets (visual only for now)
        # CustomTkinter doesn't support rich text natively, so we just return as is
        return text
    
    def refresh_data(self) -> None:
        """Reload configuration data from file and refresh the UI."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Reload and regroup
        self.raw_data = self.load_json()
        self.grouped_data = self.normalize_grouped(self.raw_data)
        
        # Repopulate
        self.populate_ui()
    
    def populate_ui(self) -> None:
        """Populate the UI with categorized and filtered tool items."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Track if any items match search
        has_results = False
        
        for category, types in self.grouped_data.items():
            if not types:
                continue
            
            # Filter items by search query first
            filtered_types: Dict[str, List[Tuple[int, Dict[str, str]]]] = {}
            for item_type, items in types.items():
                filtered_items = [(idx, item) for idx, item in enumerate(items) if self.matches_search(item)]
                if filtered_items:
                    filtered_types[item_type] = filtered_items
            
            # Skip category if no items match search
            if not filtered_types:
                continue
            
            has_results = True
            
            # Category header label
            category_header = ctk.CTkLabel(
                self.scrollable_frame,
                text=f"{category.title()}",
                font=ctk.CTkFont(size=18, weight="bold")
            )
            category_header.pack(pady=(20, 10), anchor="w")
            
            # Category frame
            category_frame = ctk.CTkFrame(self.scrollable_frame)
            category_frame.pack(fill="x", padx=10, pady=5)
            
            for item_type, filtered_items in filtered_types.items():
                if not filtered_items:
                    continue
                
                # Type sub-header label
                type_header = ctk.CTkLabel(
                    category_frame,
                    text=f"  {item_type.title()}:",
                    font=ctk.CTkFont(size=14, weight="bold")
                )
                type_header.pack(pady=(10, 5), anchor="w")
                
                # Frame for buttons
                type_frame = ctk.CTkFrame(category_frame)
                type_frame.pack(fill="x", padx=10, pady=2)
                
                for idx, item in filtered_items:
                    name = item.get('name', 'Unnamed')
                    path = item.get('path', '')
                    
                    # Highlight search matches in displayed text
                    display_name = name
                    if self.search_query:
                        # Add visual indicator for search matches
                        if self.search_query in name.lower():
                            display_name = f"🔍 {name}"
                    
                    # Main button frame for launch
                    button_frame = ctk.CTkFrame(type_frame, fg_color="transparent")
                    button_frame.pack(fill="x", pady=2, padx=10)
                    
                    # Launch button (dynamic width, no fixed)
                    def create_command(t: str = item_type, p: str = path) -> callable:
                        return lambda: self.open_item(t, p)
                    
                    launch_btn = ctk.CTkButton(
                        button_frame,
                        text=display_name,
                        command=create_command(),
                        height=30,
                        anchor="w"
                    )
                    launch_btn.pack(side="left", fill="x", expand=True, pady=2)
                    
                    # Delete button
                    delete_btn = ctk.CTkButton(
                        button_frame,
                        text="🗑️",
                        width=40,
                        height=30,
                        fg_color="transparent",
                        hover_color=("gray70", "gray30"),
                        font=ctk.CTkFont(size=14),
                        command=lambda cat=category, typ=item_type, index=idx, it=item: self.confirm_delete(cat, typ, index, it)
                    )
                    delete_btn.pack(side="right", pady=2, padx=(2, 0))
                    
                    # Edit button
                    edit_btn = ctk.CTkButton(
                        button_frame,
                        text="✏️",
                        width=40,
                        height=30,
                        fg_color="transparent",
                        hover_color=("gray70", "gray30"),
                        font=ctk.CTkFont(size=14),
                        command=lambda cat=category, typ=item_type, index=idx, it=item: self.show_sidebar_for_edit(cat, typ, index, it)
                    )
                    edit_btn.pack(side="right", pady=2)
        
        # Show message if no results
        if not has_results:
            no_results_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="No items found" if self.search_query else "No items configured",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_results_label.pack(pady=50)
    
    def open_item(self, item_type: str, path: str) -> None:
        """
        Open or launch an item based on its type.
        
        Args:
            item_type: The type of item (folder, python project, bat file, web page)
            path: The path or URL to open
        """
        system = platform.system()
        
        if item_type == "web page":
            webbrowser.open(path)
            return
        
        if system != "Windows":
            # Fallback for non-Windows (limited support for keeping console open)
            if item_type == "python project":
                try:
                    subprocess.Popen([sys.executable, path])
                except Exception as e:
                    print(f"Error launching Python project: {e}")
            elif item_type == "folder":
                try:
                    if system == "Darwin":  # macOS
                        subprocess.Popen(["open", path])
                    elif system == "Linux":
                        subprocess.Popen(["xdg-open", path])
                except Exception as e:
                    print(f"Error opening folder: {e}")
            elif item_type == "bat file":
                print("BAT files are Windows-specific.")
            return
        
        # Windows-specific handling
        try:
            create_new_console = subprocess.CREATE_NEW_CONSOLE
            
            if item_type == "folder":
                os.startfile(path)
            elif item_type == "python project":
                # Run with -i to drop into interactive mode after execution
                subprocess.Popen([sys.executable, '-i', path], creationflags=create_new_console)
            elif item_type == "bat file":
                # Run via cmd /k to keep console open after execution
                subprocess.Popen(['cmd', '/k', path], creationflags=create_new_console)
        except Exception as e:
            print(f"Error opening item: {e}")
    
    def run(self) -> None:
        """Start the main application loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = ToolLauncher()
    app.run()
