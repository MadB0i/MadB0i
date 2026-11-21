#!/usr/bin/env python3
"""Generate an animated Tactical Security Drone (KAVACH Sentinel) contribution graph.

Visualizes the GitHub contribution grid as a high-tech Zero-Trust Security Matrix.
A tactical cyber-sentinel drone sweeps across the grid with high-speed quad rotors,
a holographic scanner cone and targeting crosshair, authorizing commit cells
with a crisp verification flash and peak-node radar pings.

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
PAD_L = 52
PAD_T = 44
PAD_R = 36
PAD_B = 34
GRID_W = COLS * PITCH - GAP  # 792px
GRID_H = ROWS * PITCH - GAP  # 102px
WIDTH = PAD_L + GRID_W + PAD_R  # 880px
HEIGHT = PAD_T + GRID_H + PAD_B  # 180px

WEEKDAYS = ["", "Mon", "", "Wed", "", "Fri", ""]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_COLS = [0, 5, 9, 14, 18, 22, 27, 31, 36, 40, 44, 49]

# ── Theme Palettes ───────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg": "#070512",
        "bg_gradient_end": "#110b24",
        "border": "#28174a",
        "grid_empty": "#130d24",
        "unverified_fill": "#1b1333",
        "unverified_stroke": "#382261",
        "cells": [
            "#130d24",  # Level 0 (Dormant substrate)
            "#3b1c6e",  # Level 1 (Policy checked - deep violet)
            "#7c3aed",  # Level 2 (Zero-trust verified - vivid purple)
            "#06b6d4",  # Level 3 (Guarded execution - cyan blue)
            "#00f0ff",  # Level 4 (Cryptographically sealed - peak electric cyan)
        ],
        "drone_body": "#0e091d",
        "drone_edge": "#a78bfa",
        "drone_arm": "#3b2269",
        "rotor_ring": "#00f0ff",
        "rotor_blade": "#38bdf8",
        "eye_core": "#00f0ff",
        "radar_cone": "#00f0ff",
        "reticle": "#a78bfa",
        "trace_line": "#8b5cf6",
        "pulse_ring": "#00f0ff",
        "hud_title": "#00f0ff",
        "hud_subtitle": "#a78bfa",
        "hud_accent": "#10b981",
        "label": "#7e6f99",
        "footer_text": "#655684",
        "footer_border": "#22163b",
    },
    "light": {
        "bg": "#f8f9ff",
        "bg_gradient_end": "#ede9fe",
        "border": "#ddd6fe",
        "grid_empty": "#ede9fe",
        "unverified_fill": "#dfd7fa",
        "unverified_stroke": "#c4b5fd",
        "cells": [
            "#ede9fe",  # Level 0
            "#c084fc",  # Level 1
            "#8b5cf6",  # Level 2
            "#0284c7",  # Level 3
            "#059669",  # Level 4
        ],
        "drone_body": "#1e1b4b",
        "drone_edge": "#6366f1",
        "drone_arm": "#4338ca",
        "rotor_ring": "#0284c7",
        "rotor_blade": "#38bdf8",
        "eye_core": "#0284c7",
        "radar_cone": "#38bdf8",
        "reticle": "#6366f1",
        "trace_line": "#818cf8",
        "pulse_ring": "#0284c7",
        "hud_title": "#4338ca",
        "hud_subtitle": "#6366f1",
        "hud_accent": "#059669",
        "label": "#64748b",
        "footer_text": "#748398",
        "footer_border": "#e2e8f0",
    },
}


def cell_centre(col: int, row: int) -> tuple[float, float]:
    """Return the center pixel coordinate of grid cell (col, row)."""
    return (PAD_L + col * PITCH + CELL / 2, PAD_T + row * PITCH + CELL / 2)


def generate_flight_path(
    curve_radius: float = 14.0,
) -> tuple[str, float, list[tuple[int, int, float]], list[dict]]:
    """Build the smooth continuous sentinel patrol trajectory across all 7 rows.

    Maintains safe horizontal clearance (>16px) from weekday text labels on the left edge.
    """
    R = curve_radius
    x0, y0 = cell_centre(0, 0)
    # Start point is aligned with turn apex, safely to the right of weekday labels
    start_x = x0 - 16.0
    start_y = y0

    segments = []
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
                # Right sweeping turn down to r + 1 (Clockwise)
                y_next = cell_centre(COLS - 1, r + 1)[1]
                p0 = (x_end, y_row)
                p1 = (x_end + R * 1.2, y_row)
                p2 = (x_end + R * 1.2, y_next)
                p3 = (x_end, y_next)
                segments.append(("curve", p0, p1, p2, p3, True))
        else:
            for c in range(COLS - 1, -1, -1):
                cell_positions.append((c, r, cell_centre(c, r)))
            x_start, y_row = cell_centre(COLS - 1, r)
            x_end, _ = cell_centre(0, r)
            segments.append(("line", (x_start, y_row), (x_end, y_row)))

            if r < ROWS - 1:
                # Left sweeping turn down to r + 1 (Counter-Clockwise)
                y_next = cell_centre(0, r + 1)[1]
                p0 = (x_end, y_row)
                p1 = (x_end - R * 1.2, y_row)
                p2 = (x_end - R * 1.2, y_next)
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
                }
            )

    route_d = " ".join(route_d_parts)

    cell_timings = []
    for c, r, _pt in cell_positions:
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

    return route_d, total_len, cell_timings, turns_info


def build_drone_svg(th: dict, total_dur: float, walk_dur: float) -> str:
    """Build the high-tech Tactical Security Sentinel Drone SVG markup.

    Features spinning 4-rotor quadcopter blades, holographic scanner cone,
    dual-ring rotating reticles, and cryptographic central sensor eye.
    """
    walk_fraction = walk_dur / total_dur
    t_pulse_peak = min(0.985, walk_fraction + 0.02)
    t_pulse_end = min(0.985, walk_fraction + 0.06)

    return f"""
    <!-- Holographic Scanner Aura Zone -->
    <circle cx="0" cy="0" r="14" fill="url(#scan-zone-grad)" opacity="0.65" filter="url(#sentinel-glow)"/>

    <!-- Forward Conical Radar Sweep -->
    <polygon points="0,0 30,-11 30,11" fill="url(#radar-beam-grad)" opacity="0.48"/>

    <!-- Tactical Targeting Reticle Crosshair (Outer & Inner Counter-Rotating) -->
    <g opacity="0.85">
      <!-- Outer Reticle Ring -->
      <circle cx="0" cy="0" r="11" fill="none" stroke="{th['reticle']}" stroke-width="0.75" stroke-dasharray="3.5 2.5">
        <animateTransform attributeName="transform" type="rotate" values="0; 360" dur="6s" repeatCount="indefinite"/>
      </circle>
      <!-- Inner Reticle Ring (Counter-Clockwise) -->
      <circle cx="0" cy="0" r="6.5" fill="none" stroke="{th['eye_core']}" stroke-width="0.6" stroke-dasharray="2 2" opacity="0.75">
        <animateTransform attributeName="transform" type="rotate" values="360; 0" dur="4s" repeatCount="indefinite"/>
      </circle>
      <!-- Crosshair Tick Lines -->
      <line x1="-14" y1="0" x2="-7" y2="0" stroke="{th['reticle']}" stroke-width="0.8"/>
      <line x1="7" y1="0" x2="14" y2="0" stroke="{th['reticle']}" stroke-width="0.8"/>
      <line x1="0" y1="-14" x2="0" y2="-7" stroke="{th['reticle']}" stroke-width="0.8"/>
      <line x1="0" y1="7" x2="0" y2="14" stroke="{th['reticle']}" stroke-width="0.8"/>
    </g>

    <!-- Carbon Fiber X-Frame Arms -->
    <line x1="-8.5" y1="-8.5" x2="8.5" y2="8.5" stroke="{th['drone_arm']}" stroke-width="2.6" stroke-linecap="round"/>
    <line x1="-8.5" y1="8.5" x2="8.5" y2="-8.5" stroke="{th['drone_arm']}" stroke-width="2.6" stroke-linecap="round"/>

    <!-- 4 High-Speed Quad-Rotor Thruster Rings with Animated Spinning Blades -->
    <!-- Top-Left Rotor Hub (CCW Spin) -->
    <circle cx="-8.5" cy="-8.5" r="4.2" fill="none" stroke="{th['rotor_ring']}" stroke-width="1.0" opacity="0.85" filter="url(#sentinel-glow)"/>
    <circle cx="-8.5" cy="-8.5" r="3.8" fill="{th['rotor_blade']}" opacity="0.15"/>
    <g transform="translate(-8.5, -8.5)">
      <line x1="-3.8" y1="0" x2="3.8" y2="0" stroke="{th['rotor_blade']}" stroke-width="1.1" stroke-linecap="round" opacity="0.85">
        <animateTransform attributeName="transform" type="rotate" values="0; -360" dur="0.14s" repeatCount="indefinite"/>
      </line>
      <circle cx="0" cy="0" r="1.3" fill="{th['drone_body']}"/>
    </g>

    <!-- Top-Right Rotor Hub (CW Spin) -->
    <circle cx="8.5" cy="-8.5" r="4.2" fill="none" stroke="{th['rotor_ring']}" stroke-width="1.0" opacity="0.85" filter="url(#sentinel-glow)"/>
    <circle cx="8.5" cy="-8.5" r="3.8" fill="{th['rotor_blade']}" opacity="0.15"/>
    <g transform="translate(8.5, -8.5)">
      <line x1="-3.8" y1="0" x2="3.8" y2="0" stroke="{th['rotor_blade']}" stroke-width="1.1" stroke-linecap="round" opacity="0.85">
        <animateTransform attributeName="transform" type="rotate" values="0; 360" dur="0.14s" repeatCount="indefinite"/>
      </line>
      <circle cx="0" cy="0" r="1.3" fill="{th['drone_body']}"/>
    </g>

    <!-- Bottom-Left Rotor Hub (CW Spin) -->
    <circle cx="-8.5" cy="8.5" r="4.2" fill="none" stroke="{th['rotor_ring']}" stroke-width="1.0" opacity="0.85" filter="url(#sentinel-glow)"/>
    <circle cx="-8.5" cy="8.5" r="3.8" fill="{th['rotor_blade']}" opacity="0.15"/>
    <g transform="translate(-8.5, 8.5)">
      <line x1="-3.8" y1="0" x2="3.8" y2="0" stroke="{th['rotor_blade']}" stroke-width="1.1" stroke-linecap="round" opacity="0.85">
        <animateTransform attributeName="transform" type="rotate" values="0; 360" dur="0.14s" repeatCount="indefinite"/>
      </line>
      <circle cx="0" cy="0" r="1.3" fill="{th['drone_body']}"/>
    </g>

    <!-- Bottom-Right Rotor Hub (CCW Spin) -->
    <circle cx="8.5" cy="8.5" r="4.2" fill="none" stroke="{th['rotor_ring']}" stroke-width="1.0" opacity="0.85" filter="url(#sentinel-glow)"/>
    <circle cx="8.5" cy="8.5" r="3.8" fill="{th['rotor_blade']}" opacity="0.15"/>
    <g transform="translate(8.5, 8.5)">
      <line x1="-3.8" y1="0" x2="3.8" y2="0" stroke="{th['rotor_blade']}" stroke-width="1.1" stroke-linecap="round" opacity="0.85">
        <animateTransform attributeName="transform" type="rotate" values="0; -360" dur="0.14s" repeatCount="indefinite"/>
      </line>
      <circle cx="0" cy="0" r="1.3" fill="{th['drone_body']}"/>
    </g>

    <!-- Central Armored Tactical Pod / Fuselage -->
    <polygon points="0,-6.5 5.5,-3 5.5,3 0,6.5 -5.5,3 -5.5,-3"
             fill="{th['drone_body']}" stroke="{th['drone_edge']}" stroke-width="0.9"/>

    <!-- Forward Optical Emitters -->
    <circle cx="6.5" cy="-2.5" r="0.9" fill="{th['eye_core']}"/>
    <circle cx="6.5" cy="2.5" r="0.9" fill="{th['eye_core']}"/>

    <!-- Central Zero-Trust Cryptographic Sensor Eye -->
    <circle cx="0" cy="0" r="3.2" fill="{th['eye_core']}" filter="url(#eye-glow)">
      <animate attributeName="r" values="3.0; 3.6; 3.0" dur="1.4s" repeatCount="indefinite"/>
    </circle>
    <circle cx="0" cy="0" r="1.4" fill="#ffffff"/>

    <!-- Final Verification Pulse: Expands across final day during hold period -->
    <circle cx="0" cy="0" r="12" fill="none" stroke="{th['eye_core']}" stroke-width="1.2" opacity="0">
      <animate attributeName="opacity" values="0; 0; 0.9; 0; 0"
               keyTimes="0; {walk_fraction:.4f}; {t_pulse_peak:.4f}; {t_pulse_end:.4f}; 1"
               dur="{total_dur:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="r" values="12; 12; 26; 32; 32"
               keyTimes="0; {walk_fraction:.4f}; {t_pulse_peak:.4f}; {t_pulse_end:.4f}; 1"
               dur="{total_dur:.2f}s" repeatCount="indefinite"/>
    </circle>
    """


def build_svg(
    grid: list[list[int]],
    theme: str,
    duration: float,
    total: int,
) -> str:
    """Build a complete, performance-safe KAVACH Sentinel Drone SVG."""
    th = THEMES[theme]

    walk_dur = duration
    hold_dur = 3.5
    total_dur = walk_dur + hold_dur
    walk_fraction = walk_dur / total_dur

    route_d, total_len, cell_timings, _turns_info = generate_flight_path()

    o: list[str] = []
    add = o.append

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" role="img" '
        f'aria-label="GitHub Contribution Graph: {total} commits, '
        f'scanned and authorized by the KAVACH Tactical Security Sentinel">'
    )
    add(
        "<title>KAVACH Sentinel // Zero-Trust Security Audit Matrix</title>"
        f"<desc>{total} annual contributions monitored and cryptographically verified "
        "by an autonomous security drone scanning across the zero-trust commit matrix.</desc>"
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
        f'<stop offset="60%" stop-color="{th["hud_subtitle"]}"/>'
        f'<stop offset="100%" stop-color="{th["hud_accent"]}"/>'
        "</linearGradient>"
        # Scanner Zone Radial Gradient
        f'<radialGradient id="scan-zone-grad">'
        f'<stop offset="0%" stop-color="{th["eye_core"]}" stop-opacity="0.75"/>'
        f'<stop offset="50%" stop-color="{th["eye_core"]}" stop-opacity="0.25"/>'
        f'<stop offset="100%" stop-color="{th["eye_core"]}" stop-opacity="0"/>'
        "</radialGradient>"
        # Radar Beam Linear Gradient
        f'<linearGradient id="radar-beam-grad" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{th["radar_cone"]}" stop-opacity="0.6"/>'
        f'<stop offset="55%" stop-color="{th["radar_cone"]}" stop-opacity="0.18"/>'
        f'<stop offset="100%" stop-color="{th["radar_cone"]}" stop-opacity="0"/>'
        "</linearGradient>"
        # Performance-Safe Filters (Applied ONLY to drone and scanner core)
        '<filter id="sentinel-glow" x="-40%" y="-40%" width="180%" height="180%">'
        '<feGaussianBlur stdDeviation="1.5" result="blur"/>'
        "<feMerge><feMergeNode in=\"blur\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        '<filter id="eye-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2.0" result="blur"/>'
        "<feMerge><feMergeNode in=\"blur\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        # Flight route path for animateMotion
        f'<path id="sentinel-route" d="{route_d}"/>'
        "</defs>"
    )

    # ── Background Shell ─────────────────────────────────────────────────────
    add(
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg-grad)" rx="10" '
        f'stroke="{th["border"]}" stroke-width="1.2"/>'
    )

    # ── Tactical HUD Header ──────────────────────────────────────────────────
    # Left: Title
    add(
        f'<text x="{PAD_L:g}" y="20" font-family="system-ui, -apple-system, BlinkMacSystemFont, '
        f'\'Segoe UI\', Roboto, sans-serif" font-weight="900" font-size="11.5" '
        f'letter-spacing="1.2" fill="url(#title-grad)">KAVACH SENTINEL '
        f'<tspan font-weight="500" font-size="10" fill="{th["hud_subtitle"]}" letter-spacing="0.5">// ZERO-TRUST MATRIX</tspan></text>'
    )

    # Mid-Right: Pulsing Status Indicator Dot + Enforced Label
    status_x = 445
    add(
        f'<g transform="translate({status_x}, 16)">'
        f'<circle cx="0" cy="0" r="3.2" fill="{th["hud_accent"]}">'
        f'<animate attributeName="opacity" values="1;0.35;1" dur="2s" repeatCount="indefinite"/>'
        f'<animate attributeName="r" values="3.0;3.8;3.0" dur="2s" repeatCount="indefinite"/>'
        f'</circle>'
        f'<text x="9" y="3.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="9.5" font-weight="500" fill="{th["label"]}" letter-spacing="0.8">'
        f'STATUS: <tspan fill="{th["hud_accent"]}" font-weight="800">ENFORCED</tspan></text>'
        f'</g>'
    )

    # Right: Verified Commits Counter with explicit Rolling Time Window (LAST 12M)
    add(
        f'<text x="{WIDTH - PAD_R:g}" y="20" text-anchor="end" font-family="ui-monospace, SFMono-Regular, '
        f'Menlo, monospace" font-size="9.5" font-weight="500" fill="{th["label"]}" letter-spacing="0.8">'
        f'[ <tspan fill="{th["hud_title"]}" font-weight="800">{total} COMMITS VERIFIED</tspan> · '
        f'<tspan fill="{th["label"]}" font-weight="600">LAST 12M</tspan> ]</text>'
    )

    # Header Divider Line
    add(
        f'<line x1="{PAD_L:g}" y1="28" x2="{WIDTH - PAD_R:g}" y2="28" '
        f'stroke="{th["border"]}" stroke-width="0.8" stroke-dasharray="4 3" opacity="0.6"/>'
    )

    # ── Month Markers (Above Grid Columns) ────────────────────────────────────
    month_svg = []
    for col_idx, name in zip(MONTH_COLS, MONTH_NAMES):
        mx = PAD_L + col_idx * PITCH
        month_svg.append(
            f'<text x="{mx}" y="39" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
            f'font-size="8.5" font-weight="500" fill="{th["label"]}" opacity="0.7">{name}</text>'
        )
    add("".join(month_svg))

    # ── Day-of-Week Labels (Left of Grid, Safe Clearance >16px from turn apex) ─
    for r, name in enumerate(WEEKDAYS):
        if name:
            y = PAD_T + r * PITCH + CELL / 2 + 3.5
            add(
                f'<text x="24" y="{y:g}" text-anchor="end" fill="{th["label"]}" '
                f'font-size="8.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
                f'font-weight="600" opacity="0.75">{name}</text>'
            )

    # ── Base Grid: Zero-Trust Substrate (Dormant empty + Dim Unverified Commit Nodes)
    # Renders level-0 as flat empty slots, and level>0 as dim, low-contrast unverified nodes
    base_rects = []
    for r in range(ROWS):
        for c in range(COLS):
            x = PAD_L + c * PITCH
            y = PAD_T + r * PITCH
            level = grid[r][c]
            if level <= 0:
                base_rects.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                    f'fill="{th["grid_empty"]}"/>'
                )
            else:
                base_rects.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                    f'fill="{th["unverified_fill"]}" stroke="{th["unverified_stroke"]}" '
                    f'stroke-width="0.7"/>'
                )
    add("".join(base_rects))

    # ── Tactical Scanner Circuit Trail (Follows behind drone) ────────────────
    route_dash = f"{total_len:.1f}"
    add(
        f'<path d="{route_d}" fill="none" stroke="{th["trace_line"]}" stroke-width="1.2" '
        f'stroke-dasharray="4 4" stroke-dashoffset="{route_dash}" opacity="0.45">'
        f'<animate attributeName="stroke-dashoffset" values="{route_dash};0;0;{route_dash}" '
        f'keyTimes="0;{walk_fraction:.4f};0.985;1" dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
        f"</path>"
    )

    # ── Two-Stage Cell Reveal: Verification Flash + Final Authorized Commit Color
    # Single high-performance rect per commit cell:
    # Ignites with a crisp white/cyan flash, then blooms into the verified commit color
    lit_cells = []
    peak_pings = []

    for col, row, norm_time in cell_timings:
        level = grid[row][col]
        if level <= 0:
            continue
        x = PAD_L + col * PITCH
        y = PAD_T + row * PITCH
        cell_color = th["cells"][level]

        t_ignite = max(0.001, norm_time * walk_fraction)
        t_flash = min(0.985, t_ignite + 0.003)
        t_settle = min(0.985, t_ignite + 0.010)

        # Flash color: bright cyan for level 4, crisp white-violet for lower levels
        flash_color = "#e0f2fe" if level >= 3 else "#ffffff"

        # Verification rect: starts at opacity 0, flashes bright at t_ignite,
        # settles into its final level color, and holds for the full 3.5s review period
        lit_cells.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
            f'fill="{cell_color}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;1;0" '
            f'keyTimes="0;{t_ignite:.3f};{t_flash:.3f};0.985;1" '
            f'dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="fill" values="{flash_color};{flash_color};{cell_color};{cell_color};{flash_color}" '
            f'keyTimes="0;{t_ignite:.3f};{t_settle:.3f};0.985;1" '
            f'dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
            f"</rect>"
        )

        # High-Intensity Peak Node Radar Ping (Level 4 commits only)
        if level >= 4:
            cx = x + CELL / 2
            cy = y + CELL / 2
            t_ping_peak = min(0.985, t_ignite + 0.004)
            t_ping_end = min(0.985, t_ignite + 0.028)
            peak_pings.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="none" stroke="{th["cells"][4]}" '
                f'stroke-width="1.1" opacity="0">'
                f'<animate attributeName="r" values="6;6;16;22;22" '
                f'keyTimes="0;{t_ignite:.3f};{t_ping_peak:.3f};{t_ping_end:.3f};1" '
                f'dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0;0;0.75;0;0" '
                f'keyTimes="0;{t_ignite:.3f};{t_ping_peak:.3f};{t_ping_end:.3f};1" '
                f'dur="{total_dur:.2f}s" repeatCount="indefinite"/>'
                f"</circle>"
            )

    add("".join(lit_cells))
    add("".join(peak_pings))

    # ── Tactical Sentinel Drone Hero Sprite ──────────────────────────────────
    drone_markup = build_drone_svg(th, total_dur, walk_dur)
    add(
        f'<g id="moving-sentinel">'
        f'<animateMotion dur="{total_dur:.2f}s" rotate="auto" fill="freeze" repeatCount="indefinite" '
        f'keyPoints="0;1;1;0" keyTimes="0;{walk_fraction:.4f};0.985;1" calcMode="linear">'
        f'<mpath xlink:href="#sentinel-route" href="#sentinel-route"/>'
        f"</animateMotion>"
        f'<g id="drone-hover-banking">'
        # Subtle hover banking oscillation
        f'<animateTransform attributeName="transform" type="scale" '
        f'values="1 1; 1.03 0.97; 1 1" dur="1.8s" repeatCount="indefinite"/>'
        f"{drone_markup}"
        f"</g></g>"
    )

    # ── Minimal Bottom HUD Footer ────────────────────────────────────────────
    # Bottom divider line
    add(
        f'<line x1="{PAD_L:g}" y1="155" x2="{WIDTH - PAD_R:g}" y2="155" '
        f'stroke="{th["footer_border"]}" stroke-width="0.8" stroke-dasharray="3 3" opacity="0.7"/>'
    )

    # Footer Left: Monospace Security Policy Telemetry
    add(
        f'<text x="{PAD_L:g}" y="169" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="9" fill="{th["footer_text"]}" letter-spacing="0.8">'
        f'POLICY: <tspan fill="{th["hud_subtitle"]}" font-weight="700">DEFAULT-DENY</tspan> // '
        f'AUDIT: <tspan fill="{th["hud_accent"]}" font-weight="700">PASS</tspan></text>'
    )

    # Footer Right: Compact Intensity Legend (UNVERIFIED → LOW → MED → PEAK)
    # Rendered right-aligned ending at WIDTH - PAD_R (844)
    # UNVERIFIED [box] → LOW [box] → MED [box] → PEAK [box]
    legend_right_x = WIDTH - PAD_R
    add(
        f'<g transform="translate({legend_right_x - 245}, 162)">'
        # UNVERIFIED
        f'<rect x="0" y="0" width="7" height="7" rx="1.5" fill="{th["unverified_fill"]}" '
        f'stroke="{th["unverified_stroke"]}" stroke-width="0.6"/>'
        f'<text x="11" y="6.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8.5" fill="{th["footer_text"]}">UNVERIFIED</text>'
        # Arrow 1
        f'<text x="80" y="6.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8.5" fill="{th["footer_text"]}" opacity="0.5">→</text>'
        # LOW
        f'<rect x="94" y="0" width="7" height="7" rx="1.5" fill="{th["cells"][1]}"/>'
        f'<text x="105" y="6.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8.5" fill="{th["footer_text"]}">LOW</text>'
        # Arrow 2
        f'<text x="131" y="6.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8.5" fill="{th["footer_text"]}" opacity="0.5">→</text>'
        # MED
        f'<rect x="145" y="0" width="7" height="7" rx="1.5" fill="{th["cells"][2]}"/>'
        f'<text x="156" y="6.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8.5" fill="{th["footer_text"]}">MED</text>'
        # Arrow 3
        f'<text x="182" y="6.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8.5" fill="{th["footer_text"]}" opacity="0.5">→</text>'
        # PEAK
        f'<rect x="196" y="0" width="7" height="7" rx="1.5" fill="{th["cells"][4]}"/>'
        f'<text x="207" y="6.5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8.5" fill="{th["footer_text"]}" font-weight="700">PEAK</text>'
        f'</g>'
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
    for _w in range(COLS):
        week = []
        for _d in range(ROWS):
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
            "User-Agent": "gen-kavach-drone",
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
        default=11.5,
        help="Patrol sweep duration in seconds (loop adds 3.5s hold, total=15s)",
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
        if not token:
            try:
                import subprocess

                res = subprocess.run(
                    ["gh", "auth", "token"], capture_output=True, text=True, check=True
                )
                token = res.stdout.strip() or None
            except Exception:
                token = None

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
        ("dark", "github-contribution-grid-sentinel-dark.svg"),
        ("light", "github-contribution-grid-sentinel.svg"),
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
        total_loop = args.duration + 3.5
        print(
            f"✓ {path:<48} {file_size_kb:>6.1f} KiB  "
            f"sweep={args.duration:g}s hold=3.5s loop={total_loop:g}s  "
            f"theme={theme:<5}  total={total}"
        )

    print("\nKAVACH Tactical Sentinel Contribution Graph generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
