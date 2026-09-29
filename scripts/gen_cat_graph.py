#!/usr/bin/env python3
"""Render a GitHub contribution graph as an animated neon cat.

Fetches the contribution calendar over the GitHub GraphQL API, then writes two
animated SVGs (light + dark) in which a pixel cat walks the whole grid. Every
day the cat crosses lights up in its real contribution colour, and once the walk
finishes the cat curls up and falls asleep on the newest day.

Stdlib only, so the workflow needs no install step.
"""

from __future__ import annotations

import argparse
import json
import os
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

# ── layout ────────────────────────────────────────────────────────────────────
CELL = 12
GAP = 3
PITCH = CELL + GAP
COLS = 53
ROWS = 7
PAD_L = 30
PAD_T = 18
PAD_R = 34
PAD_B = 14
GRID_W = COLS * PITCH - GAP
GRID_H = ROWS * PITCH - GAP
WIDTH = PAD_L + GRID_W + PAD_R
HEIGHT = PAD_T + GRID_H + PAD_B
WEEKDAYS = ["", "Mon", "", "Wed", "", "Fri", ""]

SPRITE_PX = 1.7

# ── sprite layers ─────────────────────────────────────────────────────────────
# B body · W eye · E ear/highlight · T tail · K paws · C curl · S tucked paw.
# All walk layers share one 16x11 grid so they overlay exactly; check_layers()
# enforces that at build time.
WALK_BODY = [
    "..........EE.EE.",
    ".........EBBEBB.",
    ".........EBWWBB.",
    "........BBBBBBB.",
    ".....BBBBBBBBBBB",
    "....BBBBBBBBBBBB",
    "....BBBBBBBBBBBB",
    "....BBBBBBBBBBBB",
    "................",
    "................",
    "................",
]
WALK_LEGS_A = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "...BBB..BBB.....",
    "..KKK....KKK....",
]
WALK_LEGS_B = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "..BBBB..BBBB....",
    ".KKK......KKK...",
]
WALK_TAIL = [
    "................",
    "................",
    "T...............",
    "T...............",
    ".T..............",
    "..T.............",
    "...T............",
    "....T...........",
    "................",
    "................",
    "................",
]
SLEEP_BODY = [
    "...E..E.......",
    "...EE.EE......",
    "..EBBBBEB.....",
    ".CBBBBBBBBC...",
    ".CBBBBBBBBC...",
    ".CBBBBBBBBC...",
    "..CCCCCCCCC...",
    "..............",
]
SLEEP_PAWS = [
    "..............",
    "..............",
    "..............",
    "..............",
    "..............",
    "..............",
    "..............",
    "..SS.....SS...",
]


def norm(layer: list[str]) -> list[str]:
    """Pad every row of a character grid out to the widest row."""
    width = max(len(r) for r in layer)
    return [r.ljust(width, ".") for r in layer]


WALK_BODY = norm(WALK_BODY)
WALK_LEGS_A = norm(WALK_LEGS_A)
WALK_LEGS_B = norm(WALK_LEGS_B)
WALK_TAIL = norm(WALK_TAIL)
SLEEP_BODY = norm(SLEEP_BODY)
SLEEP_PAWS = norm(SLEEP_PAWS)


def check_layers() -> None:
    """Every layer must be rectangular, and matching layers must agree."""
    for name, layer in (
        ("WALK_BODY", WALK_BODY),
        ("WALK_LEGS_A", WALK_LEGS_A),
        ("WALK_LEGS_B", WALK_LEGS_B),
        ("WALK_TAIL", WALK_TAIL),
        ("SLEEP_BODY", SLEEP_BODY),
        ("SLEEP_PAWS", SLEEP_PAWS),
    ):
        width = len(layer[0])
        bad = [i for i, row in enumerate(layer) if len(row) != width]
        if bad:
            raise SystemExit(f"{name}: ragged rows at {bad} (width {width})")
    for name, layer in (("WALK_LEGS_A", WALK_LEGS_A), ("WALK_TAIL", WALK_TAIL)):
        if (len(layer), len(layer[0])) != (len(WALK_BODY), len(WALK_BODY[0])):
            raise SystemExit(f"{name} must match the WALK_BODY grid")
    if (len(SLEEP_PAWS), len(SLEEP_PAWS[0])) != (
        len(SLEEP_BODY),
        len(SLEEP_BODY[0]),
    ):
        raise SystemExit("SLEEP_PAWS must match the SLEEP_BODY grid")


