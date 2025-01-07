import tomllib
from pathlib import Path

from imgdb import config, img

EXPECT = tomllib.load(open('test/expect.toml', 'rb'))  # noqa


def test_images():
    cfg = config.Config()
    cfg.metadata = []

    for name in EXPECT:
        pth = Path(f'test/{name}')
        _, nfo = img.img_to_meta(pth, cfg)
        # print(name, nfo)
        nfo.update(nfo['__e'])
        del nfo['__e']

        nfo['maker_model'] = nfo['maker-model']
        nfo['aperture'] = img.get_aperture(nfo)
        nfo['focal_length'] = img.get_focal_length(nfo)
        nfo['shutter_speed'] = img.get_shutter_speed(nfo)

        for key, expect in EXPECT[name].items():
            value = str(nfo[key])
            assert value == expect
