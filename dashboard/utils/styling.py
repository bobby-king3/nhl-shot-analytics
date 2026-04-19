"""Color and styling utilities for the dashboard."""

# Performance color thresholds
PERFORMANCE_COLORS = {
    "gold": "#FFD700",
    "orange": "#F08030",
    "blue": "#4a90d9",
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple. Example: '#FF0000' -> (255, 0, 0)"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_performance_color(value: float, thresholds: dict) -> str:
    """
    Get color based on value and thresholds.

    Args:
        value: The value to evaluate
        thresholds: Dict with 'high' and 'medium' keys for threshold values

    Example:
        get_performance_color(75, {'high': 67, 'medium': 34})
    """
    high = thresholds.get("high", 67)
    medium = thresholds.get("medium", 34)

    if value >= high:
        return PERFORMANCE_COLORS["gold"]
    elif value >= medium:
        return PERFORMANCE_COLORS["orange"]
    else:
        return PERFORMANCE_COLORS["blue"]
