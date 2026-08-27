"""
AutoLabeler Design System
========================

Design tokens and constants extracted from UI_DESIGN_SPEC_v2.md sections 1.1-1.5.
Defines color palettes (dark/light themes), typography, spacing, border radius, and shadow system.

Version: 2.1 (Performance Optimized)
Last Updated: 2026-08-24
"""

from dataclasses import dataclass
from typing import List, Tuple
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect


# =============================================================================
# 1.1 COLOR SYSTEM
# =============================================================================

@dataclass(frozen=True)
class DarkThemeColors:
    """Deep Professional Dark Theme (Default)"""

    # Background Colors
    BG_APP: str = "#0A0E14"          # Application base (deepest layer)
    BG_SURFACE: str = "#141922"      # Main content area background
    BG_ELEVATED: str = "#1C2128"     # Cards, dialogs (floating layer)
    BG_HOVER: str = "#252D38"        # Hover state background
    BG_ACTIVE: str = "#2D3642"       # Active/selected state background
    BG_INPUT: str = "#1A1F29"        # Input field background

    # Text Colors
    TEXT_PRIMARY: str = "#E6EDF3"    # Primary text (titles, key info)
    TEXT_SECONDARY: str = "#9DA9BB"  # Secondary text (descriptions)
    TEXT_TERTIARY: str = "#6B7785"   # Auxiliary text (hints, placeholders)
    TEXT_DISABLED: str = "#484F5C"   # Disabled state text

    # Brand Colors
    BRAND_PRIMARY: str = "#0EA5E9"   # Primary brand color (sky blue)
    BRAND_HOVER: str = "#0284C7"     # Hover state
    BRAND_ACTIVE: str = "#0369A1"    # Active state
    BRAND_SUBTLE: str = "#082F49"    # Brand background in dark mode

    # Semantic Colors - Success
    SUCCESS: str = "#10B981"
    SUCCESS_BG: str = "#064E3B"
    SUCCESS_BORDER: str = "#065F46"

    # Semantic Colors - Warning
    WARNING: str = "#F59E0B"
    WARNING_BG: str = "#78350F"
    WARNING_BORDER: str = "#92400E"

    # Semantic Colors - Error
    ERROR: str = "#EF4444"
    ERROR_BG: str = "#7F1D1D"
    ERROR_BORDER: str = "#991B1B"

    # Semantic Colors - Info
    INFO: str = "#3B82F6"
    INFO_BG: str = "#1E3A8A"
    INFO_BORDER: str = "#1E40AF"

    # Borders and Dividers
    BORDER_DEFAULT: str = "#30363D"  # Default border
    BORDER_SUBTLE: str = "#21262D"   # Subtle divider
    BORDER_EMPHASIS: str = "#525964" # Emphasis border


@dataclass(frozen=True)
class LightThemeColors:
    """Light Professional Theme (Day Mode)"""

    # Background Colors
    BG_APP: str = "#F8FAFC"          # Application base
    BG_SURFACE: str = "#FFFFFF"      # Main content area background
    BG_ELEVATED: str = "#FFFFFF"     # Cards, dialogs (white + shadow)
    BG_HOVER: str = "#F1F5F9"        # Hover state background
    BG_ACTIVE: str = "#E2E8F0"       # Active/selected state background
    BG_INPUT: str = "#FFFFFF"        # Input field background

    # Text Colors
    TEXT_PRIMARY: str = "#0F172A"    # Primary text
    TEXT_SECONDARY: str = "#475569"  # Secondary text
    TEXT_TERTIARY: str = "#94A3B8"   # Auxiliary text
    TEXT_DISABLED: str = "#CBD5E1"   # Disabled state

    # Brand Colors (consistent with dark theme)
    BRAND_PRIMARY: str = "#0EA5E9"
    BRAND_HOVER: str = "#0284C7"
    BRAND_ACTIVE: str = "#0369A1"
    BRAND_SUBTLE: str = "#E0F2FE"    # Light background block

    # Semantic Colors - Success
    SUCCESS: str = "#10B981"
    SUCCESS_BG: str = "#D1FAE5"
    SUCCESS_BORDER: str = "#34D399"

    # Semantic Colors - Warning
    WARNING: str = "#F59E0B"
    WARNING_BG: str = "#FEF3C7"
    WARNING_BORDER: str = "#FBBF24"

    # Semantic Colors - Error
    ERROR: str = "#EF4444"
    ERROR_BG: str = "#FEE2E2"
    ERROR_BORDER: str = "#F87171"

    # Semantic Colors - Info
    INFO: str = "#3B82F6"
    INFO_BG: str = "#DBEAFE"
    INFO_BORDER: str = "#60A5FA"

    # Borders and Dividers
    BORDER_DEFAULT: str = "#E2E8F0"
    BORDER_SUBTLE: str = "#F1F5F9"
    BORDER_EMPHASIS: str = "#CBD5E1"


