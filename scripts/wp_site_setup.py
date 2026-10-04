#!/usr/bin/env python3
"""Plugin-based site design (requirements §35-14, T-51).

data/wp-site.json is the single source of truth: the block theme, the plugins
(with a purpose each) and the global styles (palette, fonts, card CSS).

Usage:
  python3 scripts/wp_site_setup.py check   # validate the manifest (also check_wired W17)
  python3 scripts/wp_site_setup.py plan    # operator: show what apply would change (read-only)
  python3 scripts/wp_site_setup.py apply   # operator: install/activate plugins, update global styles
Auth: same selection as scripts/wp-init.sh (requirements §24). Additive only:
this script never deactivates or deletes a plugin and never switches the theme.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Any, Callable, Mapping

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tool_pages import http_transport, wp_target  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_FILE = ROOT / "data" / "wp-site.json"
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HEX_RE = re.compile(r"#([0-9a-fA-F]{6})")
# WP_REST_Global_Styles_Controller::validate_custom_css rejects anything that looks like markup.
CSS_TAG_RE = re.compile(r"</?\w+")
TARGETS = ("wpcom", "self-hosted")
MIN_CONTRAST = 4.5  # WCAG 2.x AA for normal text

Transport = Callable[[str, str, dict[str, Any] | None], Any]


def load_manifest(path: pathlib.Path = SITE_FILE) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def validate(data: Any) -> list[str]:
    """§35-14 W17 schema checks."""
    if not isinstance(data, dict):
        return ["wp-site.json must be an object"]
    errors: list[str] = []
    theme = data.get("theme")
    if not isinstance(theme, dict) or not SLUG_RE.fullmatch(str(theme.get("stylesheet", ""))):
        errors.append("theme.stylesheet must be a theme slug")
    forbidden = set(data.get("forbidden_plugins") or [])
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append("plugins must be a non-empty list")
        plugins = []
    seen: set[str] = set()
    for i, plugin in enumerate(plugins):
        slug = plugin.get("slug") if isinstance(plugin, dict) else None
        where = slug if isinstance(slug, str) and slug else f"plugins[{i}]"
        if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
            errors.append(f"{where}: slug must be a wordpress.org plugin slug")
            continue
        if slug in seen:
            errors.append(f"{slug}: duplicate plugin")
        seen.add(slug)
        if slug in forbidden:
            errors.append(f"{slug}: forbidden plugin (§35-14)")
        if not isinstance(plugin.get("purpose"), str) or not plugin["purpose"].strip():
            errors.append(f"{slug}: purpose is required")
        targets = plugin.get("targets")
        if not isinstance(targets, list) or not targets or any(t not in TARGETS for t in targets):
            errors.append(f"{slug}: targets must be a non-empty subset of {TARGETS}")

    styles = (data.get("global_styles") or {}).get("styles") or {}
    css = styles.get("css", "")
    if not isinstance(css, str) or CSS_TAG_RE.search(css):
        errors.append("global_styles.styles.css must be plain CSS without HTML tags")
    palette = (((data.get("global_styles") or {}).get("settings") or {})
               .get("color", {}).get("palette", {}).get("theme"))
    colors = {c.get("slug"): c.get("color") for c in palette} if isinstance(palette, list) else {}
    for slug in ("base", "contrast"):
        if slug not in colors:
            errors.append(f"palette must define {slug}")
    for pair in data.get("contrast_pairs") or []:
        fg, bg = (colors.get(pair[0]), colors.get(pair[1])) if len(pair) == 2 else (None, None)
        if not (isinstance(fg, str) and HEX_RE.fullmatch(fg)
                and isinstance(bg, str) and HEX_RE.fullmatch(bg)):
            errors.append(f"contrast pair {pair}: both colors must be #RRGGBB in the palette")
            continue
        ratio = contrast_ratio(fg, bg)
        if ratio < MIN_CONTRAST:
            errors.append(f"contrast pair {pair}: {ratio:.2f}:1 < {MIN_CONTRAST}:1")
    return errors


def target_of(env: Mapping[str, str]) -> str:
    return "wpcom" if env.get("WP_BEARER_TOKEN") else "self-hosted"


def setup(data: Mapping[str, Any], send: Transport, target: str, apply: bool) -> list[str]:
    """Plan or apply the manifest. Additive only; never deactivates, deletes or switches theme."""
    log: list[str] = []
    try:
        installed = send("GET", "/plugins?context=edit", None) or []
    except Exception as exc:  # noqa: BLE001 - report and stop, nothing was changed
        return [f"[WARN] cannot list plugins ({exc}); install them from the admin screen"]
    by_slug = {p["plugin"].split("/")[0]: p for p in installed if isinstance(p, dict) and p.get("plugin")}

    for plugin in data["plugins"]:
        slug = plugin["slug"]
        if target not in plugin["targets"]:
            log.append(f"[SKIP] {slug}: not for {target}")
            continue
        current = by_slug.get(slug)
        if current and current.get("status") == "active":
            log.append(f"[SKIP] {slug}: already active")
            continue
        action = "activate" if current else "install+activate"
        if not apply:
            log.append(f"[PLAN] {slug}: {action}")
            continue
        try:
            if current:
                send("POST", f"/plugins/{current['plugin']}", {"status": "active"})
            else:
                send("POST", "/plugins", {"slug": slug, "status": "active"})
            log.append(f"[DONE] {slug}: {action}")
        except Exception as exc:  # noqa: BLE001 - one plugin failing must not stop the rest
            log.append(f"[WARN] {slug}: {action} failed ({exc}); install it from the admin screen")

    wanted = data["theme"]["stylesheet"]
    try:
        active = (send("GET", "/themes?status=active", None) or [{}])[0]
    except Exception as exc:  # noqa: BLE001
        log.append(f"[WARN] cannot read the active theme ({exc})")
        return log
    if active.get("stylesheet") != wanted:
        log.append(f"[TODO] activate theme {wanted} in the admin screen "
                   f"(active: {active.get('stylesheet')}); REST cannot switch themes. "
                   "Global styles are left untouched until then.")
        return log
    links = (active.get("_links") or {}).get("wp:user-global-styles") or []
    href = links[0].get("href", "") if links else ""
    match = re.search(r"/global-styles/(\d+)", href)
    if not match:
        log.append("[TODO] user global styles id not exposed; apply styles in the Site Editor")
        return log
    styles_id = match.group(1)
    if not apply:
        log.append(f"[PLAN] global styles {styles_id}: palette, fonts, card CSS")
        return log
    try:
        send("POST", f"/global-styles/{styles_id}", data["global_styles"])
        log.append(f"[DONE] global styles {styles_id}: palette, fonts, card CSS")
    except Exception as exc:  # noqa: BLE001
        log.append(f"[WARN] global styles update failed ({exc})")
    return log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("check", "plan", "apply"))
    args = ap.parse_args(argv)
    data = load_manifest()
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    if args.cmd == "check":
        print(f"[OK] wp-site.json valid: theme {data['theme']['stylesheet']}, "
              f"{len(data['plugins'])} plugins")
        return 0
    base, auth = wp_target(os.environ)
    for line in setup(data, http_transport(base, auth), target_of(os.environ),
                      apply=args.cmd == "apply"):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
