#!/usr/bin/env python3
"""
MU110N - Click-to-Edit Overlay for Sheepy: A Short Adventure
Works while Sheepy is running. Click any game element to edit its properties.
"""

import os, sys, json, time, threading, tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
import subprocess

#
# CONFIGURATION
#
GAME_EXE = "Sheepy.exe"
GAME_HTML = "index.html"
GAME_WINDOW_TITLE = "Sheepy A Short Adventure"  # Exact window title match
MODS_DIR = "Mods"
EDITOR_DIR = "Editor"
SNAPSHOT_FILE = "editor_snapshot.json"
OVERLAY_ALPHA = 0.3

#
# GAME SCANNER - Detects running Sheepy process
#
class GameScanner:
    def __init__(self):
        self.process = None
        self.hwnd = None
        self.game_path = None

    def find_game(self):
        """Find Sheepy: A Short Adventure game window and path"""
        try:
            import psutil
            for proc in psutil.process_iter(['name', 'pid', 'exe']):
                if proc.info['name'] and 'sheepy' in proc.info['name'].lower():
                    self.process = proc
                    if proc.info['exe']:
                        self.game_path = Path(proc.info['exe']).parent
                        return True
        except ImportError:
            pass

        # Fallback: scan common paths for Sheepy
        guesses = [
            Path("."),
            Path.home() / "Games" / "Sheepy",
            Path("C:/Games/Sheepy"),
            Path("C:/Program Files (x86)/Steam/steamapps/common/Sheepy A Short Adventure"),
        ]
        for path in guesses:
            if (path / GAME_EXE).exists() or (path / GAME_HTML).exists():
                self.game_path = path
                return True
        return False

    def get_game_rect(self):
        """Get Sheepy A Short Adventure game window position for overlay alignment"""
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                # Find window by exact title match
                def enum_windows_callback(hwnd, extra):
                    text = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetWindowTextW(hwnd, text, 256)
                    window_title = text.value.lower()
                    # Only match Sheepy: A Short Adventure
                    if 'sheepy' in window_title and 'short' in window_title and 'adventure' in window_title:
                        extra.append(hwnd)
                    return True

                windows = []
                EnumWindows = ctypes.windll.user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(
                    ctypes.c_bool, wintypes.HWND, ctypes.POINTER(ctypes.c_int)
                )
                EnumWindows(EnumWindowsProc(enum_windows_callback), ctypes.pointer(ctypes.c_int(0)))

                if windows:
                    self.hwnd = windows[0]
                    rect = ctypes.wintypes.RECT()
                    ctypes.windll.user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
                    return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
            except:
                pass
        return None

