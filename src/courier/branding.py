"""Brand identity for Courier by StageGrid Systems."""

from __future__ import annotations

BRAND_NAME = "Courier"
PUBLISHER = "StageGrid Systems"
TAGLINE = "Send from your own Gmail, safely."
APP_ID = "systems.stagegrid.courier"

# Teal / slate palette (dark + light)
COLORS = {
    "primary": "#0D9488",
    "primary_hover": "#0F766E",
    "primary_muted": "#5EEAD4",
    "accent": "#14B8A6",
    "danger": "#DC2626",
    "warning": "#D97706",
    "success": "#059669",
    "dark_bg": "#0F172A",
    "dark_surface": "#1E293B",
    "dark_surface_2": "#334155",
    "dark_text": "#F1F5F9",
    "dark_muted": "#94A3B8",
    "light_bg": "#F1F5F9",
    "light_surface": "#FFFFFF",
    "light_surface_2": "#E2E8F0",
    "light_text": "#0F172A",
    "light_muted": "#64748B",
    "border_dark": "#475569",
    "border_light": "#CBD5E1",
}

# Prefer expressive UI fonts available on common desktops; avoid Inter/Roboto/Arial.
FONT_UI = '"IBM Plex Sans", "Source Sans 3", "Noto Sans", "Segoe UI Variable", sans-serif'
FONT_MONO = '"IBM Plex Mono", "Source Code Pro", "Cascadia Code", "Consolas", monospace'
FONT_DISPLAY = '"IBM Plex Sans", "Source Sans 3", "Noto Sans", sans-serif'

SCOPES = (
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
)