# Theme instances
DARK_THEME = DarkThemeColors()
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
            "Microsoft YaHei UI",      # Windows recommended
            "Microsoft YaHei",         # Windows fallback
            "PingFang SC",             # macOS
            "SF Pro Display",          # macOS system font
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
    """Font size hierarchy in pixels"""

    # Heading levels
    H1: int = 28    # Page main title
    H2: int = 22    # Section title
    H3: int = 18    # Card title
    H4: int = 16    # Subsection title

    # Body levels
    BODY_L: int = 15    # Large body (key descriptions)
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
    """8px base grid spacing system"""

    SPACE_1: int = 4     # Minimal spacing (icon + text)
    SPACE_2: int = 8     # Small spacing (tight elements)
    SPACE_3: int = 12    # Standard spacing (related elements)
    SPACE_4: int = 16    # Medium spacing (group elements)
    SPACE_5: int = 24    # Large spacing (between groups)
    SPACE_6: int = 32    # Extra large spacing (block separation)
    SPACE_8: int = 48    # Super large spacing (page areas)
    SPACE_10: int = 64   # Page-level spacing


@dataclass(frozen=True)
class ComponentPadding:
    """Component internal padding specifications"""

    # Button padding (vertical, horizontal)
    BUTTON_SM: Tuple[int, int] = (6, 12)     # Small button
    BUTTON_MD: Tuple[int, int] = (10, 20)    # Standard button
    BUTTON_LG: Tuple[int, int] = (14, 28)    # Large button

    # Card padding
    CARD_PADDING: int = 24              # Standard card
    CARD_PADDING_COMPACT: int = 16      # Compact card
    CARD_PADDING_SPACIOUS: int = 32     # Spacious card

    # Page margins
    PAGE_PADDING: int = 32              # Page main area
    SIDEBAR_PADDING: int = 20           # Sidebar


# Spacing instances
SPACING = Spacing()
PADDING = ComponentPadding()


# =============================================================================
# 1.4 BORDER RADIUS SYSTEM
# =============================================================================

@dataclass(frozen=True)
class BorderRadius:
    """Border radius values in pixels"""

    SM: int = 4       # Small elements (tags, badges)
    MD: int = 6       # Buttons, input fields
    LG: int = 8       # Cards
    XL: int = 12      # Dialogs, large cards
    XXL: int = 16     # Modal dialogs
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

    # Dark theme border shadows
    DARK_LIGHT: Tuple[str, str, int] = ("#21262D", "#1A1F29", 2)  # (border, bottom_border, bottom_width)
    DARK_MEDIUM: Tuple[str, str, int] = ("#30363D", "#21262D", 3)
    DARK_EMPHASIS: Tuple[str, str, int] = ("#525964", "#30363D", 4)

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
    Real shadow factory (Scheme B) - Selective Use Only

    Performance Note:
    - Use ONLY for: login page cards, dialogs/modals, hover states (dynamic)
    - AVOID for: static cards, lists with many items (>10)
    - QGraphicsDropShadowEffect has significant rendering cost
    """

    @staticmethod
    def create_small_shadow_dark() -> QGraphicsDropShadowEffect:
        """Small shadow for dark theme (temporary/hover elements)"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(4)
        effect.setColor(QColor(0, 0, 0, 128))  # 50% opacity
        effect.setOffset(0, 2)
        return effect

    @staticmethod
    def create_medium_shadow_dark() -> QGraphicsDropShadowEffect:
        """Medium shadow for dark theme (dialogs, modals)"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(8)
        effect.setColor(QColor(0, 0, 0, 128))  # 50% opacity
        effect.setOffset(0, 4)
        return effect

    @staticmethod
    def create_large_shadow_dark() -> QGraphicsDropShadowEffect:
        """Large shadow for dark theme (prominent dialogs)"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(16)
        effect.setColor(QColor(0, 0, 0, 102))  # 40% opacity
        effect.setOffset(0, 8)
        return effect

    @staticmethod
    def create_small_shadow_light() -> QGraphicsDropShadowEffect:
        """Small shadow for light theme"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(4)
        effect.setColor(QColor(0, 0, 0, 13))   # 5% opacity
        effect.setOffset(0, 2)
        return effect

    @staticmethod
    def create_medium_shadow_light() -> QGraphicsDropShadowEffect:
        """Medium shadow for light theme"""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(8)
        effect.setColor(QColor(0, 0, 0, 26))   # 10% opacity
        effect.setOffset(0, 4)
        return effect


@dataclass(frozen=True)
class ShadowUsageGuide:
    """
    Shadow usage decision tree and component mapping

    Decision Tree:
    - Static display? → Border simulation (Scheme A)
    - Hover/Temporary? → Real shadow (Scheme B)
    - Element count > 10? → Border simulation (Scheme A)

    Component Mapping:
    - Homepage module cards (static): Scheme A
    - Homepage module cards (hover): Scheme A (use border + translateY)
    - Login page form card: Scheme B (single static card acceptable)
    - Task center task cards: Scheme A (variable count)
    - Preflight result cards: Scheme A (multiple cards)
    - Manual page chapter cards: Scheme A (border only, no shadow)
    - Settings page parameter cards: Scheme A (border only)
    - Primary buttons: Scheme A (border on hover)
    - Input fields (focus): No shadow (use outline for glow simulation)
    - Dialogs/confirmation modals: Scheme B (temporary display acceptable)
    """
    pass


# Shadow system instances
BORDER_SHADOW = BorderSimulatedShadow()
REAL_SHADOW = RealShadowFactory()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_current_theme() -> DarkThemeColors | LightThemeColors:
    """
    Get the current active theme

    ThemeManager owns runtime switching. This design-system helper provides the
    same light default for callers that only need a palette without a manager.
    """
    return LIGHT_THEME


def get_qss_color(color_name: str, theme: DarkThemeColors | LightThemeColors = None) -> str:
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
    "DARK_THEME",
    "LIGHT_THEME",
    "DarkThemeColors",
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
