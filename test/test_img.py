from bs4 import BeautifulSoup
from PIL import Image

from imgdb.algorithm import top_colors
from imgdb.config import Config
from imgdb.img import el_to_meta, img_to_meta, meta_to_html


def test_img_meta():
    img, m = img_to_meta('test/pics/Mona_Lisa_by_Leonardo_da_Vinci.jpg', Config())
    assert m and isinstance(m, dict)
    assert img and isinstance(img, Image.Image)
    assert m['format'] == 'JPEG' and m['mode'] == 'RGB'

    img, m = img_to_meta('test/pics/Claudius_Ptolemy_The_World.png')
    assert m['format'] == 'PNG' and m['mode'] == 'P'

    p = 'test/pics/Aldrin_Apollo_11.jpg'
    img, m = img_to_meta(p)
    assert m['pth'] == p and m['format'] == 'JPEG' and m['mode'] == 'RGB'


def test_el_meta():
    soup = BeautifulSoup(
        """<img data-blake2b="8e67c10552405140d9f818baf3764224d48e98ae89440542" data-bytes="76" data-dhash="0000000000000000000000000000" data-format="PNG" data-mode="RGB" data-pth="Pictures/archive/8e67c10552405140d9f818baf3764224d48e98ae89440542.png" data-size="8,8" id="8e67c10552405140d9f818baf3764224d48e98ae89440542" src="data:image/webp;base64,UklGRjgAAABXRUJQVlA4ICwAAABwAQCdASoIAAgAAkA4JaACdAFAAAD+76xX/unr//aev/9p6/qZ8jnelRgAAA=="/>""",
        'lxml',
    )
    meta = el_to_meta(soup.img)  # type: ignore

    assert len(meta['id'])
    assert meta['mode'] == 'RGB'
    assert meta['format'] == 'PNG'
    assert meta['dhash'] == 28 * '0'
    assert isinstance(meta['bytes'], int) and meta['bytes'] > 50
    assert isinstance(meta['width'], int) and meta['width'] == 8
    assert isinstance(meta['height'], int) and meta['height'] == 8


def test_meta_to_html_back():
    m = {
        'id': 'asdzxc123',
        'pth': '/some/place/somewhere/img.jpg',
        'format': 'JPEG',
        'mode': 'RGB',
        'bytes': 1234,
        '__t': Image.new('RGB', (32, 32)),
    }
    h = meta_to_html(m, Config())
    assert h.startswith('<img id')
    del m['__t']
    soup = BeautifulSoup(h, 'lxml')
    n = el_to_meta(soup.img)  # type: ignore
    for k in m:
        assert str(n[k]) == str(m[k])


def test_top_colors():
    img = Image.new('RGB', (32, 32))
    assert top_colors(img) == ['#000000=100.0']
    img = Image.new('RGB', (32, 32), (255, 254, 253))
    assert top_colors(img) == ['#ffffff=100.0']
