#!/usr/bin/env python3
"""Generate an animated Cyber-Cat Rocket Drift contribution graph for GitHub.

Features a Cyberpunk Mecha-Cat with glowing cyber-visor riding an afterburning
rocket drift-board across the GitHub contribution grid. As the Cyber-Cat drifts
around corners, twin plasma thrusters carve neon light trails and ignite each
commit cell in Vice City neon hues.

Stdlib only: zero external dependencies, 100% GitHub Camo & SVG SMIL compatible.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import ssl
import sys
import urllib.error
import urllib.request
from xml.dom import minidom

API_URL = "https://api.github.com/graphql"

QUERY = """
query ($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionLevel
          }
        }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

# ── Grid Layout Constants ────────────────────────────────────────────────────
CELL = 12
GAP = 3
PITCH = CELL + GAP  # 15px
COLS = 53
ROWS = 7
PAD_L = 36
PAD_T = 38
PAD_R = 36
PAD_B = 16
GRID_W = COLS * PITCH - GAP  # 792px
GRID_H = ROWS * PITCH - GAP  # 102px
WIDTH = PAD_L + GRID_W + PAD_R  # 864px
HEIGHT = PAD_T + GRID_H + PAD_B  # 156px
WEEKDAYS = ["", "Mon", "", "Wed", "", "Fri", ""]

# ── Theme Palettes ───────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg": "#080414",
        "bg_gradient_end": "#120826",
        "border": "#2e1252",
        "grid_empty": "#150b29",
        "cells": [
            "#150b29",  # Level 0
            "#451c7a",  # Level 1 (Neon Violet)
            "#8a2be2",  # Level 2 (Vivid Electric Purple)
            "#ff2a85",  # Level 3 (Vice City Hot Pink)
            "#00f0ff",  # Level 4 (Cyber Cyan)
        ],
        "cat_fur": "#1e1b2e",
        "cat_fur_rim": "#a78bfa",
        "cat_ear_inner": "#c084fc",
        "cat_visor": "#00f0ff",
        "board_deck": "#ff2a85",
        "board_accent": "#c026d3",
        "board_thruster": "#381254",
        "flame_core": "#ffffff",
        "flame_outer": "#00f0ff",
        "underglow": "#ff2a85",
        "skid_line": "#a855f7",
        "spark": "#00f0ff",
        "hud_title": "#ff2a85",
        "hud_subtitle": "#a78bfa",
        "hud_accent": "#00f0ff",
        "label": "#8a7ba3",
    },
    "light": {
        "bg": "#f8f7ff",
        "bg_gradient_end": "#ede9fe",
        "border": "#ddd6fe",
        "grid_empty": "#e5e0f7",
        "cells": [
            "#e5e0f7",  # Level 0
            "#c084fc",  # Level 1
            "#9333ea",  # Level 2
            "#e11d48",  # Level 3
            "#0284c7",  # Level 4
        ],
        "cat_fur": "#2d2a3e",
        "cat_fur_rim": "#7c3aed",
        "cat_ear_inner": "#e879f9",
        "cat_visor": "#06b6d4",
        "board_deck": "#e11d48",
        "board_accent": "#be123c",
        "board_thruster": "#475569",
        "flame_core": "#fef08a",
        "flame_outer": "#f97316",
        "underglow": "#e11d48",
        "skid_line": "#64748b",
        "spark": "#7c3aed",
        "hud_title": "#e11d48",
        "hud_subtitle": "#7c3aed",
        "hud_accent": "#0284c7",
        "label": "#64748b",
    },
}


def cell_centre(col: int, row: int) -> tuple[float, float]:
    """Return the center pixel coordinate of grid cell (col, row)."""
    return (PAD_L + col * PITCH + CELL / 2, PAD_T + row * PITCH + CELL / 2)