#
# DATA PARSER - Reads Construct game data
#
class ConstructDataParser:
    def __init__(self, game_path):
        self.game_path = Path(game_path)
        self.data_file = self.game_path / "data.json"
        self.project = None
        self.objects = {} # uid -> object info
        self.layouts = {}
        self.event_sheets = {}

        # Auto-create data.json if it doesn't exist
        if not self.data_file.exists():
            self._create_default_data()
        
        if self.data_file.exists():
            self.load_data()

    def _create_default_data(self):
        """Create a default data.json file if it doesn't exist"""
        try:
            default_data = {
                "version": "1.0.0",
                "objectTypes": [],
                "layouts": [],
                "eventSheets": []
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2)
            print(f"Created default data.json at {self.data_file}")
        except Exception as e:
            print(f"Error creating data.json: {e}")

    def load_data(self):
        """Parse Construct 3 project data.json"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.project = json.load(f)

            # Index all objects by UID
            for obj in self.project.get("objectTypes", []):
                self.objects[obj.get("name", "unknown")] = {
                    "type": "objectType",
                    "data": obj,
                    "plugin": obj.get("plugin", ""),
                    "sid": obj.get("sid", 0)
                }

            # Index layouts
            for layout in self.project.get("layouts", []):
                self.layouts[layout.get("name", "unknown")] = layout
                # Index instances within layout
                for layer in layout.get("layers", []):
                    for inst in layer.get("instances", []):
                        uid = inst.get("uid", 0)
                        self.objects[f"inst_{uid}"] = {
                            "type": "instance",
                            "data": inst,
                            "layout": layout.get("name"),
                            "layer": layer.get("name"),
                            "uid": uid
                        }

            # Index event sheets
            for sheet in self.project.get("eventSheets", []):
                self.event_sheets[sheet.get("name", "unknown")] = sheet

        except Exception as e:
            print(f"Data load error: {e}")

    def get_object_at_position(self, x, y, layout_name=None):
        """Find object instance at screen coordinates"""
        results = []

        for key, obj in self.objects.items():
            if obj["type"] != "instance":
                continue

            inst = obj["data"]
            # Construct instances have x, y, width, height
            ix = inst.get("x", 0)
            iy = inst.get("y", 0)
            iw = inst.get("width", inst.get("w", 32))
            ih = inst.get("height", inst.get("h", 32))

            # Simple AABB check
            if ix <= x <= ix + iw and iy <= y <= iy + ih:
                results.append({
                    "uid": obj.get("uid", 0),
                    "name": inst.get("type", "Unknown"),
                    "type": inst.get("type", ""),
                    "x": ix, "y": iy,
                    "width": iw, "height": ih,
                    "properties": inst,
                    "layer": obj.get("layer", ""),
                    "layout": obj.get("layout", "")
                })

        return results

    def get_object_by_name(self, name):
        """Get object type definition"""
        return self.objects.get(name)

    def get_event_sheet_for_layout(self, layout_name):
        """Get event sheet linked to a layout"""
        layout = self.layouts.get(layout_name)
        if layout:
            es_name = layout.get("eventSheet", "")
            return self.event_sheets.get(es_name)
        return None

    def get_all_behaviors(self, obj_name):
        """Get behaviors attached to an object type"""
        obj = self.objects.get(obj_name)
        if obj and obj["type"] == "objectType":
            return obj["data"].get("behaviors", [])
        return []

    def get_all_animations(self, obj_name):
        """Get animations for sprite objects"""
        obj = self.objects.get(obj_name)
        if obj and obj["type"] == "objectType":
            return obj["data"].get("animations", [])
        return []

#
# OVERLAY WINDOW - Transparent click-through overlay (SHEEPY ONLY)
#
class GameOverlay:
    def __init__(self, master, game_rect, game_hwnd, on_click):
        self.master = master
        self.game_rect = game_rect # (x, y, w, h)
        self.game_hwnd = game_hwnd  # Sheepy window handle
        self.on_click = on_click
        self.click_mode = False
        self.overlay_hwnd = None

        # Create overlay window
        self.window = tk.Toplevel(master)
        self.window.title("MU110N - Sheepy Editor Overlay")
        self.window.geometry(f"{game_rect[2]}x{game_rect[3]}+{game_rect[0]}+{game_rect[1]}")

        # Make transparent and click-through when not in click mode
        self.window.attributes('-alpha', OVERLAY_ALPHA)
        self.window.attributes('-topmost', True)
        self.window.overrideredirect(True)

        # Prevent window from appearing in taskbar
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                self.overlay_hwnd = int(self.window.winfo_id())
                # Set window to not show in taskbar
                GWL_EXSTYLE = -20
                WS_EX_TOOLWINDOW = 0x00000080
                ctypes.windll.user32.SetWindowLongW(self.overlay_hwnd, GWL_EXSTYLE, WS_EX_TOOLWINDOW)
            except:
                pass

        # Canvas for drawing selection boxes
        self.canvas = tk.Canvas(self.window, highlightthickness=0, bg='black')
        self.canvas.pack(fill='both', expand=True)

        # Bind clicks
        self.canvas.bind("<Button-1>", self._handle_click)
        self.canvas.bind("<Button-3>", self._toggle_mode)
        self.canvas.bind("<Motion>", self._handle_hover)

        # Status label
        self.status = tk.Label(self.window, text="RIGHT-CLICK to toggle click mode | LEFT-CLICK to select",
                               bg='yellow', fg='black', font=('Segoe UI', 10, 'bold'))
        self.status.place(relx=0.5, rely=0.02, anchor='n')

        # Selection highlight
        self.selection_box = None

        self._update_loop()

    def _toggle_mode(self, event):
        """Toggle between click-through and click-capture modes"""
        self.click_mode = not self.click_mode
        if self.click_mode:
            self.window.attributes('-alpha', 0.1)
            self.status.config(text=" CLICK MODE ACTIVE — Click game objects to edit")
            # Bring Sheepy to focus
            self._focus_sheepy()
        else:
            self.window.attributes('-alpha', OVERLAY_ALPHA)
            self.status.config(text="RIGHT-CLICK to toggle click mode | LEFT-CLICK to select")

    def _focus_sheepy(self):
        """Bring Sheepy window to focus"""
        if sys.platform == "win32" and self.game_hwnd:
            try:
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(self.game_hwnd)
            except:
                pass

    def _handle_click(self, event):
        """Handle click on overlay"""
        if not self.click_mode:
            return

        # Convert to game coordinates
        game_x = event.x
        game_y = event.y

        self.on_click(game_x, game_y)

    def _handle_hover(self, event):
        """Show hover preview"""
        if self.click_mode:
            self.canvas.delete("hover")
            self.canvas.create_rectangle(
                event.x - 20, event.y - 20, event.x + 20, event.y + 20,
                outline='cyan', width=2, tags="hover", dash=(4, 4)
            )

    def highlight_object(self, x, y, w, h, color='red'):
        """Draw selection box around clicked object"""
        self.canvas.delete("selection")
        self.selection_box = self.canvas.create_rectangle(
            x, y, x + w, y + h,
            outline=color, width=3, tags="selection"
        )
        # Flash effect
        self._flash_selection()

    def _flash_selection(self, count=0):
        if count > 6:
            return
        colors = ['red', 'orange', 'yellow', 'orange', 'red']
        if self.selection_box:
            self.canvas.itemconfig(self.selection_box, outline=colors[count % len(colors)])
            self.window.after(100, lambda: self._flash_selection(count + 1))

    def _update_loop(self):
        """Keep overlay synced with game window"""
        if sys.platform == "win32" and self.game_hwnd:
            try:
                import ctypes
                from ctypes import wintypes
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(self.game_hwnd, ctypes.byref(rect))
                new_geo = f"{rect.right-rect.left}x{rect.bottom-rect.top}+{rect.left}+{rect.top}"
                self.window.geometry(new_geo)
            except:
                pass
        self.window.after(100, self._update_loop)

    def hide(self):
        self.window.withdraw()

    def show(self):
        self.window.deiconify()
        self.window.attributes('-topmost', True)

#
# PROPERTY EDITOR - Edit object properties (STAYS OPEN)
#
class PropertyEditor:
    def __init__(self, master, obj_data, parser, on_save):
        self.master = master
        self.obj_data = obj_data
        self.parser = parser
        self.on_save = on_save

        self.window = tk.Toplevel(master)
        self.window.title(f"Edit: {obj_data.get('name', 'Unknown')}")
        self.window.geometry("500x700")
        self.window.transient(master)
        
        # Prevent window from closing automatically
        self.window.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        self._build_ui()

    def _on_close_attempt(self):
        """Handle close button - ask user before closing"""
        if messagebox.askyesno("Close Editor", "Close this editor window?"):
            self.window.destroy()

    def _build_ui(self):
        # Header
        header = ttk.Frame(self.window, padding=10)
        header.pack(fill='x')

        ttk.Label(header, text=f" {self.obj_data.get('name', 'Unknown')}",
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(header, text=f"Type: {self.obj_data.get('type', 'Unknown')} | "
                               f"UID: {self.obj_data.get('uid', 'N/A')} | "
                               f"Layer: {self.obj_data.get('layer', 'N/A')}",
                  font=('Segoe UI', 9)).pack(anchor='w')

        ttk.Separator(self.window, orient='horizontal').pack(fill='x', padx=10)

        # Notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Properties tab
        self._build_properties_tab()

        # Behaviors tab
        self._build_behaviors_tab()

        # Events tab (simplified)
        self._build_events_tab()

        # Bottom buttons
        btn_frame = ttk.Frame(self.window, padding=10)
        btn_frame.pack(fill='x', side='bottom')

        ttk.Button(btn_frame, text=" Save Changes", command=self._save).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="↩ Close", command=self._on_close_attempt).pack(side='right', padx=5)
        ttk.Button(btn_frame, text=" Export as Mod", command=self._export_mod).pack(side='left', padx=5)

    def _build_properties_tab(self):
        """Build editable properties panel"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text='Properties')

        props = self.obj_data.get('properties', {})
        self.prop_vars = {}

        # Common properties
        common_props = ['x', 'y', 'width', 'height', 'angle', 'opacity', 'visible']
        row = 0

        for prop in common_props:
            if prop in props:
                ttk.Label(frame, text=prop.capitalize() + ":").grid(row=row, column=0, sticky='w', pady=2)

                var = tk.StringVar(value=str(props[prop]))
                self.prop_vars[prop] = var

                entry = ttk.Entry(frame, textvariable=var, width=20)
                entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                row += 1

        # Instance variables
        inst_vars = props.get('instanceVariables', [])
        if inst_vars:
            ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
            row += 1
            ttk.Label(frame, text="Instance Variables:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky='w', pady=5)
            row += 1

            for iv in inst_vars:
                name = iv.get('name', 'unnamed')
                ttk.Label(frame, text=f" {name}:").grid(row=row, column=0, sticky='w', pady=2)

                var = tk.StringVar(value=str(iv.get('value', '')))
                self.prop_vars[f"iv_{name}"] = (var, iv)

                entry = ttk.Entry(frame, textvariable=var, width=20)
                entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                row += 1

        frame.columnconfigure(1, weight=1)

        # Scroll if needed
        if row > 20:
            canvas = tk.Canvas(frame)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

    def _build_behaviors_tab(self):
        """Show and edit behaviors"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text='Behaviors')

        obj_type = self.obj_data.get('type', '')
        behaviors = self.parser.get_all_behaviors(obj_type)

        if not behaviors:
            ttk.Label(frame, text="No behaviors attached to this object type.",
                      font=('Segoe UI', 10)).pack(pady=20)
            return

        self.behavior_vars = {}
        for i, beh in enumerate(behaviors):
            ttk.Label(frame, text=f" {beh.get('type', 'Unknown')}",
                      font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(10, 0))

            props = beh.get('properties', {})
            for j, (key, val) in enumerate(props.items()):
                row = ttk.Frame(frame)
                row.pack(fill='x', pady=1)

                ttk.Label(row, text=f" {key}:").pack(side='left')
                var = tk.StringVar(value=str(val))
                self.behavior_vars[f"{beh.get('type', '')}_{key}"] = (var, beh, key)
                ttk.Entry(row, textvariable=var, width=15).pack(side='right')

    def _build_events_tab(self):
        """Show related events"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text='Events')

        layout = self.obj_data.get('layout', '')
        event_sheet = self.parser.get_event_sheet_for_layout(layout)

        if not event_sheet:
            ttk.Label(frame, text="No event sheet found for this layout.",
                      font=('Segoe UI', 10)).pack(pady=20)
            return

        # Show events in a text widget
        text = tk.Text(frame, wrap='word', font=('Consolas', 9))
        text.pack(fill='both', expand=True)

        events = event_sheet.get('events', [])
        text.insert('1.0', f"Event Sheet: {event_sheet.get('name', 'Unknown')}\n")
        text.insert('end', f"Total Events: {len(events)}\n\n")

        for i, event in enumerate(events[:50]): # Limit display
            text.insert('end', f"[{i}] {json.dumps(event, indent=2)[:200]}...\n\n")

        text.config(state='disabled')

    def _save(self):
        """Save changes back to data"""
        changes = {}

        # Collect property changes
        for prop, var in self.prop_vars.items():
            if isinstance(var, tuple):
                # Instance variable
                str_var, iv_data = var
                old_val = iv_data.get('value', '')
                new_val = str_var.get()
                if str(old_val) != new_val:
                    changes[f"iv_{iv_data.get('name', '')}"] = new_val
            else:
                # Regular property
                # Would need to write back to data.json
                pass

        self.on_save(self.obj_data, changes)
        messagebox.showinfo("Saved", f"Changes saved for {self.obj_data.get('name', 'object')}")

    def _export_mod(self):
        """Export current changes as a mod package"""
        from tkinter import filedialog

        mod_name = simpledialog.askstring("Mod Name", "Enter mod name:", parent=self.window)
        if not mod_name:
            return

        mod_data = {
            "name": mod_name,
            "version": "1.0.0",
            "author": "Sheepy Editor",
            "description": f"Modified {self.obj_data.get('name', 'object')}",
            "priority": 10,
            "data_patches": [
                {
                    "target": "data.json",
                    "operation": "replace",
                    "path": f"layouts.{self.obj_data.get('layout', '')}.layers.0.instances.{self.obj_data.get('uid', 0)}.x",
                    "value": self.obj_data.get('x', 0)
                }
            ]
        }

        folder = filedialog.askdirectory(title="Select Mods Folder")
        if folder:
            mod_dir = Path(folder) / mod_name
            mod_dir.mkdir(exist_ok=True)
            with open(mod_dir / "mod.json", 'w') as f:
                json.dump(mod_data, f, indent=2)
            messagebox.showinfo("Exported", f"Mod exported to:\n{mod_dir}")

#
# MAIN MOD MAKER APPLICATION
#
class ModMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(" MU110N - Sheepy: A Short Adventure Editor")
        self.root.geometry("400x500")
        self.root.minsize(350, 400)

        self.scanner = GameScanner()
        self.parser = None
        self.overlay = None
        self.game_rect = None
        self.game_hwnd = None
        self.selected_object = None
        self.editors = []

        self._build_ui()
        self._auto_connect()

    def _build_ui(self):
        # Header
        header = ttk.Frame(self.root, padding=15)
        header.pack(fill='x')

        ttk.Label(header, text=" MU110N",
                  font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(header, text="Click-to-edit overlay for Sheepy: A Short Adventure",
                  font=('Segoe UI', 9), foreground='gray').pack(anchor='w')

        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=10)

        # Connection status
        self.status_frame = ttk.Frame(self.root, padding=15)
        self.status_frame.pack(fill='x')

        self.status_var = tk.StringVar(value=" Scanning for Sheepy: A Short Adventure...")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var,
                                       font=('Segoe UI', 10))
        self.status_label.pack(anchor='w')

        self.path_var = tk.StringVar(value="")
        ttk.Label(self.status_frame, textvariable=self.path_var,
                  font=('Segoe UI', 8), foreground='gray').pack(anchor='w')

        # Action buttons
        btn_frame = ttk.Frame(self.root, padding=15)
        btn_frame.pack(fill='x')

        self.btn_overlay = ttk.Button(btn_frame, text=" Start Click Mode",
                                       command=self._start_overlay, state='disabled')
        self.btn_overlay.pack(fill='x', pady=3)

        self.btn_edit = ttk.Button(btn_frame, text=" Edit Selected",
                                    command=self._edit_selected, state='disabled')
        self.btn_edit.pack(fill='x', pady=3)

        self.btn_refresh = ttk.Button(btn_frame, text=" Refresh Data",
                                       command=self._refresh_data)
        self.btn_refresh.pack(fill='x', pady=3)

        ttk.Button(btn_frame, text=" Browse Game Folder",
                   command=self._browse_game).pack(fill='x', pady=3)

        # Object list
        list_frame = ttk.LabelFrame(self.root, text="Detected Objects", padding=10)
        list_frame.pack(fill='both', expand=True, padx=15, pady=10)

        self.obj_list = tk.Listbox(list_frame, font=('Segoe UI', 10))
        self.obj_list.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.obj_list.yview)
        self.obj_list.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        self.obj_list.bind("<<ListboxSelect>>", self._on_list_select)
        self.obj_list.bind("<Double-1>", lambda e: self._edit_selected())

        # Bottom
        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill='x', side='bottom')

        ttk.Label(bottom, text="Tip: Launch Sheepy, then click ' Start Click Mode'",
                  font=('Segoe UI', 8), foreground='gray').pack()

    def _auto_connect(self):
        """Try to find game automatically"""
        if self.scanner.find_game():
            self._connect_game(self.scanner.game_path)
        else:
            self.status_var.set(" Sheepy: A Short Adventure not found")
            self.path_var.set("Click 'Browse Game Folder' to set path manually")

    def _browse_game(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select Sheepy: A Short Adventure Folder")
        if folder:
            self._connect_game(Path(folder))

    def _connect_game(self, path):
        """Connect to game data"""
        self.parser = ConstructDataParser(path)
        self.scanner.game_path = path

        if self.parser.project:
            obj_count = len([k for k in self.parser.objects if self.parser.objects[k]["type"] == "instance"])
            self.status_var.set(f" Connected — {obj_count} objects loaded")
            self.path_var.set(str(path))
            self.btn_overlay.config(state='normal')
            self._populate_object_list()
        else:
            self.status_var.set(" Connected but no data.json found")
            self.path_var.set(str(path))

    def _populate_object_list(self):
        """Fill object list"""
        self.obj_list.delete(0, 'end')

        # Add object types
        for name, obj in sorted(self.parser.objects.items()):
            if obj["type"] == "objectType":
                plugin = obj.get("plugin", "")
                self.obj_list.insert('end', f" {name} ({plugin})")

        # Add some instances
        count = 0
        for name, obj in sorted(self.parser.objects.items()):
            if obj["type"] == "instance" and count < 100:
                uid = obj.get("uid", 0)
                layout = obj.get("layout", "")
                self.obj_list.insert('end', f" Instance #{uid} in {layout}")
                count += 1

    def _refresh_data(self):
        """Reload game data"""
        if self.parser:
            self.parser.load_data()
            self._populate_object_list()
            self.status_var.set(" Data refreshed")

    def _start_overlay(self):
        """Launch click-to-edit overlay"""
        if not self.scanner.game_path:
            return

        # Get game window position and handle
        self.game_rect = self.scanner.get_game_rect()
        if not self.game_rect:
            messagebox.showerror("Error", "Could not find Sheepy: A Short Adventure window.\nMake sure the game is running!")
            return

        # Get game window handle
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                
                def enum_windows_callback(hwnd, extra):
                    text = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetWindowTextW(hwnd, text, 256)
                    window_title = text.value.lower()
                    if 'sheepy' in window_title and 'short' in window_title and 'adventure' in window_title:
                        extra.append(hwnd)
                    return True

                windows = []
                EnumWindows = ctypes.windll.user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(
                    ctypes.c_bool, wintypes.HWND, ctypes.POINTER(ctypes.c_int)
                )
                EnumWindows(EnumWindowsProc(enum_windows_callback), ctypes.pointer(ctypes.c_int(0)))
                
                if windows:
                    self.game_hwnd = windows[0]
            except:
                pass

        # Create overlay with game window handle
        self.overlay = GameOverlay(self.root, self.game_rect, self.game_hwnd, self._on_overlay_click)
        self.status_var.set(" Click mode active — Right-click overlay to toggle capture")

        # Launch game if not running
        self._ensure_game_running()

    def _ensure_game_running(self):
        """Launch game if not already running"""
        if not self.scanner.process:
            exe = self.scanner.game_path / GAME_EXE
            html = self.scanner.game_path / GAME_HTML

            if exe.exists():
                subprocess.Popen([str(exe)], cwd=str(self.scanner.game_path))
            elif html.exists():
                import webbrowser
                webbrowser.open(str(html.resolve()))

    def _on_overlay_click(self, x, y):
        """Handle click on game via overlay"""
        if not self.parser:
            return

        # Find objects at position
        objects = self.parser.get_object_at_position(x, y)

        if objects:
            # Pick the smallest/topmost object
            obj = min(objects, key=lambda o: o['width'] * o['height'])
            self.selected_object = obj

            # Highlight on overlay
            if self.overlay:
                self.overlay.highlight_object(obj['x'], obj['y'],
                                              obj['width'], obj['height'])

            # Update UI
            self.status_var.set(f" Selected: {obj['name']} at ({x}, {y})")
            self.btn_edit.config(state='normal')

            # Auto-open editor
            self._edit_selected()
        else:
            self.status_var.set(f"No object found at ({x}, {y})")

    def _on_list_select(self, event):
        """Select object from list"""
        selection = self.obj_list.curselection()
        if not selection:
            return

        idx = selection[0]
        text = self.obj_list.get(idx)

        # Parse name from text
        if text.startswith(" "):
            name = text[2:].split(" (")[0].strip()
            obj = self.parser.get_object_by_name(name)
            if obj:
                self.selected_object = {
                    "name": name,
                    "type": obj.get("plugin", "objectType"),
                    "properties": obj["data"],
                    "uid": obj.get("sid", 0),
                    "layer": "",
                    "layout": ""
                }
                self.btn_edit.config(state='normal')

    def _edit_selected(self):
        """Open property editor for selected object"""
        if not self.selected_object:
            return

        editor = PropertyEditor(self.root, self.selected_object,
                                self.parser, self._on_save_changes)
        self.editors.append(editor)

    def _on_save_changes(self, obj_data, changes):
        """Handle save from property editor"""
        self.status_var.set(f" Saved changes to {obj_data.get('name', 'object')}")

        # Here you would write changes back to data.json
        # For now, we track changes for mod export
        print(f"Changes for {obj_data.get('name')}: {changes}")

def main():
    root = tk.Tk()
    app = ModMakerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
