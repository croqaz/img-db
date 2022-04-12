class Bar:
    """ From: https://github.com/lord63/ascii_art """
    def __init__(self, data, width=78, bar_chr='#'):
        self.data = data
        self.width = width
        self.bar_chr = bar_chr
        # prepare data
        self.max_key_len = max([len(key) for key in self.data.keys()])
        self.max_val = max(self.data.values())
        self.items = self.data.items()

    def render(self):
        result = ''
        for k, v in self.items:
            p = v / self.max_val
            shown = round(self.width * p)
            shown = shown + 1 if shown == 0 and v != 0 else shown
            blank = self.width - shown
            bar = self.bar_chr * (shown) + ' ' * (blank)
            result += "{:>{}s} | {} | {}\n".format(k, self.max_key_len, bar, v)
        return '\n' + result
