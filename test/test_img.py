from imgdb.img import *
from PIL import Image
from bs4 import BeautifulSoup


def test_img_meta():
    img, m = img_to_meta('test/pics/Mona_Lisa_by_Leonardo_da_Vinci.jpg')
    assert(m and isinstance(m, dict))
    assert(img and isinstance(img, Image.Image))
    assert(m['format'] == 'JPEG' and m['mode'] == 'RGB')

    img, m = img_to_meta('test/pics/Claudius_Ptolemy_The_World.png')
    assert(m['format'] == 'PNG' and m['mode'] == 'P')


def test_el_meta():
    soup = BeautifulSoup('''<img data-blake2b="8e67c10552405140d9f818baf3764224d48e98ae89440542" data-bytes="76" data-dhash="0000000000000000000000000000" data-format="PNG" data-mode="RGB" data-pth="Pictures/archive/8e67c10552405140d9f818baf3764224d48e98ae89440542.png" data-size="8,8" id="8e67c10552405140d9f818baf3764224d48e98ae89440542" src="data:image/webp;base64,UklGRjgAAABXRUJQVlA4ICwAAABwAQCdASoIAAgAAkA4JaACdAFAAAD+76xX/unr//aev/9p6/qZ8jnelRgAAA=="/>''', 'lxml')
    meta = el_to_meta(soup.img)

    assert(len(meta['id']))
    assert(meta['mode'] == 'RGB')
    assert(meta['format'] == 'PNG')
    assert(meta['dhash'] == 28 * '0')
    assert(isinstance(meta['bytes'], int) and meta['bytes'] > 50)
    assert(isinstance(meta['width'], int) and meta['width'] == 8)
    assert(isinstance(meta['height'], int) and meta['height'] == 8)
