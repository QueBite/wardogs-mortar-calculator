import tkinter as tk
import math
import json
import sys
from pathlib import Path

# Windows scales most displays to 125-150%. Tk does not follow that by
# default, so text renders blurry and widgets get clipped. Declaring the
# process DPI-aware fixes both. No-op on Linux and macOS.
if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)   # Windows 8.1 and newer
    except (ImportError, AttributeError, OSError):
        try:
            windll.user32.SetProcessDPIAware()    # Windows 7 fallback
        except Exception:
            pass                                  # not fatal - carry on

# The save file lives next to the program, so it is found no matter which
# directory you launch from.
#
# When bundled by PyInstaller, __file__ points inside a temporary extraction
# folder that is DELETED on exit - saving there would silently lose the
# position every run. sys.executable is the real .exe, so use that instead.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

SAVE_FILE = BASE_DIR / "mortar_position.json"

# Cap the shot log so the save file cannot grow without limit over a long
# session. Oldest entries fall off the end.
MAX_HISTORY = 200


def logic(x1, x2, y1, y2):
    """Return (distance, bearing, compass) from firing position to target.

    Field 1 of each pair is the EASTING (X), field 2 is the NORTHING (Y) -
    this matches how War Dogs prints a grid reference.
    """
    dx = round(x2 - x1, 6)          # easting  difference
    dy = round(y2 - y1, 6)          # northing difference
    distance = ((dx**2 + dy**2)**0.5) * 100

    # Compass bearing is measured CLOCKWISE FROM NORTH, so the easting
    # difference is the atan2 numerator and the northing the denominator:
    # atan2(dx, dy). Swapping them measures anticlockwise from east
    # instead, which is what made due north read 85 degrees and due east
    # 355 degrees. No fudge offset is needed once the axes are right.
    bearing = math.degrees(math.atan2(dx, dy)) % 360

    if dx == 0 and dy == 0:
        compass = "same position"
    elif bearing < 22.5:   compass = "N"
    elif bearing < 67.5:   compass = "NE"
    elif bearing < 112.5:  compass = "E"
    elif bearing < 157.5:  compass = "SE"
    elif bearing < 202.5:  compass = "S"
    elif bearing < 247.5:  compass = "SW"
    elif bearing < 292.5:  compass = "W"
    elif bearing < 337.5:  compass = "NW"
    else:                  compass = "N"      # 337.5-360 wraps back to N

    return distance, round(bearing, 1), compass


# ---------- window ----------
window = tk.Tk()
window.title("Mortar Calculator")
# No fixed geometry: Tk sizes the window to fit its widgets, so it stays
# correct at any DPI / font scaling instead of clipping the bottom row.
window.minsize(600, 400)

# Two panels side by side: inputs on the left, shot history on the right.
# Only the history column gets weight, so when the window is resized the
# list grows and the input column stays its natural width.
window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(0, weight=0)
window.grid_columnconfigure(1, weight=1)

left = tk.Frame(window)
left.grid(row=0, column=0, sticky="n")

right = tk.Frame(window)
right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=(10, 8))
right.grid_rowconfigure(1, weight=1)      # the list row absorbs spare height
right.grid_columnconfigure(0, weight=1)   # the list absorbs spare width

# ---------- firing position (saved to disk) ----------
tk.Label(left, text="Firing position", font=("TkDefaultFont", 10, "bold")).grid(
    row=0, column=0, columnspan=2, pady=(10, 4))

tk.Label(left, text="Lat 1 (X):").grid(row=1, column=0, sticky="e", padx=6, pady=2)
lat1_entry = tk.Entry(left, width=14)
lat1_entry.grid(row=1, column=1, padx=6, pady=2)

tk.Label(left, text="Lon 1 (Y):").grid(row=2, column=0, sticky="e", padx=6, pady=2)
lon1_entry = tk.Entry(left, width=14)
lon1_entry.grid(row=2, column=1, padx=6, pady=2)

# ---------- target ----------
tk.Label(left, text="Target", font=("TkDefaultFont", 10, "bold")).grid(
    row=4, column=0, columnspan=2, pady=(10, 4))

tk.Label(left, text="Lat 2 (X):").grid(row=5, column=0, sticky="e", padx=6, pady=2)
lat2_entry = tk.Entry(left, width=14)
lat2_entry.grid(row=5, column=1, padx=6, pady=2)

tk.Label(left, text="Lon 2 (Y):").grid(row=6, column=0, sticky="e", padx=6, pady=2)
lon2_entry = tk.Entry(left, width=14)
lon2_entry.grid(row=6, column=1, padx=6, pady=2)

# ---------- output ----------
# A StringVar is a value the Label watches: set it and the label redraws itself.
result_var = tk.StringVar(value="Enter coordinates and press Calculate")
tk.Label(left, textvariable=result_var, justify="left", fg="#0a0").grid(
    row=8, column=0, columnspan=2, pady=10)

status_var = tk.StringVar(value="")
tk.Label(left, textvariable=status_var, fg="#666", font=("TkDefaultFont", 8),
         wraplength=200, justify="center").grid(row=9, column=0, columnspan=2)

# ---------- shot history (right panel) ----------
tk.Label(right, text="Shot history", font=("TkDefaultFont", 10, "bold")).grid(
    row=0, column=0, columnspan=2, pady=(0, 4))

# A monospaced font is what keeps the number columns lined up down the list.
history_list = tk.Listbox(right, width=32, height=15, activestyle="none",
                          font=("Consolas", 9), exportselection=False)
history_list.grid(row=1, column=0, sticky="nsew")

# The scrollbar and the list drive each other: the list tells the bar where
# it is (yscrollcommand), the bar tells the list where to go (command).
history_scroll = tk.Scrollbar(right, orient="vertical", command=history_list.yview)
history_scroll.grid(row=1, column=1, sticky="ns")
history_list.configure(yscrollcommand=history_scroll.set)