def generate_drift_path(
    curve_radius: float = 18.0,
) -> tuple[str, str, str, list[tuple[int, int, float]], float, list[dict]]:
    """Build the smooth continuous drift trajectory across all 7 rows."""
    R = curve_radius
    track_w = 4.2  # Dual thruster skid offset

    start_x = PAD_L - 32.0
    start_y = PAD_T + CELL / 2

    segments = []
    x0, y0 = cell_centre(0, 0)
    segments.append(("line", (start_x, start_y), (x0, y0)))

    cell_positions = []

    for r in range(ROWS):
        is_even = r % 2 == 0
        if is_even:
            for c in range(COLS):
                cell_positions.append((c, r, cell_centre(c, r)))
            x_start, y_row = cell_centre(0, r)
            x_end, _ = cell_centre(COLS - 1, r)
            segments.append(("line", (x_start, y_row), (x_end, y_row)))

            if r < ROWS - 1:
                # Right U-turn (Clockwise)
                y_next = cell_centre(COLS - 1, r + 1)[1]
                p0 = (x_end, y_row)
                p1 = (x_end + R * 1.35, y_row)
                p2 = (x_end + R * 1.35, y_next)
                p3 = (x_end, y_next)
                segments.append(("curve", p0, p1, p2, p3, True))
        else:
            for c in range(COLS - 1, -1, -1):
                cell_positions.append((c, r, cell_centre(c, r)))
            x_start, y_row = cell_centre(COLS - 1, r)
            x_end, _ = cell_centre(0, r)
            segments.append(("line", (x_start, y_row), (x_end, y_row)))

            if r < ROWS - 1:
                # Left U-turn (Counter-Clockwise)
                y_next = cell_centre(0, r + 1)[1]
                p0 = (x_end, y_row)
                p1 = (x_end - R * 1.35, y_row)
                p2 = (x_end - R * 1.35, y_next)
                p3 = (x_end, y_next)
                segments.append(("curve", p0, p1, p2, p3, False))

    def bezier_len(p0, p1, p2, p3, steps=25):
        length = 0.0
        prev = p0
        for s in range(1, steps + 1):
            t = s / steps
            omt = 1.0 - t
            bx = (
                omt * omt * omt * p0[0]
                + 3 * omt * omt * t * p1[0]
                + 3 * omt * t * t * p2[0]
                + t * t * t * p3[0]
            )
            by = (
                omt * omt * omt * p0[1]
                + 3 * omt * omt * t * p1[1]
                + 3 * omt * t * t * p2[1]
                + t * t * t * p3[1]
            )
            length += math.hypot(bx - prev[0], by - prev[1])
            prev = (bx, by)
        return length

    seg_lens = []
    for seg in segments:
        if seg[0] == "line":
            p_a, p_b = seg[1], seg[2]
            seg_lens.append(math.hypot(p_b[0] - p_a[0], p_b[1] - p_a[1]))
        else:
            seg_lens.append(bezier_len(seg[1], seg[2], seg[3], seg[4]))

    total_len = sum(seg_lens)

    route_d_parts = []
    turns_info = []
    dist_accum = 0.0

    p_start = segments[0][1]
    route_d_parts.append(f"M {p_start[0]:.1f} {p_start[1]:.1f}")

    for idx, seg in enumerate(segments):
        d_prev = dist_accum
        d_len = seg_lens[idx]
        dist_accum += d_len

        if seg[0] == "line":
            p_b = seg[2]
            route_d_parts.append(f"L {p_b[0]:.1f} {p_b[1]:.1f}")
        else:
            p1, p2, p3 = seg[2], seg[3], seg[4]
            route_d_parts.append(
                f"C {p1[0]:.1f} {p1[1]:.1f}, {p2[0]:.1f} {p2[1]:.1f}, {p3[0]:.1f} {p3[1]:.1f}"
            )
            turns_info.append(
                {
                    "enter": d_prev / total_len,
                    "apex": (d_prev + d_len * 0.5) / total_len,
                    "exit": dist_accum / total_len,
                    "is_clockwise": seg[5],
                    "apex_pt": (
                        (seg[1][0] + seg[4][0]) / 2 + (R if seg[5] else -R),
                        (seg[1][1] + seg[4][1]) / 2,
                    ),
                }
            )

    route_d = " ".join(route_d_parts)

    cell_timings = []
    for c, r, pt in cell_positions:
        if r % 2 == 0:
            c_dist = c * PITCH
        else:
            c_dist = (COLS - 1 - c) * PITCH

        row_start_dist = seg_lens[0]
        for past_r in range(r):
            row_start_dist += (COLS - 1) * PITCH
            row_start_dist += seg_lens[1 + past_r * 2 + 1]

        dist_at_cell = row_start_dist + c_dist
        cell_timings.append((c, r, min(0.999, dist_at_cell / total_len)))

    def offset_line(p1, p2, offset):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1.0
        nx = -dy / length * offset
        ny = dx / length * offset
        return (p1[0] + nx, p1[1] + ny), (p2[0] + nx, p2[1] + ny)

    left_skid_parts = []
    right_skid_parts = []

    for seg in segments:
        if seg[0] == "line":
            p_a, p_b = seg[1], seg[2]
            l_a, l_b = offset_line(p_a, p_b, -track_w)
            r_a, r_b = offset_line(p_a, p_b, track_w)
            if not left_skid_parts:
                left_skid_parts.append(f"M {l_a[0]:.1f} {l_a[1]:.1f}")
                right_skid_parts.append(f"M {r_a[0]:.1f} {r_a[1]:.1f}")
            left_skid_parts.append(f"L {l_b[0]:.1f} {l_b[1]:.1f}")
            right_skid_parts.append(f"L {r_b[0]:.1f} {r_b[1]:.1f}")
        else:
            p0, p1, p2, p3 = seg[1], seg[2], seg[3], seg[4]
            for t_step in [0.25, 0.5, 0.75, 1.0]:
                omt = 1.0 - t_step
                bx = (
                    omt * omt * omt * p0[0]
                    + 3 * omt * omt * t_step * p1[0]
                    + 3 * omt * t_step * t_step * p2[0]
                    + t_step * t_step * t_step * p3[0]
                )
                by = (
                    omt * omt * omt * p0[1]
                    + 3 * omt * omt * t_step * p1[1]
                    + 3 * omt * t_step * t_step * p2[1]
                    + t_step * t_step * t_step * p3[1]
                )
                tx = (
                    3 * omt * omt * (p1[0] - p0[0])
                    + 6 * omt * t_step * (p2[0] - p1[0])
                    + 3 * t_step * t_step * (p3[0] - p2[0])
                )
                ty = (
                    3 * omt * omt * (p1[1] - p0[1])
                    + 6 * omt * t_step * (p2[1] - p1[1])
                    + 3 * t_step * t_step * (p3[1] - p2[1])
                )
                t_len = math.hypot(tx, ty) or 1.0
                nx = -ty / t_len
                ny = tx / t_len
                left_skid_parts.append(
                    f"L {bx - nx * track_w:.1f} {by - ny * track_w:.1f}"
                )
                right_skid_parts.append(
                    f"L {bx + nx * track_w:.1f} {by + ny * track_w:.1f}"
                )

    left_skid_d = " ".join(left_skid_parts)
    right_skid_d = " ".join(right_skid_parts)

    return (
        route_d,
        left_skid_d,
        right_skid_d,
        cell_timings,
        total_len,
        turns_info,
    )


