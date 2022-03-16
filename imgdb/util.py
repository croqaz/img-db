import re
import operator
from difflib import ndiff, SequenceMatcher
from typing import no_type_check


def to_base(num, b, alpha='123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'):
    # max base 36: 0123456789abcdefghijklmnopqrstuvwxyz
    # max base 58: 123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ
    # ref: https://stackoverflow.com/a/53675480
    return '0' if not num else to_base(num // b, b, alpha).lstrip('0') + alpha[num % b]


def hamming_distance(s1: str, s2: str):
    """ The Hamming distance between equal-length strings """
    if len(s1) != len(s2):
        return float('inf')
    return sum(el1 != el2 for el1, el2 in zip(s1, s2))


@no_type_check
def levenshtein_distance(s1: str, s2: str):
    """
    Levenshtein distance between strings
    ref: https://codereview.stackexchange.com/a/217074
    """
    counter = {'+': 0, '-': 0}
    distance = 0
    for edit_code, *_ in ndiff(s1, s2):
        if edit_code == ' ':
            distance += max(counter.values())
            counter = {'+': 0, '-': 0}
        else:
            counter[edit_code] += 1
    distance += max(counter.values())
    return distance


def sm_ratio(s1: str, s2: str):
    """ SequenceMatcher string distance ratio """
    return SequenceMatcher(None, s1, s2).ratio()


def rgb_to_hex(color_pair: tuple) -> str:
    # ex: (111, 78, 55) -> #6F4E37
    assert len(color_pair) >= 3, 'Need 3 colors'
    return '#{:02x}{:02x}{:02x}'.format(*color_pair)


def hex_to_rgb(color: str) -> tuple:
    # ex: #914E72 -> (145, 78, 114)
    color = color.lstrip('#')
    assert len(color) >= 6, 'Need a HEX string'
    r_hex = color[0:2]
    g_hex = color[2:4]
    b_hex = color[4:6]
    return int(r_hex, 16), int(g_hex, 16), int(b_hex, 16)


def html_escape(s: str) -> str:
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace('"', "&quot;").replace('\'', "&#x27;")
    return s


def parse_query_expr(expr) -> list:
    """" Parse query expressions coming from --filter args """
    if isinstance(expr, str):
        items = [s for s in re.split('[,; ]', expr) if s]
    elif isinstance(expr, (list, tuple)):
        items = []
        for exp in expr:
            items.extend(s for s in re.split('[,; ]', exp) if s)
    else:
        raise Exception('Invalid filter expression type')

    if len(items) % 3 != 0:
        raise Exception('Invalid filter expression length')

    from .img import IMG_ATTRS, get_attr_type
    EXP = {
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        '=': operator.eq,
        '==': operator.eq,
        '!=': operator.ne,
        '~': lambda val, pat: bool(re.search(pat, val)),
        '!~': lambda val, pat: not re.search(pat, val),
    }
    i = 0
    aev = []
    result = []
    for word in items:
        # is it a meta?
        if not i:
            if word not in IMG_ATTRS:
                raise Exception(f'Invalid property name: "{word}"')
            aev.append(word)
        # is it an expression?
        elif i == 1:
            if word not in EXP:
                raise Exception(f'Invalid expression name: "{word}"')
            aev.append(EXP[word])
        # it must be a value
        else:
            if get_attr_type(aev[0]) is int:
                aev.append(int(word, 10))
            else:
                aev.append(word)
        if i > 1:
            i = 0
            result.append(aev)
            aev = []
        else:
            i += 1

    return result
