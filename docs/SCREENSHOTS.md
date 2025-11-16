# How to Add Screenshots

To complete the documentation with actual screenshots from the running application, follow these steps:

## Prerequisites

1. Application must be running locally or deployed
2. GTFS data must be initialized (run `python scripts/init_data.py`)
3. Screenshot tool (OS built-in or tool like Flameshot, ShareX, etc.)

## Screenshots Needed

### 1. Main Interface (`main-interface.png`)

**Setup:**
- Open the application in browser (http://localhost:8000)
- Clear any errors or selections
- Show the default view with Munich centered on map
- Ensure all UI elements are visible (header, controls panel, map, footer)

**What to capture:**
- Full browser window or application area
- Controls panel on the left showing all options
- Map centered on Munich with visible transit stops
- Footer with MVV attribution

**Recommended size:** 1920x1080 or 1600x900

**Example view:**
```
┌─────────────────────────────────────────────┐
│ Munich Transit Reachability Map             │
│ Visualize how far you can travel...        │
├──────────┬──────────────────────────────────┤
│ Controls │                                  │
│          │        [Munich Map]              │
│ □ Stop   │                                  │
│ □ Time   │    • • •    (transit stops)      │
│ □ Day    │        • •                       │
│          │      •   •                       │
│ [Calc]   │    •       •                     │
│          │                                  │
│ Legend   │                                  │
├──────────┴──────────────────────────────────┤
│ Data: MVV | Retrieved: YYYY-MM-DD          │
└─────────────────────────────────────────────┘
```

---

### 2. Reachability Visualization (`reachability-visualization.png`)

**Setup:**
1. Select "Marienplatz" as origin (search or click)
2. Set max time to 30 minutes
3. Set departure time to 09:00
4. Day type: Weekday
5. Click "Calculate Reachability"
6. Wait for calculation to complete
7. Press "Stop" button to show full 30-minute reachability (don't animate)

**What to capture:**
- Map showing color-coded reachable stops
- Blue origin marker at Marienplatz clearly visible
- Green stops (0-15 min) and light green stops (15-30 min)
- Legend showing color coding
- Selected stop info in controls panel

**Key elements:**
- Origin marker (blue, large)
- Green cluster around origin (close stops)
- Light green further out
- Animation controls visible but stopped at 30 minutes

---

### 3. Animation Controls (`animation-controls.png`)

**Setup:**
1. Same as reachability visualization setup
2. Press "Play" button
3. Let animation run to about 15-20 minutes
4. Take screenshot while animation is playing (or paused mid-animation)

**What to capture:**
- Close-up of animation controls section showing:
  - Time display (e.g., "15 minutes")
  - Progress bar partially filled
  - Play/Pause/Stop buttons
  - Stops being added progressively to map

**Alternative:**
- Take screenshot of controls panel only
- Show progress bar at ~50%
- Time display showing intermediate value

---

## Capturing Screenshots

### On macOS
```bash
# Full screen
Cmd + Shift + 3

# Selected area
Cmd + Shift + 4
```

### On Windows
```bash
# Snipping Tool or Snip & Sketch
Windows + Shift + S

# Or use built-in screenshot
PrtScn (Print Screen)
```

### On Linux
```bash
# GNOME Screenshot
gnome-screenshot -a

# Or Flameshot (recommended)
flameshot gui
```

## Processing Screenshots

1. **Resize if needed**: Max width 1920px, optimize for web
2. **Format**: PNG (for UI), JPEG (if file size is too large)
3. **Compress**: Use tools like TinyPNG or ImageOptim to reduce file size
4. **Naming**: Use exact names specified above
   - `main-interface.png`
   - `reachability-visualization.png`
   - `animation-controls.png`

## Saving Screenshots

Save all screenshots to:
```
docs/screenshots/
├── main-interface.png
├── reachability-visualization.png
└── animation-controls.png
```

## Quick Script to Take All Screenshots

After you've taken screenshots manually and saved them locally:

```bash
# Create directory if it doesn't exist
mkdir -p docs/screenshots

# Copy your screenshots (adjust paths as needed)
cp ~/Pictures/screenshot1.png docs/screenshots/main-interface.png
cp ~/Pictures/screenshot2.png docs/screenshots/reachability-visualization.png
cp ~/Pictures/screenshot3.png docs/screenshots/animation-controls.png

# Verify
ls -lh docs/screenshots/
```

## Updating Git

After adding screenshots:

```bash
git add docs/screenshots/*.png
git commit -m "Add application screenshots to documentation"
git push
```

## Tips for Best Screenshots

1. **Use a clean browser**: Close unnecessary tabs, use incognito/private mode
2. **Check resolution**: Ensure text is readable when scaled down
3. **Consistent zoom**: Use same browser zoom level for all screenshots
4. **Good timing**: For animation screenshot, capture mid-animation for dynamic effect
5. **Real data**: Use actual GTFS data, not mock data, for authentic look
6. **Highlight features**: Ensure key UI elements are clearly visible
7. **No personal info**: Don't include any personal bookmarks or browser info

## Example Test Run

```bash
# 1. Start application
uvicorn backend.api.app:app --reload

# 2. Open browser
open http://localhost:8000

# 3. Take screenshots following guide above

# 4. Save to docs/screenshots/

# 5. Verify images display in README
# (GitHub will show them automatically in the README.md)
```

## Alternative: Use Demo GIF

If you want to show the animation in action, consider creating an animated GIF:

```bash
# Using ffmpeg to create GIF from screen recording
ffmpeg -i screenrecording.mp4 -vf "fps=10,scale=800:-1" animation-demo.gif

# Save as
docs/screenshots/animation-demo.gif
```

Then add to README:
```markdown
### Animation Demo
![Animation Demo](docs/screenshots/animation-demo.gif)
```
