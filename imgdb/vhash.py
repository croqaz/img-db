from .config import g_config
from .util import to_base

import numpy
from PIL import Image


def array_to_string(arr, base=g_config.visual_hash_base):
    bit_string = ''.join(str(b) for b in 1 * arr.flatten())
    width = len(to_base(int('1' * len(bit_string), 2), base))
    return to_base(int(bit_string, 2), base).zfill(width)


def ahash(image: Image.Image, hash_sz=g_config.visual_hash_size):
    """
    Average Hash computation
    following: http://hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    Step by step explanation:
    https://web.archive.org/web/20171112054354/https://www.safaribooksonline.com/blog/2013/11/26/image-hashing-with-python
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    # reduce size and complexity, then covert to grayscale
    image = image.convert('L').resize((hash_sz, hash_sz), Image.ANTIALIAS)
    # find average pixel value; 'pixels' is an array of the pixel values, ranging from 0 (black) to 255 (white)
    pixels = numpy.asarray(image)
    avg = numpy.mean(pixels)
    # create string of bits
    return pixels > avg


def diff_hash(image: Image.Image, hash_sz=g_config.visual_hash_size):
    """
    Difference Hash computation, horizontally.
    following: http://hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    image = image.convert('L').resize((hash_sz + 1, hash_sz), Image.ANTIALIAS)
    pixels = numpy.asarray(image)
    # compute differences between columns
    return pixels[:, 1:] > pixels[:, :-1]


def diff_hash_vert(image: Image.Image, hash_sz=g_config.visual_hash_size):
    """
    Difference Hash computations, vertically.
    following: http://hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    image = image.convert('L').resize((hash_sz, hash_sz + 1), Image.ANTIALIAS)
    pixels = numpy.asarray(image)
    # compute differences between rows
    return pixels[1:, :] > pixels[:-1, :]


def dhash_row_col(image: Image.Image, size=g_config.visual_hash_size):
    """
    Inspired by the Dhash implementation from:
    https://github.com/benhoyt/dhash
    """
    width = size + 1
    gray_image = image.convert('L')
    small_image = gray_image.resize((width, width), Image.ANTIALIAS)
    grays = list(small_image.getdata())

    row_hash = 0
    col_hash = 0
    for y in range(size):
        for x in range(size):
            offset = y * width + x
            row_bit = grays[offset] < grays[offset + 1]
            row_hash = row_hash << 1 | row_bit

            col_bit = grays[offset] < grays[offset + width]
            col_hash = col_hash << 1 | col_bit

    return row_hash << (size * size) | col_hash


def phash(image: Image.Image, hash_sz=g_config.visual_hash_size, highfreq_fact=4):
    """
    Perceptual Hash computation.
    following: http://hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    import scipy.fftpack
    img_size = hash_sz * highfreq_fact
    image = image.convert('L').resize((img_size, img_size), Image.ANTIALIAS)
    pixels = numpy.asarray(image)
    dct = scipy.fftpack.dct(scipy.fftpack.dct(pixels, axis=0), axis=1)
    dctlowfreq = dct[:hash_sz, :hash_sz]
    med = numpy.median(dctlowfreq)
    return dctlowfreq > med


def bhash(img: Image.Image, sz=(4, 3)):
    """
    Encoder for the BlurHash algorithm
    https://github.com/woltapp/blurhash-python
    """
    from itertools import chain
    from blurhash._functions import ffi, lib
    image = img.convert('RGB')
    r_band = image.getdata(band=0)
    g_band = image.getdata(band=1)
    b_band = image.getdata(band=2)
    rgb_data = list(chain.from_iterable(zip(r_band, g_band, b_band)))
    width, height = image.size
    image.close()

    rgb = ffi.new('uint8_t[]', rgb_data)
    bytes_per_row = ffi.cast('size_t', width * 3)
    width = ffi.cast('int', width)
    height = ffi.cast('int', height)
    x_components = ffi.cast('int', sz[0])
    y_components = ffi.cast('int', sz[1])

    result = lib.create_hash_from_pixels(x_components, y_components, width, height, rgb, bytes_per_row)

    if result == ffi.NULL:
        raise ValueError('Invalid x_components or y_components')

    return ffi.string(result).decode()


VHASHES = {
    'ahash': ahash,
    'bhash': bhash,
    'dhash': diff_hash,
    'phash': phash,
    'rchash': dhash_row_col,
    'vhash': diff_hash_vert,
}
