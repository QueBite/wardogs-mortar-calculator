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
window.minsize(320, 300)

# ---------- firing position (saved to disk) ----------
tk.Label(window, text="Firing position", font=("TkDefaultFont", 10, "bold")).grid(
    row=0, column=0, columnspan=2, pady=(10, 4))

tk.Label(window, text="Lat 1 (X):").grid(row=1, column=0, sticky="e", padx=6, pady=2)
lat1_entry = tk.Entry(window, width=14)
lat1_entry.grid(row=1, column=1, padx=6, pady=2)

tk.Label(window, text="Lon 1 (Y):").grid(row=2, column=0, sticky="e", padx=6, pady=2)
lon1_entry = tk.Entry(window, width=14)
lon1_entry.grid(row=2, column=1, padx=6, pady=2)

# ---------- target ----------
tk.Label(window, text="Target", font=("TkDefaultFont", 10, "bold")).grid(
    row=4, column=0, columnspan=2, pady=(10, 4))

tk.Label(window, text="Lat 2 (X):").grid(row=5, column=0, sticky="e", padx=6, pady=2)
lat2_entry = tk.Entry(window, width=14)
lat2_entry.grid(row=5, column=1, padx=6, pady=2)

tk.Label(window, text="Lon 2 (Y):").grid(row=6, column=0, sticky="e", padx=6, pady=2)
lon2_entry = tk.Entry(window, width=14)
lon2_entry.grid(row=6, column=1, padx=6, pady=2)

# ---------- output ----------
# A StringVar is a value the Label watches: set it and the label redraws itself.
result_var = tk.StringVar(value="Enter coordinates and press Calculate")
tk.Label(window, textvariable=result_var, justify="left", fg="#0a0").grid(
    row=8, column=0, columnspan=2, pady=10)

status_var = tk.StringVar(value="")
tk.Label(window, textvariable=status_var, fg="#666", font=("TkDefaultFont", 8)).grid(
    row=9, column=0, columnspan=2)


def save_position():
    """Write Lat 1 / Lon 1 to disk, replacing whatever was saved before."""
    try:
        lat1 = float(lat1_entry.get())
        lon1 = float(lon1_entry.get())
    except ValueError:
        status_var.set("Firing position must be two numbers - not saved")
        return

    # Mode "w" truncates the file first, so the previous position is
    # overwritten rather than appended to.
    with open(SAVE_FILE, "w") as f:
        json.dump({"lat1": lat1, "lon1": lon1}, f)

    status_var.set(f"Saved firing position: {lat1}, {lon1}")


def load_position():
    """Fill Lat 1 / Lon 1 from disk at startup, if a save exists."""
    if not SAVE_FILE.exists():
        status_var.set("No saved firing position yet")
        return

    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
        lat1 = float(data["lat1"])
        lon1 = float(data["lon1"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError, OSError):
        # A corrupt or hand-edited file must not stop the program starting.
        status_var.set("Saved position unreadable - ignoring")
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


tk.Button(window, text="Save firing position", command=save_position,
          width=18).grid(row=3, column=0, columnspan=2, pady=4)

tk.Button(window, text="Calculate", command=calculate, width=12).grid(
    row=7, column=0, columnspan=2, pady=8)

# Pressing Enter anywhere in the window does the same as clicking Calculate.
window.bind("<Return>", calculate)

load_position()   # restore the last firing position before the window opens

if __name__ == "__main__":
    window.mainloop()
