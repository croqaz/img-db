import numpy
import scipy.fftpack
from PIL import Image

from .util import to_base


def array_to_string(arr, base=36):
    bit_string = ''.join(str(b) for b in 1 * arr.flatten())
    width = len(to_base(int('1' * len(bit_string), 2), base))
    return to_base(int(bit_string, 2), base).zfill(width)


def ahash(image, hash_sz=12):
    """
    Average Hash computation
    following: http://hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    Step by step explanation: https://web.archive.org/web/20171112054354/https://www.safaribooksonline.com/blog/2013/11/26/image-hashing-with-python/
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    # reduce size and complexity, then covert to grayscale
    image = image.convert("L").resize((hash_sz, hash_sz), Image.ANTIALIAS)
    # find average pixel value; 'pixels' is an array of the pixel values, ranging from 0 (black) to 255 (white)
    pixels = numpy.asarray(image)
    avg = numpy.mean(pixels)
    # create string of bits
    return pixels > avg


def diff_hash(image, hash_sz=12):
    """
    Difference Hash computation.
    Computes differences horizontally.
    following: http://hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    image = image.convert("L").resize((hash_sz + 1, hash_sz), Image.ANTIALIAS)
    pixels = numpy.asarray(image)
    # compute differences between columns
    return pixels[:, 1:] > pixels[:, :-1]


def diff_hash_vert(image, hash_sz=12):
    """
    Difference Hash computation.
    Computes differences vertically.
    following: http://hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    image = image.convert("L").resize((hash_sz, hash_sz + 1), Image.ANTIALIAS)
    pixels = numpy.asarray(image)
    # compute differences between rows
    return pixels[1:, :] > pixels[:-1, :]


def phash(image, hash_sz=12, highfreq_fact=4):
    """
    Perceptual Hash computation.
    following: http://hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    img_size = hash_sz * highfreq_fact
    image = image.convert("L").resize((img_size, img_size), Image.ANTIALIAS)
    pixels = numpy.asarray(image)
    dct = scipy.fftpack.dct(scipy.fftpack.dct(pixels, axis=0), axis=1)
    dctlowfreq = dct[:hash_sz, :hash_sz]
    med = numpy.median(dctlowfreq)
    return dctlowfreq > med
