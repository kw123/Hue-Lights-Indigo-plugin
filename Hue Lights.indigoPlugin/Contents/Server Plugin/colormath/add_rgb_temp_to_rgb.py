#! /usr/local/bin/python
"""
add lamps  to new rgb value 
input rgb or color temp 

# Example Usage
rgb_list = [(255, 0, 0)]      # One pure red lamp
kelvin_list = [2700, 6500]    # One warm and one cool lamp

calculate_total_rgb(rgb_list, kelvin_list) --> r, g, b

"""
import math
def kelvin_to_rgb(kelvin):
    """
    Approximate RGB from Kelvin (1,000K to 40,000K).
    Based on Tanner Helland's algorithm.
    """
    temp = kelvin / 100
    
    # Red component
    if temp <= 66:
        r = 255.
    else:
        r = 329.698727446 * ((temp - 60) ** -0.1332047592)
    
    # Green component
    if temp <= 66:
        g = 99.4708025861 * math.log(temp) - 161.1195681661
    else:
        g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    
    # Blue component
    if temp >= 66:
        b = 255.
    elif temp <= 19:
        b = 0
    else:
        b = 138.5177312231 * math.log(temp - 10) - 305.0447927307

    # Clamp values to 0-255 range
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    
    return (r, g, b)

def calculate_total_rgb(rgb_lamps, kelvin_lamps):
    """
    rgb_lamps: List of (R, G, B) tuples (e.g., [(255, 0, 0)])
    kelvin_lamps: List of integers (e.g., [2700, 6500])
    """
    all_colors = []
    
    # Add standard RGB lamps
    all_colors.extend(rgb_lamps)
    
    # Convert Kelvin lamps and add them
    for k in kelvin_lamps:
        all_colors.append(kelvin_to_rgb(k))
    
    if not all_colors:
        return (0, 0, 0)
    
    # Sum and average the components
    sum_r = sum(c[0] for c in all_colors)
    sum_g = sum(c[1] for c in all_colors)
    sum_b = sum(c[2] for c in all_colors)
    count = len(all_colors)
    
    return (sum_r // count, sum_g // count, sum_b // count)

