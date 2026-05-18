## MU110N (Click-to-Edit)

```bash
python MU110N.py
```

### How It Works

1. **Launch Sheepy** — Start the game normally
2. **Start Click Mode** — Click " Start Click Mode" in the MU110N
3. **Overlay Appears** — A transparent overlay covers the game window
4. **Right-Click Overlay** — Toggles between click-through and click-capture
5. **Left-Click Game Objects** — Selects whatever you click on
6. **Edit Properties** — A property editor opens with the object's data

### What You Can Edit

| Tab | What You Change |
|-----|----------------|
| **Properties** | Position (x, y), size, angle, opacity, instance variables |
| **Behaviors** | Platform behavior settings, physics, movement speeds |
| **Events** | View event sheet code linked to the object's layout |

### Export as Mod

After editing, click **" Export as Mod"** to save your changes as a proper mod package that the 011 can install.

---

## Creating Mods Manually

Use the `mod_template.json` as a starting point:

```
MyMod/
 mod.json ← metadata & instructions
 assets/
 sprites/ ← replacement images
 audio/ ← replacement sounds
 (any files)
```

### mod.json Fields

```json
{
 "name": "My Mod",
 "version": "1.0.0",
 "author": "You",
 "description": "What it does",
 "priority": 10,
 "file_mappings": {
 "assets/sprites/new.png": "images/player_000.png"
 },
 "data_patches": [
 {
 "target": "data.json",
 "operation": "replace",
 "path": "player.speed",
 "value": 300
 }
 ]
}
```

---

## Workflow: MU110N → 011

```
1. Play Sheepy
2. Open MU110N → click game objects → edit properties
3. Export as Mod (creates a mod folder)
4. Open 011 → Install Mod → select exported folder
5. Enable → Apply → Launch
```

---

## Safety

- **Auto-backups** before any file changes
- **One-click restore** to vanilla
- **Priority system** for load ordering
- **Separate tools** — Maker doesn't touch files until you export