# ── themes ────────────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "bg": "#ffffff",
        "grid": "#e4e6eb",
        "cells": ["#d7dbe0", "#c2e5c8", "#8fd39b", "#3ba55c", "#1a7f37"],
        "body": "#7C3AED",
        "shade": "#5B21B6",
        "ear": "#A78BFA",
        "eye": "#ffffff",
        "tail": "#22D3EE",
        "curl": "#8B5CF6",
        "paw": "#5B21B6",
        "label": "#57606a",
        "z": "#0E7490",
        "glow": "#7C3AED",
        "halo": 0.16,
    },
    "dark": {
        "bg": "#0d1117",
        "grid": "#21262d",
        "cells": ["#21262d", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "body": "#8B5CF6",
        "shade": "#4C1D95",
        "ear": "#C4B5FD",
        "eye": "#ffffff",
        "tail": "#67E8F9",
        "curl": "#8B5CF6",
        "paw": "#C4B5FD",
        "label": "#8b949e",
        "z": "#67E8F9",
        "glow": "#A78BFA",
        "halo": 0.26,
    },
}

THEME_INK = {
    "B": "body",
    "W": "eye",
    "E": "ear",
    "T": "tail",
    "K": "shade",
    "C": "curl",
    "S": "paw",
}


def layer_rects(layer: list[str], th: dict, px: float) -> str:
    """Paint a character grid, merging horizontal runs of the same colour."""
    out: list[str] = []
    for y, row in enumerate(layer):
        x = 0
        while x < len(row):
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            colour = th[THEME_INK[ch]]
            n = 0
            while x + n < len(row) and row[x + n] == ch:
                n += 1
            out.append(
                f'<rect x="{x * px:g}" y="{y * px:g}" width="{n * px:g}" '
                f'height="{px:g}" fill="{colour}"/>'
            )
            x += n
    return "".join(out)


def cell_centre(col: int, row: int) -> tuple[float, float]:
    return (PAD_L + col * PITCH + CELL / 2, PAD_T + row * PITCH + CELL / 2)


def walk_cells() -> list[tuple[int, int]]:
    """Boustrophedon over rows: the cat sweeps left to right, drops one row and
    comes back. Almost all travel is horizontal, which suits a side-on cat."""
    cells: list[tuple[int, int]] = []
    for row in range(ROWS):
        cols = range(COLS) if row % 2 == 0 else range(COLS - 1, -1, -1)
        cells.extend((col, row) for col in cols)
    return cells


