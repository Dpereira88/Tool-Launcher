import customtkinter as ctk
import json
import os
import sys
import subprocess
import webbrowser
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox as tk_msgbox

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ─────────────────────────────────────────────
#  Icon library  — grouped for the picker
# ─────────────────────────────────────────────
ICON_GROUPS = {
    "General":    ["⚙️","🔧","🛠️","🔩","📌","📍","🗂️","📁","📂","💾","💿","🖥️","🖨️","⌨️","🖱️","📡","🔌","🔋","💡","🔦"],
    "Files":      ["📄","📃","📋","📊","📈","📉","📝","✏️","🖊️","📎","🗃️","🗄️","🗑️","📦","📬","📭","📮","📯","📰","🗞️"],
    "Web":        ["🌐","🔗","🔒","🔓","📧","💬","🗨️","💭","📲","☎️","📞","📟","📠","🛜","📶","🔈","🔉","🔊","🔕","🔔"],
    "Code":       ["💻","🖥️","⌨️","🐍","🐞","🦟","🔬","🧪","🧬","⚗️","🧮","🧩","🗜️","📐","📏","🔭","🛰️","🤖","🧠","💾"],
    "Workflow":   ["▶️","⏩","⏸️","⏹️","⏺️","🔄","♻️","✅","❌","⚠️","🚫","❓","❗","💯","🏁","🚀","🎯","📌","🗝️","🔑"],
    "Data":       ["📊","📈","📉","🗃️","💹","🏦","💰","💵","💳","🧾","📋","🗂️","🔢","🔡","🔠","🔣","🔤","Ω","∑","π"],
    "Tools":      ["🔨","⛏️","⚒️","🛠️","⚙️","🔧","🪛","🔩","🗜️","⚖️","🧲","🪝","🧰","🪤","🪣","🪜","🧱","🪞","🪟","🚪"],
    "Symbols":    ["★","☆","♦","♣","♠","♥","✦","✧","✪","✫","✬","✭","✮","✯","✰","⬛","⬜","🟥","🟩","🟦"],
    "Arrows":     ["→","←","↑","↓","↗","↘","↙","↖","↔","↕","⇒","⇐","⇑","⇓","⇔","⇕","➡️","⬅️","⬆️","⬇️"],
    "People":     ["👤","👥","🧑","👨","👩","🧑‍💻","👨‍💻","👩‍💻","🧑‍🔧","👷","🧑‍🏭","👔","🤝","👋","✋","🖐️","👍","👎","🫱","🫲"],
}