def build_oversteer_keyframe_data(
    turns_info: list[dict],
    total_dur: float,
    walk_fraction: float,
) -> tuple[str, str]:
    """Construct synchronized rotation values and keyTimes for drift oversteer."""
    pts = [(0.0, 0.0)]

    for t_info in turns_info:
        t_enter = t_info["enter"] * walk_fraction
        t_apex = t_info["apex"] * walk_fraction
        t_exit = t_info["exit"] * walk_fraction
        is_cw = t_info["is_clockwise"]

        drift_angle = 30.0 if is_cw else -30.0
        counter_angle = -7.0 if is_cw else 7.0

        t_init = max(pts[-1][0] + 0.002, t_enter - 0.012)
        pts.append((t_init, 0.0))
        pts.append((t_apex, drift_angle))
        t_rec = min(walk_fraction, t_exit + 0.008)
        pts.append((t_rec, counter_angle))
        pts.append((min(walk_fraction, t_rec + 0.015), 0.0))

    # Final Stop: Handbrake drift slide onto newest day
    t_pre_stop = max(pts[-1][0] + 0.005, walk_fraction - 0.025)
    pts.append((t_pre_stop, 0.0))
    pts.append((walk_fraction - 0.005, 36.0))
    pts.append((walk_fraction, 34.0))  # Parked drift pose
    pts.append((0.999, 34.0))
    pts.append((1.0, 0.0))

    cleaned = [pts[0]]
    for t_val, ang in pts[1:]:
        if t_val > cleaned[-1][0]:
            cleaned.append((min(1.0, t_val), ang))

    if cleaned[-1][0] < 1.0:
        cleaned.append((1.0, cleaned[-1][1]))
    else:
        cleaned[-1] = (1.0, cleaned[-1][1])

    key_times = ";".join(f"{t:.4f}" for t, _ in cleaned)
    values = ";".join(f"{ang:.1f}" for _, ang in cleaned)
    return values, key_times


