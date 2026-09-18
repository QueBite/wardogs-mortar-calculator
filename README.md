# War Dogs Mortar Calculator

A small Windows desktop tool that works out the **distance** and **compass
bearing** from your mortar's firing position to a target, using the in-game
grid coordinates from War Dogs.

Type the two coordinate pairs, press Enter, and it gives you the range,
the bearing in degrees, and the compass heading.

## Download (for players)

**[Download the latest MortarCalculator.exe](../../releases/latest)**

Grab `MortarCalculator.exe` from the Assets list on that page. No install,
no Python needed — just double-click it.

### Windows SmartScreen warning

The .exe isn't code-signed (signing certificates cost money), so Windows
will likely show **"Windows protected your PC"** the first time you run it.
That's expected for any unsigned indie tool. To run it anyway:

1. Click **More info**
2. Click **Run anyway**

If you'd rather not trust a prebuilt binary, the full source is in this repo
(`Mortar_calc.py`, ~180 lines of readable Python) and you can build it
yourself — see below.

## How to use it

1. **Firing position** — enter your mortar's coordinates as `Lat 1 (X)` and
   `Lon 1 (Y)`.
2. Press **Save firing position**. It's written to disk and reloaded
   automatically next time you open the app, so you only enter it once per
   position.
3. **Target** — enter the target's coordinates as `Lat 2 (X)` and `Lon 2 (Y)`.
4. Press **Calculate** (or just hit **Enter**).

You get:

```
Distance: 335.18
Bearing:  228.7°
Heading:  SW
```

Coordinate fields are **X (easting) first, Y (northing) second** — the same
order the game prints a grid reference.

### Shot history

Every calculation is logged to the panel on the right — shot number, range,
bearing, heading and target coordinates in aligned columns, newest at the top.

- **Scrolls** with the scrollbar or the mouse wheel, and grows taller when you
  resize the window.
- **Double-click any past shot** to load its target back into the input boxes —
  handy for re-ranging a target you've already hit.
- **Survives restarts**, saved alongside the firing position.
- Repeating the same target won't add a duplicate row. The log caps at 200
  shots, oldest dropping off.
- **Clear history** empties the log; your saved firing position is kept.

### Where the saved position is stored

`mortar_position.json`, created in the same folder as the .exe. It holds both
your firing position and the shot history. Keep the .exe somewhere writable
(Desktop or a normal folder is fine — `C:\Program Files` would need admin
rights). Move the .exe and the saved data stays behind.

## How it works

Distance is the straight-line (Pythagorean) distance between the two points,
scaled by 100 to match in-game units:

```
distance = sqrt(dx² + dy²) × 100
```

Bearing is measured clockwise from north, which is `atan2(dx, dy)` — easting
difference over northing difference:

```
bearing = degrees(atan2(dx, dy)) mod 360
```

Verified against the game: firing `97.24, 109.58` at target `94.72, 107.37`
gives 335.18 range and 228.7°, matching the in-game reading of ~228°. All
eight compass points land exactly on 0/45/90/135/180/225/270/315°.

## Building it yourself

Requires Python 3.9+ on Windows (tkinter ships with the standard installer).

```bash
git clone https://github.com/QueBite/wardogs-mortar-calculator.git
cd wardogs-mortar-calculator

# Run straight from source
python Mortar_calc.py

# Or build the standalone .exe
python -m venv buildenv
buildenv\Scripts\python.exe -m pip install pyinstaller pillow
buildenv\Scripts\python.exe make_icon.py          # generates mortar.ico
buildenv\Scripts\python.exe -m PyInstaller --onefile --windowed \
    --name MortarCalculator --icon mortar.ico Mortar_calc.py
```

The finished exe lands in `dist\MortarCalculator.exe`.

## Files

| File | Purpose |
|---|---|
| `Mortar_calc.py` | The whole application |
| `make_icon.py` | Generates the app icon |
| `MortarCalculator.spec` | PyInstaller build config |

## License

MIT — see [LICENSE](LICENSE). Do what you like with it.
