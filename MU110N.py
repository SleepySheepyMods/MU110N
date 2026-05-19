#!/usr/bin/env python3
"""
MU110N - Visual Mod Builder for Sheepy: A Short Adventure
Drag-and-drop interface to create and edit game mods - No overlay required!
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
import json
import shutil

#
# CONFIGURATION
#
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 700
PALETTE_WIDTH = 450

BLOCK_WIDTH = 120
BLOCK_HEIGHT = 50
BLOCK_COLORS = {
    "Player": "#FF6B6B",
    "Enemy": "#FF6B6B",
    "Item": "#4ECDC4",
    "Platform": "#45B7D1",
    "Trigger": "#FFA07A",
    "Property": "#98D8C8",
    "Event": "#F7DC6F",
    "Action": "#BB8FCE"
}

#
# BLOCK CLASS - Represents a drag-and-drop block
#
class Block:
    def __init__(self, block_type, x, y, canvas):
        self.block_type = block_type
        self.x = x
        self.y = y
        self.canvas = canvas
        self.rect_id = None
        self.text_id = None
        self.properties = {}
        self.children = []
        self.parent = None
        self.is_selected = False
        
        self.draw()
    
    def draw(self):
        """Draw block on canvas"""
        color = BLOCK_COLORS.get(self.block_type, "#95A5A6")
        
        self.rect_id = self.canvas.create_rectangle(
            self.x, self.y, self.x + BLOCK_WIDTH, self.y + BLOCK_HEIGHT,
            fill=color, outline="black", width=2, tags=("block", str(id(self)))
        )
        
        self.text_id = self.canvas.create_text(
            self.x + BLOCK_WIDTH // 2, self.y + BLOCK_HEIGHT // 2,
            text=self.block_type, font=("Arial", 9, "bold"),
            fill="white", tags=("block", str(id(self)))
        )
    
    def move(self, dx, dy):
        """Move block"""
        self.x += dx
        self.y += dy
        self.canvas.coords(self.rect_id, self.x, self.y, 
                          self.x + BLOCK_WIDTH, self.y + BLOCK_HEIGHT)
        self.canvas.coords(self.text_id, self.x + BLOCK_WIDTH // 2, 
                          self.y + BLOCK_HEIGHT // 2)
    
    def select(self):
        """Select block"""
        self.is_selected = True
        self.canvas.itemconfig(self.rect_id, outline="gold", width=3)
    
    def deselect(self):
        """Deselect block"""
        self.is_selected = False
        self.canvas.itemconfig(self.rect_id, outline="black", width=2)
    
    def to_dict(self):
        """Convert block to dictionary for saving"""
        return {
            "type": self.block_type,
            "x": self.x,
            "y": self.y,
            "properties": self.properties,
            "children": [child.to_dict() for child in self.children]
        }

#
# DRAG AND DROP HANDLER
#
class DragDropHandler:
    def __init__(self, canvas, blocks_list):
        self.canvas = canvas
        self.blocks_list = blocks_list
        self.dragging_block = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-3>", self.on_right_click)
    
    def on_mouse_down(self, event):
        """Handle mouse down"""
        clicked_items = self.canvas.find_overlapping(
            event.x - 2, event.y - 2, event.x + 2, event.y + 2
        )
        
        # Deselect all blocks
        for block in self.blocks_list:
            block.deselect()
        
        # Find clicked block
        for item_id in clicked_items:
            tags = self.canvas.gettags(item_id)
            if "block" in tags:
                for block in self.blocks_list:
                    if str(id(block)) in tags:
                        self.dragging_block = block
                        block.select()
                        self.drag_start_x = event.x
                        self.drag_start_y = event.y
                        break
                break
    
    def on_mouse_drag(self, event):
        """Handle mouse drag"""
        if self.dragging_block:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.dragging_block.move(dx, dy)
            self.drag_start_x = event.x
            self.drag_start_y = event.y
    
    def on_mouse_up(self, event):
        """Handle mouse up"""
        self.dragging_block = None

    def on_right_click(self, event):
        """Open property editor for clicked block"""
        clicked_items = self.canvas.find_overlapping(
            event.x - 2, event.y - 2, event.x + 2, event.y + 2
        )
        for item_id in clicked_items:
            tags = self.canvas.gettags(item_id)
            if "block" in tags:
                for block in self.blocks_list:
                    if str(id(block)) in tags:
                        BlockPropertyEditor(self.canvas.master, block)
                        return

#
# PROPERTY EDITOR FOR BLOCKS
#
class BlockPropertyEditor:
    def __init__(self, master, block):
        self.master = master
        self.block = block
        self.window = tk.Toplevel(master)
        self.window.title(f"Properties - {block.block_type}")
        self.window.geometry("360x320")
        self.window.transient(master)

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=f"{self.block.block_type} Properties", font=("Segoe UI", 12, "bold")).pack(pady=(0,10))

        # Name / Label
        ttk.Label(frame, text="Label:").pack(anchor='w')
        self.label_var = tk.StringVar(value=self.block.properties.get('label', self.block.block_type))
        ttk.Entry(frame, textvariable=self.label_var).pack(fill='x', pady=5)

        # Custom properties area
        ttk.Label(frame, text="Custom Properties (key=value, one per line):").pack(anchor='w', pady=(10,0))
        self.props_text = tk.Text(frame, height=8)
        self.props_text.pack(fill='both', expand=True)

        # Load existing properties
        props = self.block.properties.get('custom', {})
        for k, v in props.items():
            self.props_text.insert('end', f"{k}={v}\n")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=10)

        ttk.Button(btn_frame, text="Save", command=self._save).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack(side='right')

    def _save(self):
        # Save label
        self.block.properties['label'] = self.label_var.get()
        # Parse custom properties
        text = self.props_text.get('1.0', 'end').strip()
        custom = {}
        for line in text.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                custom[k.strip()] = v.strip()
        self.block.properties['custom'] = custom
        messagebox.showinfo("Saved", "Properties saved")
        self.window.destroy()

#
# TUTORIAL DIALOG
#
class TutorialDialog:
    def __init__(self, parent):
        self.parent = parent
        self.win = tk.Toplevel(parent)
        self.win.title("MU110N Tutorial")
        self.win.geometry("600x400")
        self.win.transient(parent)

        self.pages = [
            {
                "title": "Welcome",
                "text": (
                    "Welcome to MU110N Visual Mod Builder for Sheepy!\n\n"
                    "This tutorial will walk you through creating a simple mod using blocks.\n\n"
                    "Click Next to continue."
                )
            },
            {
                "title": "Palette",
                "text": (
                    "Block Palette:\n\n"
                    "Use the palette on the left to add blocks to the canvas.\n"
                    "Each block represents an element (Player, Enemy, Item, Platform, Trigger, Event, Action).\n\n"
                    "Click a block type to add it to the editor canvas."
                )
            },
            {
                "title": "Positioning",
                "text": (
                    "Positioning Blocks:\n\n"
                    "Drag blocks to position them on the canvas.\n"
                    "Click a block to select it (gold border).\n\n"
                    "You can arrange blocks visually to represent your level or mod layout."
                )
            },
            {
                "title": "Editing Properties",
                "text": (
                    "Editing Properties:\n\n"
                    "Right-click a block to open the property editor.\n"
                    "Add or change key-value properties that will be included in the exported mod.json.\n\n"
                    "For example, set a Player speed property or an Enemy health property."
                )
            },
            {
                "title": "Save & Load",
                "text": (
                    "Save & Load Projects:\n\n"
                    "Use the toolbar buttons to save your project to a .json file and load it later.\n\n"
                    "This preserves block positions and properties."
                )
            },
            {
                "title": "Export as Mod",
                "text": (
                    "Exporting:\n\n"
                    "When you're ready, Export as Mod to create a mod folder containing a mod.json file.\n"
                    "You can further refine mod.json to match Sheepy's expected structure or I can add automatic mapping.\n\n"
                    "That's it — enjoy building mods!"
                )
            }
        ]

        self.index = 0

        # UI
        self.title_label = ttk.Label(self.win, text="", font=("Segoe UI", 14, "bold"))
        self.title_label.pack(pady=(10, 5))
        self.text_area = tk.Text(self.win, wrap='word', font=("Segoe UI", 10), state='disabled')
        self.text_area.pack(fill='both', expand=True, padx=10, pady=5)

        nav = ttk.Frame(self.win)
        nav.pack(fill='x', pady=10)
        self.prev_btn = ttk.Button(nav, text="← Previous", command=self.prev_page)
        self.prev_btn.pack(side='left', padx=10)
        self.next_btn = ttk.Button(nav, text="Next →", command=self.next_page)
        self.next_btn.pack(side='right', padx=10)
        ttk.Button(nav, text="Close", command=self.win.destroy).pack(side='right')

        self._show_page()

    def _show_page(self):
        page = self.pages[self.index]
        self.title_label.config(text=page['title'])
        self.text_area.config(state='normal')
        self.text_area.delete('1.0', 'end')
        self.text_area.insert('1.0', page['text'])
        self.text_area.config(state='disabled')
        # update buttons
        self.prev_btn.config(state='normal' if self.index > 0 else 'disabled')
        self.next_btn.config(state='normal' if self.index < len(self.pages)-1 else 'disabled')

    def next_page(self):
        if self.index < len(self.pages)-1:
            self.index += 1
            self._show_page()

    def prev_page(self):
        if self.index > 0:
            self.index -= 1
            self._show_page()

#
# MAIN APPLICATION
#
class ModBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MU110N - Visual Mod Builder for Sheepy")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(1000, 600)
        
        self.blocks = []
        self.current_project = None
        self.selected_block = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI"""
        # Add menu bar with Tutorial under Help so it's always visible
        menubar = tk.Menu(self.root)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Tutorial", command=self._show_tutorial)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.root.config(menu=menubar)

        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(toolbar, text="📁 New Project", command=self._new_project).pack(side="left", padx=5)
        ttk.Button(toolbar, text="💾 Save Project", command=self._save_project).pack(side="left", padx=5)
        ttk.Button(toolbar, text="📂 Load Project", command=self._load_project).pack(side="left", padx=5)
        ttk.Button(toolbar, text="📦 Export as Mod", command=self._export_mod).pack(side="left", padx=5)
        # Make tutorial button larger and always visible
        ttk.Button(toolbar, text="❓ Tutorial", command=self._show_tutorial).pack(side="left", padx=5)
        ttk.Button(toolbar, text="❌ Clear All", command=self._clear_all).pack(side="left", padx=5)
        
        # Main content area
        content = ttk.Frame(main_frame)
        content.pack(fill="both", expand=True)
        
        # Left panel - Block palette
        left_panel = ttk.LabelFrame(content, text="Block Palette", padding=10)
        left_panel.pack(side="left", fill="both", padx=(0, 10))
        
        self._build_palette(left_panel)
        
        # Right panel - Canvas
        right_panel = ttk.LabelFrame(content, text="Mod Editor", padding=10)
        right_panel.pack(side="left", fill="both", expand=True)
        
        # Canvas
        self.canvas = tk.Canvas(
            right_panel, bg="white", width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
            relief="sunken", borderwidth=2
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Draw grid
        for i in range(0, CANVAS_WIDTH, 50):
            self.canvas.create_line(i, 0, i, CANVAS_HEIGHT, fill="#E0E0E0", dash=(2, 2))
        for i in range(0, CANVAS_HEIGHT, 50):
            self.canvas.create_line(0, i, CANVAS_WIDTH, i, fill="#E0E0E0", dash=(2, 2))
        
        # Drag and drop handler
        self.drag_handler = DragDropHandler(self.canvas, self.blocks)
        
        # Bottom info panel
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(info_frame, text="💡 Drag blocks from palette onto canvas. Click blocks to select. Right-click to edit properties.", 
                 foreground="gray").pack()
    
    def _build_palette(self, parent):
        """Build block palette"""
        palette_blocks = [
            "Player", "Enemy", "Item", "Platform", "Trigger", "Property", "Event", "Action"
        ]
        
        for block_type in palette_blocks:
            btn = tk.Button(
                parent, text=block_type, bg=BLOCK_COLORS.get(block_type, "#95A5A6"),
                fg="white", font=("Arial", 9, "bold"), width=15, height=2,
                command=lambda bt=block_type: self._add_block(bt)
            )
            btn.pack(fill="x", pady=5)
            
            # Tooltip
            self._create_tooltip(btn, f"Click to add a {block_type} block to the canvas")
    
    def _add_block(self, block_type):
        """Add a block to the canvas"""
        # Random position
        import random
        x = random.randint(50, CANVAS_WIDTH - BLOCK_WIDTH - 50)
        y = random.randint(50, CANVAS_HEIGHT - BLOCK_HEIGHT - 50)
        
        block = Block(block_type, x, y, self.canvas)
        self.blocks.append(block)
    
    def _new_project(self):
        """Create new project"""
        if self.blocks and not messagebox.askyesno("Clear All", "Clear all blocks and start new project?"):
            return
        
        self.blocks = []
        self.canvas.delete("block")
        self.current_project = None
        messagebox.showinfo("New Project", "New project created!")
    
    def _save_project(self):
        """Save project to JSON"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        project_data = {
            "blocks": [block.to_dict() for block in self.blocks]
        }
        
        with open(file_path, 'w') as f:
            json.dump(project_data, f, indent=2)
        
        self.current_project = file_path
        messagebox.showinfo("Saved", f"Project saved to:\n{file_path}")
    
    def _load_project(self):
        """Load project from JSON"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        self.canvas.delete("block")
        self.blocks = []
        
        with open(file_path, 'r') as f:
            project_data = json.load(f)
        
        for block_data in project_data.get("blocks", []):
            block = Block(
                block_data["type"],
                block_data["x"],
                block_data["y"],
                self.canvas
            )
            block.properties = block_data.get("properties", {})
            self.blocks.append(block)
        
        self.current_project = file_path
        messagebox.showinfo("Loaded", f"Project loaded from:\n{file_path}")
    
    def _export_mod(self):
        """Export as mod package"""
        if not self.blocks:
            messagebox.showwarning("Empty Project", "Add some blocks before exporting!")
            return
        
        folder_path = filedialog.askdirectory(title="Select where to save mod folder")
        if not folder_path:
            return
        
        mod_name = simpledialog.askstring("Mod Name", "Enter mod name:", parent=self.root)
        if not mod_name:
            return
        
        # Create mod structure
        mod_dir = Path(folder_path) / mod_name
        mod_dir.mkdir(exist_ok=True)
        
        # Create mod.json
        mod_config = {
            "name": mod_name,
            "version": "1.0.0",
            "author": "MU110N Visual Builder",
            "description": f"Mod with {len(self.blocks)} blocks",
            "priority": 10,
            "blocks": [block.to_dict() for block in self.blocks],
            "data_patches": []
        }
        
        with open(mod_dir / "mod.json", 'w') as f:
            json.dump(mod_config, f, indent=2)
        
        messagebox.showinfo("Exported", f"Mod exported to:\n{mod_dir}\n\nYou can now install this in Sheepy!")
    
    def _clear_all(self):
        """Clear all blocks"""
        if self.blocks and messagebox.askyesno("Clear All", "Remove all blocks?"):
            self.canvas.delete("block")
            self.blocks = []
    
    def _on_canvas_double_click(self, event):
        """Open property editor for the block under the cursor (if any)"""
        clicked_items = self.canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        for item_id in clicked_items:
            tags = self.canvas.gettags(item_id)
            if "block" in tags:
                for block in self.blocks:
                    if str(id(block)) in tags:
                        BlockPropertyEditor(self.root, block)
                        return

    def _show_tutorial(self):
        TutorialDialog(self.root)

    def _create_tooltip(self, widget, text):
        """Create hover tooltip"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="lightyellow", 
                           relief="solid", borderwidth=1, font=("Arial", 8))
            label.pack()
        
        widget.bind("<Enter>", on_enter)

def main():
    root = tk.Tk()
    app = ModBuilderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
