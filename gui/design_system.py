"""AutoLabeler visual design tokens.

The workbench uses a light content canvas with a dark navy navigation rail.
All visual surfaces consume these tokens so a palette refresh never changes
workflow semantics or widget contracts.
"""

from dataclasses import dataclass
from typing import List, Tuple
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect


# =============================================================================
# 1.1 COLOR SYSTEM
# =============================================================================

@dataclass(frozen=True)
class LightThemeColors:
    """Premium light theme for the local-first production workbench."""

    # Background Colors
    BG_APP: str = "#F4F7FA"          # Cool mist canvas
    BG_SURFACE: str = "#FFFFFF"      # Primary content surface
    BG_ELEVATED: str = "#FFFFFF"     # Cards, dialogs (white + shadow)
    BG_HOVER: str = "#EEF3F7"        # Hover state background
    BG_ACTIVE: str = "#E4ECF2"       # Active/selected state background
    BG_INPUT: str = "#FFFFFF"        # Input field background

    # Navigation rail
    NAV_BG: str = "#101C2E"
    NAV_SURFACE: str = "#17263B"
    NAV_HOVER: str = "#20334D"
    NAV_ACTIVE: str = "#28435F"
    NAV_TEXT: str = "#D7E2EE"
    NAV_MUTED: str = "#8EA2B8"

    # Text Colors
    TEXT_PRIMARY: str = "#0B1220"    # Deep ink
    TEXT_SECONDARY: str = "#52657A"  # Secondary text
    TEXT_TERTIARY: str = "#94A3B8"   # Auxiliary text (Slate 400)
    TEXT_DISABLED: str = "#CBD5E1"   # Disabled state (Slate 300)

    # Brand Colors
    BRAND_PRIMARY: str = "#0C766E"   # Cool teal (AA on white)
    BRAND_HOVER: str = "#0B6F69"
    BRAND_ACTIVE: str = "#07534F"
    BRAND_SUBTLE: str = "#E2F3F0"

    # Brand Accent
    BRAND_ACCENT: str = "#C89B5B"     # Champagne gold (brand detail only)
    BRAND_ACCENT_HOVER: str = "#A97C43"
    BRAND_ACCENT_ACTIVE: str = "#805A2B"
    BRAND_ACCENT_SUBTLE: str = "#F5EBDD"

    # Semantic Colors - Success
    SUCCESS: str = "#059669"         # Emerald 600
    SUCCESS_BG: str = "#D1FAE5"      # Emerald 100
    SUCCESS_BORDER: str = "#6EE7B7"  # Emerald 300

    # Semantic Colors - Warning
    WARNING: str = "#8A5A13"         # Amber (AA on warning surface)
    WARNING_BG: str = "#FFF7E6"
    WARNING_BORDER: str = "#F2D39B"

    # Semantic Colors - Error
    ERROR: str = "#B91C1C"           # Red (AA on error surface)
    ERROR_BG: str = "#FEE2E2"        # Red 100
    ERROR_BORDER: str = "#FCA5A5"    # Red 300

    # Semantic Colors - Info
    INFO: str = "#0369A1"            # Sky (AA on info surface)
    INFO_BG: str = "#E0F2FE"         # Sky 100
    INFO_BORDER: str = "#7DD3FC"     # Sky 300

    # Borders and Dividers
    BORDER_DEFAULT: str = "#D9E2EC"      # Standard borders
    BORDER_SUBTLE: str = "#EAF0F4"       # Very light borders
    BORDER_EMPHASIS: str = "#B8C7D6"     # Strong borders
    BORDER_CARD: str = "#D5E0E9"         # Card edge definition

    # Focus and inverse surfaces
    FOCUS_RING: str = "#58BEB7"
    TEXT_INVERSE: str = "#FFFFFF"

    # Per-module accents keep the workflow scannable without recolouring
    # business states. Values are used for a thin card edge and icon tint.
    MODULE_SCAN: str = "#1C9DB5"
    MODULE_SAMPLE: str = "#7B69C7"
    MODULE_LABEL: str = "#C27C3A"
    MODULE_TRAIN: str = "#B05D88"
    MODULE_INFER: str = "#0F8F86"
    MODULE_REVIEW: str = "#2E9B72"
    MODULE_RESTORE: str = "#5B75B8"
    MODULE_CONVERT: str = "#759D3A"


LIGHT_THEME = LightThemeColors()


# =============================================================================
# 1.2 TYPOGRAPHY SYSTEM
# =============================================================================