def build_cyber_cat_svg(th: dict, total_dur: float, walk_dur: float) -> str:
    """Build top-down Cyber-Cat on afterburning Rocket Drift-Board."""
    return f"""
    <!-- Glowing Neon Underglow Aura -->
    <ellipse cx="0" cy="0" rx="15" ry="9.5" fill="url(#underglow-grad)" opacity="0.85" filter="url(#cyber-glow)"/>

    <!-- Dual Rocket Afterburner Thruster Flames (Rear: x = -13) -->
    <!-- Left Thruster Flame -->
    <polygon points="-13,-4.2 -22,-4.2 -13,-4.2" fill="url(#thruster-flame-grad)" filter="url(#cyber-glow)">
      <animate attributeName="points"
        values="-13,-3.4 -21,-4.2 -13,-5.0; -13,-3.2 -25,-4.2 -13,-5.2; -13,-3.4 -21,-4.2 -13,-5.0"
        dur="0.16s" repeatCount="indefinite"/>
    </polygon>
    <!-- Right Thruster Flame -->
    <polygon points="-13,4.2 -22,4.2 -13,4.2" fill="url(#thruster-flame-grad)" filter="url(#cyber-glow)">
      <animate attributeName="points"
        values="-13,3.4 -21,4.2 -13,5.0; -13,3.2 -25,4.2 -13,5.2; -13,3.4 -21,4.2 -13,5.0"
        dur="0.16s" repeatCount="indefinite"/>
    </polygon>

    <!-- Rocket Drift-Board Chassis -->
    <!-- Rear Thruster Nozzles -->
    <rect x="-14.5" y="-5.5" width="3" height="2.6" rx="0.8" fill="{th['board_thruster']}"/>
    <rect x="-14.5" y="2.9" width="3" height="2.6" rx="0.8" fill="{th['board_thruster']}"/>

    <!-- Main Aerodynamic Board Deck -->
    <path d="M 12.5 0 C 12 -2.8 9.5 -5.8 5.5 -6 L -11.5 -6 C -12.5 -6 -13 -5 -13 -3.5 L -13 3.5 C -13 5 -12.5 6 -11.5 6 L 5.5 6 C 9.5 5.8 12 2.8 12.5 0 Z"
          fill="{th['board_deck']}" stroke="{th['board_accent']}" stroke-width="0.8"/>
    <!-- Board Neon Grip Accents -->
    <line x1="-8" y1="-4.5" x2="3" y2="-4.5" stroke="{th['hud_accent']}" stroke-width="0.7" opacity="0.8"/>
    <line x1="-8" y1="4.5" x2="3" y2="4.5" stroke="{th['hud_accent']}" stroke-width="0.7" opacity="0.8"/>

    <!-- Cyber-Cat Body (Seated forward-leaning on board) -->
    <!-- Tail (Curved, extending back between thrusters with swish animation) -->
    <g transform="rotate(-5 -8 0)">
      <path d="M -8 0 C -11 0 -13 -1 -16 -3 C -17 -3.8 -16 -5 -15 -4.5 C -13 -3.5 -11 -2.5 -8 0"
            fill="{th['cat_fur']}" stroke="{th['cat_fur_rim']}" stroke-width="0.6"/>
      <!-- Tail Neon Tip -->
      <circle cx="-16" cy="-3.5" r="1.1" fill="{th['cat_visor']}" filter="url(#cyber-glow)"/>
      <animateTransform attributeName="transform" type="rotate"
        values="-10 -8 0; 8 -8 0; -10 -8 0" dur="1.8s" repeatCount="indefinite"/>
    </g>

    <!-- Torso / Back Fur -->
    <ellipse cx="-2.5" cy="0" rx="6.5" ry="4.5" fill="{th['cat_fur']}" stroke="{th['cat_fur_rim']}" stroke-width="0.7"/>

    <!-- Front Paws (Gripping board nose / controls) -->
    <ellipse cx="6" cy="-3.5" rx="1.8" ry="1.2" fill="{th['cat_fur']}" stroke="{th['cat_fur_rim']}" stroke-width="0.5"/>
    <ellipse cx="6" cy="3.5" rx="1.8" ry="1.2" fill="{th['cat_fur']}" stroke="{th['cat_fur_rim']}" stroke-width="0.5"/>

    <!-- Cat Head -->
    <circle cx="2.5" cy="0" r="4.8" fill="{th['cat_fur']}" stroke="{th['cat_fur_rim']}" stroke-width="0.7"/>

    <!-- Pointy Cat Ears -->
    <!-- Left Ear -->
    <polygon points="1,-3.5 1,-7 4.5,-4.2" fill="{th['cat_fur']}" stroke="{th['cat_fur_rim']}" stroke-width="0.5"/>
    <polygon points="1.5,-4 1.5,-6.2 3.8,-4.5" fill="{th['cat_ear_inner']}"/>
    <!-- Right Ear -->
    <polygon points="1,3.5 1,7 4.5,4.2" fill="{th['cat_fur']}" stroke="{th['cat_fur_rim']}" stroke-width="0.5"/>
    <polygon points="1.5,4 1.5,6.2 3.8,4.5" fill="{th['cat_ear_inner']}"/>

    <!-- Glowing Cyber-Visor / HUD Goggles (Across eyes) -->
    <path d="M 4.2 -3.2 L 6.8 -2.4 L 6.8 2.4 L 4.2 3.2 Z"
          fill="{th['cat_visor']}" filter="url(#visor-glow)"/>
    <!-- Visor Scanline Sweep -->
    <line x1="4.5" y1="0" x2="6.6" y2="0" stroke="#ffffff" stroke-width="0.8" opacity="0.9"/>

    <!-- Front Energy Blasters / Headlights -->
    <circle cx="11.5" cy="-2.5" r="1.2" fill="{th['cat_visor']}" filter="url(#visor-glow)"/>
    <circle cx="11.5" cy="2.5" r="1.2" fill="{th['cat_visor']}" filter="url(#visor-glow)"/>
    <!-- Forward Light Beams -->
    <polygon points="12,-2.5 36,-10 36,10 12,2.5" fill="url(#beam-gradient)" opacity="0.38"/>

    <!-- Rear Brake / Nitro Flare on Final Stop -->
    <circle cx="-13" cy="-4.2" r="3.8" fill="{th['board_deck']}" opacity="0" filter="url(#cyber-glow)">
      <animate attributeName="opacity" values="0;0;1;1;0"
               keyTimes="0;{walk_dur / total_dur:.3f};{(walk_dur + 0.1) / total_dur:.3f};0.98;1"
               dur="{total_dur:.2f}s" repeatCount="indefinite"/>
    </circle>
    <circle cx="-13" cy="4.2" r="3.8" fill="{th['board_deck']}" opacity="0" filter="url(#cyber-glow)">
      <animate attributeName="opacity" values="0;0;1;1;0"
               keyTimes="0;{walk_dur / total_dur:.3f};{(walk_dur + 0.1) / total_dur:.3f};0.98;1"
               dur="{total_dur:.2f}s" repeatCount="indefinite"/>
    </circle>
    """