def build_svg(grid: list[list[int]], theme: str, duration: float, total: int) -> str:
    check_layers()
    th = THEMES[theme]
    px = SPRITE_PX

    cells = walk_cells()
    step = duration / len(cells)

    walk_w, walk_h = len(WALK_BODY[0]) * px, len(WALK_BODY) * px
    sleep_w, sleep_h = len(SLEEP_BODY[0]) * px, len(SLEEP_BODY) * px

    # stroll in from off-canvas, two cells to the left
    fx, fy = cell_centre(0, 0)
    start = (fx - 2 * PITCH, fy)
    pts = [start] + [cell_centre(c, r) for c, r in cells]
    route = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    walk_dur = (len(pts) - 1) * step
    sleep_t = walk_dur + 0.45
    hold = 0.5
    blink = 0.28

    o: list[str] = []
    add = o.append

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" role="img" '
        f'aria-label="Contribution graph: {total} commits in the last year, '
        f'as a cat walking across every day">'
    )
    add(
        "<title>Contribution cat</title>"
        "<desc>A pixel cat walks across a year of commits, lighting up each "
        "day it crosses, then curls up and falls asleep on the newest day."
        "</desc>"
    )

    add(
        "<defs>"
        f'<pattern id="grid" width="{PITCH}" height="{PITCH}" '
        f'patternUnits="userSpaceOnUse" x="{PAD_L - CELL / 2:g}" '
        f'y="{PAD_T - CELL / 2:g}">'
        f'<rect width="{CELL}" height="{CELL}" rx="3" fill="{th["grid"]}"/>'
        "</pattern>"
        '<filter id="glow" x="-45%" y="-45%" width="190%" height="190%">'
        '<feGaussianBlur stdDeviation="1.1" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
        '<radialGradient id="halo">'
        f'<stop offset="0%" stop-color="{th["glow"]}" stop-opacity="{th["halo"]}"/>'
        f'<stop offset="60%" stop-color="{th["glow"]}" '
        f'stop-opacity="{th["halo"] / 3:.3f}"/>'
        f'<stop offset="100%" stop-color="{th["glow"]}" stop-opacity="0"/>'
        "</radialGradient>"
        f'<path id="route" d="{route}"/>'
        "</defs>"
    )

    add(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{th["bg"]}" rx="8"/>')
    add(
        f'<rect x="{PAD_L:g}" y="{PAD_T:g}" width="{GRID_W}" height="{GRID_H}" '
        f'fill="url(#grid)"/>'
    )

    labels = "".join(
        f'<text x="{PAD_L - 8:g}" y="{PAD_T + r * PITCH + CELL / 2 + 3:g}" '
        f'text-anchor="end" fill="{th["label"]}" font-size="8" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'opacity="0.7">{name}</text>'
        for r, name in enumerate(WEEKDAYS)
        if name
    )
    add(labels)

    lit = []
    for i, (col, row) in enumerate(cells):
        x, y = cell_centre(col, row)
        lit.append(
            f'<rect x="{x - CELL / 2:g}" y="{y - CELL / 2:g}" width="{CELL}" '
            f'height="{CELL}" rx="3" fill="{th["cells"][grid[row][col]]}" '
            f'opacity="0">'
            f'<set attributeName="opacity" to="1" begin="{(i + 2) * step:.2f}s"/>'
            "</rect>"
        )
    add("".join(lit))

    # ── walking cat ──
    halo = (
        f'<ellipse cx="{walk_w / 2:g}" cy="{walk_h / 2 + 1:g}" rx="18" ry="12" '
        f'fill="url(#halo)"/>'
    )
    # tail hinges where it meets the body, around col 5 / row 6
    tp = f"{5.4 * px:g} {6.4 * px:g}"
    tail = (
        f'<g transform="rotate(-7 {tp})">'
        f"{layer_rects(WALK_TAIL, th, px)}"
        f'<animateTransform attributeName="transform" type="rotate" '
        f'values="-13 {tp};9 {tp};-13 {tp}" dur="2.4s" '
        f'repeatCount="indefinite"/></g>'
    )
    legs_a = (
        f'<g opacity="1">{layer_rects(WALK_LEGS_A, th, px)}'
        f'<animate attributeName="opacity" values="1;0;1" dur="{blink * 2:g}s" '
        f'repeatCount="indefinite"/></g>'
    )
    legs_b = (
        f'<g opacity="0">{layer_rects(WALK_LEGS_B, th, px)}'
        f'<animate attributeName="opacity" values="0;1;0" dur="{blink * 2:g}s" '
        f'repeatCount="indefinite"/></g>'
    )
    bob = (
        '<animateTransform attributeName="transform" type="translate" '
        f'values="0 0;0 -0.5;0 0" dur="{blink * 2:g}s" repeatCount="indefinite"/>'
    )
    add(
        f'<g transform="translate({-walk_w / 2:g} {-walk_h / 2 + 3:g})">'
        f"{halo}"
        f'<g filter="url(#glow)">{bob}{layer_rects(WALK_BODY, th, px)}'
        f"{tail}{legs_a}{legs_b}</g>"
        f'<animateMotion dur="{walk_dur:.2f}s" calcMode="linear" fill="freeze" '
        f'rotate="0"><mpath xlink:href="#route" href="#route"/></animateMotion>'
        f'<animate attributeName="opacity" from="1" to="0" '
        f'begin="{sleep_t + hold:.2f}s" dur="0.4s" fill="freeze"/>'
        "</g>"
    )

    # ── sleeping cat, on the newest day ──
    lx, ly = cell_centre(*cells[-1])
    # drift the z's up and to the left so they never clip the right edge
    zs = "".join(
        f'<text x="{-dx:g}" y="{dy:g}" font-size="{size:g}" fill="{th["z"]}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'opacity="0">z'
        f'<animate attributeName="opacity" values="0;0.85;0" dur="3.4s" '
        f'begin="{delay:g}s" repeatCount="indefinite"/>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="0 0;-2 -7" dur="3.4s" begin="{delay:g}s" '
        f'repeatCount="indefinite"/></text>'
        for dx, dy, size, delay in ((7, -6, 7, 0), (13, -14, 8, 1.1), (19, -22, 9, 2.2))
    )
    add(
        f'<g transform="translate({lx:g} {ly:g})" opacity="0">'
        f'<set attributeName="opacity" to="1" begin="{sleep_t + 0.15:.2f}s"/>'
        f'<ellipse cx="0" cy="{sleep_h / 2 - 2:g}" rx="16" ry="10" '
        f'fill="url(#halo)"/>'
        f'<g filter="url(#glow)">'
        f'<g transform="translate({-sleep_w / 2:g} {-(sleep_h / 2 - 2):g})">'
        f'<animateTransform attributeName="transform" type="scale" '
        f'values="1 1;1.04 0.95;1 1" additive="sum" dur="3.4s" '
        f'repeatCount="indefinite"/>'
        f"{layer_rects(SLEEP_BODY, th, px)}"
        f"{layer_rects(SLEEP_PAWS, th, px)}"
        "</g></g>"
        f'<g transform="translate({-sleep_w / 2:g} {-(sleep_h / 2 - 2):g})">'
        f"{zs}</g>"
        "</g>"
    )
    add("</svg>")
    return "".join(o)


# ── data ──────────────────────────────────────────────────────────────────────
def normalise(weeks: list[list[int]]) -> list[list[int]]:
    """API order is weeks x days; return a row-major ROWS x COLS grid."""
    grid = [row[:ROWS] + [0] * (ROWS - len(row[:ROWS])) for row in weeks]
    if len(grid) > COLS:
        grid = grid[-COLS:]
    if not grid:
        grid = [[0] * ROWS]
    if len(grid) < COLS:
        grid = [[0] * ROWS] * (COLS - len(grid)) + grid
    return [list(row) for row in zip(*grid)]


def fetch(username: str, token: str) -> tuple[list[list[int]], int]:
    body = json.dumps({"query": QUERY, "variables": {"login": username}}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "gen-cat-graph",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"github api http {exc.code}: {exc.read()[:400]!r}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"github api unreachable: {exc.reason}") from exc

    if payload.get("errors"):
        raise SystemExit(f"graphql error: {payload['errors']}")

    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [LEVELS[d["contributionLevel"]] for d in week["contributionDays"]]
        for week in cal["weeks"]
    ]
    return normalise(weeks), cal["totalContributions"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", default="MadB0i")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--duration", type=float, default=25.0)
    ap.add_argument("--fixture", help="cached calendar json, for offline renders")
    args = ap.parse_args()

    if args.fixture:
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
            raise SystemExit("GITHUB_TOKEN is not set")
        grid, total = fetch(args.user, token)

    os.makedirs(args.out, exist_ok=True)
    for theme, name in (
        ("light", "github-contribution-grid-cat.svg"),
        ("dark", "github-contribution-grid-cat-dark.svg"),
    ):
        svg = build_svg(grid, theme, args.duration, total)
        minidom.parseString(svg.encode())
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
        print(f"{path}  {len(svg) / 1024:.1f} KiB  walk={args.duration:g}s  total={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
