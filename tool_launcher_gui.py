import customtkinter as ctk
from tkinter import messagebox
import os
from typing import Dict, Optional
from tool_launcher_logic import ToolLauncherLogic


class ToolLauncherGUI:
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.logic = ToolLauncherLogic(script_dir)
        sets = self.logic.load_settings()
        self.saved_settings = sets
        ctk.set_appearance_mode(sets["appearance_mode"])
        ctk.set_default_color_theme(sets["color_theme"])

        self.root = ctk.CTk()
        self.root.title("Tool Launcher")
        self.root.geometry("340x680")
        self.root.minsize(340, 500)

        self.edit_mode = False
        self.search_query = ""
        self.sidebar_visible = False
        self.animating = False
        self.sidebar_mode = ""
        self.editing_item: Optional[Dict] = None

        self._build_ui()
        self._load_first_config()

    def _build_ui(self):
        line1 = ctk.CTkFrame(self.root)
        line1.pack(fill="x", padx=12, pady=(12, 4))

        self.combo = ctk.CTkComboBox(line1, width=150,
            values=[c["name"] for c in self.logic.configs_list],
            command=self.on_config_change)
        self.combo.pack(side="left", padx=(0, 8))

        ctk.CTkButton(line1, text="Edit", width=70, command=self.toggle_edit).pack(side="left", padx=4)
        ctk.CTkButton(line1, text="History", width=80, command=self.show_history).pack(side="left", padx=4)

        self.search = ctk.CTkEntry(self.root, placeholder_text="Search name or path...")
        self.search.pack(fill="x", padx=12, pady=(0, 10))
        self.search.bind("<KeyRelease>", lambda e: self.search_update())

        self.edit_bar = ctk.CTkFrame(self.root)

        cfg_row = ctk.CTkFrame(self.edit_bar)
        cfg_row.pack(fill="x", pady=4, padx=12)
        btn = ctk.CTkButton(cfg_row, text="Add Config", width=100)
        btn.configure(command=lambda: self.open_sidebar("config_add", "Add Config"))
        btn.pack(side="left", padx=4)
        btn = ctk.CTkButton(cfg_row, text="Edit Config", width=100)
        btn.configure(command=lambda: self.open_sidebar("config_edit", "Edit Config"))
        btn.pack(side="left", padx=4)
        btn = ctk.CTkButton(cfg_row, text="Delete Config", width=100, fg_color="red")
        btn.configure(command=self.delete_config)
        btn.pack(side="left", padx=4)

        item_row = ctk.CTkFrame(self.edit_bar)
        item_row.pack(fill="x", pady=4, padx=12)
        btn = ctk.CTkButton(item_row, text="Add Item", width=100)
        btn.configure(command=lambda: self.open_sidebar("item_add", "Add Item"))
        btn.pack(side="left", padx=4)
        ctk.CTkButton(item_row, text="Refresh", width=80, command=self.refresh).pack(side="left", padx=4)
        ctk.CTkButton(item_row, text="Settings", width=90, command=self.show_settings).pack(side="left", padx=4)

        self.scroll = ctk.CTkScrollableFrame(self.root)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=8)

        self.sidebar = ctk.CTkFrame(self.root, width=300, corner_radius=0)
        self.sidebar_title = ctk.CTkLabel(self.sidebar, text="", font=("Segoe UI", 18, "bold"), anchor="w")
        self.sidebar_title.pack(pady=(16, 8), padx=16, fill="x")
        self.msg = ctk.CTkLabel(self.sidebar, text="")
        self.msg.pack(pady=4)

        # Create entry fields with proper configuration
        self.f_name = ctk.CTkEntry(self.sidebar, placeholder_text="Config Name", height=35)
        self.f_path = ctk.CTkEntry(self.sidebar, placeholder_text="Folder Path (optional)", height=35)
        self.f_filename = ctk.CTkEntry(self.sidebar, placeholder_text="Filename (e.g., my_config.json)", height=35)
        self.f_cat = ctk.CTkEntry(self.sidebar, placeholder_text="Category", height=35)
        self.f_type = ctk.CTkComboBox(self.sidebar, 
            values=["folder", "python project", "bat file", "web page"],
            height=35)
        self.f_type.set("folder")
        self.f_iname = ctk.CTkEntry(self.sidebar, placeholder_text="Name", height=35)
        self.f_ipath = ctk.CTkEntry(self.sidebar, placeholder_text="Path / URL", height=35)

        for w in (self.f_name, self.f_path, self.f_filename, self.f_cat, self.f_type, self.f_iname, self.f_ipath):
            w.pack_forget()

        btns = ctk.CTkFrame(self.sidebar)
        btns.pack(pady=20, fill="x", padx=20)
        right_frame = ctk.CTkFrame(btns)
        right_frame.pack(side="right")
        ctk.CTkButton(right_frame, text="Cancel", width=90, fg_color="gray", 
                     command=self.hide_sidebar).pack(side="right", padx=5)
        ctk.CTkButton(right_frame, text="OK", width=90, 
                     command=self.save_sidebar).pack(side="right", padx=5)
        
        
    def open_sidebar(self, mode: str, title: str, cat="", typ="", idx=-1, itm=None):
        self.sidebar_mode = mode
        self.editing_item = {"cat": cat, "typ": typ, "idx": idx, "itm": itm} if itm else None
        self.sidebar_title.configure(text=title)
        self.msg.configure(text="")

        # Hide all fields first
        for w in (self.f_name, self.f_path, self.f_filename, self.f_cat, self.f_type, self.f_iname, self.f_ipath):
            w.pack_forget()

        # Clear all fields - delete and unfocus
        for w in (self.f_name, self.f_path, self.f_filename, self.f_cat, self.f_iname, self.f_ipath):
            w.delete(0, "end")
        
        self.f_type.set("folder")

        if "config" in mode:
            self.f_name.pack(pady=8, padx=20, fill="x")
            self.f_filename.pack(pady=8, padx=20, fill="x")
            self.f_path.pack(pady=8, padx=20, fill="x")
            
            if mode == "config_edit" and self.logic.current_config:
                # Parse existing path
                full_path = self.logic.current_config.get('config_path', '')
                if full_path:
                    directory = os.path.dirname(full_path)
                    filename = os.path.basename(full_path)
                    self.f_name.insert(0, self.logic.current_config['name'])
                    self.f_filename.insert(0, filename)
                    if directory:
                        self.f_path.insert(0, directory)
        else:
            self.f_cat.pack(pady=8, padx=20, fill="x")
            self.f_type.pack(pady=8, padx=20, fill="x")
            self.f_iname.pack(pady=8, padx=20, fill="x")
            self.f_ipath.pack(pady=8, padx=20, fill="x")
            
            if mode == "item_edit" and itm:
                # For edit mode, set values (this will hide placeholders)
                self.f_cat.insert(0, cat)
                self.f_type.set(typ)
                self.f_iname.insert(0, itm["name"])
                self.f_ipath.insert(0, itm["path"])

        # Force focus away from entries to show placeholders
        self.sidebar_title.focus()
        self._show_sidebar()

    def on_config_change(self, selection):
        self.logic.select_config(selection)
        self.refresh()

    def toggle_edit(self):
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.edit_bar.pack(fill="x", pady=8)
        else:
            self.edit_bar.pack_forget()
        self.refresh()

    def search_update(self):
        self.search_query = self.search.get().strip()
        self.refresh()

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        data = self.logic.search(self.search_query)
        if not data:
            ctk.CTkLabel(self.scroll, text="No items", text_color="gray").pack(pady=40)
            return
        for cat, types in data.items():
            ctk.CTkLabel(self.scroll, text=cat.title(), 
                        font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=10, pady=(16, 4))
            for typ, items in types.items():
                ctk.CTkLabel(self.scroll, text=f"  {typ.title()}", 
                            font=("Segoe UI", 13)).pack(anchor="w", padx=20)
                for idx, itm in items:
                    self._row(itm, cat, typ, idx)

    def _row(self, itm: Dict, cat: str, typ: str, idx: int):
        frm = ctk.CTkFrame(self.scroll)
        frm.pack(fill="x", pady=3, padx=16)
        name = itm.get("name", "?")
        launch_btn = ctk.CTkButton(frm, text=name, anchor="w", height=35)
        launch_btn.configure(command=lambda: self.launch(typ, itm["path"], name))
        launch_btn.pack(side="left", fill="x", expand=True)

        if self.edit_mode:
            edit_btn = ctk.CTkButton(frm, text="Edit", width=60, height=35)
            edit_btn.configure(command=lambda: self.open_sidebar("item_edit", "Edit Item", cat, typ, idx, itm))
            edit_btn.pack(side="right", padx=2)

            del_btn = ctk.CTkButton(frm, text="Del", width=50, height=35, fg_color="red")
            del_btn.configure(command=lambda: self.del_item(cat, typ, idx))
            del_btn.pack(side="right")

    def launch(self, typ: str, path: str, name: str):
        ok, err = self.logic.launch(typ, path, name)
        if not ok:
            messagebox.showerror("Error", err)

    def save_sidebar(self):
        ok, msg = False, "Error"
        if self.sidebar_mode == "config_add":
            ok, msg = self.logic.add_config(
                self.f_name.get(), 
                self.f_path.get(), 
                self.f_filename.get()
            )
            if ok:
                self.combo.configure(values=[c["name"] for c in self.logic.configs_list])
                self.combo.set(self.f_name.get())
                self.on_config_change(self.f_name.get())
        elif self.sidebar_mode == "config_edit":
            ok, msg = self.logic.edit_config(
                self.logic.current_config['name'],
                self.f_path.get(),
                self.f_filename.get()
            )
            if ok:
                self.on_config_change(self.logic.current_config['name'])
        elif self.sidebar_mode == "item_add":
            ok, msg = self.logic.add_item(self.f_cat.get(), self.f_type.get(),
                                         self.f_iname.get(), self.f_ipath.get())
        elif self.sidebar_mode == "item_edit" and self.editing_item:
            ok, msg = self.logic.edit_item(
                self.editing_item["cat"], self.editing_item["typ"], self.editing_item["idx"],
                self.f_iname.get(), self.f_ipath.get())
        
        self.msg.configure(text=msg, text_color="green" if ok else "red")
        if ok:
            self.refresh()
            self.root.after(1200, self.hide_sidebar)

    def hide_sidebar(self):
        """Smooth sidebar closing animation."""
        if not self.sidebar_visible or self.animating:
            return
        
        self.animating = True
        steps = 20
        
        def step(n=0):
            if n <= steps:
                # Ease-in cubic for smooth closing
                progress = n / steps
                eased = progress ** 3
                new_x = 0 - (0.68 * eased)
                
                try:
                    self.sidebar.place(relx=new_x, rely=0, relheight=1, relwidth=0.68)
                    self.root.after(10, lambda: step(n + 1))
                except:
                    # Widget destroyed, stop animation
                    self.animating = False
                    return
            else:
                # Animation complete
                self.sidebar.place_forget()
                self.sidebar_visible = False
                self.animating = False
                
                # Clear all fields and remove focus to show placeholders
                for w in (self.f_name, self.f_path, self.f_filename, self.f_cat, self.f_iname, self.f_ipath):
                    w.delete(0, "end")
                
                self.f_type.set("folder")
                
                # Force focus to root to ensure placeholders show next time
                self.root.focus()
        
        step()

    def _show_sidebar(self):
        """Smooth sidebar opening animation."""
        if self.sidebar_visible or self.animating:
            return
        
        self.animating = True
        self.sidebar_visible = True
        self.sidebar.place(relx=-0.68, rely=0, relheight=1, relwidth=0.68)
        steps = 20
        
        def step(n=0):
            if n <= steps:
                # Ease-out cubic for smooth opening
                progress = n / steps
                eased = 1 - ((1 - progress) ** 3)
                new_x = -0.68 + (0.68 * eased)
                
                try:
                    self.sidebar.place(relx=new_x, rely=0, relheight=1, relwidth=0.68)
                    self.root.after(10, lambda: step(n + 1))
                except:
                    # Widget destroyed, stop animation
                    self.animating = False
                    return
            else:
                # Animation complete
                self.sidebar.place(relx=0, rely=0, relheight=1, relwidth=0.68)
                self.animating = False
        
        step()

    def del_item(self, cat: str, typ: str, idx: int):
        if messagebox.askyesno("Delete", "Remove this item?"):
            self.logic.delete_item(cat, typ, idx)
            self.refresh()

    def delete_config(self):
        if len(self.logic.configs_list) <= 1:
            messagebox.showinfo("Stop", "Keep at least one config")
            return
        if messagebox.askyesno("Delete", f"Delete {self.combo.get()}?"):
            self.logic.configs_list = [c for c in self.logic.configs_list 
                                       if c["name"] != self.combo.get()]
            self.logic.save_configs_list()
            self.combo.configure(values=[c["name"] for c in self.logic.configs_list])
            self.combo.set(self.logic.configs_list[0]["name"])
            self.on_config_change(self.logic.configs_list[0]["name"])

    def show_history(self):
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("History")
        dlg.geometry("620x540")
        dlg.transient(self.root)
        dlg.grab_set()
        
        # Center dialog
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 310
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 270
        dlg.geometry(f"+{x}+{y}")
        
        # Header
        header = ctk.CTkFrame(dlg)
        header.pack(fill="x", padx=12, pady=(12, 8))
        ctk.CTkLabel(header, text="Launch History", 
                    font=("Segoe UI", 16, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(header, text="Clear All", width=100, fg_color="red",
                     command=lambda: self._clear_history(dlg)).pack(side="right", padx=10)
        
        s = ctk.CTkScrollableFrame(dlg)
        s.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        if not self.logic.launch_history:
            ctk.CTkLabel(s, text="No history yet", text_color="gray").pack(pady=40)
        else:
            for e in reversed(self.logic.launch_history):
                f = ctk.CTkFrame(s)
                f.pack(fill="x", pady=3)
                ctk.CTkLabel(f, text=e["timestamp"], 
                            font=("Consolas", 10), text_color="gray").pack(anchor="w", padx=10, pady=(5, 0))
                ctk.CTkLabel(f, text=e["name"], 
                            font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10)
                ctk.CTkLabel(f, text=e["path"], 
                            font=("Consolas", 9)).pack(anchor="w", padx=10, pady=(0, 5))
        
        ctk.CTkButton(dlg, text="Close", width=100, command=dlg.destroy).pack(pady=8)

    def _clear_history(self, dialog):
        """Clear launch history."""
        if messagebox.askyesno("Clear History", "Clear all launch history?"):
            self.logic.clear_history()
            dialog.destroy()
            messagebox.showinfo("Done", "History cleared")

    def show_settings(self):
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("340x240")
        dlg.transient(self.root)
        dlg.grab_set()
        
        # Center dialog
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 170
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 120
        dlg.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dlg, text="Appearance Mode:").pack(pady=(20, 5))
        mode = ctk.CTkComboBox(dlg, values=["Light", "Dark", "System"], width=250)
        mode.set(self.saved_settings["appearance_mode"])
        mode.pack(pady=5)

        ctk.CTkLabel(dlg, text="Color Theme:").pack(pady=(10, 5))
        theme = ctk.CTkComboBox(dlg, values=["blue", "green", "dark-blue"], width=250)
        theme.set(self.saved_settings["color_theme"])
        theme.pack(pady=5)

        def ok():
            s = {"appearance_mode": mode.get(), "color_theme": theme.get()}
            self.logic._save_settings(s)
            self.saved_settings = s
            dlg.destroy()
            messagebox.showinfo("Settings Saved", 
                              "Changes will take effect after restarting the application.")

        btns = ctk.CTkFrame(dlg)
        btns.pack(pady=15)
        ctk.CTkButton(btns, text="OK", width=90, command=ok).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancel", width=90, command=dlg.destroy).pack(side="left", padx=10)

    def _load_first_config(self):
        if self.logic.configs_list:
            self.combo.set(self.logic.configs_list[0]["name"])
            self.logic.select_config(self.logic.configs_list[0]["name"])
            self.refresh()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ToolLauncherGUI().run()