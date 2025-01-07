from typing import Dict, List


class Bar:
    """ASCII bar charting
    Inspired from: https://github.com/lord63/ascii_art
    Also: https://github.com/jstrace/bars"""

    def __init__(self, data: Dict[str, int], width=78, bar_chr='#'):
        self.data = data
        self.width = width
        self.bar_chr = bar_chr

    def render(self):
        # prepare data
        self.max_key_len = max([len(key) for key in self.data])
        self.max_val = max(self.data.values())
        result = ''
        for k, v in self.data.items():
            p = v / self.max_val
            shown = round(self.width * p)
            shown = shown + 1 if shown == 0 and v != 0 else shown
            blank = self.width - shown
            bar = self.bar_chr * (shown) + ' ' * (blank)
            result += '{:>{}s} | {} | {}\n'.format(k, self.max_key_len, bar, v)
        return '\n' + result


class Chart:
    """ASCII chart
    Inspired from: https://github.com/lord63/ascii_art
    Also: https://github.com/jstrace/chart"""

    def __init__(
        self, data: List[int], width=100, height=30, padding=2, point_char='█', negative_point_char='░', axis_char='.'
    ):
        self.data = data
        self.padding = padding
        self.width = width - padding * 2
        self.height = height - padding * 2
        self.point_char = point_char
        self.negative_point_char = negative_point_char
        self.axis_char = axis_char
        self.skeleton: List[List[str]] = []

    def render(self):
        # prepare data
        self.skeleton = [[' '] * self.width for _ in range(self.height)]
        self.max = max(abs(n) for n in self.data)
        self.label = str(self.max)
        self.label_width = len(self.label)
        self.label_padding = 1
        self.char_height = self.height
        self.char_width = self.width - self.label_width - self.label_padding

        self._draw_y_axis()
        self._draw_x_axis()
        return self._plot_data()

    def _draw_y_axis(self):
        label_with_padding = self.label_width + self.label_padding
        zero_position = self.label_width - self.label_padding
        for y in range(self.height):
            self.skeleton[y][label_with_padding] = self.axis_char
        self.skeleton[0][: self.label_width] = self.label
        self.skeleton[self.height - 1][zero_position] = '0'

    def _draw_x_axis(self):
        label_with_padding = self.label_width + self.label_padding
        while label_with_padding < self.width - 2:
            self.skeleton[self.height - 1][label_with_padding] = '.'
            label_with_padding += 1
            self.skeleton[self.height - 1][label_with_padding] = ' '
            label_with_padding += 1

    def _plot_data(self):
        x = self.label_width + self.label_padding + 2
        for d in self.data:
            p = d / self.max
            y = round((self.height - 2) * p)
            c = self.negative_point_char if y < 0 else self.point_char
            y = abs(y)
            while y:
                y = y - 1
                self.skeleton[abs(y - self.height) - 2][x] = c
            x = x + 2
        self._add_padding()
        return '\n'.join([''.join(line) for line in self.skeleton])

    def _add_padding(self):
        line_width = len(self.skeleton[0])
        blank_line = [' '] * line_width
        # On Y axis
        self.skeleton.insert(0, blank_line)
        self.skeleton.append(blank_line)
        # On X axis
        self.skeleton = [[' '] * self.padding + line for line in self.skeleton]
