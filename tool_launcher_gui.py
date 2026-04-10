import customtkinter as ctk
from tkinter import messagebox, filedialog, BooleanVar
import os
import screeninfo
import logging
from typing import Dict, Optional, Any, Tuple
from tool_launcher_logic import ToolLauncherLogic


class ToolLauncherGUI:
    def __init__(self):
        # Configure logging
        self.logger = logging.getLogger('ToolLauncherGUI')
        if not self.logger.handlers:
             logging.basicConfig(level=logging.INFO,
                                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                filename='tool_launcher.log',
                                filemode='a')
             
        self.logger.info("ToolLauncherGUI initialized.")
        self.logic = ToolLauncherLogic()
        sets = self.logic.load_settings()
        self.saved_settings = sets

        ctk.set_appearance_mode(sets["appearance_mode"])
        self.apply_color_theme(sets["color_theme"])

        self.root = ctk.CTk()
        self.root.title("Tool Launcher")
        self.root.minsize(340, 500)

        self.restore_window_position()

        self.edit_mode = False
        self.show_text = sets.get("show_text", True)
        self.sidebar_visible = False
        self.animating = False
        self.sidebar_mode = ""
        self.editing_item: Optional[Dict] = None

        # ROBUST FIX: Initialize the BooleanVar as a permanent instance variable
        self.text_switch_var = ctk.BooleanVar(value=self.show_text) 
        
        self._build_ui()
        self._load_first_config()
        self.root.after(200, self._redraw_entries)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def apply_color_theme(self, theme_name: str):
        # 🟢 FIX: Only include the three core CustomTkinter built-in themes here.
        # This prevents CustomTkinter from failing to find a "built-in" theme and then looking for a file named 'gray'
        core_builtin = {"blue", "green", "dark-blue"}
        
        if theme_name in core_builtin:
            ctk.set_default_color_theme(theme_name)
            self.logger.info(f"Applied built-in theme: {theme_name}")
        else:
            # All other themes (like 'gray', 'purple', 'orange') must be loaded via their full file path
            path = os.path.join(os.path.dirname(__file__), "themes", f"{theme_name}.json")
            try:
                if os.path.isfile(path):
                    # Pass the full path to load a custom theme
                    ctk.set_default_color_theme(path) 
                    self.logger.info(f"Applied custom theme: {theme_name} from {path}")
                else:
                    self.logger.error(f"Custom theme file '{path}' not found! Falling back to 'blue'.")
                    ctk.set_default_color_theme("blue")
                    self.saved_settings["color_theme"] = "blue"
                    self.logic.save_settings(self.saved_settings)
            except Exception as e:
                self.logger.critical(f"Theme loading failed for '{theme_name}': {e}. Check theme JSON file structure!")
                ctk.set_default_color_theme("blue")
                self.saved_settings["color_theme"] = "blue"
                self.logic.save_settings(self.saved_settings)
                
    def get_screen_config(self):
        monitors = screeninfo.get_monitors()
        config = []
        for m in monitors:
            config.append(f"{m.width}x{m.height}+{m.x}+{m.y}")
        return "|".join(sorted(config))

    def restore_window_position(self):
        current = self.get_screen_config()
        saved = self.saved_settings.get("window_positions", {})

        if current in saved:
            p = saved[current]
            self.root.geometry(f"{p['w']}x{p['h']}+{p['x']}+{p['y']}")
            self.logger.info("Restored window position.")
        else:
            self.root.geometry("440x680")

    def on_close(self):
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        current = self.get_screen_config()
        pos = self.saved_settings.get("window_positions", {})
        pos[current] = {"x": x, "y": y, "w": w, "h": h}
        self.saved_settings["window_positions"] = pos

        self.logic.save_settings(self.saved_settings)
        self.logger.info("Application closed.")
        self.root.destroy()

    def _build_ui(self):
        # Top line with combobox and Edit button
        line1 = ctk.CTkFrame(self.root)
        line1.pack(fill="x", padx=12, pady=(12, 4))

        self.combo = ctk.CTkComboBox(
            line1,
            width=200,
            values=[c["name"] for c in self.logic.configs_list],
            command=self.on_config_change
        )
        self.combo.pack(side="left", padx=(0, 8))

        self.edit_btn = ctk.CTkButton(line1, text="Edit", width=70, command=self.toggle_edit)
        self.edit_btn.pack(side="left", padx=4)

        # Container for search bar and edit buttons (same position)
        self.search_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.search_container.pack(fill="x", padx=12, pady=(0, 10))

        # Search bar (shown in normal mode)
        self.search = ctk.CTkEntry(self.search_container, placeholder_text="Search name or path...")
        self.search.pack(fill="x")
        self.search.bind("<KeyRelease>", lambda e: self.search_update())

        # Edit mode buttons (hidden by default, equal width using grid)
        self.edit_bar = ctk.CTkFrame(self.search_container, fg_color="transparent")
        self.edit_bar.grid_columnconfigure(0, weight=1, uniform="edit_btns")
        self.edit_bar.grid_columnconfigure(1, weight=1, uniform="edit_btns")
        self.edit_bar.grid_columnconfigure(2, weight=1, uniform="edit_btns")
        
        ctk.CTkButton(self.edit_bar, text="+Category",
                      command=self.add_category).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(self.edit_bar, text="Edit Pages",
                      command=self.show_edit_config).grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(self.edit_bar, text="Settings",
                      command=self.show_settings).grid(row=0, column=2, sticky="ew", padx=4)

        self.scroll = ctk.CTkScrollableFrame(self.root)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=8)

        # Sidebar for adding/editing items
        self.sidebar = ctk.CTkFrame(self.root, width=300, corner_radius=0)
        self.sidebar_title = ctk.CTkLabel(self.sidebar, text="", font=("Segoe UI", 18, "bold"), anchor="w")
        self.sidebar_title.pack(pady=(16, 8), padx=16, fill="x")
        self.msg = ctk.CTkLabel(self.sidebar, text="")
        self.msg.pack(pady=4)

        self.f_cat = ctk.CTkEntry(self.sidebar, placeholder_text="Category", height=35)
        self.f_type = ctk.CTkComboBox(self.sidebar, values=["folder", "python project", "bat file", "web page"], height=35)
        self.f_type.set("folder")
        self.f_iname = ctk.CTkEntry(self.sidebar, placeholder_text="Name", height=35)
        self.f_ipath = ctk.CTkEntry(self.sidebar, placeholder_text="Path / URL", height=35)

        for w in (self.f_cat, self.f_type, self.f_iname, self.f_ipath):
            w.pack_forget()

        btns = ctk.CTkFrame(self.sidebar)
        btns.pack(pady=20, fill="x", padx=20)
        right = ctk.CTkFrame(btns)
        right.pack(side="right")
        ctk.CTkButton(right, text="Cancel", width=90, fg_color="gray", command=self.hide_sidebar).pack(side="right", padx=5)
        ctk.CTkButton(right, text="OK", width=90, command=self.save_sidebar).pack(side="right", padx=5)

    def _redraw_entries(self):
        for w in (self.f_cat, self.f_type, self.f_iname, self.f_ipath, self.search):
            w.update_idletasks()

    def on_config_change(self, selection):
        self.logic.select_config(selection)
        self.refresh()

    def toggle_edit(self):
        self.edit_mode = not self.edit_mode
        self.logger.info(f"Edit mode toggled: {'ON' if self.edit_mode else 'OFF'}")
        
        if self.edit_mode:
            self.edit_btn.configure(fg_color=("gray75", "gray25"), text="✓ Edit")
            self.search.pack_forget()
            self.edit_bar.pack(fill="x")
        else:
            self.edit_btn.configure(fg_color=["#3B8ED0", "#1F6AA5"], text="Edit")
            self.edit_bar.pack_forget()
            self.search.pack(fill="x")
        
        self.refresh()

    def search_update(self):
        self.refresh()

    def refresh(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

        data = self.logic.search(self.search.get().strip())
        if not data:
            ctk.CTkLabel(self.scroll, text="No items", text_color="gray").pack(pady=40)
            return

        for cat, types in data.items():
            # Category header with buttons
            cat_frame = ctk.CTkFrame(self.scroll)
            cat_frame.pack(fill="x", padx=10, pady=(16, 4))
            
            if self.edit_mode:
                ctk.CTkButton(cat_frame, text="+", width=35, font=("Segoe UI", 14),
                              command=lambda c=cat: self.add_item_to_category(c)).pack(side="left", padx=2)
                ctk.CTkButton(cat_frame, text="✏", width=35, font=("Segoe UI", 14),
                              command=lambda c=cat: self.edit_category(c)).pack(side="left", padx=2)
                ctk.CTkButton(cat_frame, text="✕", width=35, font=("Segoe UI", 14), 
                              fg_color="red", hover_color="darkred",
                              command=lambda c=cat: self.delete_category(c)).pack(side="left", padx=2)
            
            ctk.CTkLabel(cat_frame, text=cat.title(), font=("Segoe UI", 18, "bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=(10 if self.edit_mode else 0, 0))
            
            for typ, items in types.items():
                ctk.CTkLabel(self.scroll, text=f"  {typ.title()}", font=("Segoe UI", 13)).pack(anchor="w", padx=20)
                for idx, itm in items:
                    self._row(itm, cat, typ, idx)

    def _row(self, itm: Dict, cat: str, typ: str, idx: int):
        frm = ctk.CTkFrame(self.scroll)
        frm.pack(fill="x", pady=3, padx=16)

        if self.edit_mode:
            ctk.CTkButton(frm, text="✏", width=35, font=("Segoe UI", 14),
                          command=lambda c=cat, t=typ, i=idx, item=itm: self.open_item_sidebar("item_edit", "Edit Item", c, t, i, item))\
                .pack(side="left", padx=2)
            ctk.CTkButton(frm, text="✕", width=35, font=("Segoe UI", 14), 
                          fg_color="red", hover_color="darkred",
                          command=lambda c=cat, t=typ, i=idx: self.del_item(c, t, i))\
                .pack(side="left", padx=2)

        name = itm.get("name", "?")
        btn = ctk.CTkButton(frm, text=name, anchor="w",
                            command=lambda t=typ, p=itm["path"], n=name: self.launch(t, p, n))
        btn.pack(side="left", fill="x", expand=True, padx=(5 if self.edit_mode else 0, 0))

    def launch(self, typ: str, path: str, name: str):
        ok, err = self.logic.launch(typ, path, name)
        if not ok:
            messagebox.showerror("Error", err)

    def del_item(self, cat: str, typ: str, idx: int):
        if messagebox.askyesno("Delete Item", "Remove this item?"):
            if self.logic.delete_item(cat, typ, idx):
                self.refresh()
            else:
                messagebox.showerror("Save Error", "Failed to save configuration after deletion.")
                self.logger.error(f"Failed to delete item: {cat}/{typ} at index {idx}")


    def add_item_to_category(self, cat: str):
        """Add item to specific category"""
        self.open_item_sidebar("item_add", f"Add Item to {cat.title()}", cat=cat)

    def add_category(self):
        """Add a new category"""
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Add Category")
        dlg.geometry("350x150")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy) 

        ctk.CTkLabel(dlg, text="Category Name:", font=("Segoe UI", 13)).pack(pady=(20, 5), padx=20, anchor="w")
        cat_entry = ctk.CTkEntry(dlg, height=35)
        cat_entry.pack(fill="x", padx=20, pady=5)

        def save():
            cat_name = cat_entry.get().strip()
            if not cat_name:
                messagebox.showwarning("Error", "Category name is required!")
                return
            
            if cat_name not in self.logic.current_data:
                self.logic.current_data[cat_name] = {}
                if self.logic.save_current_config(): 
                    self.logger.info(f"Added new empty category: {cat_name}")
                    self.refresh()
                    dlg.destroy()
                else:
                    messagebox.showerror("Save Error", "Failed to save configuration file.")
                    self.logger.error(f"Failed to save after adding category {cat_name}.")
            else:
                messagebox.showinfo("Info", "Category already exists!")

        btn_frame = ctk.CTkFrame(dlg)
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Add", width=100, command=save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="gray", command=dlg.destroy).pack(side="left", padx=10)

    def edit_category(self, old_cat: str):
        """Edit category name"""
        dlg = ctk.CTkToplevel(self.root)
        dlg.title(f"Edit Category: {old_cat}")
        dlg.geometry("350x150")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

        ctk.CTkLabel(dlg, text="Category Name:", font=("Segoe UI", 13)).pack(pady=(20, 5), padx=20, anchor="w")
        cat_entry = ctk.CTkEntry(dlg, height=35)
        cat_entry.pack(fill="x", padx=20, pady=5)
        cat_entry.insert(0, old_cat)

        def save():
            new_cat = cat_entry.get().strip()
            if not new_cat:
                messagebox.showwarning("Error", "Category name is required!")
                return
            
            if new_cat != old_cat:
                if new_cat in self.logic.current_data:
                    messagebox.showinfo("Info", "Category already exists!")
                    return
                
                old_data = self.logic.current_data.pop(old_cat)
                self.logic.current_data[new_cat] = old_data
                
                if self.logic.save_current_config():
                    self.logger.info(f"Renamed category from {old_cat} to {new_cat}")
                    self.refresh()
                    dlg.destroy()
                else:
                    messagebox.showerror("Save Error", "Failed to save configuration file.")
                    self.logger.error(f"Failed to save after renaming category {old_cat} to {new_cat}.")
                    self.logic.current_data[old_cat] = self.logic.current_data.pop(new_cat)
            else:
                dlg.destroy()

        btn_frame = ctk.CTkFrame(dlg)
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Save", width=100, command=save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="gray", command=dlg.destroy).pack(side="left", padx=10)

    def delete_category(self, cat: str):
        """Delete entire category"""
        if messagebox.askyesno("Delete Category", f"Delete category '{cat}' and all its items?"):
            if cat in self.logic.current_data:
                del self.logic.current_data[cat]
                if self.logic.save_current_config():
                    self.logger.info(f"Deleted category: {cat}")
                    self.refresh()
                else:
                    messagebox.showerror("Save Error", "Failed to save configuration file.")
                    self.logger.error(f"Failed to save after deleting category {cat}.")

    def show_edit_config(self):
        """Open a window to edit all configurations"""
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Edit Page Tool")
        dlg.geometry("600x500")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
        self.logger.info("Opening Edit Config dialog.")

        ctk.CTkLabel(dlg, text="Manage Configurations", font=("Segoe UI", 18, "bold")).pack(pady=(20, 10))

        scroll = ctk.CTkScrollableFrame(dlg, height=300)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        def refresh_list():
            for widget in scroll.winfo_children():
                widget.destroy()

            for i, cfg in enumerate(self.logic.configs_list):
                row = ctk.CTkFrame(scroll)
                row.pack(fill="x", pady=5, padx=10)

                btn_frame = ctk.CTkFrame(row, width=70)
                btn_frame.pack(side="left", padx=(0, 5))
                btn_frame.pack_propagate(False)

                if i > 0:
                    ctk.CTkButton(btn_frame, text="▲", width=30, height=25,
                                  command=lambda idx=i: move_config(idx, -1)).pack(side="top", pady=1)
                if i < len(self.logic.configs_list) - 1:
                    ctk.CTkButton(btn_frame, text="▼", width=30, height=25,
                                  command=lambda idx=i: move_config(idx, 1)).pack(side="bottom", pady=1)

                info_frame = ctk.CTkFrame(row)
                info_frame.pack(side="left", fill="x", expand=True, padx=5)
                
                ctk.CTkLabel(info_frame, text=cfg["name"], font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x")
                path_text = f"{cfg['path']} / {cfg['filename']}"
                ctk.CTkLabel(info_frame, text=path_text, font=("Segoe UI", 10), 
                             text_color="gray", anchor="w").pack(fill="x")

                ctk.CTkButton(row, text="✏", width=40, 
                              command=lambda c=cfg, idx=i: edit_config(c, idx)).pack(side="right", padx=2)
                
                if len(self.logic.configs_list) > 1:
                    ctk.CTkButton(row, text="✕", width=40, fg_color="red", hover_color="darkred",
                                  command=lambda c=cfg, idx=i: delete_config(c, idx)).pack(side="right", padx=2)

        def move_config(idx: int, direction: int):
            new_idx = idx + direction
            if 0 <= new_idx < len(self.logic.configs_list):
                self.logic.configs_list[idx], self.logic.configs_list[new_idx] = \
                    self.logic.configs_list[new_idx], self.logic.configs_list[idx]
                
                if self.logic.save_configs_list():
                    self.combo.configure(values=[c["name"] for c in self.logic.configs_list])
                    refresh_list()
                    self.logger.info(f"Moved config index {idx} to {new_idx}")
                else:
                    messagebox.showerror("Save Error", "Failed to save configuration list after move.")
                    self.logger.error(f"Failed to save config list after moving index {idx}.")
                    # Revert move
                    self.logic.configs_list[new_idx], self.logic.configs_list[idx] = \
                        self.logic.configs_list[idx], self.logic.configs_list[new_idx]


        def edit_config(cfg: Dict, idx: int):
            edit_dlg = ctk.CTkToplevel(dlg)
            edit_dlg.title(f"Edit Config: {cfg['name']}")
            edit_dlg.geometry("500x300")
            edit_dlg.transient(dlg)
            edit_dlg.grab_set()
            edit_dlg.protocol("WM_DELETE_WINDOW", edit_dlg.destroy)

            ctk.CTkLabel(edit_dlg, text="Config Name:", font=("Segoe UI", 13)).pack(pady=(20, 5), padx=20, anchor="w")
            name_entry = ctk.CTkEntry(edit_dlg, height=35)
            name_entry.pack(fill="x", padx=20, pady=5)
            name_entry.insert(0, cfg["name"])

            ctk.CTkLabel(edit_dlg, text="Folder Path:", font=("Segoe UI", 13)).pack(pady=(10, 5), padx=20, anchor="w")
            
            path_frame = ctk.CTkFrame(edit_dlg, fg_color="transparent")
            path_frame.pack(fill="x", padx=20, pady=5)
            path_entry = ctk.CTkEntry(path_frame, height=35)
            path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            path_entry.insert(0, cfg["path"])
            
            def browse_path():
                folder = filedialog.askdirectory(initialdir=cfg["path"], title="Select Folder")
                if folder:
                    path_entry.delete(0, "end")
                    path_entry.insert(0, folder)
            
            ctk.CTkButton(path_frame, text="Browse", width=80, command=browse_path).pack(side="right")

            ctk.CTkLabel(edit_dlg, text="Filename:", font=("Segoe UI", 13)).pack(pady=(10, 5), padx=20, anchor="w")
            file_entry = ctk.CTkEntry(edit_dlg, height=35)
            file_entry.pack(fill="x", padx=20, pady=5)
            display_filename = cfg["filename"].replace(".json", "") if cfg["filename"].endswith(".json") else cfg["filename"]
            file_entry.insert(0, display_filename)

            def save_changes():
                new_name = name_entry.get().strip()
                new_path = path_entry.get().strip()
                new_file = file_entry.get().strip()
                
                if not new_name or not new_path or not new_file:
                    messagebox.showwarning("Error", "All fields are required!")
                    return
                
                if not new_file.lower().endswith(".json"):
                    new_file += ".json"
                    
                old_cfg = self.logic.configs_list[idx].copy()

                self.logic.configs_list[idx]["name"] = new_name
                self.logic.configs_list[idx]["path"] = new_path
                self.logic.configs_list[idx]["filename"] = new_file
                
                if self.logic.save_configs_list():
                    self.combo.configure(values=[c["name"] for c in self.logic.configs_list])
                    
                    if self.combo.get() == cfg["name"]:
                        self.combo.set(new_name)
                    
                    refresh_list()
                    edit_dlg.destroy()
                    self.logger.info(f"Edited config index {idx}: {new_name}")
                else:
                    messagebox.showerror("Save Error", "Failed to save configuration list.")
                    self.logger.error(f"Failed to save config list after editing index {idx}.")
                    self.logic.configs_list[idx] = old_cfg


            btn_frame = ctk.CTkFrame(edit_dlg)
            btn_frame.pack(side="bottom", pady=20, anchor="e", padx=20)
            ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="gray", 
                          command=edit_dlg.destroy).pack(side="right", padx=(10, 0))
            ctk.CTkButton(btn_frame, text="Save", width=100, command=save_changes).pack(side="right")

        def delete_config(cfg: Dict, idx: int):
            if messagebox.askyesno("Delete Config", f"Delete configuration '{cfg['name']}'?"):
                is_current = self.combo.get() == cfg["name"]
                
                deleted_cfg = self.logic.configs_list.pop(idx)
                
                if self.logic.save_configs_list():
                    self.combo.configure(values=[c["name"] for c in self.logic.configs_list])
                    
                    if is_current and self.logic.configs_list:
                        self.combo.set(self.logic.configs_list[0]["name"])
                        self.on_config_change(self.logic.configs_list[0]["name"])
                    
                    refresh_list()
                    self.logger.info(f"Deleted config: {deleted_cfg['name']}")
                else:
                    messagebox.showerror("Save Error", "Failed to save configuration list after deletion.")
                    self.logger.error(f"Failed to save config list after deleting {deleted_cfg['name']}.")
                    self.logic.configs_list.insert(idx, deleted_cfg)

        def add_new_config():
            add_dlg = ctk.CTkToplevel(dlg)
            add_dlg.title("Add New Config")
            add_dlg.geometry("500x330") 
            add_dlg.transient(dlg)
            add_dlg.grab_set()
            add_dlg.protocol("WM_DELETE_WINDOW", add_dlg.destroy)

            ctk.CTkLabel(add_dlg, text="Config Name:", font=("Segoe UI", 13)).pack(pady=(20, 5), padx=20, anchor="w")
            name_entry = ctk.CTkEntry(add_dlg, height=35)
            name_entry.pack(fill="x", padx=20, pady=5)

            ctk.CTkLabel(add_dlg, text="Folder Path:", font=("Segoe UI", 13)).pack(pady=(10, 5), padx=20, anchor="w")
            
            path_frame = ctk.CTkFrame(add_dlg, fg_color="transparent")
            path_frame.pack(fill="x", padx=20, pady=5)
            path_entry = ctk.CTkEntry(path_frame, height=35)
            path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            path_entry.insert(0, self.logic.script_dir)
            
            def browse_path():
                folder = filedialog.askdirectory(initialdir=self.logic.script_dir, title="Select Folder")
                if folder:
                    path_entry.delete(0, "end")
                    path_entry.insert(0, folder)
            
            ctk.CTkButton(path_frame, text="Browse Folder", width=120, command=browse_path).pack(side="right")

            ctk.CTkLabel(add_dlg, text="Filename:", font=("Segoe UI", 13)).pack(pady=(10, 5), padx=20, anchor="w")
            file_entry = ctk.CTkEntry(add_dlg, height=35)
            file_entry.pack(fill="x", padx=20, pady=5)
            file_entry.insert(0, "config")

            def load_existing():
                file_path = filedialog.askopenfilename(
                    initialdir=self.logic.script_dir,
                    title="Select an Existing Config File",
                    filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
                )
                if file_path:
                    dir_name = os.path.dirname(file_path)
                    file_name = os.path.basename(file_path)
                    config_name = file_name.replace(".json", "").replace("_", " ").title()
                    
                    name_entry.delete(0, "end")
                    name_entry.insert(0, config_name)
                    path_entry.delete(0, "end")
                    path_entry.insert(0, dir_name)
                    file_entry.delete(0, "end")
                    file_entry.insert(0, file_name.replace(".json", ""))


            def save_new():
                new_name = name_entry.get().strip()
                new_path = path_entry.get().strip()
                new_file = file_entry.get().strip()

                if not new_name or not new_path or not new_file:
                    messagebox.showwarning("Error", "All fields are required!")
                    return
                
                ok, err = self.logic.add_config(new_name, new_path, new_file)

                if ok:
                    self.combo.configure(values=[c["name"] for c in self.logic.configs_list])
                    self.combo.set(new_name)
                    self.on_config_change(new_name)
                    refresh_list()
                    add_dlg.destroy()
                else:
                    messagebox.showerror("Error Adding Config", err)

            btn_frame = ctk.CTkFrame(add_dlg)
            btn_frame.pack(side="bottom", pady=20, fill="x", padx=20)
            
            ctk.CTkButton(btn_frame, text="Load Existing Config", width=150, command=load_existing).pack(side="left")
            
            right_btns = ctk.CTkFrame(btn_frame)
            right_btns.pack(side="right")
            ctk.CTkButton(right_btns, text="Cancel", width=100, fg_color="gray", 
                          command=add_dlg.destroy).pack(side="right", padx=(10, 0))
            ctk.CTkButton(right_btns, text="Add/Create", width=100, command=save_new).pack(side="right")

        refresh_list()

        btn_frame = ctk.CTkFrame(dlg)
        btn_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkButton(btn_frame, text="+ Add Config", width=150, command=add_new_config).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Close", width=150, command=dlg.destroy).pack(side="right", padx=5)

    def open_item_sidebar(self, mode: str, title: str, cat="", typ="", idx=-1, itm=None):
        self.sidebar_mode = mode
        self.sidebar_title.configure(text=title)
        self.msg.configure(text="")
        self.logger.info(f"Opening sidebar in mode: {mode}")

        for w in (self.f_cat, self.f_type, self.f_iname, self.f_ipath):
            w.pack_forget()
            w.delete(0, "end")

        self.f_cat.pack(pady=8, padx=16, fill="x")
        self.f_type.pack(pady=8, padx=16, fill="x")
        self.f_iname.pack(pady=8, padx=16, fill="x")
        self.f_ipath.pack(pady=8, padx=16, fill="x")

        if mode == "item_edit":
            self.editing_item = {"cat": cat, "typ": typ, "idx": idx, "item": itm}
            self.f_cat.insert(0, cat)
            self.f_type.set(typ)
            self.f_iname.insert(0, itm.get("name", ""))
            self.f_ipath.insert(0, itm.get("path", ""))
        elif mode == "item_add" and cat:
            self.f_cat.insert(0, cat)

        self.sidebar.place(relx=1, rely=0, relheight=1, anchor="ne")

    def hide_sidebar(self):
        self.sidebar.place_forget()
        self.editing_item = None
        self.logger.info("Sidebar hidden.")

    def save_sidebar(self):
        mode = self.sidebar_mode
        cat = self.f_cat.get().strip()
        typ = self.f_type.get()
        name = self.f_iname.get().strip()
        path = self.f_ipath.get().strip()

        if not cat or not name or not path:
            self.msg.configure(text="Fill all fields!", text_color="red")
            return

        ok = False
        err = ""
        if mode == "item_add":
            ok, err = self.logic.add_item(cat, typ, name, path)
        elif mode == "item_edit":
            old = self.editing_item
            
            original_data = self.logic.current_data.copy()
            
            if self.logic.delete_item(old["cat"], old["typ"], old["idx"]):
                ok, err = self.logic.add_item(cat, typ, name, path)
            else:
                ok, err = False, "Failed to delete original item during edit."

            if not ok:
                self.logger.error("Failed to add new item during edit. Attempting to restore original config.")
                self.logic.current_data = original_data
                self.logic.save_current_config()
                err = f"Failed to save item: {err}"


        if ok:
            self.refresh()
            self.hide_sidebar()
            self.logger.info(f"Item saved successfully in mode: {mode}")
        else:
            self.msg.configure(text=f"Save failed: {err}", text_color="red")
            self.logger.error(f"Item save failed in mode {mode}: {err}")

    def show_settings(self):
        self.logger.info("Opening Settings dialog.")
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("380x340")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

        ctk.CTkLabel(dlg, text="Appearance:", font=("Segoe UI", 14)).pack(pady=(20, 5))
        mode = ctk.CTkComboBox(dlg, values=["Light", "Dark", "System"], width=320)
        mode.set(self.saved_settings["appearance_mode"])
        mode.pack(pady=5)

        ctk.CTkLabel(dlg, text="Color Theme:", font=("Segoe UI", 14)).pack(pady=(15, 5))
        # Theme list should contain all themes the user might use
        theme = ctk.CTkComboBox(dlg, values=["blue", "green", "dark-blue", "gray", "purple", "orange"], width=320)
        theme.set(self.saved_settings["color_theme"])
        theme.pack(pady=5)

        ctk.CTkLabel(dlg, text="Button Labels:", font=("Segoe UI", 14)).pack(pady=(15, 5))
        
        # FINAL FIX: Set the permanent BooleanVar and link it to the widget
        self.text_switch_var.set(self.show_text) 
        text_switch = ctk.CTkSwitch(dlg, text="Show Text (vs Symbols)", variable=self.text_switch_var)
        
        text_switch.pack(pady=5)

        def ok():
            s = {
                "appearance_mode": mode.get(),
                "color_theme": theme.get(),
                "show_text": self.text_switch_var.get(), 
                "window_positions": self.saved_settings.get("window_positions", {})
            }
            self.logic.save_settings(s)
            self.saved_settings = s
            self.show_text = s["show_text"]

            ctk.set_appearance_mode(s["appearance_mode"])
            self.apply_color_theme(s["color_theme"])

            self.logger.info("Settings saved and applied. Destroying dialog.")
            dlg.destroy()
            self.refresh()

        btns = ctk.CTkFrame(dlg)
        btns.pack(pady=20)
        ctk.CTkButton(btns, text="OK", width=120, command=ok).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancel", width=120, command=dlg.destroy).pack(side="left", padx=10)

    def _load_first_config(self):
        if self.logic.configs_list:
            self.combo.set(self.logic.configs_list[0]["name"])
            self.logic.select_config(self.logic.configs_list[0]["name"])
            self.refresh()
            self.logger.info(f"Loaded initial config: {self.logic.configs_list[0]['name']}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ToolLauncherGUI()
    app.run()