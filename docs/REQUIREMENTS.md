# Requirements — Display Location

**Last Updated:** 2026-11-12
**Status:** Approved by owner (scope agreed in Advisor session, 2026-11-12)

## 1. Purpose

The owner has two monitors and often wants to change where the second monitor sits relative to the primary (to the right, left, above or below). Doing this in *Settings → System → Display* is slow. **Display Location** is a small Windows tray app that opens a compact popup, styled like the Windows display-arrangement view, where the owner drags the second monitor's tile and the change is applied immediately.

## 2. Users and environment

| Item | Value |
|---|---|
| User | The owner (single user, non-admin account is fine) |
| OS | Windows 11 (Windows 10 should work but is not a target) |
| Monitors | Exactly two, in **Extend** mode. Primary = "1", secondary = "2" |
| Distribution | Single `DisplayLocation.exe`, no installer |

## 3. Functional requirements

| ID | Requirement |
|---|---|
| **FR-01 Tray icon** | The app runs in the background and shows an icon in the notification area (system tray). Hovering shows the tooltip "Display Location". |
| **FR-02 Open popup** | Left-clicking the tray icon toggles the popup (opens it; if already open, closes it). |
| **FR-03 Popup look** | Compact (about 360 × 240 logical px), dark theme, rounded corners, no title bar, drop shadow. Visual style follows the Windows 11 Settings display view: grey tile "1", accent (purple) tile "2", large centred numbers. Footer shows the current side (e.g. "Display 2: Right of 1") and the secondary monitor's resolution. |
| **FR-04 Popup position** | The popup opens directly above the tray icon, inside the primary monitor's work area. It cannot be moved by the user. If the tray icon's position is unknown, it opens at the bottom-right of the primary work area. |
| **FR-05 Popup close** | The popup closes on: clicking anywhere outside it, pressing **Esc**, or clicking the tray icon again. Closing never changes the display layout (except the revert in FR-07). |
| **FR-06 Drag & snap** | Tile "1" is fixed. Tile "2" can be dragged with the mouse (hand cursor on hover, closed-hand while dragging) and follows the cursor freely. On release it **snaps** to the nearest side of tile 1 (left, right, top, bottom), keeping its drop position along that edge. It also magnet-snaps to the "start-aligned", "centred" and "end-aligned" positions when released close to them. The tiles must always touch and overlap along the shared edge (see ARCHITECTURE §4). |
| **FR-07 Apply & revert** | On release, the new position is applied to Windows immediately. A bar then appears in the popup: **"Keep changes?  [Keep]  [Revert] (10)"** with a countdown. *Keep* confirms. *Revert*, or the countdown reaching 0, restores the previous position. If the popup is closed while the bar is showing, the countdown continues and still reverts unless Keep was pressed. |
| **FR-08 No-op drop** | If tile 2 is dropped in the position it already has (same snapped coordinates), nothing is applied and no revert bar appears. |
| **FR-09 Apply failure** | If Windows rejects the change, the tile animates back to the current real position and an inline error message is shown in the popup for 5 s. The error is written to the log. |
| **FR-10 Right-click menu** | Right-clicking the tray icon shows: **Open** (same as left-click), **Identify displays**, **Start with Windows** (checkable), separator, **Exit**. |
| **FR-11 Identify** | "Identify displays" shows a large number ("1", "2") in a translucent box at the centre of each physical monitor for 3 seconds, matching the tile numbers. |
| **FR-12 Start with Windows** | The checkable menu item adds/removes the app from the current user's startup. The check mark reflects the real current state on every menu open. Default on first run of the exe: **off** (owner turns it on). |
| **FR-13 Single instance** | Only one instance runs. Launching the exe again while it is running does not create a second tray icon; instead it opens the popup of the running instance and exits. |
| **FR-14 Display changes** | If monitors are connected/disconnected, or the layout/resolution changes from elsewhere (e.g. Windows Settings), the popup content updates to the real state the next time it is shown, and live while open. |
| **FR-15 Unsupported states** | The popup shows a clear message instead of tiles when: only one display is active ("Only one display is connected"), displays are duplicated ("Displays are duplicated — press Win+P and choose Extend"), or more than two displays are active ("More than two displays are not supported yet"). |
| **FR-16 Exit** | "Exit" removes the tray icon and ends the process. If a revert countdown is running, Exit first reverts (safe default). |

## 4. Non-functional requirements

| ID | Requirement |
|---|---|
| **NFR-01 No admin** | Runs and changes display position without administrator rights. |
| **NFR-02 Footprint** | Idle CPU ≈ 0 %; memory under ~120 MB; no polling loops. |
| **NFR-03 Startup** | Tray icon visible within 3 s of launch. |
| **NFR-04 DPI** | Correct tile proportions and positions with any scaling (100–200 %) including mixed scaling between monitors. All display maths in physical pixels. |
| **NFR-05 Packaging** | One-file `DisplayLocation.exe` with its own icon, no console window. |
| **NFR-06 Robustness** | Unhandled exceptions are logged and never leave the layout changed without a revert path. |
| **NFR-07 Logging** | Rotating log at `%LOCALAPPDATA%\DisplayLocation\logs\app.log` (max 1 MB × 3). |
| **NFR-08 Privacy** | No network access, no telemetry. |

## 5. Out of scope (v1)

- Independent taskbars, per-monitor taskbar icons, per-monitor virtual desktops — **handled by Windhawk mods** (DECISIONS D-001).
- Three or more monitors (only the message in FR-15).
- Changing resolution, orientation, scaling, refresh rate or which monitor is primary.
- Moving windows between monitors.
- Global hotkeys, saved layout presets, installers, auto-update, other operating systems.

These may be revisited later; see ROADMAP "Later ideas".

## 6. Acceptance (v1 done when)

1. All FR-01 … FR-16 pass a QA session on the owner's machine.
2. `DisplayLocation.exe` built by the documented build command runs on a clean login with Start with Windows enabled.
3. Unit tests for the snap maths pass.