@dataclass(frozen=True)
class FontFamily:
    """Font family priorities (Windows primary)"""

    # Primary font stack
    SANS_SERIF: List[str] = None

    # Monospace font stack (for code, paths)
    MONOSPACE: List[str] = None

    def __post_init__(self):
        # Using object.__setattr__ because dataclass is frozen
        object.__setattr__(self, 'SANS_SERIF', [
            "Inter",                   # Primary (must bundle fonts)
            "SF Pro Display",          # macOS system font
            "Microsoft YaHei UI",      # Windows recommended
            "Segoe UI",                # Windows system font
            "-apple-system",
            "BlinkMacSystemFont",
            "sans-serif"
        ])

        object.__setattr__(self, 'MONOSPACE', [
            "Consolas",
            "Monaco",
            "SF Mono",
            "Courier New",
            "monospace"
        ])

    def get_sans_serif_family(self) -> str:
        """Get comma-separated font family string for Qt stylesheets"""
        return ", ".join(f'"{font}"' if " " in font else font for font in self.SANS_SERIF)

    def get_monospace_family(self) -> str:
        """Get comma-separated monospace font family string for Qt stylesheets"""
        return ", ".join(f'"{font}"' if " " in font else font for font in self.MONOSPACE)


@dataclass(frozen=True)
class FontSize:
    """Font size hierarchy in pixels (Desktop-first scale)"""

    # Display and heading levels
    DISPLAY: int = 40   # Hero headlines
    H1: int = 32        # Page main title
    H2: int = 24        # Section title
    H3: int = 18        # Card title
    H4: int = 16        # Subsection title

    # Body levels
    BODY_L: int = 16    # Large body (key descriptions)
    BODY: int = 14      # Standard body (form labels, buttons)
    BODY_S: int = 13    # Small body (description text)
    CAPTION: int = 12   # Auxiliary text (hints, tags)


@dataclass(frozen=True)
class LineHeight:
    """Line height multipliers"""

    TIGHT: float = 1.2      # Headings
    NORMAL: float = 1.5     # Body text
    RELAXED: float = 1.7    # Description text


@dataclass(frozen=True)
class FontWeight:
    """Font weight values"""

    REGULAR: int = 400
    MEDIUM: int = 500      # Emphasis, buttons
    SEMIBOLD: int = 600    # Headings
    BOLD: int = 700        # Special emphasis


# Typography instances
FONT_FAMILY = FontFamily()
FONT_SIZE = FontSize()
LINE_HEIGHT = LineHeight()
FONT_WEIGHT = FontWeight()


# =============================================================================
# 1.3 SPACING SYSTEM
# =============================================================================

@dataclass(frozen=True)
class Spacing:
    """8px base grid spacing system (Desktop-generous scale)"""

    SPACE_1: int = 4     # Minimal spacing (icon + text)
    SPACE_2: int = 8     # Small spacing (tight elements)
    SPACE_3: int = 12    # Standard spacing (related elements)
    SPACE_4: int = 16    # Medium spacing (group elements)
    SPACE_5: int = 24    # Large spacing (between groups)
    SPACE_6: int = 40    # Extra large spacing (block separation)
    SPACE_8: int = 64    # Super large spacing (page areas)
    SPACE_10: int = 80   # Page-level spacing


@dataclass(frozen=True)
class ComponentPadding:
    """Component internal padding specifications (Desktop-generous)"""

    # Button padding (vertical, horizontal)
    BUTTON_SM: Tuple[int, int] = (6, 12)     # Small button
    BUTTON_MD: Tuple[int, int] = (10, 20)    # Standard button
    BUTTON_LG: Tuple[int, int] = (14, 32)    # Large button

    # Card padding
    CARD_PADDING: int = 32              # Standard card (hero/module cards)
    CARD_PADDING_COMPACT: int = 24      # Compact card
    CARD_PADDING_SPACIOUS: int = 40     # Spacious card

    # Page margins
    PAGE_PADDING: int = 48              # Page main area
    SIDEBAR_PADDING: int = 20           # Sidebar


# Spacing instances
SPACING = Spacing()
PADDING = ComponentPadding()


# =============================================================================
# 1.4 BORDER RADIUS SYSTEM
# =============================================================================

@dataclass(frozen=True)
class BorderRadius:
    """Border radius values in pixels (Warm, modern scale)"""

    SM: int = 4       # Small elements (tags, badges)
    MD: int = 8       # Buttons, input fields
    LG: int = 12      # Cards, panels
    XL: int = 16      # Large cards, hero sections
    XXL: int = 20     # Modal dialogs
    FULL: int = 9999  # Circular elements


RADIUS = BorderRadius()


# =============================================================================
# 1.5 SHADOW SYSTEM (PERFORMANCE OPTIMIZED)
# =============================================================================

