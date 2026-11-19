#!/usr/bin/env python3
"""Generate an animated GTA 6 / Vice City Drift contribution graph for GitHub.

Fetches the GitHub contribution calendar over the GraphQL API (with realistic
offline demo fallback), then writes two high-performance animated SVGs
(light + dark) where a top-down retro-modern sports car drifts across the grid,
laying down glowing neon tire trails and lighting up commit squares in neon colors.

Stdlib only: zero external dependencies.
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
PAD_T = 38  # Extra space for sleek GTA HUD header
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
        "bg": "#090514",
        "bg_gradient_end": "#130924",
        "border": "#2c134d",
        "grid_empty": "#160d29",
        "cells": [
            "#160d29",  # Level 0 (inactive asphalt)
            "#431d75",  # Level 1 (dim purple neon)
            "#8b2fc9",  # Level 2 (vivid neon purple)
            "#ff2a85",  # Level 3 (GTA 6 hot pink)
            "#00f0ff",  # Level 4 (Vice City electric cyan)
        ],
        "car_body": "#ff2a85",
        "car_accent": "#c026d3",
        "car_roof": "#1e0e38",
        "car_glass": "#0a0314",
        "car_spoiler": "#f43f5e",
        "headlight": "#e0f2fe",
        "headlight_beam": "#38bdf8",
        "taillight": "#ef4444",
        "underglow": "#00f0ff",
        "skid_line": "#a855f7",
        "smoke": "#c084fc",
        "hud_title": "#ff2a85",
        "hud_subtitle": "#a78bfa",
        "hud_accent": "#00f0ff",
        "label": "#8b7ca6",
        "glow": "#ff2a85",
    },
    "light": {
        "bg": "#f9f8ff",
        "bg_gradient_end": "#ede9fe",
        "border": "#ddd6fe",
        "grid_empty": "#e5e0f7",
        "cells": [
            "#e5e0f7",  # Level 0
            "#c084fc",  # Level 1
            "#9333ea",  # Level 2
            "#e11d48",  # Level 3 (Miami crimson)
            "#0284c7",  # Level 4 (Ocean blue)
        ],
        "car_body": "#e11d48",
        "car_accent": "#be123c",
        "car_roof": "#334155",
        "car_glass": "#0f172a",
        "car_spoiler": "#991b1b",
        "headlight": "#fef08a",
        "headlight_beam": "#fde047",
        "taillight": "#dc2626",
        "underglow": "#f43f5e",
        "skid_line": "#475569",
        "smoke": "#94a3b8",
        "hud_title": "#e11d48",
        "hud_subtitle": "#7c3aed",
        "hud_accent": "#0284c7",
        "label": "#64748b",
        "glow": "#e11d48",
    },
}


def cell_centre(col: int, row: int) -> tuple[float, float]:
    """Return the center pixel coordinate of grid cell (col, row)."""
    return (PAD_L + col * PITCH + CELL / 2, PAD_T + row * PITCH + CELL / 2)


def generate_drift_path(
    curve_radius: float = 18.0,
) -> tuple[str, str, str, list[tuple[int, int, float]], float, list[dict]]:
    """Build the smooth continuous drift trajectory across all 7 rows.

    Returns:
        route_d: SVG path string for car centerline
        left_skid_d: SVG path for left tire marks
        right_skid_d: SVG path for right tire marks
        cell_timings: list of (col, row, normalized_time)
        total_length: approximate arc length in pixels
        turns_info: list of turn metadata (entry, apex, exit normalized times, direction)
    """
    R = curve_radius
    track_w = 4.0  # Half wheel track width for dual tire skids

    # Start off-canvas to the left of row 0
    start_x = PAD_L - 30.0
    start_y = PAD_T + CELL / 2

    # Segments list: each item is ('line', x1, y1, x2, y2) or ('curve', p0, p1, p2, p3, is_clockwise)
    segments = []

    # Lead-in line to row 0 start
    x0, y0 = cell_centre(0, 0)
    segments.append(("line", (start_x, start_y), (x0, y0)))

    cell_positions = []

    for r in range(ROWS):
        is_even = r % 2 == 0
        if is_even:
            # Traveling Left to Right (row r)
            for c in range(COLS):
                cell_positions.append((c, r, cell_centre(c, r)))
            x_start, y_row = cell_centre(0, r)
            x_end, _ = cell_centre(COLS - 1, r)
            segments.append(("line", (x_start, y_row), (x_end, y_row)))

            if r < ROWS - 1:
                # Right U-Turn down to r + 1 (Clockwise)
                y_next = cell_centre(COLS - 1, r + 1)[1]
                p0 = (x_end, y_row)
                p1 = (x_end + R * 1.35, y_row)
                p2 = (x_end + R * 1.35, y_next)
                p3 = (x_end, y_next)
                segments.append(("curve", p0, p1, p2, p3, True))
        else:
            # Traveling Right to Left (row r)
            for c in range(COLS - 1, -1, -1):
                cell_positions.append((c, r, cell_centre(c, r)))
            x_start, y_row = cell_centre(COLS - 1, r)
            x_end, _ = cell_centre(0, r)
            segments.append(("line", (x_start, y_row), (x_end, y_row)))

            if r < ROWS - 1:
                # Left U-Turn down to r + 1 (Counter-Clockwise)
                y_next = cell_centre(0, r + 1)[1]
                p0 = (x_end, y_row)
                p1 = (x_end - R * 1.35, y_row)
                p2 = (x_end - R * 1.35, y_next)
                p3 = (x_end, y_next)
                segments.append(("curve", p0, p1, p2, p3, False))

    # Calculate arc lengths of all segments
    def bezier_len(p0, p1, p2, p3, steps=30):
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

    # Build SVG path string for route
    route_d_parts = []
    turns_info = []
    dist_accum = 0.0

    # First segment: start point
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

    # Calculate normalized time for each cell
    # Match cell coordinates along line segments
    cell_timings = []
    for c, r, pt in cell_positions:
        # Distance along path up to row r, col c
        # Row 0 start has dist seg_lens[0]
        # Each row r has a straight line segment index
        # We can compute exact distance along path
        if r % 2 == 0:
            c_dist = c * PITCH
        else:
            c_dist = (COLS - 1 - c) * PITCH

        # Cumulative distance before row r
        row_start_dist = seg_lens[0]
        for past_r in range(r):
            # Past row line + past curve
            row_start_dist += (COLS - 1) * PITCH
            row_start_dist += seg_lens[1 + past_r * 2 + 1]

        dist_at_cell = row_start_dist + c_dist
        cell_timings.append((c, r, min(0.999, dist_at_cell / total_len)))

    # Dual tire skid paths: offset path parallel to centerline
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
            # Curve: sample offsets along Bezier
            p0, p1, p2, p3 = seg[1], seg[2], seg[3], seg[4]
            # Simple curve approximation for skids
            is_cw = seg[5]
            # For clockwise: left is outer (+R), right is inner (-R)
            # Use radial offset
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
                # Tangent
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
    """Construct synchronized rotation values and keyTimes for drift oversteer.

    During turns, the rear kicks out:
      - Clockwise turns (Right edge): +28° rotation
      - Counter-Clockwise turns (Left edge): -28° rotation
      - Straights: 0°
      - Turn exit: brief counter-steer flick (-6° / +6°) then 0°
      - Final stop: aggressive 34° handbrake drift halt
    """
    # Build timeline points: (normalized_time_in_cycle, angle)
    pts = [(0.0, 0.0)]

    for t_info in turns_info:
        t_enter = t_info["enter"] * walk_fraction
        t_apex = t_info["apex"] * walk_fraction
        t_exit = t_info["exit"] * walk_fraction
        is_cw = t_info["is_clockwise"]

        drift_angle = 28.0 if is_cw else -28.0
        counter_angle = -6.0 if is_cw else 6.0

        # Initiation slightly before apex
        t_init = max(pts[-1][0] + 0.002, t_enter - 0.012)
        pts.append((t_init, 0.0))
        pts.append((t_apex, drift_angle))
        # Exit and counter-steer recovery
        t_rec = min(walk_fraction, t_exit + 0.008)
        pts.append((t_rec, counter_angle))
        pts.append((min(walk_fraction, t_rec + 0.015), 0.0))

    # Final Stop: Handbrake slide at the end of the walk
    t_pre_stop = max(pts[-1][0] + 0.005, walk_fraction - 0.025)
    pts.append((t_pre_stop, 0.0))
    pts.append((walk_fraction - 0.005, 34.0))  # Aggressive final slide
    pts.append((walk_fraction, 32.0))  # Settle into final parked angle
    pts.append((0.999, 32.0))  # Hold parked angle until loop reset
    pts.append((1.0, 0.0))

    # Deduplicate and sort strictly
    cleaned = [pts[0]]
    for t_val, ang in pts[1:]:
        if t_val > cleaned[-1][0]:
            cleaned.append((min(1.0, t_val), ang))

    # Ensure last keyTime is 1.0
    if cleaned[-1][0] < 1.0:
        cleaned.append((1.0, cleaned[-1][1]))
    else:
        cleaned[-1] = (1.0, cleaned[-1][1])

    key_times = ";".join(f"{t:.4f}" for t, _ in cleaned)
    values = ";".join(f"{ang:.1f}" for _, ang in cleaned)
    return values, key_times


def build_car_svg(th: dict, total_dur: float, walk_dur: float) -> str:
    """Return top-down sports car SVG markup with neon underglow and lights."""
    # Car is oriented pointing to +X (length 24px, width 13px)
    return f"""
    <!-- Underglow -->
    <ellipse cx="0" cy="0" rx="14" ry="8.5" fill="url(#underglow-grad)" opacity="0.85" filter="url(#car-glow)"/>

    <!-- Headlight Beams (Forward cone) -->
    <polygon points="12,-4 38,-12 38,12 12,4" fill="url(#headlight-beam-grad)" opacity="0.45"/>

    <!-- Wheels (4 tires) -->
    <rect x="5.5" y="-6.6" width="5.2" height="2.2" rx="1" fill="#0f091c"/>
    <rect x="5.5" y="4.4" width="5.2" height="2.2" rx="1" fill="#0f091c"/>
    <rect x="-8.5" y="-6.6" width="5.2" height="2.4" rx="1" fill="#0f091c"/>
    <rect x="-8.5" y="4.2" width="5.2" height="2.4" rx="1" fill="#0f091c"/>

    <!-- Main Aerodynamic Body -->
    <path d="M 12.2 0 C 12 -2.5 9.5 -5.2 6.5 -5.4 L -9 -5.4 C -10.8 -5.4 -11.8 -4.2 -11.8 -2.8 L -11.8 2.8 C -11.8 4.2 -10.8 5.4 -9 5.4 L 6.5 5.4 C 9.5 5.2 12 2.5 12.2 0 Z"
          fill="{th['car_body']}" stroke="{th['car_accent']}" stroke-width="0.8"/>

    <!-- Hood Vents -->
    <polygon points="4.5,-2 7.5,-1.2 7.5,1.2 4.5,2" fill="{th['car_accent']}" opacity="0.65"/>

    <!-- Cockpit & Windshield -->
    <path d="M 2.8 -3.8 L 4.8 -3 L 4.8 3 L 2.8 3.8 L -4.2 3.8 L -5.2 2.8 L -5.2 -2.8 L -4.2 -3.8 Z"
          fill="{th['car_glass']}"/>
    <!-- Glass Sun Reflection -->
    <line x1="3.8" y1="-2" x2="-2.5" y2="2.5" stroke="#ffffff" stroke-width="0.6" opacity="0.4"/>

    <!-- Roof -->
    <rect x="-3" y="-2.8" width="5" height="5.6" rx="1" fill="{th['car_roof']}"/>

    <!-- Rear Spoiler -->
    <rect x="-11.8" y="-6.2" width="1.8" height="12.4" rx="0.8" fill="{th['car_spoiler']}"/>
    <rect x="-10.5" y="-3.2" width="1.5" height="1" fill="#0f091c"/>
    <rect x="-10.5" y="2.2" width="1.5" height="1" fill="#0f091c"/>

    <!-- Front LED Headlights -->
    <polygon points="11,-4.6 12.2,-3.4 10.8,-3.2 9.8,-4.2" fill="{th['headlight']}" filter="url(#headlight-glow)"/>
    <polygon points="11,4.6 12.2,3.4 10.8,3.2 9.8,4.2" fill="{th['headlight']}" filter="url(#headlight-glow)"/>

    <!-- Rear LED Taillight Bar -->
    <rect x="-11.8" y="-4.6" width="1.2" height="9.2" rx="0.6" fill="{th['taillight']}" filter="url(#taillight-glow)"/>

    <!-- Brake Lights Glow on final stop -->
    <circle cx="-11.8" cy="-3.5" r="3.5" fill="{th['taillight']}" opacity="0" filter="url(#taillight-glow)">
      <animate attributeName="opacity" values="0;0;1;1;0"
               keyTimes="0;{walk_dur / total_dur:.3f};{(walk_dur + 0.1) / total_dur:.3f};0.98;1"
               dur="{total_dur:.2f}s" repeatCount="indefinite"/>
    </circle>
    <circle cx="-11.8" cy="3.5" r="3.5" fill="{th['taillight']}" opacity="0" filter="url(#taillight-glow)">
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
    """Build a complete, performance-safe GTA 6 drift animated SVG."""
    th = THEMES[theme]

    # Timing
    walk_dur = duration  # Duration of the car traversal across the grid
    hold_dur = 3.5  # Time car rests in final drift stop before loop reset
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
        f'aria-label="GitHub Contribution Graph: {total} commits in the last year, '
        f'visualized as a GTA 6 style car drifting across the calendar">'
    )
    add(
        "<title>Vice City Drift // GitHub Contribution Graph</title>"
        f"<desc>{total} contributions across 52 weeks, brought to life by a retro sports car "
        "drifting across the commit grid, lighting up activity in neon Vice City hues.</desc>"
    )

    # ── SVG Defs: Gradients, Paths & Lightweight Glow Filters ────────────────
    add(
        "<defs>"
        # Background gradient
        f'<linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{th["bg"]}"/>'
        f'<stop offset="100%" stop-color="{th["bg_gradient_end"]}"/>'
        "</linearGradient>"
        # HUD Title GTA gradient
        f'<linearGradient id="title-grad" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{th["hud_title"]}"/>'
        f'<stop offset="60%" stop-color="{th["hud_subtitle"]}"/>'
        f'<stop offset="100%" stop-color="{th["hud_accent"]}"/>'
        "</linearGradient>"
        # Underglow radial gradient
        f'<radialGradient id="underglow-grad">'
        f'<stop offset="0%" stop-color="{th["underglow"]}" stop-opacity="0.8"/>'
        f'<stop offset="60%" stop-color="{th["underglow"]}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{th["underglow"]}" stop-opacity="0"/>'
        "</radialGradient>"
        # Headlight beam linear gradient
        f'<linearGradient id="headlight-beam-grad" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{th["headlight_beam"]}" stop-opacity="0.55"/>'
        f'<stop offset="50%" stop-color="{th["headlight_beam"]}" stop-opacity="0.2"/>'
        f'<stop offset="100%" stop-color="{th["headlight_beam"]}" stop-opacity="0"/>'
        "</linearGradient>"
        # Optimized Selective Filters (ONLY used on car and lights, never on cells)
        '<filter id="car-glow" x="-40%" y="-40%" width="180%" height="180%">'
        '<feGaussianBlur stdDeviation="1.5" result="blur"/>'
        "<feMerge><feMergeNode in=\"blur\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        '<filter id="headlight-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="1.8" result="blur"/>'
        "<feMerge><feMergeNode in=\"blur\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        '<filter id="taillight-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2.0" result="blur"/>'
        "<feMerge><feMergeNode in=\"blur\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        # Trajectory Path for animateMotion
        f'<path id="drift-route" d="{route_d}"/>'
        "</defs>"
    )

    # ── Background Shell ─────────────────────────────────────────────────────
    add(
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg-grad)" rx="10" '
        f'stroke="{th["border"]}" stroke-width="1.2"/>'
    )

    # ── HUD Header (GTA 6 / Vice City Aesthetic) ─────────────────────────────
    # Title Left
    add(
        f'<text x="{PAD_L:g}" y="22" font-family="system-ui, -apple-system, BlinkMacSystemFont, '
        f'\'Segoe UI\', Roboto, sans-serif" font-weight="900" font-style="italic" font-size="12" '
        f'letter-spacing="1.5" fill="url(#title-grad)">VICE CITY DRIFT '
        f'<tspan font-weight="400" font-size="10" fill="{th["hud_subtitle"]}" letter-spacing="0.5">// COMMIT GRAPH</tspan></text>'
    )
    # Total Commits Stat Right
    add(
        f'<text x="{WIDTH - PAD_R:g}" y="22" text-anchor="end" font-family="ui-monospace, SFMono-Regular, '
        f'Menlo, monospace" font-size="10" font-weight="500" fill="{th["label"]}" letter-spacing="0.8">'
        f'ANNUAL COMMITS: <tspan fill="{th["hud_accent"]}" font-weight="800">{total}</tspan></text>'
    )
    # Subtle glowing divider line under header
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

    # ── Base Grid: Inactive / Empty Asphalt Cells ────────────────────────────
    # Render static background cells with no filters for instant 60 FPS
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

    # ── Neon Skid Tracks (Drawn dynamically as car drives) ───────────────────
    # Both tire tracks unwind using stroke-dashoffset matching the walk progress
    skid_dash = f"{total_len:.1f}"
    add(
        f'<g opacity="0.45">'
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

    # ── Tire Smoke Puffs at Drift Corners ────────────────────────────────────
    smoke_elements = []
    for turn in turns_info:
        ax, ay = turn["apex_pt"]
        # Trigger smoke when car hits turn apex
        t_smoke = turn["apex"] * walk_dur
        smoke_elements.append(
            f'<g transform="translate({ax:.1f} {ay:.1f})">'
            f'<circle cx="0" cy="0" r="4.5" fill="{th["smoke"]}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.55;0" '
            f'begin="{t_smoke:.2f}s" dur="0.9s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="scale" values="0.4;1.8" '
            f'begin="{t_smoke:.2f}s" dur="0.9s" repeatCount="indefinite"/>'
            f"</circle></g>"
        )
    add("".join(smoke_elements))

    # ── Dynamic Commit Cell Lighting ─────────────────────────────────────────
    # Only render lit overlays for cells that actually have contributions (> 0)
    lit_cells = []
    for col, row, norm_time in cell_timings:
        level = grid[row][col]
        if level <= 0:
            continue
        x = PAD_L + col * PITCH
        y = PAD_T + row * PITCH
        cell_color = th["cells"][level]

        # Timing: cell ignites as car reaches it, stays lit through hold, resets at cycle end
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

    # ── Drifting Sports Car ──────────────────────────────────────────────────
    # Outer group follows route tangent via animateMotion rotate="auto"
    # Inner group applies dynamic oversteer rotation to kick the tail out realistically
    car_markup = build_car_svg(th, total_dur, walk_dur)
    add(
        f'<g id="moving-car">'
        f'<animateMotion dur="{total_dur:.2f}s" rotate="auto" fill="freeze" repeatCount="indefinite" '
        f'keyPoints="0;1;1;0" keyTimes="0;{walk_fraction:.3f};0.985;1" calcMode="linear">'
        f'<mpath xlink:href="#drift-route" href="#drift-route"/>'
        f"</animateMotion>"
        f'<g id="car-chassis-oversteer">'
        f'<animateTransform attributeName="transform" type="rotate" '
        f'values="{oversteer_values}" keyTimes="{oversteer_keytimes}" '
        f'dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
        f"{car_markup}"
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
    random.seed(42)  # Deterministic sample
    weeks = []
    total = 0
    for w in range(COLS):
        week = []
        for d in range(ROWS):
            # Realistic commit probability distribution
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
            "User-Agent": "gen-gta-drift",
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
        ("dark", "github-contribution-grid-car-dark.svg"),
        ("light", "github-contribution-grid-car.svg"),
    )

    for theme, filename in outputs:
        svg = build_svg(grid, theme, args.duration, total)

        # Strict XML syntax validation
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
            f"✓ {path:<42} {file_size_kb:>6.1f} KiB  "
            f"walk={args.duration:g}s  theme={theme:<5}  total={total}"
        )

    print("\nGTA 6 / Vice City Drift Contribution Graph generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