def build_svg(
    grid: list[list[int]],
    theme: str,
    duration: float,
    total: int,
) -> str:
    """Build a complete, performance-safe Cyber-Cat Drift SVG."""
    th = THEMES[theme]

    walk_dur = duration
    hold_dur = 3.5
    total_dur = walk_dur + hold_dur
    walk_fraction = walk_dur / total_dur

    route_d, left_skid_d, right_skid_d, cell_timings, total_len, turns_info = (
        generate_drift_path()
    )

    oversteer_values, oversteer_keytimes = build_oversteer_keyframe_data(
        turns_info, total_dur, walk_fraction
    )

    o: list[str] = []
    add = o.append

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" role="img" '
        f'aria-label="GitHub Contribution Graph: {total} commits, '
        f'featuring Cyber-Cat drifting on a rocket hoverboard across the matrix">'
    )
    add(
        "<title>Cyber-Cat // Neon Drift Contribution Graph</title>"
        f"<desc>{total} annual contributions brought to life by Cyber-Cat drifting an afterburning "
        "rocket hoverboard across the contribution matrix, igniting verified commits in neon Vice City hues.</desc>"
    )

    # ── SVG Defs ─────────────────────────────────────────────────────────────
    add(
        "<defs>"
        # Background gradient
        f'<linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{th["bg"]}"/>'
        f'<stop offset="100%" stop-color="{th["bg_gradient_end"]}"/>'
        "</linearGradient>"
        # HUD Title gradient
        f'<linearGradient id="title-grad" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{th["hud_title"]}"/>'
        f'<stop offset="50%" stop-color="{th["hud_subtitle"]}"/>'
        f'<stop offset="100%" stop-color="{th["hud_accent"]}"/>'
        "</linearGradient>"
        # Underglow aura gradient
        f'<radialGradient id="underglow-grad">'
        f'<stop offset="0%" stop-color="{th["underglow"]}" stop-opacity="0.85"/>'
        f'<stop offset="55%" stop-color="{th["underglow"]}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{th["underglow"]}" stop-opacity="0"/>'
        "</radialGradient>"
        # Rocket thruster flame linear gradient
        f'<linearGradient id="thruster-flame-grad" x1="100%" y1="0%" x2="0%" y2="0%">'
        f'<stop offset="0%" stop-color="{th["flame_core"]}"/>'
        f'<stop offset="35%" stop-color="{th["flame_outer"]}"/>'
        f'<stop offset="100%" stop-color="{th["flame_outer"]}" stop-opacity="0"/>'
        "</linearGradient>"
        # Forward beam gradient
        f'<linearGradient id="beam-gradient" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{th["cat_visor"]}" stop-opacity="0.5"/>'
        f'<stop offset="60%" stop-color="{th["cat_visor"]}" stop-opacity="0.15"/>'
        f'<stop offset="100%" stop-color="{th["cat_visor"]}" stop-opacity="0"/>'
        "</linearGradient>"
        # Performance-Safe Glow Filters (Only on hero sprite, never on 371 cells)
        '<filter id="cyber-glow" x="-40%" y="-40%" width="180%" height="180%">'
        '<feGaussianBlur stdDeviation="1.6" result="blur"/>'
        "<feMerge><feMergeNode in=\"blur\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        '<filter id="visor-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="1.8" result="blur"/>'
        "<feMerge><feMergeNode in=\"blur\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        # Route path for animateMotion
        f'<path id="drift-route" d="{route_d}"/>'
        "</defs>"
    )

    # ── Background Shell ─────────────────────────────────────────────────────
    add(
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg-grad)" rx="10" '
        f'stroke="{th["border"]}" stroke-width="1.2"/>'
    )

    # ── HUD Header (Cyber-Cat Branding) ──────────────────────────────────────
    add(
        f'<text x="{PAD_L:g}" y="22" font-family="system-ui, -apple-system, BlinkMacSystemFont, '
        f'\'Segoe UI\', Roboto, sans-serif" font-weight="900" font-style="italic" font-size="12" '
        f'letter-spacing="1.5" fill="url(#title-grad)">CYBER-CAT '
        f'<tspan font-weight="500" font-size="10" fill="{th["hud_subtitle"]}" letter-spacing="0.5">// DRIFT MATRIX</tspan></text>'
    )
    add(
        f'<text x="{WIDTH - PAD_R:g}" y="22" text-anchor="end" font-family="ui-monospace, SFMono-Regular, '
        f'Menlo, monospace" font-size="10" font-weight="500" fill="{th["label"]}" letter-spacing="0.8">'
        f'MadB0i · <tspan fill="{th["hud_accent"]}" font-weight="800">{total} COMMITS</tspan></text>'
    )
    add(
        f'<line x1="{PAD_L:g}" y1="28" x2="{WIDTH - PAD_R:g}" y2="28" '
        f'stroke="{th["border"]}" stroke-width="0.8" stroke-dasharray="4 3" opacity="0.6"/>'
    )

    # ── Day-of-Week Labels ───────────────────────────────────────────────────
    for r, name in enumerate(WEEKDAYS):
        if name:
            y = PAD_T + r * PITCH + CELL / 2 + 3.5
            add(
                f'<text x="{PAD_L - 8:g}" y="{y:g}" text-anchor="end" fill="{th["label"]}" '
                f'font-size="8.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
                f'font-weight="600" opacity="0.75">{name}</text>'
            )

    # ── Base Grid: Inactive Cells (0 filters for 60 FPS) ─────────────────────
    base_rects = []
    for r in range(ROWS):
        for c in range(COLS):
            x = PAD_L + c * PITCH
            y = PAD_T + r * PITCH
            base_rects.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
                f'fill="{th["grid_empty"]}"/>'
            )
    add("".join(base_rects))

    # ── Neon Plasma Skid Tracks ──────────────────────────────────────────────
    skid_dash = f"{total_len:.1f}"
    add(
        f'<g opacity="0.55">'
        f'<path d="{left_skid_d}" fill="none" stroke="{th["skid_line"]}" stroke-width="1.6" '
        f'stroke-dasharray="{skid_dash}" stroke-dashoffset="{skid_dash}">'
        f'<animate attributeName="stroke-dashoffset" values="{skid_dash};0;0;{skid_dash}" '
        f'keyTimes="0;{walk_fraction:.3f};0.98;1" dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
        f"</path>"
        f'<path d="{right_skid_d}" fill="none" stroke="{th["skid_line"]}" stroke-width="1.6" '
        f'stroke-dasharray="{skid_dash}" stroke-dashoffset="{skid_dash}">'
        f'<animate attributeName="stroke-dashoffset" values="{skid_dash};0;0;{skid_dash}" '
        f'keyTimes="0;{walk_fraction:.3f};0.98;1" dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
        f"</path>"
        f"</g>"
    )

    # ── Plasma Spark Bursts at Drift Corners ─────────────────────────────────
    spark_elements = []
    for turn in turns_info:
        ax, ay = turn["apex_pt"]
        t_spark = turn["apex"] * walk_dur
        spark_elements.append(
            f'<g transform="translate({ax:.1f} {ay:.1f})">'
            f'<circle cx="0" cy="0" r="4.5" fill="{th["spark"]}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.7;0" '
            f'begin="{t_spark:.2f}s" dur="0.8s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="scale" values="0.3;1.9" '
            f'begin="{t_spark:.2f}s" dur="0.8s" repeatCount="indefinite"/>'
            f"</circle></g>"
        )
    add("".join(spark_elements))

    # ── Dynamic Commit Cell Lighting ─────────────────────────────────────────
    lit_cells = []
    for col, row, norm_time in cell_timings:
        level = grid[row][col]
        if level <= 0:
            continue
        x = PAD_L + col * PITCH
        y = PAD_T + row * PITCH
        cell_color = th["cells"][level]

        t_ignite = norm_time * walk_fraction
        t_lit = min(1.0, t_ignite + 0.005)

        lit_cells.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
            f'fill="{cell_color}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;1;0" '
            f'keyTimes="0;{t_ignite:.4f};{t_lit:.4f};0.985;1" '
            f'dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
            f"</rect>"
        )
    add("".join(lit_cells))

    # ── Cyber-Cat Hero Sprite with Drift Oversteer ───────────────────────────
    cat_markup = build_cyber_cat_svg(th, total_dur, walk_dur)
    add(
        f'<g id="moving-cyber-cat">'
        f'<animateMotion dur="{total_dur:.2f}s" rotate="auto" fill="freeze" repeatCount="indefinite" '
        f'keyPoints="0;1;1;0" keyTimes="0;{walk_fraction:.3f};0.985;1" calcMode="linear">'
        f'<mpath xlink:href="#drift-route" href="#drift-route"/>'
        f"</animateMotion>"
        f'<g id="cyber-cat-oversteer">'
        f'<animateTransform attributeName="transform" type="rotate" '
        f'values="{oversteer_values}" keyTimes="{oversteer_keytimes}" '
        f'dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
        f"{cat_markup}"
        f"</g></g>"
    )

    add("</svg>")
    return "".join(o)


