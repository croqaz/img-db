from argparse import Namespace
from bs4 import BeautifulSoup
from base64 import b64encode
from io import BytesIO
from PIL import Image


def img_to_html(img: Image.Image, m: dict, opts: Namespace) -> str:
    props = []
    for key, val in m.items():
        if key == 'id':
            continue
        if val is None:
            continue
        if isinstance(val, (tuple, list)):
            val = ','.join(str(x) for x in val)
        elif isinstance(val, (int, float)):
            val = str(val)
        props.append(f'data-{key}="{val}"')

    img = img.copy()
    img.thumbnail((opts.thumb_sz, opts.thumb_sz))
    fd = BytesIO()
    img.save(fd, format=opts.thumb_type, quality=opts.thumb_qual)
    m['thumb'] = b64encode(fd.getvalue()).decode('ascii')

    return f'<img id="{m["id"]}" {" ".join(props)} src="data:image/webp;base64,{m["thumb"]}">\n'


def db_query(opts: Namespace):
    db = BeautifulSoup(open(opts.db), 'lxml')
    print(f'There are {len(db.find_all("img"))} imgs in img-DB')
    from IPython import embed
    embed(colors='linux')


def db_gc(*args) -> str:
    print('DB compacting...')
    images = {}
    for content in args:
        _gc_one(content, images)
    tmpl = '<!DOCTYPE html><html lang="en">\n<head><meta charset="utf-8">' + \
           '<title>img-DB</title></head>\n<body>\n{}\n</body></html>'
    elems = []
    for el in sorted(images.values(),
                     reverse=True,
                     key=lambda el: el.attrs.get('data-date', '00' + el['id'])):
        elems.append(str(el))
    print(f'Compacted {len(elems)} imgs')
    return tmpl.format('\n'.join(elems))


def _gc_one(content, images: dict):
    for img in BeautifulSoup(content, 'lxml').find_all('img'):
        img_id = img['id']
        if img_id in images:
            _merge_imgs(images[img_id], img)
        else:
            images[img_id] = img


def _merge_imgs(img1, img2):
    # the logic is to assume the second IMG is newer,
    # so it contains fresh & better information
    for key, val in img2.attrs.items():
        img1[key] = val
