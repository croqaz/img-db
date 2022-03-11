from imgdb.img import *
from imgdb.main import *
from imgdb.__main__ import parse_args
from PIL import Image


def test_img_meta():
    opts = parse_args(['test/pics'])

    img, m = img_meta('test/pics/Mona_Lisa_by_Leonardo_da_Vinci.jpg', opts)
    assert(m and isinstance(m, dict))
    assert(img and isinstance(img, Image.Image))
    assert(m['format'] == 'JPEG' and m['mode'] == 'RGB')

    img, m = img_meta('test/pics/Claudius_Ptolemy_The_World.png', opts)
    assert(m['format'] == 'PNG' and m['mode'] == 'P')