# ─────────────────────────────────────────────
#  Icon picker dialog  — full CustomTkinter UI
# ─────────────────────────────────────────────
class IconPickerDialog:
    COLS = 8

    def __init__(self, parent, current_icon=""):
        self.result   = None
        self._selected = current_icon

        # ── Window ──
        self._win = ctk.CTkToplevel(parent)
        self._win.title("Pick Icon")
        self._win.grab_set()
        self._win.resizable(True, True)
        parent.update_idletasks()
        self._win.geometry(f"480x520+{parent.winfo_rootx()+20}+{parent.winfo_rooty()+20}")

        # ── Search row ──
        search_row = ctk.CTkFrame(self._win, fg_color="transparent")
        search_row.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(search_row, text="🔍", width=24).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._render())
        ctk.CTkEntry(search_row, textvariable=self._search_var,
                     placeholder_text="Search icons…").pack(
                     side="left", fill="x", expand=True, padx=(6, 0))

        # ── Selected preview row ──
        sel_row = ctk.CTkFrame(self._win, fg_color="transparent")
        sel_row.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(sel_row, text="Selected:", font=("Arial", 12),
                     width=70, anchor="w").pack(side="left")
        self._sel_label = ctk.CTkLabel(sel_row, text=current_icon or "—",
                                       font=("Segoe UI Emoji", 22), width=40)
        self._sel_label.pack(side="left", padx=6)
        ctk.CTkButton(sel_row, text="✖  Clear", width=80, fg_color="#555",
                      hover_color="#666", command=self._clear).pack(side="left", padx=4)

        # ── Group tab bar (scrollable horizontally via wrapping frame) ──
        self._group_var = tk.StringVar(value=list(ICON_GROUPS.keys())[0])
        tab_outer = ctk.CTkFrame(self._win)
        tab_outer.pack(fill="x", padx=12, pady=(0, 4))
        self._tab_btns = {}
        for g in ICON_GROUPS:
            b = ctk.CTkButton(tab_outer, text=g, width=0,
                              fg_color="transparent", hover_color=("gray80","gray30"),
                              font=("Arial", 11),
                              command=lambda grp=g: self._switch_group(grp))
            b.pack(side="left", padx=2, pady=4)
            self._tab_btns[g] = b
        self._highlight_tab(self._group_var.get())

        # ── Icon grid inside a CTkScrollableFrame ──
        self._grid_frame = ctk.CTkScrollableFrame(self._win)
        self._grid_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # ── OK / Cancel ──
        bot = ctk.CTkFrame(self._win, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(bot, text="Cancel", width=100, fg_color="#555",
                      hover_color="#666",
                      command=self._win.destroy).pack(side="right", padx=4)
        ctk.CTkButton(bot, text="✔  OK", width=100,
                      command=self._ok).pack(side="right", padx=4)

        self._render()
        self._win.wait_window()

    # ── Tab highlight ──
    def _switch_group(self, grp):
        self._group_var.set(grp)
        self._highlight_tab(grp)
        self._render()

    def _highlight_tab(self, active):
        for g, b in self._tab_btns.items():
            if g == active:
                b.configure(fg_color=("gray75", "gray35"),
                            font=("Arial", 11, "bold"))
            else:
                b.configure(fg_color="transparent",
                            font=("Arial", 11))

    # ── Icon grid render ──
    def _render(self):
        for w in self._grid_frame.winfo_children():
            w.destroy()
        query = self._search_var.get().lower()
        icons = ([ic for grp in ICON_GROUPS.values() for ic in grp if query in ic.lower()]
                 if query else ICON_GROUPS.get(self._group_var.get(), []))

        for col in range(self.COLS):
            self._grid_frame.columnconfigure(col, weight=1)

        for i, icon in enumerate(icons):
            r, c = divmod(i, self.COLS)
            is_sel = (icon == self._selected)
            fg = ("gray70", "gray40") if not is_sel else ("#3a7ebf", "#1a5ea0")
            btn = ctk.CTkButton(
                self._grid_frame,
                text=icon,
                font=("Segoe UI Emoji", 18),
                width=44, height=44,
                fg_color=fg,
                hover_color=("gray65", "gray45"),
                border_width=2 if is_sel else 0,
                border_color="#3a7ebf",
                command=lambda ic=icon: self._pick(ic)
            )
            btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

    def _pick(self, icon):
        self._selected = icon
        self._sel_label.configure(text=icon)
        self._render()

    def _clear(self):
        self._selected = ""
        self._sel_label.configure(text="—")
        self._render()

    def _ok(self):
        self.result = self._selected
        self._win.destroy()


# ═════════════════════════════════════════════
#  Main App
# ═════════════════════════════════════════════
class ToolLauncher:
    def __init__(self) -> None:
        self.root = ctk.CTk()
        self.root.title("Tool Launcher")

        self.sidebar_width   = 300
        self.main_base_width = 450

        self.script_dir          = self.get_app_dir()
        self.unified_config_file = os.path.join(self.script_dir, "app_config.json")
        self.app_data            = self.load_unified_data()

        _s = self.app_data.get("settings", {})
        self.font_size      = _s.get("font_size",      13)
        self.text_anchor    = _s.get("text_anchor",    "center")
        self.topic_color    = _s.get("topic_color",    "#3a7ebf")
        self.topic_font     = _s.get("topic_font",     "bold")
        self.subtopic_color = _s.get("subtopic_color", "")
        self.subtopic_font  = _s.get("subtopic_font",  "italic")
        self.btn_columns    = _s.get("btn_columns",    1)
        self.btn_square     = _s.get("btn_square",     False)

        self.apply_window_state()

        self.current_tools      = {}
        self.active_config_path = None
        self.search_query       = ""
        self.selected_color     = "#3a7ebf"
        self.editing_tool_ref   = None
        self._context_menu      = None
        self._collapsed_cats    = set()
        self._drag_tool         = None
        self._drag_widget       = None
        # icon editor state
        self._edit_icon         = ""
        self._edit_icon_mode    = "text"   # "text" | "icon" | "both"

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Button-1>", self._dismiss_context_menu, add="+")
        self.root.bind("<Control-f>", lambda e: self._focus_search())
        self.root.bind("<Control-F>", lambda e: self._focus_search())

        # ── Main layout ──
        self.main_view = ctk.CTkFrame(self.root, width=self.main_base_width)
        self.main_view.pack(side="right", fill="both", expand=False)
        self.main_view.pack_propagate(False)

        self.header = ctk.CTkFrame(self.main_view)
        self.header.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(self.header, text="⚙️", width=20, command=self.show_settings,
                      fg_color="transparent").pack(side="left", padx=2)
        self.config_combo = ctk.CTkComboBox(self.header, values=[], command=self.on_config_select)
        self.config_combo.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(self.header, text="➕", width=20, command=self.show_add_sidebar,
                      fg_color="transparent").pack(side="left", padx=2)

        self.search_entry = ctk.CTkEntry(self.main_view, placeholder_text="Search tools…  (Ctrl+F)")
        self.search_entry.pack(fill="x", padx=15, pady=(0, 10))
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_view)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.focus_sink = ctk.CTkLabel(self.main_view, text="", width=1)
        self.focus_sink.place(x=-10, y=-10)

        # ── Sidebars ──
        self.sidebar_settings = ctk.CTkFrame(self.root, width=self.sidebar_width, border_width=1)
        self.sidebar_settings.pack_propagate(False)
        self.setup_settings_ui()

        self.sidebar_editor = ctk.CTkFrame(self.root, width=self.sidebar_width, border_width=1)
        self.sidebar_editor.pack_propagate(False)
        self.setup_editor_ui()

        self.refresh_config_list()
        if self.app_data["configs_list"]:
            self.on_config_select(self.app_data["configs_list"][0]['name'])

    # ══════════════════════════════════════════
    #  Ctrl+F
    # ══════════════════════════════════════════
    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    # ══════════════════════════════════════════
    #  CONTEXT MENU
    # ══════════════════════════════════════════
    def _dismiss_context_menu(self, event=None):
        if self._context_menu:
            try:
                self._context_menu.destroy()
            except Exception:
                pass
            self._context_menu = None

    def show_context_menu(self, event, cat, sub, tool):
        self._dismiss_context_menu()
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="✏️  Edit",      command=lambda: self.trigger_edit(cat, sub, tool))
        menu.add_command(label="📋  Duplicate", command=lambda: self.duplicate_tool(cat, sub, tool))
        path   = tool.get('path', '')
        is_web = path.startswith("http")
        is_dir = os.path.isdir(path)
        if not is_web and not is_dir:
            menu.add_command(label="📂  Open File Location",
                             command=lambda: self.open_file_location(path))
        menu.add_separator()
        menu.add_command(label="📄  Copy Path / URL",
                         command=lambda: self._copy_to_clipboard(path))
        menu.post(event.x_root, event.y_root)
        self._context_menu = menu
        menu.bind("<FocusOut>", lambda e: self._dismiss_context_menu())

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def duplicate_tool(self, cat, sub, tool):
        import copy
        new_tool = copy.deepcopy(tool)
        new_tool['name'] = tool['name'] + " (copy)"
        self.current_tools[cat][sub].append(new_tool)
        self.save_current_json()
        self.populate_ui()

    def open_file_location(self, path):
        if not path or not os.path.exists(path):
            return
        subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')

    # ══════════════════════════════════════════
    #  DRAG & DROP
    # ══════════════════════════════════════════
    def _drag_start(self, event, cat, sub, tool):
        self._drag_tool   = (cat, sub, tool)
        self._drag_widget = event.widget
        try:
            event.widget.configure(fg_color="#555555")
        except Exception:
            pass

    def _drag_end(self, event, cat, sub, tool):
        if self._drag_tool is None:
            return
        src_cat, src_sub, src_tool = self._drag_tool
        self._drag_tool = None
        if self._drag_widget:
            try:
                self._drag_widget.configure(fg_color=src_tool.get("color") or "#3a7ebf")
            except Exception:
                pass
        target = event.widget.winfo_containing(event.x_root, event.y_root)
        if target is None or target is self._drag_widget:
            return
        dst = getattr(target, "_tool_data", None)
        if dst is None:
            return
        dst_cat, dst_sub, dst_tool = dst
        if src_cat != dst_cat or src_sub != dst_sub:
            return
        lst = self.current_tools.get(src_cat, {}).get(src_sub, [])
        if src_tool not in lst or dst_tool not in lst:
            return
        si, di = lst.index(src_tool), lst.index(dst_tool)
        lst.insert(di, lst.pop(si))
        for idx, t in enumerate(lst):
            t["pos_id"] = str(idx + 1)
        self.save_current_json()
        self.populate_ui()

    # ══════════════════════════════════════════
    #  BUTTON RENDERING HELPERS
    # ══════════════════════════════════════════
    def _btn_display(self, tool):
        """Return label text based on icon_mode."""
        name      = tool.get('name', '')
        icon      = tool.get('icon', '')
        icon_mode = tool.get('icon_mode', 'text')
        if icon and icon_mode == 'icon':
            return icon
        elif icon and icon_mode == 'both':
            return f"{icon}  {name}"
        return name

    def _btn_font(self, tool):
        """Return correct font depending on display mode."""
        icon_mode = tool.get('icon_mode', 'text')
        icon      = tool.get('icon', '')
        if icon and (icon_mode == 'icon' or icon_mode == 'both'):
            return ("Segoe UI Emoji", self.font_size)
        # 'both' and 'text' — use regular font so Latin text renders correctly
        return ("Arial", self.font_size)

    # ══════════════════════════════════════════
    #  CORE UI  — grid layout
    # ══════════════════════════════════════════
    def _make_btn_grid(self, parent, tools_sorted):
        cols = max(1, self.btn_columns)

        def _layout(_tools=tools_sorted, _parent=parent):
            _parent.update_idletasks()
            available = _parent.winfo_width()
            if available < 10:
                available = self.main_base_width - 30
            cell_w = available // cols
            btn_h  = cell_w if self.btn_square else 34

            for col_idx in range(cols):
                _parent.columnconfigure(col_idx, weight=1, minsize=cell_w)

            for i, tool in enumerate(_tools):
                r, c = divmod(i, cols)
                btn_color   = tool.get('color') or "#3a7ebf"
                label       = self._btn_display(tool)
                font        = self._btn_font(tool)

                btn = ctk.CTkButton(
                    _parent,
                    text=label,
                    font=font,
                    fg_color=btn_color,
                    anchor=self.text_anchor,
                    height=btn_h,
                    command=lambda p=tool.get('path'): self.smart_open(p)
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                btn._tool_data = (tool.get('_cat',''), tool.get('_sub',''), tool)

                btn.bind("<Button-3>",
                         lambda e, t=tool: self.show_context_menu(
                             e, t.get('_cat',''), t.get('_sub',''), t))
                btn.bind("<ButtonPress-1>",
                         lambda e, t=tool: self._drag_start(
                             e, t.get('_cat',''), t.get('_sub',''), t), add="+")
                btn.bind("<ButtonRelease-1>",
                         lambda e, t=tool: self._drag_end(
                             e, t.get('_cat',''), t.get('_sub',''), t), add="+")

        parent.after(10, _layout)

    def populate_ui(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        topic_kw   = {"text_color": self.topic_color} if self.topic_color else {}
        topic_font = ("Arial", self.font_size + 4, self.topic_font)
        sub_kw     = {"text_color": self.subtopic_color} if self.subtopic_color else {}
        sub_font   = ("Arial", self.font_size + 2, self.subtopic_font)

        for cat_name, sub_cats in sorted(self.current_tools.items()):
            is_collapsed = cat_name in self._collapsed_cats
            hdr_row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            hdr_row.pack(fill="x", pady=(15, 2))
            arrow   = "▶" if is_collapsed else "▼"
            hdr_lbl = ctk.CTkLabel(hdr_row, text=f"{arrow}  {cat_name.upper()}",
                                   font=topic_font, cursor="hand2", **topic_kw)
            hdr_lbl.pack(side="left")
            hdr_lbl.bind("<Button-1>", lambda e, c=cat_name: self._toggle_cat(c))

            if is_collapsed:
                continue

            for sub_name, tools in sorted(sub_cats.items()):
                ctk.CTkLabel(self.scroll_frame, text=f"  {sub_name}",
                             font=sub_font, **sub_kw).pack(anchor="w", pady=(4, 2))

                filtered = [t for t in
                            sorted(tools, key=lambda x: (int(x.get('pos_id', 999)),
                                                          x['name'].lower()))
                            if not self.search_query or self.search_query in t['name'].lower()]
                if not filtered:
                    continue

                for t in filtered:
                    t['_cat'] = cat_name
                    t['_sub'] = sub_name

                grid_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
                grid_frame.pack(fill="x", pady=2)
                self._make_btn_grid(grid_frame, filtered)

    def _toggle_cat(self, cat_name):
        if cat_name in self._collapsed_cats:
            self._collapsed_cats.discard(cat_name)
        else:
            self._collapsed_cats.add(cat_name)
        self.populate_ui()

    # ══════════════════════════════════════════
    #  SETTINGS UI
    # ══════════════════════════════════════════
    def setup_settings_ui(self):
        settings_scroll = ctk.CTkScrollableFrame(self.sidebar_settings)
        settings_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(settings_scroll, text="App Settings",
                     font=("Arial", 18, "bold")).pack(pady=20)

        # Config manager
        self.cfg_scroll = ctk.CTkScrollableFrame(settings_scroll, height=160,
                                                 label_text="Configurations")
        self.cfg_scroll.pack(fill="x", padx=10, pady=5)
        self.render_config_manager()
        ctk.CTkButton(settings_scroll, text="+ Add Config",
                      command=self.add_config_file).pack(pady=5, padx=20, fill="x")

        # Alignment
        pref_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        pref_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(pref_frame, text="Button Text Alignment:",
                     font=("Arial", 12)).pack(anchor="w", padx=5)
        self.anchor_combo = ctk.CTkComboBox(pref_frame, values=["Center","Left","Right"],
                                            command=self.change_text_anchor)
        inv_map = {"center":"Center","w":"Left","e":"Right"}
        self.anchor_combo.set(inv_map.get(self.text_anchor,"Center"))
        self.anchor_combo.pack(fill="x", padx=5, pady=5)

        # Font size
        fs_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        fs_frame.pack(fill="x", padx=10, pady=(4, 0))
        ctk.CTkLabel(fs_frame, text="Button Font Size:", font=("Arial",12)).pack(anchor="w", padx=5)
        fs_row = ctk.CTkFrame(fs_frame, fg_color="transparent")
        fs_row.pack(fill="x", padx=5)
        self._fs_label = ctk.CTkLabel(fs_row, text=str(self.font_size), width=28)
        self._fs_label.pack(side="right")
        self._fs_slider = ctk.CTkSlider(fs_row, from_=9, to=24, number_of_steps=15,
                                        command=self._on_font_size_change)
        self._fs_slider.set(self.font_size)
        self._fs_slider.pack(side="left", fill="x", expand=True, pady=4)

        # Button Layout
        layout_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        layout_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(layout_frame, text="Button Layout",
                     font=("Arial",12,"bold")).pack(anchor="w", padx=5, pady=(4,6))

        col_row = ctk.CTkFrame(layout_frame, fg_color="transparent")
        col_row.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(col_row, text="Columns per row:", width=130,
                     anchor="w", font=("Arial",12)).pack(side="left")
        self._col_label = ctk.CTkLabel(col_row, text=str(self.btn_columns), width=24)
        self._col_label.pack(side="right")
        self._col_slider = ctk.CTkSlider(col_row, from_=1, to=6, number_of_steps=5,
                                         command=self._on_col_change)
        self._col_slider.set(self.btn_columns)
        self._col_slider.pack(side="left", fill="x", expand=True, padx=(4,4))

        sq_row = ctk.CTkFrame(layout_frame, fg_color="transparent")
        sq_row.pack(fill="x", padx=5, pady=(6,2))
        ctk.CTkLabel(sq_row, text="Square buttons:", font=("Arial",12)).pack(side="left")
        self._sq_switch = ctk.CTkSwitch(sq_row, text="", command=self._on_square_toggle)
        if self.btn_square:
            self._sq_switch.select()
        self._sq_switch.pack(side="left", padx=8)

        prev_outer = ctk.CTkFrame(layout_frame, fg_color="transparent")
        prev_outer.pack(fill="x", padx=5, pady=(8,4))
        ctk.CTkLabel(prev_outer, text="Preview:", font=("Arial",11),
                     text_color="gray").pack(anchor="w")
        self._preview_frame = ctk.CTkFrame(prev_outer, height=80)
        self._preview_frame.pack(fill="x", pady=2)
        self._preview_frame.pack_propagate(False)
        self._refresh_layout_preview()

        # Topic / Subtopic Style
        style_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        style_frame.pack(fill="x", padx=10, pady=(10,0))
        ctk.CTkLabel(style_frame, text="Topic & Subtopic Style",
                     font=("Arial",12,"bold")).pack(anchor="w", padx=5, pady=(4,6))

        FONT_STYLES = ["bold","italic","normal","bold italic"]

        topic_row = ctk.CTkFrame(style_frame, fg_color="transparent")
        topic_row.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(topic_row, text="Topic:", width=62, anchor="w",
                     font=("Arial",12)).pack(side="left")
        self._topic_preview = ctk.CTkLabel(topic_row, text="Aa", width=28,
                                           font=("Arial",13,self.topic_font),
                                           text_color=self.topic_color or None)
        self._topic_preview.pack(side="left", padx=(0,4))
        self.topic_font_combo = ctk.CTkComboBox(topic_row, values=FONT_STYLES, width=110,
                                                command=self._on_topic_font_change)
        self.topic_font_combo.set(self.topic_font)
        self.topic_font_combo.pack(side="left", padx=2)
        ctk.CTkButton(topic_row, text="🎨", width=34,
                      command=lambda: self._pick_color("topic")).pack(side="left", padx=2)
        ctk.CTkButton(topic_row, text="↺", width=28, fg_color="#555",
                      command=lambda: self._reset_style("topic")).pack(side="left", padx=1)

        sub_row = ctk.CTkFrame(style_frame, fg_color="transparent")
        sub_row.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(sub_row, text="Subtopic:", width=62, anchor="w",
                     font=("Arial",12)).pack(side="left")
        self._subtopic_preview = ctk.CTkLabel(sub_row, text="Aa", width=28,
                                              font=("Arial",12,self.subtopic_font),
                                              text_color=self.subtopic_color or None)
        self._subtopic_preview.pack(side="left", padx=(0,4))
        self.subtopic_font_combo = ctk.CTkComboBox(sub_row, values=FONT_STYLES, width=110,
                                                   command=self._on_subtopic_font_change)
        self.subtopic_font_combo.set(self.subtopic_font)
        self.subtopic_font_combo.pack(side="left", padx=2)
        ctk.CTkButton(sub_row, text="🎨", width=34,
                      command=lambda: self._pick_color("subtopic")).pack(side="left", padx=2)
        ctk.CTkButton(sub_row, text="↺", width=28, fg_color="#555",
                      command=lambda: self._reset_style("subtopic")).pack(side="left", padx=1)

        # Startup
        startup_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        startup_frame.pack(fill="x", padx=10, pady=(14,0))
        ctk.CTkLabel(startup_frame, text="Windows Startup",
                     font=("Arial",12,"bold")).pack(anchor="w", padx=5, pady=(0,4))
        self.startup_status_label = ctk.CTkLabel(startup_frame, text="",
                                                 font=("Arial",11), text_color="gray")
        self.startup_status_label.pack(anchor="w", padx=5)
        self.startup_btn = ctk.CTkButton(startup_frame, text="", command=self.toggle_startup)
        self.startup_btn.pack(fill="x", padx=5, pady=4)
        self._refresh_startup_ui()

        ctk.CTkButton(settings_scroll, text="Close",
                      command=lambda: self._collapse_sidebar(self.sidebar_settings)).pack(pady=20)

    # ── Layout preview ──
    def _refresh_layout_preview(self):
        for w in self._preview_frame.winfo_children():
            w.destroy()
        self._preview_frame.update_idletasks()
        w_px = self._preview_frame.winfo_width() or 240
        cols = max(1, self.btn_columns)
        cell_w = w_px // cols
        btn_h  = cell_w if self.btn_square else 32
        COLORS = ["#3a7ebf","#008040","#ca6500","#800000","#008080","#7d7d7d","#004080"]
        for i in range(min(cols * 2, 12)):
            r, c = divmod(i, cols)
            self._preview_frame.columnconfigure(c, weight=1)
            ctk.CTkButton(self._preview_frame, text=f"Tool {i+1}",
                          font=("Arial",10), fg_color=COLORS[i % len(COLORS)],
                          height=btn_h, state="disabled").grid(
                          row=r, column=c, sticky="nsew", padx=2, pady=2)

    def _on_col_change(self, value):
        self.btn_columns = int(round(value))
        self._col_label.configure(text=str(self.btn_columns))
        self.app_data["settings"]["btn_columns"] = self.btn_columns
        self._refresh_layout_preview()
        self.populate_ui()

    def _on_square_toggle(self):
        self.btn_square = bool(self._sq_switch.get())
        self.app_data["settings"]["btn_square"] = self.btn_square
        self._refresh_layout_preview()
        self.populate_ui()

    # ══════════════════════════════════════════
    #  OTHER SETTINGS LOGIC
    # ══════════════════════════════════════════
    def _on_font_size_change(self, value):
        self.font_size = int(value)
        self._fs_label.configure(text=str(self.font_size))
        self.app_data["settings"]["font_size"] = self.font_size
        self.populate_ui()

    def change_text_anchor(self, choice):
        mapping = {"Center":"center","Left":"w","Right":"e"}
        self.text_anchor = mapping.get(choice,"center")
        self.app_data["settings"]["text_anchor"] = self.text_anchor
        self.populate_ui()

    def _on_topic_font_change(self, choice):
        self.topic_font = choice
        self._save_label_styles()
        self._topic_preview.configure(font=("Arial",13,self.topic_font))
        self.populate_ui()

    def _on_subtopic_font_change(self, choice):
        self.subtopic_font = choice
        self._save_label_styles()
        self._subtopic_preview.configure(font=("Arial",12,self.subtopic_font))
        self.populate_ui()

    def _pick_color(self, target):
        current = self.topic_color if target == "topic" else self.subtopic_color
        color = colorchooser.askcolor(title=f"Pick {target.title()} Color",
                                      initialcolor=current or "#ffffff")
        if not color[1]:
            return
        if target == "topic":
            self.topic_color = color[1]
            self._topic_preview.configure(text_color=color[1])
        else:
            self.subtopic_color = color[1]
            self._subtopic_preview.configure(text_color=color[1])
        self._save_label_styles()
        self.populate_ui()

    def _reset_style(self, target):
        if target == "topic":
            self.topic_color = "#3a7ebf"; self.topic_font = "bold"
            self.topic_font_combo.set("bold")
            self._topic_preview.configure(text_color="#3a7ebf", font=("Arial",13,"bold"))
        else:
            self.subtopic_color = ""; self.subtopic_font = "italic"
            self.subtopic_font_combo.set("italic")
            self._subtopic_preview.configure(text_color=None, font=("Arial",12,"italic"))
        self._save_label_styles()
        self.populate_ui()

    def _save_label_styles(self):
        self.app_data["settings"].update({
            "topic_color": self.topic_color, "topic_font": self.topic_font,
            "subtopic_color": self.subtopic_color, "subtopic_font": self.subtopic_font,
        })
        try:
            with open(self.unified_config_file,'w') as f:
                json.dump(self.app_data, f, indent=4)
        except Exception:
            pass

    # ══════════════════════════════════════════
    #  STARTUP
    # ══════════════════════════════════════════
    def _startup_shortcut_path(self):
        return os.path.join(os.environ.get("APPDATA",""),
                            r"Microsoft\Windows\Start Menu\Programs\Startup",
                            "ToolLauncher.lnk")

    def _startup_is_enabled(self):
        return os.path.exists(self._startup_shortcut_path())

    def _refresh_startup_ui(self):
        if self._startup_is_enabled():
            self.startup_status_label.configure(text="✅ Runs at Windows startup",
                                                text_color="#4caf50")
            self.startup_btn.configure(text="🗑️  Remove from Startup",
                                       fg_color="#a33", hover_color="#c44")
        else:
            self.startup_status_label.configure(text="⛔ Not in startup", text_color="gray")
            self.startup_btn.configure(text="🚀  Add to Startup",
                                       fg_color="#3a7ebf", hover_color="#2d6bad")

    def toggle_startup(self):
        if self._startup_is_enabled():
            try:
                os.remove(self._startup_shortcut_path())
                tk_msgbox.showinfo("Startup","ToolLauncher removed from Windows startup.",
                                   parent=self.root)
            except Exception as e:
                tk_msgbox.showerror("Error", f"Could not remove shortcut:\n{e}", parent=self.root)
        else:
            self._create_startup_shortcut()
        self._refresh_startup_ui()

    def _create_startup_shortcut(self):
        target   = sys.executable if getattr(sys,'frozen',False) else os.path.abspath(__file__)
        work_dir = os.path.dirname(target)
        ps = (f'$ws = New-Object -ComObject WScript.Shell; '
              f'$sc = $ws.CreateShortcut("{self._startup_shortcut_path()}"); '
              f'$sc.TargetPath = "{target}"; $sc.WorkingDirectory = "{work_dir}"; '
              f'$sc.WindowStyle = 1; $sc.Save()')
        try:
            r = subprocess.run(["powershell","-NoProfile","-Command",ps],
                               capture_output=True, text=True)
            if r.returncode == 0:
                tk_msgbox.showinfo("Startup",
                                   "ToolLauncher added to Windows startup.\n"
                                   "It will launch automatically on next login.",
                                   parent=self.root)
            else:
                tk_msgbox.showerror("Error", f"PowerShell error:\n{r.stderr}", parent=self.root)
        except Exception as e:
            tk_msgbox.showerror("Error", f"Could not create shortcut:\n{e}", parent=self.root)

    # ══════════════════════════════════════════
    #  WINDOW & SIDEBAR
    # ══════════════════════════════════════════
    def log_dimensions(self, label):
        self.root.update_idletasks()
        print(f"\n--- {label} ---")
        print(f"Root Geometry:   {self.root.geometry()}")
        print(f"Main View Width: {self.main_view.winfo_width()}px")
        print("-" * 30)

    def toggle_sidebar(self, target_sidebar, action_name="Action"):
        self.log_dimensions(f"BEFORE {action_name}")
        if self.sidebar_settings.winfo_ismapped() or self.sidebar_editor.winfo_ismapped():
            active = (self.sidebar_settings if self.sidebar_settings.winfo_ismapped()
                      else self.sidebar_editor)
            self._collapse_sidebar(active, internal=True)
            if active == target_sidebar:
                return
        cx, cy = self.root.winfo_x(), self.root.winfo_y()
        cw, ch = self.root.winfo_width(), self.root.winfo_height()
        self.root.geometry(f"{cw+self.sidebar_width}x{ch}+{cx-self.sidebar_width}+{cy}")
        target_sidebar.pack(side="left", fill="y", before=self.main_view)
        if target_sidebar == self.sidebar_editor:
            self.prime_focus()
        self.log_dimensions(f"AFTER {action_name}")

    def _collapse_sidebar(self, sidebar, internal=False):
        sidebar.pack_forget()
        cx, cy = self.root.winfo_x(), self.root.winfo_y()
        cw, ch = self.root.winfo_width(), self.root.winfo_height()
        self.root.geometry(f"{cw-self.sidebar_width}x{ch}+{cx+self.sidebar_width}+{cy}")

    def prime_focus(self):
        for w in [self.pos_id_in, self.name_in, self.path_in]:
            w.focus_set()
            self.root.update_idletasks()
        self.focus_sink.focus_set()

    # ══════════════════════════════════════════
    #  DATA & HELPERS
    # ══════════════════════════════════════════
    def get_app_dir(self):
        return (os.path.dirname(sys.executable) if getattr(sys,'frozen',False)
                else os.path.dirname(os.path.abspath(__file__)))

    def load_unified_data(self):
        defaults = {
            "font_size":13, "text_anchor":"center",
            "topic_color":"#3a7ebf", "topic_font":"bold",
            "subtopic_color":"", "subtopic_font":"italic",
            "btn_columns":1, "btn_square":False
        }
        if os.path.exists(self.unified_config_file):
            with open(self.unified_config_file,'r') as f:
                data = json.load(f)
            if "settings" not in data:
                data["settings"] = defaults
            else:
                for k,v in defaults.items():
                    data["settings"].setdefault(k,v)
            return data
        return {"configs_list":[], "settings":defaults}

    def apply_window_state(self):
        s = self.app_data.get("window_state",
                              {"w":self.main_base_width,"h":700,"x":100,"y":100})
        self.root.geometry(f"{s['w']}x{s['h']}+{s['x']}+{s['y']}")

    def on_closing(self):
        try:
            geom         = self.root.geometry()
            size, px, py = geom.split('+')
            pw, ph       = size.split('x')
            fw, fx       = int(pw), int(px)
            if self.sidebar_settings.winfo_ismapped() or self.sidebar_editor.winfo_ismapped():
                fw -= self.sidebar_width; fx += self.sidebar_width
            self.app_data["window_state"] = {"w":fw,"h":int(ph),"x":fx,"y":int(py)}
            with open(self.unified_config_file,'w') as f:
                json.dump(self.app_data, f, indent=4)
        except Exception:
            pass
        self.root.destroy()

    # ══════════════════════════════════════════
    #  EDITOR SIDEBAR
    # ══════════════════════════════════════════
    def setup_editor_ui(self):
        ctk.CTkLabel(self.sidebar_editor, text="Tool Editor",
                     font=("Arial",18,"bold")).pack(pady=(20,10))

        self.pos_id_in = ctk.CTkEntry(self.sidebar_editor,
                                      placeholder_text="Order ID", width=240)
        self.pos_id_in.pack(pady=6)

        self.cat_combo = ctk.CTkComboBox(self.sidebar_editor, width=240,
                                         command=self.update_subcat_options)
        self.cat_combo.pack(pady=6)

        self.sub_combo = ctk.CTkComboBox(self.sidebar_editor, width=240)
        self.sub_combo.pack(pady=6)

        self.name_in = ctk.CTkEntry(self.sidebar_editor,
                                    placeholder_text="Tool Name", width=240)
        self.name_in.pack(pady=6)

        path_row = ctk.CTkFrame(self.sidebar_editor, fg_color="transparent")
        path_row.pack(pady=6, padx=20, fill="x")
        self.path_in = ctk.CTkEntry(path_row, placeholder_text="Path / URL")
        self.path_in.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(path_row, text="📁", width=34,
                      command=self.browse_path).pack(side="left", padx=(4,0))

        # ── Icon section ──
        icon_sep = ctk.CTkFrame(self.sidebar_editor, height=1, fg_color="#444")
        icon_sep.pack(fill="x", padx=20, pady=(10,6))
        ctk.CTkLabel(self.sidebar_editor, text="Icon", font=("Arial",13,"bold")).pack()

        icon_pick_row = ctk.CTkFrame(self.sidebar_editor, fg_color="transparent")
        icon_pick_row.pack(padx=20, pady=4, fill="x")

        # Preview label shows current icon
        self._icon_preview_lbl = ctk.CTkLabel(icon_pick_row, text="—",
                                              font=("Segoe UI Emoji",22), width=36)
        self._icon_preview_lbl.pack(side="left", padx=(0,6))

        ctk.CTkButton(icon_pick_row, text="🎨  Pick Icon", width=120,
                      command=self._open_icon_picker).pack(side="left", padx=2)
        ctk.CTkButton(icon_pick_row, text="✖ Clear", width=70, fg_color="#555",
                      command=self._clear_icon).pack(side="left", padx=2)

        # Display mode selector — each option on its own line
        mode_frame = ctk.CTkFrame(self.sidebar_editor, fg_color="transparent")
        mode_frame.pack(padx=24, pady=(2, 8), fill="x")
        ctk.CTkLabel(mode_frame, text="Show:", font=("Arial", 12),
                     anchor="w").pack(anchor="w", pady=(0, 4))
        self._icon_mode_var = tk.StringVar(value=self._edit_icon_mode)
        for val, lbl in [("text", "Text only"),
                         ("icon", "Icon only  (name shown on hover)"),
                         ("both", "Icon + Text")]:
            ctk.CTkRadioButton(mode_frame, text=lbl, variable=self._icon_mode_var,
                               value=val, command=self._on_icon_mode_change
                               ).pack(anchor="w", pady=3)

        # ── Color / Save / Delete ──
        icon_sep2 = ctk.CTkFrame(self.sidebar_editor, height=1, fg_color="#444")
        icon_sep2.pack(fill="x", padx=20, pady=(4,6))

        self.color_btn = ctk.CTkButton(self.sidebar_editor, text="Button Color",
                                       command=self.choose_color)
        self.color_btn.pack(pady=8, padx=30, fill="x")

        ctk.CTkButton(self.sidebar_editor, text="💾  Save Tool", fg_color="green",
                      command=self.save_tool).pack(pady=6, padx=30, fill="x")

        self.delete_btn = ctk.CTkButton(self.sidebar_editor, text="🗑️  Delete Tool",
                                        fg_color="#a33", hover_color="#c44",
                                        command=self.delete_current_tool)

        ctk.CTkButton(self.sidebar_editor, text="Close",
                      command=lambda: self._collapse_sidebar(self.sidebar_editor)
                      ).pack(side="bottom", pady=15)

    # ── Icon editor helpers ──
    def _open_icon_picker(self):
        dlg = IconPickerDialog(self.root, current_icon=self._edit_icon)
        if dlg.result is not None:
            self._edit_icon = dlg.result
            self._icon_preview_lbl.configure(text=self._edit_icon or "—")

    def _clear_icon(self):
        self._edit_icon = ""
        self._icon_preview_lbl.configure(text="—")

    def _on_icon_mode_change(self):
        self._edit_icon_mode = self._icon_mode_var.get()

    def browse_path(self):
        picker = tk.Toplevel(self.root)
        picker.title("Browse"); picker.resizable(False,False); picker.grab_set()
        self.root.update_idletasks()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        picker.geometry(f"220x90+{rx+rw//2-110}+{ry+rh//2-45}")
        ctk.CTkLabel(picker, text="Browse for:").pack(pady=(12,6))
        btn_row = ctk.CTkFrame(picker, fg_color="transparent"); btn_row.pack()

        def pick_file():
            picker.destroy()
            p = filedialog.askopenfilename(title="Select File")
            if p: self.path_in.delete(0,"end"); self.path_in.insert(0,p)

        def pick_folder():
            picker.destroy()
            p = filedialog.askdirectory(title="Select Folder")
            if p: self.path_in.delete(0,"end"); self.path_in.insert(0,p)

        ctk.CTkButton(btn_row, text="📄 File",   width=90, command=pick_file  ).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="📁 Folder", width=90, command=pick_folder).pack(side="left", padx=6)

    def trigger_edit(self, cat, sub, tool):
        self.editing_tool_ref = {"cat":cat,"sub":sub,"old_obj":tool}
        self.pos_id_in.delete(0,'end'); self.pos_id_in.insert(0, tool.get('pos_id','999'))
        self.name_in.delete(0,'end');   self.name_in.insert(0, tool['name'])
        self.path_in.delete(0,'end');   self.path_in.insert(0, tool.get('path',''))
        self.selected_color = tool.get('color',"#3a7ebf")
        self.color_btn.configure(fg_color=self.selected_color)
        # Load icon state
        self._edit_icon      = tool.get('icon','')
        self._edit_icon_mode = tool.get('icon_mode','text')
        self._icon_preview_lbl.configure(text=self._edit_icon or "—")
        self._icon_mode_var.set(self._edit_icon_mode)
        self.cat_combo.set(cat); self.update_subcat_options(); self.sub_combo.set(sub)
        self.delete_btn.pack(pady=6, padx=30, fill="x", before=self.color_btn)
        self.toggle_sidebar(self.sidebar_editor, "Edit Tool")

    def delete_current_tool(self):
        if not self.editing_tool_ref:
            return
        name = self.editing_tool_ref['old_obj'].get('name','this tool')
        if not tk_msgbox.askyesno("Delete Tool",
                                  f'Are you sure you want to delete\n"{name}"?',
                                  icon="warning", parent=self.root):
            return
        r = self.editing_tool_ref
        self.current_tools[r['cat']][r['sub']].remove(r['old_obj'])
        self.cleanup_empty_groups(); self.save_current_json()
        self.editing_tool_ref = None
        self._collapse_sidebar(self.sidebar_editor); self.populate_ui()

    def save_current_json(self):
        if self.active_config_path:
            with open(self.active_config_path,'w') as f:
                json.dump(self.current_tools, f, indent=4)

    def on_config_select(self, val):
        self.config_combo.set(val)
        for c in self.app_data["configs_list"]:
            if c['name'] == val:
                self.active_config_path = c['path']
                if os.path.exists(self.active_config_path):
                    with open(self.active_config_path,'r') as f:
                        self.current_tools = json.load(f)
                self.populate_ui(); break

    def update_subcat_options(self, choice=None):
        cat = self.cat_combo.get()
        if cat in self.current_tools:
            self.sub_combo.configure(values=sorted(list(self.current_tools[cat].keys())))

    def choose_color(self):
        color = colorchooser.askcolor(title="Select Color", initialcolor=self.selected_color)
        if color[1]: self.selected_color = color[1]; self.color_btn.configure(fg_color=color[1])

    def show_add_sidebar(self):
        self.editing_tool_ref = None
        for e in [self.pos_id_in, self.name_in, self.path_in]: e.delete(0,'end')
        self._edit_icon = ""; self._edit_icon_mode = "text"
        self._icon_preview_lbl.configure(text="—")
        self._icon_mode_var.set("text")
        self.delete_btn.pack_forget()
        self.update_combo_lists()
        self.toggle_sidebar(self.sidebar_editor, "Add Tool")

    def show_settings(self):
        self.toggle_sidebar(self.sidebar_settings, "Settings")

    def smart_open(self, p):
        if not p: return
        if p.startswith("http"):
            webbrowser.open(p)
        else:
            os.startfile(p)

    def cleanup_empty_groups(self):
        for c in list(self.current_tools.keys()):
            for s in list(self.current_tools[c].keys()):
                if not self.current_tools[c][s]: del self.current_tools[c][s]
            if not self.current_tools[c]: del self.current_tools[c]

    def on_search(self, e):
        self.search_query = self.search_entry.get().lower()
        self.populate_ui()

    def render_config_manager(self):
        for w in self.cfg_scroll.winfo_children(): w.destroy()
        for i, cfg in enumerate(self.app_data.get("configs_list",[])):
            row = ctk.CTkFrame(self.cfg_scroll, fg_color="transparent"); row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=cfg['name'], anchor="w").pack(side="left", expand=True, fill="x")
            ctk.CTkButton(row, text="🗑️", width=30, fg_color="#a33",
                          command=lambda idx=i: self.delete_config(idx)).pack(side="right")

    def delete_config(self, index):
        if len(self.app_data["configs_list"]) > 1:
            self.app_data["configs_list"].pop(index)
            self.render_config_manager(); self.refresh_config_list()

    def refresh_config_list(self):
        names = [c['name'] for c in self.app_data.get("configs_list",[])]
        self.config_combo.configure(values=names)
        if self.active_config_path:
            self.config_combo.set(
                os.path.basename(self.active_config_path).replace(".json",""))

    def add_config_file(self):
        picker = tk.Toplevel(self.root); picker.title("Add Config")
        picker.resizable(False,False); picker.grab_set()
        self.root.update_idletasks()
        rx,ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        rw,rh = self.root.winfo_width(), self.root.winfo_height()
        picker.geometry(f"240x95+{rx+rw//2-120}+{ry+rh//2-47}")
        ctk.CTkLabel(picker, text="Config action:").pack(pady=(12,6))
        btn_row = ctk.CTkFrame(picker, fg_color="transparent"); btn_row.pack()

        def open_existing():
            picker.destroy()
            p = filedialog.askopenfilename(title="Open Existing Config",
                                           filetypes=[("JSON","*.json"),("All","*.*")])
            if p:
                n = os.path.basename(p).replace(".json","")
                self.app_data["configs_list"].append({"name":n,"path":p})
                self.render_config_manager(); self.refresh_config_list()

        def create_new():
            picker.destroy()
            p = filedialog.asksaveasfilename(title="Create New Config",
                                             defaultextension=".json",
                                             filetypes=[("JSON","*.json")])
            if p:
                n = os.path.basename(p).replace(".json","")
                self.app_data["configs_list"].append({"name":n,"path":p})
                with open(p,'w') as f: json.dump({},f)
                self.render_config_manager(); self.refresh_config_list()

        ctk.CTkButton(btn_row, text="📂 Open Existing", width=110,
                      command=open_existing).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="✨ Create New", width=110,
                      command=create_new).pack(side="left", padx=5)

    def update_combo_lists(self):
        self.cat_combo.configure(values=sorted(list(self.current_tools.keys())))

    def save_tool(self):
        cat  = self.cat_combo.get().strip()
        sub  = self.sub_combo.get().strip()
        name = self.name_in.get().strip()
        path = self.path_in.get().strip()
        if not name or not path: return
        if self.editing_tool_ref:
            r = self.editing_tool_ref
            self.current_tools[r['cat']][r['sub']].remove(r['old_obj'])
        if cat not in self.current_tools: self.current_tools[cat] = {}
        if sub not in self.current_tools[cat]: self.current_tools[cat][sub] = []
        self.current_tools[cat][sub].append({
            "name": name, "path": path,
            "pos_id": self.pos_id_in.get() or "999",
            "color": self.selected_color,
            "icon":  self._edit_icon,
            "icon_mode": self._edit_icon_mode,
        })
        self.cleanup_empty_groups(); self.save_current_json()
        self._collapse_sidebar(self.sidebar_editor); self.populate_ui()


if __name__ == "__main__":
    ToolLauncher().root.mainloop()
