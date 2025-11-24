"""
Tool Launcher - Business Logic
Pure business logic layer - ALL file operations and data management
ZERO UI code - completely independent of GUI
"""
import json
import os
import sys
import subprocess
import webbrowser
import platform
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


class ToolLauncherLogic:
    """Business logic for Tool Launcher - handles all data operations"""
    
    def __init__(self):
        """Initialize the logic layer"""
        # Create data folder for JSON files
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.app_config_file = os.path.join(self.data_dir, "app_config.json")
        self.history_file = os.path.join(self.data_dir, "launch_history.json")

        # State variables
        self.configs_list: List[Dict[str, str]] = []
        self.current_config: Optional[Dict[str, str]] = None
        self.json_file: Optional[str] = None
        self.raw_data: Any = {}
        self.grouped_data: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        self.launch_history: List[Dict[str, str]] = []

        # Initialize application
        self._ensure_defaults()
        self._load_app_config()
        self.launch_history = self._load_history()

    # ==================== INITIALIZATION ====================

    def _ensure_defaults(self):
        """Create default configuration files if they don't exist"""
        if os.path.exists(self.app_config_file):
            return
        
        # Create default app config
        default = {
            "settings": {
                "appearance_mode": "System",
                "color_theme": "blue",
                "show_text": True,
                "window_pos": None
            },
            "configs": [{
                "name": "Default Tools",
                "config_path": os.path.join(self.data_dir, "config_default.json").replace("\\", "/")
            }]
        }
        
        with open(self.app_config_file, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        
        # Create sample config file
        sample = {
            "example": {
                "web page": [
                    {"name": "Google", "path": "https://google.com"},
                    {"name": "GitHub", "path": "https://github.com"}
                ]
            }
        }
        
        with open(os.path.join(self.data_dir, "config_default.json"), "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2)

    def _load_app_config(self) -> None:
        """Load the main application configuration"""
        try:
            with open(self.app_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Only load valid configs
                self.configs_list = [
                    c for c in data.get("configs", [])
                    if "name" in c and "config_path" in c
                ]
        except Exception:
            self.configs_list = []

    def _save_app_config(self) -> None:
        """Save the main application configuration"""
        try:
            data = {}
            if os.path.exists(self.app_config_file):
                with open(self.app_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            
            data["configs"] = self.configs_list
            
            with open(self.app_config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving app config: {e}")

    # ==================== CONFIG MANAGEMENT ====================

    def get_config_names(self) -> List[str]:
        """Get list of config names for UI display"""
        return [c["name"] for c in self.configs_list]

    def get_config_count(self) -> int:
        """Get total number of configs"""
        return len(self.configs_list)

    def get_first_config_name(self) -> Optional[str]:
        """Get the first config name, if any"""
        return self.configs_list[0]["name"] if self.configs_list else None

    def get_current_config_data(self) -> Optional[Dict[str, str]]:
        """
        Get current config data split into components for editing
        
        Returns:
            Dict with 'name', 'directory', 'filename' or None
        """
        if not self.current_config:
            return None
        
        full_path = self.current_config.get('config_path', '')
        if not full_path:
            return None
        
        return {
            'name': self.current_config['name'],
            'directory': os.path.dirname(full_path),
            'filename': os.path.basename(full_path)
        }

    def add_config(self, name: str, path: str = "", filename: str = "") -> Tuple[bool, str]:
        """
        Add a new configuration
        
        Args:
            name: Config name
            path: Directory path (optional)
            filename: JSON filename (optional)
            
        Returns:
            Tuple of (success, message)
        """
        if not name.strip():
            return False, "Name required"
        
        # Check for duplicate names
        if any(c["name"] == name for c in self.configs_list):
            return False, "Config name already exists"
        
        # Determine full path
        if filename:
            full = os.path.join(path or self.data_dir, filename)
        else:
            # Generate filename from name
            safe_name = name.lower().replace(' ', '_')
            full = os.path.join(self.data_dir, f"config_{safe_name}.json")
        
        full = full.replace("\\", "/")
        
        # Ensure .json extension
        if not full.endswith(".json"):
            full += ".json"
        
        # Create the file
        try:
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception as e:
            return False, str(e)
        
        # Add to configs list
        self.configs_list.append({"name": name, "config_path": full})
        self._save_app_config()
        
        return True, "Config added successfully"

    def edit_config(self, new_path: str, new_filename: str) -> Tuple[bool, str]:
        """
        Edit the current configuration's path
        
        Args:
            new_path: New directory path
            new_filename: New filename
            
        Returns:
            Tuple of (success, message)
        """
        if not self.current_config:
            return False, "No config selected"
        
        if not new_filename.strip():
            return False, "Filename required"
        
        # Build new path
        full_path = os.path.join(new_path or self.data_dir, new_filename)
        full_path = full_path.replace("\\", "/")
        
        if not full_path.endswith(".json"):
            full_path += ".json"
        
        old_path = self.current_config["config_path"]
        
        # If path changed, move the file
        if old_path != full_path:
            try:
                # Read old data
                if os.path.exists(old_path):
                    with open(old_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {}
                
                # Write to new location
                os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                
                # Delete old file
                if os.path.exists(old_path):
                    os.remove(old_path)
                
                # Update config
                self.current_config["config_path"] = full_path
                self.json_file = full_path
                
                # Update in list
                for c in self.configs_list:
                    if c["name"] == self.current_config["name"]:
                        c["config_path"] = full_path
                        break
                
                self._save_app_config()
                
                return True, "Config updated successfully"
            except Exception as e:
                return False, str(e)
        else:
            return True, "No changes made"

    def delete_config(self, name: str) -> bool:
        """
        Delete a configuration
        
        Args:
            name: Config name to delete
            
        Returns:
            True if successful
        """
        self.configs_list = [c for c in self.configs_list if c["name"] != name]
        self._save_app_config()
        return True

    def select_config(self, name: str) -> bool:
        """
        Select and load a configuration
        
        Args:
            name: Config name to select
            
        Returns:
            True if successful
        """
        for c in self.configs_list:
            if c["name"] == name:
                self.current_config = c
                self.json_file = c["config_path"]
                self.raw_data = self._load_json()
                self.grouped_data = self._normalize(self.raw_data)
                return True
        return False

    # ==================== JSON FILE OPERATIONS ====================

    def _load_json(self) -> Any:
        """Load JSON data from current config file"""
        if not self.json_file:
            return {}
        
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            # Create empty file if it doesn't exist or is corrupted
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
            return {}

    def _save_json(self):
        """Save JSON data to current config file"""
        if self.json_file:
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(self.raw_data, f, indent=2)

    def _normalize(self, data: Any) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Normalize data structure to consistent format
        
        Args:
            data: Raw data (list or dict)
            
        Returns:
            Normalized dict structure: {category: {type: [items]}}
        """
        g: Dict[str, Dict[str, List[Dict]]] = {}
        
        if isinstance(data, list):
            # List format: [{category, type, name, path}, ...]
            for i in data:
                c = i.get("category", "uncategorized").lower()
                t = i.get("type", "").lower()
                g.setdefault(c, {}).setdefault(t, []).append(i)
                
        elif isinstance(data, dict):
            # Dict format: {category: {type: [items]}}
            for c, types in data.items():
                c = c.lower()
                g[c] = {}
                
                for t, v in types.items():
                    t = t.lower()
                    lst = []
                    
                    if isinstance(v, list):
                        lst = v
                    elif isinstance(v, dict):
                        # Single item as dict
                        lst = [v]
                    
                    g[c][t] = lst
        
        return g

    # ==================== ITEM MANAGEMENT ====================

    def add_item(self, cat: str, typ: str, name: str, path: str) -> Tuple[bool, str]:
        """
        Add a new item
        
        Args:
            cat: Category
            typ: Type
            name: Item name
            path: Item path/URL
            
        Returns:
            Tuple of (success, message)
        """
        if not all([cat, typ, name, path]):
            return False, "All fields required"
        
        new = {"name": name, "path": path}
        c, t = cat.lower(), typ.lower()
        
        # Add to raw data structure
        self.raw_data.setdefault(c, {}).setdefault(t, []).append(new)
        
        # Save and refresh
        self._save_json()
        self.grouped_data = self._normalize(self.raw_data)
        
        return True, "Item added successfully"

    def edit_item(self, cat: str, typ: str, idx: int, new_name: str, new_path: str) -> Tuple[bool, str]:
        """
        Edit an existing item
        
        Args:
            cat: Category
            typ: Type
            idx: Item index
            new_name: New item name
            new_path: New item path/URL
            
        Returns:
            Tuple of (success, message)
        """
        c, t = cat.lower(), typ.lower()
        
        if c in self.raw_data and t in self.raw_data[c]:
            items = self.raw_data[c][t]
            if 0 <= idx < len(items):
                items[idx]["name"] = new_name
                items[idx]["path"] = new_path
                
                # Save and refresh
                self._save_json()
                self.grouped_data = self._normalize(self.raw_data)
                
                return True, "Item updated successfully"
        
        return False, "Item not found"

    def delete_item(self, cat: str, typ: str, idx: int) -> bool:
        """
        Delete an item
        
        Args:
            cat: Category
            typ: Type
            idx: Item index
            
        Returns:
            True if successful
        """
        c, t = cat.lower(), typ.lower()
        
        if c in self.raw_data and t in self.raw_data[c]:
            items = self.raw_data[c][t]
            if 0 <= idx < len(items):
                del items[idx]
                
                # Clean up empty structures
                if not items:
                    del self.raw_data[c][t]
                if not self.raw_data[c]:
                    del self.raw_data[c]
                
                # Save and refresh
                self._save_json()
                self.grouped_data = self._normalize(self.raw_data)
                
                return True
        
        return False

    # ==================== SEARCH AND FILTER ====================

    def get_filtered_items(self, query: str) -> Dict[str, Dict[str, List[Tuple[int, Dict]]]]:
        """
        Get filtered items based on search query
        
        Args:
            query: Search query string
            
        Returns:
            Filtered items: {category: {type: [(index, item)]}}
        """
        q = query.lower()
        out = {}
        
        for c, types in self.grouped_data.items():
            for t, items in types.items():
                # Filter items that match query
                matches = [
                    (i, it) for i, it in enumerate(items)
                    if not q or 
                       q in it.get("name", "").lower() or 
                       q in it.get("path", "").lower()
                ]
                
                if matches:
                    out.setdefault(c, {})[t] = matches
        
        return out

    # ==================== LAUNCH OPERATIONS ====================

    def launch_item(self, typ: str, path: str, name: str) -> Tuple[bool, str]:
        """
        Launch an item
        
        Args:
            typ: Item type
            path: Item path/URL
            name: Item name
            
        Returns:
            Tuple of (success, error_message)
        """
        # Add to history
        self._add_to_history(name, path, typ)
        
        # Handle web pages
        if typ == "web page":
            try:
                webbrowser.open(path)
                return True, ""
            except Exception as e:
                return False, str(e)
        
        # Handle other types (Windows-specific)
        try:
            if platform.system() == "Windows":
                flag = subprocess.CREATE_NEW_CONSOLE
                
                if typ == "folder":
                    os.startfile(path)
                    
                elif typ == "python project":
                    subprocess.Popen(
                        [sys.executable, "-i", path], 
                        creationflags=flag
                    )
                    
                elif typ == "bat file":
                    subprocess.Popen(
                        ["cmd", "/k", path], 
                        creationflags=flag
                    )
            else:
                # Basic support for other platforms
                if typ == "folder":
                    subprocess.Popen(["xdg-open", path])
                else:
                    subprocess.Popen([path])
            
            return True, ""
            
        except Exception as e:
            return False, str(e)

    # ==================== LAUNCH HISTORY ====================

    def _load_history(self) -> List[Dict[str, str]]:
        """Load launch history from file"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                # Keep only last 50 entries
                return json.load(f)[-50:]
        except:
            return []

    def _save_history(self) -> None:
        """Save launch history to file"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.launch_history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def _add_to_history(self, name: str, path: str, typ: str):
        """
        Add entry to launch history
        
        Args:
            name: Item name
            path: Item path/URL
            typ: Item type
        """
        self.launch_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "path": path,
            "type": typ
        })
        
        # Keep only last 50 entries
        self.launch_history = self.launch_history[-50:]
        self._save_history()

    # ==================== SETTINGS MANAGEMENT ====================

    def get_settings(self) -> Dict[str, Any]:
        """
        Get application settings
        
        Returns:
            Settings dictionary
        """
        default = {
            "appearance_mode": "System",
            "color_theme": "blue",
            "show_text": True,
            "window_pos": None
        }
        
        if not os.path.exists(self.app_config_file):
            self._save_settings(default)
            return default
        
        try:
            with open(self.app_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            settings = data.get("settings", {})
            
            # Return settings with defaults for missing keys
            return {
                "appearance_mode": settings.get("appearance_mode", default["appearance_mode"]),
                "color_theme": settings.get("color_theme", default["color_theme"]),
                "show_text": settings.get("show_text", default["show_text"]),
                "window_pos": settings.get("window_pos", default["window_pos"])
            }
        except:
            self._save_settings(default)
            return default

    def update_settings(self, new_settings: Dict[str, Any]):
        """
        Update application settings (partial update)
        
        Args:
            new_settings: Dict with settings to update
        """
        current = self.get_settings()
        current.update(new_settings)
        self._save_settings(current)

    def save_window_position(self, x: int, y: int, w: int, h: int):
        """
        Save window position and size
        
        Args:
            x: X position
            y: Y position
            w: Width
            h: Height
        """
        current = self.get_settings()
        current["window_pos"] = [x, y, w, h]
        self._save_settings(current)

    def _save_settings(self, settings: Dict[str, Any]):
        """
        Save settings to file
        
        Args:
            settings: Complete settings dictionary
        """
        try:
            data = {}
            if os.path.exists(self.app_config_file):
                with open(self.app_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            
            data["settings"] = settings
            
            with open(self.app_config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")