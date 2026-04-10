"""
Tool Launcher – Business Logic (Complete, with Logging and Config Path Fix)
"""
import json
import os
import sys
import subprocess
import webbrowser
import platform
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any, Tuple


class ToolLauncherLogic:
    def __init__(self):
        # Configure logging
        self.logger = logging.getLogger('ToolLauncherLogic')
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO,
                                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                filename='tool_launcher.log',
                                filemode='a')
        self.logger.info("ToolLauncherLogic initialized. Starting application.")
            
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.app_config_file = os.path.join(self.script_dir, "app_config.json")
        self.history_file = os.path.join(self.script_dir, "launch_history.json")

        self.configs_list: List[Dict[str, str]] = []
        self.current_config: Optional[Dict[str, str]] = None
        self.current_data: Dict = {}
        self.launch_history: List[Dict[str, str]] = []

        self._ensure_defaults()
        self.configs_list = self._load_configs_list() 
        self.launch_history = self._load_history()

    def _ensure_defaults(self):
        if os.path.exists(self.app_config_file):
            return

        default_config_path = os.path.join(self.script_dir, "config_default.json")
        self.logger.info("app_config.json not found. Creating default configuration files.")
        
        default_app = {
            "settings": {
                "appearance_mode": "System",
                "color_theme": "blue",
                "show_text": True,
                "window_positions": {}
            },
            "configs": [{
                "name": "Default Tools",
                "path": self.script_dir,
                "filename": "config_default.json"
            }]
        }
        try:
            with open(self.app_config_file, "w", encoding="utf-8") as f:
                json.dump(default_app, f, indent=2)

            sample = {"example": {"web page": [{"name": "Google", "path": "https://google.com"}]}}
            with open(default_config_path, "w", encoding="utf-8") as f:
                json.dump(sample, f, indent=2)
            self.logger.info("Default files created successfully.")
        except Exception as e:
            self.logger.error(f"FATAL: Could not create default files: {e}")


    def _load_configs_list(self) -> List[Dict[str, str]]:
        """Load configs list from app_config.json, handling both old and new formats."""
        try:
            with open(self.app_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            configs = []
            for c in data.get("configs", []):
                name = c.get("name")
                if not name:
                    continue

                path = c.get("path")
                filename = c.get("filename")

                # FIX: Check for the older 'config_path' key if new keys are missing
                if not path or not filename:
                    config_path = c.get("config_path")
                    if config_path:
                        path = os.path.dirname(config_path)
                        filename = os.path.basename(config_path)
                
                # Only add if we have all three components
                if name and path and filename:
                    configs.append({
                        "name": name,
                        "path": path,
                        "filename": filename
                    })

            self.logger.info(f"Loaded {len(configs)} configurations from app_config.json.")
            return configs
        except Exception as e:
            self.logger.error(f"Error loading configs from app_config.json: {e}")
            return []

    def save_configs_list(self) -> bool:
        """Save configs list to app_config.json"""
        try:
            data = {}
            if os.path.exists(self.app_config_file):
                with open(self.app_config_file, "r", encoding="utf-8") as f:
                    # Load existing data to preserve 'settings' key
                    data = json.load(f)
            data["configs"] = self.configs_list
            with open(self.app_config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info("Successfully saved configurations list.")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configurations list to {self.app_config_file}: {e}")
            return False

    def add_config(self, name: str, path: str, filename: str) -> Tuple[bool, str]:
        """Add a new configuration"""
        if not name.strip() or not path.strip() or not filename.strip():
            return False, "All fields required"
        
        if not filename.lower().endswith(".json"):
            filename += ".json"

        if any(c["name"] == name for c in self.configs_list):
            return False, "Config name already exists"
        
        full_path = os.path.join(path, filename)
        
        try:
            os.makedirs(path, exist_ok=True)
            if not os.path.exists(full_path):
                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=2)
            else:
                with open(full_path, "r", encoding="utf-8") as f:
                    json.load(f)
        except Exception as e:
            self.logger.error(f"File or path error when adding config: {e}")
            return False, f"File or path error: {str(e)}"
        
        self.configs_list.append({"name": name, "path": path, "filename": filename})
        if self.save_configs_list():
            self.logger.info(f"Added new config: {name}")
            return True, "Config created"
        else:
            self.configs_list.pop()
            return False, "Failed to save configurations list (app_config.json)"


    def select_config(self, name: str) -> bool:
        """Select and load a configuration"""
        for c in self.configs_list:
            if c["name"] == name:
                self.current_config = c
                self.current_data = self._load_current_config()
                self.logger.info(f"Selected config: {name}")
                return True
        return False

    def _load_current_config(self) -> Dict:
        """Load the current config file"""
        if not self.current_config:
            return {}
        
        try:
            full_path = os.path.join(self.current_config["path"], self.current_config["filename"])
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._normalize_data(data)
        except Exception as e:
            self.logger.error(f"Error loading current config file ({self.current_config['filename']}): {e}")
            return {}

    def save_current_config(self) -> bool:
        """Save the current config data to file"""
        if not self.current_config:
            self.logger.warning("Attempted to save current config, but no config is selected.")
            return False
        
        try:
            full_path = os.path.join(self.current_config["path"], self.current_config["filename"])
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, indent=2)
            self.logger.info(f"Successfully saved current configuration to {full_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving current config to {full_path}: {e}")
            return False

    def _normalize_data(self, data: Any) -> Dict:
        """Normalize data to ensure consistent structure"""
        if not isinstance(data, dict):
            return {}
        
        normalized = {}
        for category, types in data.items():
            if not isinstance(types, dict):
                continue
            normalized[category] = {}
            for typ, items in types.items():
                if isinstance(items, dict):
                    normalized[category][typ] = [items]
                elif isinstance(items, list):
                    normalized[category][typ] = items
                else:
                    normalized[category][typ] = []
        
        return normalized

    def add_item(self, cat: str, typ: str, name: str, path: str) -> Tuple[bool, str]:
        """Add item to current config"""
        if not all([cat, typ, name, path]):
            return False, "All fields required"
        
        new_item = {"name": name, "path": path}
        
        if cat not in self.current_data:
            self.current_data[cat] = {}
        if typ not in self.current_data[cat]:
            self.current_data[cat][typ] = []
        
        self.current_data[cat][typ].append(new_item)
        if self.save_current_config():
            self.logger.info(f"Added item '{name}' to {cat}/{typ}")
            return True, "Item added"
        else:
            self.logger.error(f"Failed to save after adding item '{name}'.")
            return False, "Failed to save configuration file."

    def delete_item(self, cat: str, typ: str, idx: int) -> bool:
        """Delete item from current config"""
        if cat in self.current_data and typ in self.current_data[cat]:
            items = self.current_data[cat][typ]
            if 0 <= idx < len(items):
                deleted_name = items[idx]["name"]
                del items[idx]
                if not items:
                    del self.current_data[cat][typ]
                if not self.current_data[cat]:
                    del self.current_data[cat]
                
                if self.save_current_config():
                    self.logger.info(f"Deleted item '{deleted_name}' from {cat}/{typ}")
                    return True
                else:
                    self.logger.error(f"Failed to save after deleting item '{deleted_name}'.")
                    # Note: Full state restoration on failure is complex, logging the failure is key.
                    return False
        return False

    def launch(self, typ: str, path: str, name: str) -> Tuple[bool, str]:
        """Launch a tool/file/webpage"""
        self.add_to_history(name, path, typ)
        self.logger.info(f"Attempting to launch: {name} ({typ}) at {path}")
        
        if typ == "web page":
            try:
                webbrowser.open(path)
                return True, ""
            except Exception as e:
                self.logger.error(f"Web launch failed for {name}: {e}")
                return False, str(e)
        
        try:
            if platform.system() == "Windows":
                if typ == "folder":
                    os.startfile(path)
                elif typ == "python project":
                    subprocess.Popen(
                        [sys.executable, "-i", path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                elif typ == "bat file":
                    subprocess.Popen(
                        ["cmd", "/k", path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    os.startfile(path)
            else:
                if typ == "folder":
                    subprocess.Popen(["xdg-open", path])
                elif typ == "python project":
                    subprocess.Popen(["python3", "-i", path])
                else:
                    subprocess.Popen(["xdg-open", path])
            return True, ""
        except Exception as e:
            self.logger.error(f"System launch failed for {name}: {e}")
            return False, str(e)

    def _load_history(self) -> List[Dict[str, str]]:
        """Load launch history"""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)[-50:]
        except Exception as e:
            self.logger.warning(f"Error loading launch history: {e}")
            return []

    def add_to_history(self, name: str, path: str, typ: str):
        """Add entry to launch history"""
        self.launch_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "path": path,
            "type": typ
        })
        self.launch_history = self.launch_history[-50:]
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.launch_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving launch history: {e}")

    def load_settings(self) -> Dict[str, Any]:
        """Load application settings"""
        default = {
            "appearance_mode": "System",
            "color_theme": "blue",
            "show_text": True,
            "window_positions": {}
        }
        
        if not os.path.exists(self.app_config_file):
            self.logger.warning("app_config.json missing during settings load.")
            self.save_settings(default)
            return default
        
        try:
            with open(self.app_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = data.get("settings", {})
            return {
                "appearance_mode": settings.get("appearance_mode", default["appearance_mode"]),
                "color_theme": settings.get("color_theme", default["color_theme"]),
                "show_text": settings.get("show_text", default["show_text"]),
                "window_positions": settings.get("window_positions", {})
            }
        except Exception as e:
            self.logger.error(f"Error loading settings from app_config.json: {e}")
            self.save_settings(default)
            return default

    def save_settings(self, settings: Dict[str, Any]):
        """Save application settings"""
        try:
            data = {}
            if os.path.exists(self.app_config_file):
                with open(self.app_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["settings"] = settings
            with open(self.app_config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info("Settings saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")

    def search(self, query: str) -> Dict:
        """Search items by name or path"""
        query = query.lower()
        result = {}
        
        for category, types in self.current_data.items():
            for typ, items in types.items():
                matches = []
                for idx, item in enumerate(items):
                    name = item.get("name", "").lower()
                    path = item.get("path", "").lower()
                    if not query or query in name or query in path:
                        matches.append((idx, item))
                
                if matches:
                    if category not in result:
                        result[category] = {}
                    result[category][typ] = matches
        
        return result