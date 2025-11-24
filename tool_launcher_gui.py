"""
Tool Launcher GUI
Pure UI layer - ZERO business logic, no file operations
All data operations delegated to ToolLauncherLogic
"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Dict, Optional
from tool_launcher_logic import ToolLauncherLogic


class ToolLauncherGUI:
    """Main GUI class - handles ONLY user interface and events"""
    
    def __init__(self):
        """Initialize the GUI with settings and create the main window"""
        # Initialize logic layer - ALL business logic goes here
        self.logic = ToolLauncherLogic()
        
        # Load saved settings from logic layer
        self.saved_settings = self.logic.get_settings()
        
        # Apply theme settings
        ctk.set_appearance_mode(self.saved_settings["appearance_mode"])
        ctk.set_default_color_theme(self.saved_settings["color_theme"])

        # Create main window
        self.root = ctk.CTk()
        self.root.title("Tool Launcher")
        self.root.minsize(340, 500)

        # Load window position and size
        pos = self.saved_settings.get("window_pos")
        if pos and len(pos) == 4:
            self.root.geometry(f"{pos[2]}x{pos[3]}+{pos[0]}+{pos[1]}")
        else:
            self.root.geometry("440x680")

        # Initialize UI state variables
        self.edit_mode = False
        self.show_text = self.saved_settings.get("show_text", True)
        self.sidebar_visible = False
        self.animating = False
        self.sidebar_mode = ""
        self.editing_item: Optional[Dict] = None

        # Build UI components
        self._build_ui()
        self._load_first_config()
        
        # Force entry field redraw after initialization
        self.root.after(200, self._redraw_entries)

        # Save position on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """Save window position before closing"""
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        
        # Delegate to logic layer
        self.logic.save_window_position(x, y, w, h)
        self.root.destroy()

    def _build_ui(self):
        """Build all UI components"""
        # ===== HEADER LINE 1: Config selector and Edit button =====
        line1 = ctk.CTkFrame(self.root)
        line1.pack(fill="x", padx=12, pady=(12, 4))

        self.combo = ctk.CTkComboBox(
            line1, 
            width=200,
            values=self.logic.get_config_names(),
            command=self.on_config_change
        )
        self.combo.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            line1, 
            text="Edit", 
            width=80, 
            command=self.toggle_edit
        ).pack(side="left", padx=4)

        # ===== HEADER LINE 2: Search bar (full width) =====
        self.search = ctk.CTkEntry(
            self.root, 
            placeholder_text="Search name or path..."
        )
        self.search.pack(fill="x", padx=12, pady=(0, 10))
        self.search.bind("<KeyRelease>", lambda e: self.on_search_change())

        # ===== EDIT MODE BAR (hidden by default) =====
        self.edit_bar = ctk.CTkFrame(self.root)

        # Config management row
        cfg_row = ctk.CTkFrame(self.edit_bar)
        cfg_row.pack(fill="x", pady=4, padx=12)
        
        ctk.CTkButton(
            cfg_row, 
            text="Add Config", 
            width=110,
            command=lambda: self.open_sidebar("config_add", "Add Config")
        ).pack(side="left", padx=4)
        
        ctk.CTkButton(
            cfg_row, 
            text="Edit Config", 
            width=110,
            command=lambda: self.open_sidebar("config_edit", "Edit Config")
        ).pack(side="left", padx=4)
        
        ctk.CTkButton(
            cfg_row, 
            text="Delete Config", 
            width=110, 
            fg_color="red", 
            hover_color="red",
            command=self.on_delete_config
        ).pack(side="left", padx=4)

        # Item management row
        item_row = ctk.CTkFrame(self.edit_bar)
        item_row.pack(fill="x", pady=4, padx=12)
        
        ctk.CTkButton(
            item_row, 
            text="Add Item", 
            width=100,
            command=lambda: self.open_sidebar("item_add", "Add Item")
        ).pack(side="left", padx=4)
        
        ctk.CTkButton(
            item_row, 
            text="Refresh", 
            width=90, 
            command=self.refresh_display
        ).pack(side="left", padx=4)
        
        ctk.CTkButton(
            item_row, 
            text="Settings", 
            width=90, 
            command=self.show_settings
        ).pack(side="left", padx=4)

        # ===== SCROLLABLE CONTENT AREA =====
        self.scroll = ctk.CTkScrollableFrame(self.root)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=8)

        # ===== SIDEBAR (slides in from left) =====
        self.sidebar = ctk.CTkFrame(self.root, width=300, corner_radius=0)
        
        # Sidebar title
        self.sidebar_title = ctk.CTkLabel(
            self.sidebar, 
            text="", 
            font=("Segoe UI", 18, "bold"), 
            anchor="w"
        )
        self.sidebar_title.pack(pady=(16, 8), padx=16, fill="x")
        
        # Message label for feedback
        self.msg = ctk.CTkLabel(self.sidebar, text="")
        self.msg.pack(pady=4)

        # ===== SIDEBAR INPUT FIELDS =====
        # Config fields
        self.f_name = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="Config Name", 
            height=35
        )
        self.f_path = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="Folder Path (optional)", 
            height=35
        )
        self.f_filename = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="Filename (e.g., my_config.json)", 
            height=35
        )
        
        # Item fields
        self.f_cat = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="Category", 
            height=35
        )
        self.f_type = ctk.CTkComboBox(
            self.sidebar, 
            values=["folder", "python project", "bat file", "web page"], 
            height=35
        )
        self.f_type.set("folder")
        
        self.f_iname = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="Name", 
            height=35
        )
        self.f_ipath = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="Path / URL", 
            height=35
        )

        # Hide all fields initially
        for w in (self.f_name, self.f_path, self.f_filename, 
                  self.f_cat, self.f_type, self.f_iname, self.f_ipath):
            w.pack_forget()

        # Sidebar buttons
        btns = ctk.CTkFrame(self.sidebar)
        btns.pack(pady=20, fill="x", padx=20)
        
        right_frame = ctk.CTkFrame(btns)
        right_frame.pack(side="right")
        
        ctk.CTkButton(
            right_frame, 
            text="Cancel", 
            width=90, 
            fg_color="gray", 
            command=self.hide_sidebar
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            right_frame, 
            text="OK", 
            width=90, 
            command=self.on_sidebar_save
        ).pack(side="right", padx=5)

    def _redraw_entries(self):
        """Force entry fields to redraw - fixes placeholder text visibility"""
        for w in (self.f_name, self.f_path, self.f_filename, 
                  self.f_cat, self.f_iname, self.f_ipath, self.search):
            w.update_idletasks()

    def open_sidebar(self, mode: str, title: str, cat="", typ="", idx=-1, itm=None):
        """
        Open sidebar for add/edit operations
        
        Args:
            mode: Operation mode (config_add, config_edit, item_add, item_edit)
            title: Sidebar title
            cat: Category (for items)
            typ: Type (for items)
            idx: Item index (for editing)
            itm: Item data (for editing)
        """
        self.sidebar_mode = mode
        self.editing_item = {"cat": cat, "typ": typ, "idx": idx, "itm": itm} if itm else None
        self.sidebar_title.configure(text=title)
        self.msg.configure(text="")

        # Hide and clear all fields
        for w in (self.f_name, self.f_path, self.f_filename, 
                  self.f_cat, self.f_type, self.f_iname, self.f_ipath):
            w.pack_forget()
            w.delete(0, "end")

        self.f_type.set("folder")

        # Show appropriate fields based on mode
        if "config" in mode:
            self.f_name.pack(pady=8, padx=20, fill="x")
            self.f_filename.pack(pady=8, padx=20, fill="x")
            self.f_path.pack(pady=8, padx=20, fill="x")
            
            # Populate fields for edit mode
            if mode == "config_edit":
                config_data = self.logic.get_current_config_data()
                if config_data:
                    self.f_name.insert(0, config_data['name'])
                    self.f_filename.insert(0, config_data['filename'])
                    self.f_path.insert(0, config_data['directory'])
        else:
            # Item add/edit
            self.f_cat.pack(pady=8, padx=20, fill="x")
            self.f_type.pack(pady=8, padx=20, fill="x")
            self.f_iname.pack(pady=8, padx=20, fill="x")
            self.f_ipath.pack(pady=8, padx=20, fill="x")
            
            # Populate fields for edit mode
            if mode == "item_edit" and itm:
                self.f_cat.insert(0, cat)
                self.f_type.set(typ)
                self.f_iname.insert(0, itm["name"])
                self.f_ipath.insert(0, itm["path"])

        self._show_sidebar()

    def _show_sidebar(self):
        """Animate sidebar sliding in from left"""
        if self.sidebar_visible or self.animating:
            return
        
        self.animating = True
        # Start off-screen to the left
        self.sidebar.place(relx=-0.68, rely=0, relheight=1, relwidth=0.68)
        self.sidebar_visible = True
        
        def step(n=0):
            if n < 20:
                # Smooth animation: slide from -0.68 to 0
                progress = n / 20
                self.sidebar.place(
                    relx=-0.68 + 0.68 * progress, 
                    rely=0, 
                    relheight=1, 
                    relwidth=0.68
                )
                self.root.after(8, lambda: step(n + 1))
            else:
                # Final position
                self.sidebar.place(relx=0, rely=0, relheight=1, relwidth=0.68)
                self.animating = False
                # Force entry fields to redraw
                self.root.after(200, self._redraw_entries)
        
        step()

    def hide_sidebar(self):
        """Animate sidebar sliding out to the left"""
        if not self.sidebar_visible or self.animating:
            return
        
        self.animating = True
        
        def step(n=0):
            if n < 20:
                # Smooth animation: slide from 0 to -0.68
                progress = n / 20
                self.sidebar.place(
                    relx=-0.68 * progress, 
                    rely=0, 
                    relheight=1, 
                    relwidth=0.68
                )
                self.root.after(8, lambda: step(n + 1))
            else:
                # Remove from view
                self.sidebar.place_forget()
                self.sidebar_visible = False
                self.animating = False
                # Clear all fields
                for w in (self.f_name, self.f_path, self.f_filename, 
                          self.f_cat, self.f_iname, self.f_ipath):
                    w.delete(0, "end")
        
        step()

    def on_sidebar_save(self):
        """Handle sidebar save button - delegates to logic layer"""
        ok, msg = False, "Error"
        
        if self.sidebar_mode == "config_add":
            ok, msg = self.logic.add_config(
                self.f_name.get(), 
                self.f_path.get(), 
                self.f_filename.get()
            )
            if ok:
                # Update combo box with new config list
                self.combo.configure(values=self.logic.get_config_names())
                self.combo.set(self.f_name.get())
                
        elif self.sidebar_mode == "config_edit":
            ok, msg = self.logic.edit_config(
                self.f_path.get(), 
                self.f_filename.get()
            )
            
        elif self.sidebar_mode == "item_add":
            ok, msg = self.logic.add_item(
                self.f_cat.get(), 
                self.f_type.get(), 
                self.f_iname.get(), 
                self.f_ipath.get()
            )
            
        elif self.sidebar_mode == "item_edit" and self.editing_item:
            ok, msg = self.logic.edit_item(
                self.editing_item["cat"], 
                self.editing_item["typ"], 
                self.editing_item["idx"],
                self.f_iname.get(), 
                self.f_ipath.get()
            )
        
        # Show feedback message
        self.msg.configure(text=msg, text_color="green" if ok else "red")
        
        if ok:
            self.refresh_display()
            # Auto-close sidebar after 1 second
            self.root.after(1000, self.hide_sidebar)

    def on_config_change(self, selection: str):
        """Handle config selection change"""
        self.logic.select_config(selection)
        self.refresh_display()

    def toggle_edit(self):
        """Toggle edit mode on/off"""
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.edit_bar.pack(fill="x", pady=8)
        else:
            self.edit_bar.pack_forget()
        self.refresh_display()

    def on_search_change(self):
        """Handle search text change"""
        self.refresh_display()

    def refresh_display(self):
        """Refresh the items display - gets data from logic layer"""
        # Clear existing items
        for w in self.scroll.winfo_children():
            w.destroy()
        
        # Get filtered data from logic layer
        query = self.search.get().strip()
        data = self.logic.get_filtered_items(query)
        
        if not data:
            ctk.CTkLabel(
                self.scroll, 
                text="No items found", 
                text_color="gray"
            ).pack(pady=40)
            return
        
        # Display items by category and type
        for cat, types in data.items():
            # Category header
            ctk.CTkLabel(
                self.scroll, 
                text=cat.title(), 
                font=("Segoe UI", 18, "bold")
            ).pack(anchor="w", padx=10, pady=(16, 4))
            
            for typ, items in types.items():
                # Type subheader
                ctk.CTkLabel(
                    self.scroll, 
                    text=f"  {typ.title()}", 
                    font=("Segoe UI", 13)
                ).pack(anchor="w", padx=20)
                
                # Display each item
                for idx, itm in items:
                    self._create_item_row(itm, cat, typ, idx)

    def _create_item_row(self, itm: Dict, cat: str, typ: str, idx: int):
        """
        Create a row for a single item - pure UI
        
        Args:
            itm: Item data
            cat: Category
            typ: Type
            idx: Item index
        """
        frm = ctk.CTkFrame(self.scroll)
        frm.pack(fill="x", pady=3, padx=16)
        
        name = itm.get("name", "?")
        
        # Launch button (full width)
        launch_btn = ctk.CTkButton(frm, text=name, anchor="w")
        launch_btn.configure(command=lambda: self.on_launch_item(typ, itm["path"], name))
        launch_btn.pack(side="left", fill="x", expand=True)

        # Edit and Delete buttons (only in edit mode)
        if self.edit_mode:
            # Edit button
            edit_text = "Edit" if self.show_text else "✏"
            edit_btn = ctk.CTkButton(frm, text=edit_text, width=60)
            edit_btn.configure(
                command=lambda: self.open_sidebar("item_edit", "Edit Item", cat, typ, idx, itm)
            )
            edit_btn.pack(side="right", padx=2)

            # Delete button (red, no blue flash)
            del_text = "Delete" if self.show_text else "✖"
            del_btn = ctk.CTkButton(
                frm, 
                text=del_text, 
                width=70, 
                fg_color="red", 
                hover_color="red"
            )
            del_btn.configure(command=lambda: self.on_delete_item(cat, typ, idx))
            del_btn.pack(side="right")

    def on_launch_item(self, typ: str, path: str, name: str):
        """Handle item launch - delegates to logic layer"""
        ok, err = self.logic.launch_item(typ, path, name)
        if not ok:
            messagebox.showerror("Launch Error", err)

    def on_delete_item(self, cat: str, typ: str, idx: int):
        """Handle item deletion with confirmation"""
        if messagebox.askyesno("Delete Item", "Remove this item?"):
            self.logic.delete_item(cat, typ, idx)
            self.refresh_display()

    def on_delete_config(self):
        """Handle config deletion with confirmation"""
        if self.logic.get_config_count() <= 1:
            messagebox.showinfo("Cannot Delete", "Keep at least one config")
            return
        
        current_name = self.combo.get()
        if messagebox.askyesno("Delete Config", f"Delete '{current_name}'?"):
            self.logic.delete_config(current_name)
            
            # Update UI
            self.combo.configure(values=self.logic.get_config_names())
            first_config = self.logic.get_first_config_name()
            self.combo.set(first_config)
            self.on_config_change(first_config)

    def show_settings(self):
        """Show settings dialog - pure UI"""
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("400x360")
        dlg.transient(self.root)
        dlg.grab_set()

        # Get current settings from logic layer
        current_settings = self.logic.get_settings()

        # Appearance Mode
        ctk.CTkLabel(
            dlg, 
            text="Appearance:", 
            font=("Segoe UI", 14)
        ).pack(pady=(20, 5))
        
        mode = ctk.CTkComboBox(
            dlg, 
            values=["Light", "Dark", "System"], 
            width=320
        )
        mode.set(current_settings["appearance_mode"])
        mode.pack(pady=5)

        # Color Theme
        ctk.CTkLabel(
            dlg, 
            text="Color Theme:", 
            font=("Segoe UI", 14)
        ).pack(pady=(15, 5))
        
        theme = ctk.CTkComboBox(
            dlg, 
            values=["blue", "green", "dark-blue", "gray", "purple", "orange"], 
            width=320
        )
        theme.set(current_settings["color_theme"])
        theme.pack(pady=5)

        # Button Labels Toggle
        ctk.CTkLabel(
            dlg, 
            text="Button Labels:", 
            font=("Segoe UI", 14)
        ).pack(pady=(15, 5))
        
        text_switch = ctk.CTkSwitch(
            dlg, 
            text="Show Text (vs Symbols)"
        )
        text_switch.pack(pady=5)
        if self.show_text:
            text_switch.select()
        else:
            text_switch.deselect()

        def ok():
            """Save settings and apply changes"""
            new_settings = {
                "appearance_mode": mode.get(),
                "color_theme": theme.get(),
                "show_text": text_switch.get()
            }
            
            # Delegate to logic layer
            self.logic.update_settings(new_settings)
            
            # Update local state
            self.saved_settings = self.logic.get_settings()
            self.show_text = new_settings["show_text"]
            
            # Apply theme changes
            ctk.set_appearance_mode(new_settings["appearance_mode"])
            ctk.set_default_color_theme(new_settings["color_theme"])
            
            dlg.destroy()
            self.refresh_display()

        # Dialog buttons
        btns = ctk.CTkFrame(dlg)
        btns.pack(pady=20)
        
        ctk.CTkButton(
            btns, 
            text="OK", 
            width=120, 
            command=ok
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btns, 
            text="Cancel", 
            width=120, 
            command=dlg.destroy
        ).pack(side="left", padx=10)

    def _load_first_config(self):
        """Load the first available config on startup"""
        first_config = self.logic.get_first_config_name()
        if first_config:
            self.combo.set(first_config)
            self.logic.select_config(first_config)
            self.refresh_display()

    def run(self):
        """Start the application main loop"""
        self.root.mainloop()


if __name__ == "__main__":
    ToolLauncherGUI().run()