@dataclass(frozen=True)
class BorderSimulatedShadow:
    """
    Border-simulated shadows (Scheme A) - High Performance

    Priority: Use border simulation for static elements and high-frequency UI.
    Avoids QGraphicsDropShadowEffect performance overhead.
    """

    # Light theme border shadows
    LIGHT_LIGHT: Tuple[str, str, int] = ("#E2E8F0", "#CBD5E1", 2)
    LIGHT_MEDIUM: Tuple[str, str, int] = ("#CBD5E1", "#94A3B8", 3)
    LIGHT_EMPHASIS: Tuple[str, str, int] = ("#94A3B8", "#64748B", 4)

    def get_qss_style(self, shadow_spec: Tuple[str, str, int]) -> str:
        """
        Generate QSS style string for border-simulated shadow

        Args:
            shadow_spec: (border_color, bottom_border_color, bottom_width)

        Returns:
            QSS border style string
        """
        border, bottom_border, bottom_width = shadow_spec
        return f"border: 1px solid {border}; border-bottom: {bottom_width}px solid {bottom_border};"


class RealShadowFactory:
    """
    Real shadow factory (Industrial Precision Design)

    Physical depth system:
    - Small: 3mm lift (controls, pills)
    - Medium: 6mm lift (cards at rest)
    - Large: 12mm lift (cards on hover)
    - Extra large: 20mm lift (modals, elevated panels)
    """

    @staticmethod
    def create_small_shadow_light() -> QGraphicsDropShadowEffect:
        """Small shadow: 3mm physical lift"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(3)
        effect.setColor(QColor(15, 23, 42, 31))   # 12% opacity, Slate 900
        effect.setOffset(0, 1)
        return effect

    @staticmethod
    def create_medium_shadow_light() -> QGraphicsDropShadowEffect:
        """Medium shadow: 6mm physical lift (card default) - Enhanced for better visibility"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(16)                  # Increased from 12px
        effect.setColor(QColor(15, 23, 42, 31))   # Increased to 12% opacity (was 10%)
        effect.setOffset(0, 6)                    # Increased from 4px
        return effect

    @staticmethod
    def create_large_shadow_light() -> QGraphicsDropShadowEffect:
        """Large shadow: 12mm physical lift (card hover) - Enhanced for dramatic lift"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(28)                  # Increased from 20px
        effect.setColor(QColor(15, 23, 42, 36))   # Increased to 14% opacity (was 12%)
        effect.setOffset(0, 14)                   # Increased from 8px
        return effect

    @staticmethod
    def create_xlarge_shadow_light() -> QGraphicsDropShadowEffect:
        """Extra large shadow: 20mm physical lift (modals)"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(32)
        effect.setColor(QColor(15, 23, 42, 38))   # 15% opacity
        effect.setOffset(0, 16)
        return effect


@dataclass(frozen=True)
class ShadowUsageGuide:
    """
    Shadow usage for industrial precision design

    NEW STRATEGY (Industrial Design):
    - Use REAL shadows for primary surfaces (cards, panels, hero)
    - 8 module cards = acceptable performance cost
    - Border simulation ONLY for list items (>20 rows)

    Component Mapping:
    - Homepage module cards: REAL medium shadow → large shadow on hover
    - Homepage hero section: REAL medium shadow
    - Login page form card: REAL large shadow
    - Tool page panels: REAL medium shadow
    - Task center task cards: Border simulation (variable count, can be >20)
    - Preflight result cards: REAL small shadow (usually <10 items)
    - Buttons: No shadow (use solid backgrounds)
    - Dialogs/modals: REAL xlarge shadow
    """
    pass


# Shadow system instances
BORDER_SHADOW = BorderSimulatedShadow()
REAL_SHADOW = RealShadowFactory()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_current_theme() -> LightThemeColors:
    """
    Get the current active theme

    The application has one stable light palette.
    """
    return LIGHT_THEME


def get_qss_color(color_name: str, theme: LightThemeColors | None = None) -> str:
    """
    Get color value by name from theme

    Args:
        color_name: Color attribute name (e.g., "BG_SURFACE", "BRAND_PRIMARY")
        theme: Theme instance (defaults to current theme)

    Returns:
        Hex color string
    """
    if theme is None:
        theme = get_current_theme()
    return getattr(theme, color_name, "#000000")


# =============================================================================
# EXPORT ALL
# =============================================================================

__all__ = [
    # Color themes
    "LIGHT_THEME",
    "LightThemeColors",

    # Typography
    "FONT_FAMILY",
    "FONT_SIZE",
    "LINE_HEIGHT",
    "FONT_WEIGHT",
    "FontFamily",
    "FontSize",
    "LineHeight",
    "FontWeight",

    # Spacing
    "SPACING",
    "PADDING",
    "Spacing",
    "ComponentPadding",

    # Border radius
    "RADIUS",
    "BorderRadius",

    # Shadows
    "BORDER_SHADOW",
    "REAL_SHADOW",
    "BorderSimulatedShadow",
    "RealShadowFactory",
    "ShadowUsageGuide",

    # Utilities
    "get_current_theme",
    "get_qss_color",
]
