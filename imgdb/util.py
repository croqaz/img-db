def rgb_to_hex(color_pair):
    # ex: (111, 78, 55) -> #6F4E37
    assert len(color_pair) >= 3, 'Need 3 colors'
    return '#{:02x}{:02x}{:02x}'.format(*color_pair)


def hex_to_rgb(color):
    # ex: #914E72 -> (145, 78, 114)
    color = color.lstrip('#')
    assert len(color) >= 6, 'Need a HEX string'
    r_hex = color[0:2]
    g_hex = color[2:4]
    b_hex = color[4:6]
    return int(r_hex, 16), int(g_hex, 16), int(b_hex, 16)