# ── Data Normalization & Fetching ────────────────────────────────────────────
def normalise(weeks: list[list[int]]) -> list[list[int]]:
    """Convert API weeks data into a clean ROWS x COLS grid (row-major)."""
    grid = [row[:ROWS] + [0] * (ROWS - len(row[:ROWS])) for row in weeks]
    if len(grid) > COLS:
        grid = grid[-COLS:]
    if not grid:
        grid = [[0] * ROWS]
    if len(grid) < COLS:
        grid = [[0] * ROWS] * (COLS - len(grid)) + grid
    return [list(row) for row in zip(*grid)]


def generate_demo_grid() -> tuple[list[list[int]], int]:
    """Generate realistic sample contribution data for offline testing."""
    random.seed(42)
    weeks = []
    total = 0
    for w in range(COLS):
        week = []
        for d in range(ROWS):
            r = random.random()
            if r < 0.28:
                lvl = 0
            elif r < 0.58:
                lvl = 1
            elif r < 0.82:
                lvl = 2
            elif r < 0.94:
                lvl = 3
            else:
                lvl = 4
            week.append(lvl)
            if lvl > 0:
                total += lvl * random.randint(1, 3)
        weeks.append(week)
    return normalise(weeks), total


def fetch(username: str, token: str) -> tuple[list[list[int]], int]:
    """Fetch user contribution calendar from GitHub GraphQL API."""
    body = json.dumps({"query": QUERY, "variables": {"login": username}}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "gen-cyber-cat",
        },
    )

    ctx = None
    try:
        ctx = ssl.create_default_context()
    except Exception:
        pass

    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            payload = json.load(resp)
    except urllib.error.URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc) and hasattr(
            ssl, "_create_unverified_context"
        ):
            ctx_unverified = ssl._create_unverified_context()
            with urllib.request.urlopen(
                req, timeout=25, context=ctx_unverified
            ) as resp:
                payload = json.load(resp)
        else:
            raise

    if payload.get("errors"):
        raise RuntimeError(f"GraphQL error: {payload['errors']}")

    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [LEVELS[d["contributionLevel"]] for d in week["contributionDays"]]
        for week in cal["weeks"]
    ]
    return normalise(weeks), cal["totalContributions"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", default="MadB0i", help="GitHub username")
    ap.add_argument("--out", default="dist", help="Output directory")
    ap.add_argument(
        "--duration",
        type=float,
        default=24.0,
        help="Drift travel duration in seconds",
    )
    ap.add_argument("--demo", action="store_true", help="Force demo sample mode")
    ap.add_argument("--fixture", help="Path to cached calendar JSON")
    args = ap.parse_args()

    grid = None
    total = 0

    if args.demo:
        print("[Demo Mode] Generating realistic sample contribution data...")
        grid, total = generate_demo_grid()
    elif args.fixture:
        with open(args.fixture, encoding="utf-8-sig") as fh:
            cal = json.load(fh)
        weeks = [
            [LEVELS[d["contributionLevel"]] for d in week["contributionDays"]]
            for week in cal["weeks"]
        ]
        grid, total = normalise(weeks), cal.get("totalContributions", 0)
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            try:
                print(f"Fetching live GitHub contributions for @{args.user}...")
                grid, total = fetch(args.user, token)
            except Exception as exc:
                print(
                    f"Warning: Failed to fetch live data ({exc}). Falling back to demo mode."
                )
                grid, total = generate_demo_grid()
        else:
            print(
                "Notice: GITHUB_TOKEN not set. Running in automatic demo fallback mode."
            )
            grid, total = generate_demo_grid()

    os.makedirs(args.out, exist_ok=True)

    outputs = (
        ("dark", "github-contribution-grid-cybercat-dark.svg"),
        ("light", "github-contribution-grid-cybercat.svg"),
    )

    for theme, filename in outputs:
        svg = build_svg(grid, theme, args.duration, total)

        try:
            minidom.parseString(svg.encode("utf-8"))
        except Exception as exc:
            print(f"ERROR: XML parsing failed for {filename}: {exc}")
            return 1

        path = os.path.join(args.out, filename)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)

        file_size_kb = len(svg) / 1024
        print(
            f"✓ {path:<46} {file_size_kb:>6.1f} KiB  "
            f"walk={args.duration:g}s  theme={theme:<5}  total={total}"
        )

    print("\nCyber-Cat Rocket Drift Contribution Graph generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
