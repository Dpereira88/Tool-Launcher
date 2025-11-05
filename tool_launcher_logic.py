"""
Tool Launcher - Business Logic
Handles all data operations, file I/O, and item launching
"""
import json
import os
import sys
import subprocess
import webbrowser
import platform
from datetime import datetime
from typing import Dict, List, Optional, Any


class ToolLauncherLogic:
    """Handles all business logic for the Tool Launcher application."""
    
    def __init__(self, script_dir: str):
        """Initialize with script directory."""
        self.script_dir = script_dir
        self.app_config_file = os.path.join(script_dir, "app_config.json")
        self.history_file = os.path.join(script_dir, "launch_history.json")
        
        self.configs_list: List[Dict[str, str]] = []
        self.current_config: Optional[Dict[str, str]] = None
        self.json_file: Optional[str] = None
        self.raw_data: Dict[str, Any] = {}
        self.grouped_data: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        self.launch_history: List[Dict[str, str]] = []
        
        self.initialize_defaults()
        self.load_app_config()
        self.launch_history = self.load_history()
    
    # ==================== INITIALIZATION ====================
    
    def initialize_defaults(self) -> None:
        """Create default app config if missing."""
        if os.path.exists(self.app_config_file):
            return
        
        default_app_config = {
            "settings": {
                "appearance_mode": "System",
                "color_theme": "blue"
            },
            "configs": [{
                "name": "Default Tools",
                "config_path": os.path.join(self.script_dir, "config_default.json").replace("\\", "/")
            }]
        }
        
        with open(self.app_config_file, 'w', encoding='utf-8') as f:
            json.dump(default_app_config, f, indent=2)
        
        # Create default tool config
        default_config = {
            "example": {
                "web page": {
                    "name": "Sample Site",
                    "path": "https://example.com"
                }
            }
        }
        
        with open(os.path.join(self.script_dir, "config_default.json"), 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
    
    def load_app_config(self) -> None:
        """Load app configuration (settings + configs list)."""
        try:
            with open(self.app_config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.configs_list = [
                    item for item in data.get("configs", [])
                    if 'name' in item and 'config_path' in item
                ]
        except Exception:
            self.configs_list = []
    
    def save_app_config(self) -> None:
        """Save app configuration (settings + configs list)."""
        try:
            data = {}
            if os.path.exists(self.app_config_file):
                with open(self.app_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data["configs"] = self.configs_list
            
            with open(self.app_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving app config: {e}")
    
    # ==================== CONFIG MANAGEMENT ====================
    
    def load_configs_list(self) -> List[Dict[str, str]]:
        """Load configs list from app config."""
        return self.configs_list
    
    def save_configs_list(self) -> None:
        """Save configs list to app config."""
        self.save_app_config()
    
    def add_config(self, config_name: str, config_path: str = "", config_filename: str = "") -> tuple[bool, str]:
        """Add new config. Returns (success, message)."""
        if not config_name:
            return False, "Enter config name!"
        
        safe_name = config_name.lower().replace(" ", "_")
        
        # Determine the file path
        if config_filename and config_path:
            # Both provided: combine them
            full_path = os.path.join(config_path, config_filename)
        elif config_filename:
            # Only filename: use script directory
            full_path = os.path.join(self.script_dir, config_filename)
        elif config_path:
            # Only path provided (legacy): use as-is
            full_path = config_path
        else:
            # Nothing provided: generate default
            full_path = os.path.join(self.script_dir, f"config_{safe_name}.json")
        
        full_path = full_path.replace("\\", "/")
        
        # Ensure .json extension
        if not full_path.endswith('.json'):
            full_path += '.json'
        
        if any(cfg['name'] == config_name for cfg in self.configs_list):
            return False, "Config exists!"
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path) or self.script_dir, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
        except Exception as e:
            return False, f"Error: {e}"
        
        new_config = {"name": config_name, "config_path": full_path}
        self.configs_list.append(new_config)
        self.save_configs_list()
        
        return True, "Config added!"
    
    def edit_config(self, config_name: str, new_path: str, new_filename: str = "") -> tuple[bool, str]:
        """Edit existing config path. Returns (success, message)."""
        if not new_path and not new_filename:
            return False, "Enter path or filename!"
        
        # Determine the new full path
        if new_filename and new_path:
            full_path = os.path.join(new_path, new_filename)
        elif new_filename:
            # Only filename: use script directory
            full_path = os.path.join(self.script_dir, new_filename)
        elif new_path:
            # Only path: use as-is
            full_path = new_path
        else:
            return False, "Enter path or filename!"
        
        full_path = full_path.replace("\\", "/")
        
        # Ensure .json extension
        if not full_path.endswith('.json'):
            full_path += '.json'
        
        for config in self.configs_list:
            if config['name'] == config_name:
                config['config_path'] = full_path
                break
        
        self.save_configs_list()
        return True, "Config updated!"
    
    def delete_config(self, config_name: str) -> bool:
        """Delete config from list. Returns success."""
        if len(self.configs_list) <= 1:
            return False
        
        self.configs_list = [c for c in self.configs_list if c['name'] != config_name]
        self.save_configs_list()
        return True
    
    def select_config(self, config_name: str) -> bool:
        """Select a config by name. Returns success."""
        for config in self.configs_list:
            if config['name'] == config_name:
                self.current_config = config
                self.json_file = config['config_path']
                self.raw_data = self.load_json()
                self.grouped_data = self.normalize_grouped(self.raw_data)
                return True
        return False
    
    # ==================== JSON DATA OPERATIONS ====================
    
    def load_json(self) -> Any:
        """Load current JSON config."""
        if not self.json_file:
            return {}
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}
    
    def save_json(self, data: Dict) -> None:
        """Save JSON config."""
        if self.json_file:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    
    def normalize_grouped(self, data: Any) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """Normalize data to grouped format."""
        grouped = {}
        if isinstance(data, list):
            for item in [i for i in data if i]:
                category = item.get('category', 'uncategorized').lower()
                item_type = item.get('type', '').lower()
                grouped.setdefault(category, {}).setdefault(item_type, []).append(item)
        elif isinstance(data, dict):
            for category, types_dict in data.items():
                category = category.lower()
                grouped.setdefault(category, {})
                for item_type, value in types_dict.items():
                    item_type = item_type.lower()
                    grouped[category].setdefault(item_type, [])
                    if isinstance(value, dict):
                        if value:
                            grouped[category][item_type].append(value)
                    elif isinstance(value, list):
                        grouped[category][item_type].extend([i for i in value if i])
        return grouped
    
    def to_nested(self, data_list: List[Dict[str, str]]) -> Dict:
        """Convert flat list to nested dict."""
        grouped = {}
        for item in [i for i in data_list if i]:
            category = item.get('category', 'uncategorized').lower()
            item_type = item.get('type', '').lower()
            grouped.setdefault(category, {}).setdefault(item_type, []).append({
                'name': item['name'],
                'path': item['path']
            })
        return grouped
    
    def refresh_data(self) -> None:
        """Reload data from file."""
        self.raw_data = self.load_json()
        self.grouped_data = self.normalize_grouped(self.raw_data)
    
    # ==================== ITEM OPERATIONS ====================
    
    def add_item(self, category: str, item_type: str, name: str, path: str) -> tuple[bool, str]:
        """Add new item. Returns (success, message)."""
        if not all([category, item_type, name, path]):
            return False, "Fill all fields!"
        
        new_item = {'name': name, 'path': path}
        
        if self.raw_data is None:
            self.raw_data = self.load_json()
        
        if isinstance(self.raw_data, list):
            self.raw_data.append({
                'category': category,
                'type': item_type,
                'name': name,
                'path': path
            })
            nested = self.to_nested(self.raw_data)
        else:
            cat_lower = category.lower()
            typ_lower = item_type.lower()
            
            if cat_lower not in self.raw_data:
                self.raw_data[cat_lower] = {}
            if typ_lower not in self.raw_data[cat_lower]:
                self.raw_data[cat_lower][typ_lower] = []
            
            existing = self.raw_data[cat_lower][typ_lower]
            if isinstance(existing, list):
                existing.append(new_item)
            else:
                self.raw_data[cat_lower][typ_lower] = [existing, new_item] if existing else [new_item]
            
            nested = self.raw_data
        
        self.save_json(nested)
        self.refresh_data()
        return True, "Item added!"
    
    def edit_item(self, category: str, item_type: str, item_index: int, 
                  old_name: str, new_name: str, new_path: str) -> tuple[bool, str]:
        """Edit existing item. Returns (success, message)."""
        if not new_name or not new_path:
            return False, "Fill name/path!"
        
        if self.raw_data is None:
            self.raw_data = self.load_json()
        
        if isinstance(self.raw_data, list):
            for i, item in enumerate(self.raw_data):
                if (item.get('category', '').lower() == category.lower() and
                    item.get('type', '').lower() == item_type.lower() and
                    item.get('name') == old_name):
                    self.raw_data[i]['name'] = new_name
                    self.raw_data[i]['path'] = new_path
                    break
            nested = self.to_nested(self.raw_data)
        else:
            cat_lower = category.lower()
            typ_lower = item_type.lower()
            items_list = self.raw_data[cat_lower][typ_lower]
            
            if isinstance(items_list, list):
                items_list[item_index]['name'] = new_name
                items_list[item_index]['path'] = new_path
            else:
                self.raw_data[cat_lower][typ_lower]['name'] = new_name
                self.raw_data[cat_lower][typ_lower]['path'] = new_path
            
            nested = self.raw_data
        
        self.save_json(nested)
        self.refresh_data()
        return True, "Item updated!"
    
    def delete_item(self, category: str, item_type: str, item_index: int) -> bool:
        """Delete item. Returns success."""
        if not self.json_file or not self.raw_data:
            return False
        
        if isinstance(self.raw_data, list):
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
        else:
            cat_lower = category.lower()
            typ_lower = item_type.lower()
            
            if cat_lower in self.raw_data and typ_lower in self.raw_data[cat_lower]:
                items_list = self.raw_data[cat_lower][typ_lower]
                if isinstance(items_list, list):
                    if 0 <= item_index < len(items_list):
                        del items_list[item_index]
                        if not items_list:
                            del self.raw_data[cat_lower][typ_lower]
                        if not self.raw_data[cat_lower]:
                            del self.raw_data[cat_lower]
                else:
                    del self.raw_data[cat_lower][typ_lower]
                    if not self.raw_data[cat_lower]:
                        del self.raw_data[cat_lower]
            
            nested = self.raw_data
        
        self.save_json(nested)
        self.refresh_data()
        return True
    
    # ==================== ITEM LAUNCHING ====================
    
    def launch(self, item_type: str, path: str, name: str = "Unknown") -> tuple[bool, str]:
        """Launch item. Returns (success, error_message)."""
        self.add_to_history(name, path, item_type)
        
        if item_type == "web page":
            webbrowser.open(path)
            return True, ""
        
        system = platform.system()
        
        try:
            if system == "Windows":
                create_new_console = subprocess.CREATE_NEW_CONSOLE
                if item_type == "folder":
                    os.startfile(path)
                elif item_type == "python project":
                    subprocess.Popen([sys.executable, '-i', path], creationflags=create_new_console)
                elif item_type == "bat file":
                    subprocess.Popen(['cmd', '/k', path], creationflags=create_new_console)
            
            elif system == "Darwin":  # macOS
                if item_type == "folder":
                    subprocess.Popen(['open', path])
                elif item_type == "python project":
                    subprocess.Popen(['open', '-a', 'Terminal', path])
                elif item_type == "bat file":
                    subprocess.Popen(['open', '-a', 'Terminal', path])
            
            elif system == "Linux":
                if item_type == "folder":
                    subprocess.Popen(['xdg-open', path])
                elif item_type == "python project":
                    terminals = ['gnome-terminal', 'konsole', 'xterm', 'x-terminal-emulator']
                    for terminal in terminals:
                        try:
                            subprocess.Popen([terminal, '-e', f'python3 -i {path}'])
                            break
                        except FileNotFoundError:
                            continue
                elif item_type == "bat file":
                    subprocess.Popen(['bash', path])
            else:
                return False, f"Unsupported OS: {system}"
            
            return True, ""
        
        except Exception as e:
            return False, str(e)
    
    # ==================== HISTORY MANAGEMENT ====================
    
    def load_history(self) -> List[Dict]:
        """Load launch history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)[-50:]
            except:
                return []
        return []
    
    def save_history(self) -> None:
        """Save launch history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.launch_history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def add_to_history(self, name: str, path: str, item_type: str) -> None:
        """Add item to launch history."""
        self.launch_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "path": path,
            "type": item_type
        })
        self.launch_history = self.launch_history[-50:]
        self.save_history()
    
    def clear_history(self) -> None:
        """Clear all launch history."""
        self.launch_history = []
        self.save_history()
    
    # ==================== SETTINGS MANAGEMENT ====================
    
    def load_settings(self) -> Dict[str, str]:
        """Load settings from app config."""
        default = {"appearance_mode": "System", "color_theme": "blue"}
        if os.path.exists(self.app_config_file):
            try:
                with open(self.app_config_file, 'r') as f:
                    data = json.load(f)
                    settings = data.get("settings", default)
                return {
                    "appearance_mode": settings.get("appearance_mode", default["appearance_mode"]),
                    "color_theme": settings.get("color_theme", default["color_theme"])
                }
            except:
                return default
        return default
    
    def save_settings(self, settings: Dict[str, str]) -> None:
        """Save settings to app config."""
        try:
            data = {}
            if os.path.exists(self.app_config_file):
                with open(self.app_config_file, 'r') as f:
                    data = json.load(f)
            
            data["settings"] = settings
            
            with open(self.app_config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def _save_settings(self, settings: Dict[str, str]) -> None:
        """Alias for save_settings for backward compatibility."""
        self.save_settings(settings)
    
    # ==================== SEARCH ====================
    
    def search(self, query: str) -> Dict[str, Dict[str, List[tuple[int, Dict[str, str]]]]]:
        """Search items by name or path. Returns filtered grouped data with indices."""
        if not query:
            # Return all with indices
            result = {}
            for category, types in self.grouped_data.items():
                result[category] = {}
                for item_type, items in types.items():
                    result[category][item_type] = [(idx, item) for idx, item in enumerate(items)]
            return result
        
        query = query.lower()
        filtered = {}
        
        for category, types in self.grouped_data.items():
            for item_type, items in types.items():
                matches = [
                    (idx, item) for idx, item in enumerate(items)
                    if query in item.get('name', '').lower() or query in item.get('path', '').lower()
                ]
                if matches:
                    if category not in filtered:
                        filtered[category] = {}
                    filtered[category][item_type] = matches
        
        return filtered