tk.Label(right, text="Double-click a shot to reload its target",
         fg="#666", font=("TkDefaultFont", 8)).grid(
    row=2, column=0, columnspan=2, pady=(4, 0))

# Newest shot first, so the one you just fired is visible without scrolling.
history = []


def history_line(shot):
    """Format one shot as a fixed-width row: number, range, bearing, target."""
    return (f"{shot['n']:>3}  {shot['distance']:7.2f}  "
            f"{shot['bearing']:5.1f}\u00b0 {shot['compass']:<2}  "
            f"{shot['x2']:g},{shot['y2']:g}")


def refresh_history():
    """Redraw the whole list from the history data."""
    history_list.delete(0, "end")
    for shot in history:
        history_list.insert("end", history_line(shot))


def add_shot(x2, y2, distance, bearing, compass):
    """Record a calculated shot at the top of the list and save it."""
    # Pressing Enter twice on the same target should not fill the log with
    # duplicate rows.
    if history and history[0]["x2"] == x2 and history[0]["y2"] == y2:
        return

    number = history[0]["n"] + 1 if history else 1
    history.insert(0, {"n": number, "x2": x2, "y2": y2,
                       "distance": distance, "bearing": bearing,
                       "compass": compass})
    del history[MAX_HISTORY:]          # drop anything past the cap
    refresh_history()
    save_state()


def reuse_shot(event=None):
    """Double-click: copy that shot's target back into the target boxes."""
    selection = history_list.curselection()
    if not selection:
        return
    shot = history[selection[0]]
    lat2_entry.delete(0, "end")
    lat2_entry.insert(0, shot["x2"])
    lon2_entry.delete(0, "end")
    lon2_entry.insert(0, shot["y2"])
    status_var.set(f"Loaded target from shot #{shot['n']}")


history_list.bind("<Double-Button-1>", reuse_shot)


def clear_history():
    """Empty the shot log, on screen and on disk."""
    history.clear()
    refresh_history()
    save_state()
    status_var.set("Shot history cleared")


tk.Button(right, text="Clear history", command=clear_history).grid(
    row=3, column=0, columnspan=2, pady=(6, 0), sticky="e")


def save_state():
    """Write firing position and shot history to the one save file.

    Both live in the same file so there is only ever one thing sitting next
    to the exe. Writing them together also means saving a position cannot
    wipe the history, or the other way round.
    """
    data = {"history": history[:MAX_HISTORY]}

    # An invalid or empty firing position is not an error here - the history
    # still deserves to be saved.
    try:
        data["lat1"] = float(lat1_entry.get())
        data["lon1"] = float(lon1_entry.get())
    except ValueError:
        pass

    try:
        # Mode "w" truncates first, so the file is replaced rather than
        # appended to.
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        # A read-only folder must not take the program down mid-session.
        status_var.set("Could not write save file - check folder permissions")


def save_position():
    """Save button: validate the firing position, then write everything."""
    try:
        lat1 = float(lat1_entry.get())
        lon1 = float(lon1_entry.get())
    except ValueError:
        status_var.set("Firing position must be two numbers - not saved")
        return

    save_state()
    status_var.set(f"Saved firing position: {lat1}, {lon1}")


def load_state():
    """Restore firing position and shot history at startup, if saved."""
    if not SAVE_FILE.exists():
        status_var.set("No saved firing position yet")
        return

    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # A corrupt or hand-edited file must not stop the program starting.
        status_var.set("Saved file unreadable - ignoring")
        return

    # Save files written before the history feature simply have no such key.
    saved = data.get("history", []) if isinstance(data, dict) else []
    if isinstance(saved, list):
        for shot in saved[:MAX_HISTORY]:
            try:
                history.append({
                    "n": int(shot["n"]),
                    "x2": float(shot["x2"]),
                    "y2": float(shot["y2"]),
                    "distance": float(shot["distance"]),
                    "bearing": float(shot["bearing"]),
                    "compass": str(shot["compass"]),
                })
            except (KeyError, ValueError, TypeError):
                continue          # skip one bad row, keep the rest
        refresh_history()

    try:
        lat1 = float(data["lat1"])
        lon1 = float(data["lon1"])
    except (KeyError, ValueError, TypeError):
        status_var.set("No saved firing position yet")
        return

    lat1_entry.delete(0, "end")
    lat1_entry.insert(0, lat1)
    lon1_entry.delete(0, "end")
    lon1_entry.insert(0, lon1)
    status_var.set(f"Loaded firing position: {lat1}, {lon1}")


def calculate(event=None):
    """Read the four boxes, run logic(), write the answer into result_var."""
    try:
        lat1 = float(lat1_entry.get())
        lon1 = float(lon1_entry.get())
        lat2 = float(lat2_entry.get())
        lon2 = float(lon2_entry.get())
    except ValueError:
        result_var.set("All four fields must be numbers")
        return

    distance, bearing, compass = logic(lat1, lat2, lon1, lon2)
    result_var.set(
        f"Distance: {distance:.2f}\n"
        f"Bearing:  {bearing}\u00b0\n"
        f"Heading:  {compass}"
    )
    add_shot(lat2, lon2, distance, bearing, compass)


tk.Button(left, text="Save firing position", command=save_position,
          width=18).grid(row=3, column=0, columnspan=2, pady=4)

tk.Button(left, text="Calculate", command=calculate, width=12).grid(
    row=7, column=0, columnspan=2, pady=8)

# Pressing Enter anywhere in the window does the same as clicking Calculate.
window.bind("<Return>", calculate)

load_state()   # restore position and history before the window opens

if __name__ == "__main__":
    window.mainloop()
