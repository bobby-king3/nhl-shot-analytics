def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_performance_color(value, thresholds):
    high = thresholds.get("high", 67)
    medium = thresholds.get("medium", 34)
    if value >= high:
        return "#FFD700"
    elif value >= medium:
        return "#F08030"
    return "#4a90d9"
