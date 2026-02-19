from base64 import b64encode
from typing import Any

import numpy
from blurhash_rs import blurhash_encode
from PIL import Image

from .util import to_base

# image resize quality
BILINEAR = Image.Resampling.BILINEAR

# the visual hash image size; a bigger number generates a longer hash;
# must be larger than 2
# 6px seems to produce the most consistent groups of similar images
VISUAL_HASH_SIZE: int = 6

# the base used to convert visual hash numbers into strings
# a bigger number generates shorter hashes, but harder to read
# between 16 and 83
VISUAL_HASH_BASE: int = 36


def array_to_string(arr, base=VISUAL_HASH_BASE):
    # Boolean array to a string representation in the specified base
    bit_string = ''.join(str(b) for b in 1 * arr.flatten())
    width = len(to_base(int('1' * len(bit_string), 2), base))
    return to_base(int(bit_string, 2), base).zfill(width - 1)


def ahash(gray_image: Image.Image, hash_sz=VISUAL_HASH_SIZE) -> numpy.ndarray:
    """
    Average Hash computation
    following: http://hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    Step by step explanation:
    https://web.archive.org/web/20171112054354/https://www.safaribooksonline.com/blog/2013/11/26/image-hashing-with-python
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    # reduce size and complexity, then covert to grayscale
    img = gray_image.resize((hash_sz, hash_sz), BILINEAR)
    # find average pixel value; 'pixels' is an array of the pixel values, ranging from 0 (black) to 255 (white)
    pixels = numpy.asarray(img)
    avg = numpy.mean(pixels)
    # create string of bits
    return pixels > avg


def diff_hash_horiz(gray_image: Image.Image, hash_sz=VISUAL_HASH_SIZE) -> numpy.ndarray:
    """
    Difference Hash computation, horizontally.
    following: http://hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    img = gray_image.resize((hash_sz + 1, hash_sz), BILINEAR)
    pixels = numpy.asarray(img)
    # compute differences between columns
    return pixels[:, 1:] > pixels[:, :-1]


def diff_hash_vert(gray_image: Image.Image, hash_sz=VISUAL_HASH_SIZE) -> numpy.ndarray:
    """
    Difference Hash computations, vertically.
    following: http://hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
    ref: https://github.com/JohannesBuchner/imagehash/blob/master/imagehash.py
    """
    img = gray_image.resize((hash_sz, hash_sz + 1), BILINEAR)
    pixels = numpy.asarray(img)
    # compute differences between rows
    return pixels[1:, :] > pixels[:-1, :]


def combined_hash(gray_image: Image.Image) -> numpy.ndarray:
    """
    Combined/ composed hash, ahash | horiz-hash | vert-hash.
    """
    dhash_h = diff_hash_horiz(gray_image)
    dhash_v = diff_hash_vert(gray_image)
    chash_arr = numpy.concatenate([ahash(gray_image), dhash_h, dhash_v])
    return numpy.packbits(chash_arr)


def dhash_row_col(gray_image: Image.Image, size=VISUAL_HASH_SIZE) -> numpy.ndarray:
    """
    Inspired by the Dhash implementation from:
    https://github.com/benhoyt/dhash
    """
    width = size + 1
    small_image = gray_image.resize((width, width), BILINEAR)
    grays = numpy.asarray(small_image).ravel()

    row_bits = []
    col_bits = []
    for y in range(size):
        for x in range(size):
            offset = y * width + x
            row_bit = grays[offset] < grays[offset + 1]
            row_bits.append(row_bit)
            col_bit = grays[offset] < grays[offset + width]
            col_bits.append(col_bit)
    return numpy.packbits(numpy.concatenate([row_bits, col_bits]))


def bhash(image: Image.Image, sz=(4, 4)) -> str:
    """
    The BlurHash algorithm is usually calculated somewhere else
    in the code and cached.
    """
    return blurhash_encode(image, x_components=sz[0], y_components=sz[1])


#
# Experimental hashes
#

# from scipy.fftpack import dct
# from scipy.ndimage import gaussian_filter
# def compute_robust_hash(image: Image.Image, hash_sz=VISUAL_HASH_SIZE) -> numpy.ndarray:
#     """
#     Rough implementation of the VHash algorithm described in the paper:
#     Perceptual robust hashing for color images with canonical correlation analysis
#     https://arxiv.org/pdf/2012.04312 (arXiv:2012.04312)
#     """
#     # Preprocessing: Load, Resize, and Blur
#     # Downsize to a square to normalize and use RGB to capture color info
#     img = image.convert('RGB').resize((8, 8), Image.Resampling.LANCZOS)
#     img_array = numpy.array(img).astype(float)

#     # Apply Gaussian filter to remove high-frequency noise (as per paper)
#     img_filtered = gaussian_filter(img_array, sigma=1)

#     # Feature Extraction (Luminance + Color)
#     # Convert to YCbCr to separate structure (Y) from color (Cb, Cr)
#     # Y = 0.299R + 0.587G + 0.114B
#     y = 0.299 * img_filtered[..., 0] + 0.587 * img_filtered[..., 1] + 0.114 * img_filtered[..., 2]
#     cb = -0.1687 * img_filtered[..., 0] - 0.3313 * img_filtered[..., 1] + 0.5 * img_filtered[..., 2]
#     cr = 0.5 * img_filtered[..., 0] - 0.4187 * img_filtered[..., 1] - 0.0813 * img_filtered[..., 2]

#     # Frequency Domain Transformation (Simplified Global Feature)
#     # The paper uses GLCM/CCA; a robust functional equivalent for sorting is the DCT
#     # of these channels which captures the structural "energy"
#     def get_low_freq_coeffs(channel):
#         c_dct = dct(dct(channel.T, norm='ortho').T, norm='ortho')
#         # Extract the top-left hash_size x hash_size low-frequency coefficients
#         return c_dct[:hash_sz, :hash_sz].flatten()

#     y_feat = get_low_freq_coeffs(y)
#     cb_feat = get_low_freq_coeffs(cb)
#     cr_feat = get_low_freq_coeffs(cr)

#     # Deterministic Fusion
#     # We combine structural (Y) and color (Cb, Cr) components
#     combined_features = numpy.concatenate([y_feat, cb_feat, cr_feat])

#     # Binarization (Quantization)
#     # Use the median as a threshold to ensure an even distribution of 0s and 1s
#     avg = numpy.median(combined_features)
#     return numpy.packbits(combined_features > avg)


VHASHES = {
    'ahash': ahash,
    'bhash': bhash,
    'chash': combined_hash,
    'dhash': diff_hash_horiz,
    'rchash': dhash_row_col,
    'vhash': diff_hash_vert,
}


def run_vhash(images: dict[str, Any], algo: str) -> str:
    # This function is supposed to be called from img_to_meta(),
    # so images dict will always contain 64px and larger Images.
    if algo == 'bhash':
        if 'bhash' in images:
            return images['bhash']
        else:
            return bhash(images['256px'])

    # if algo == 'rhash':
    #     val = VHASHES[algo](images['64px'])
    #     return b64encode(val).decode('ascii')

    images['l'] = images['64px'].convert('L')
    val = VHASHES[algo](images['l'])
    if algo == 'chash' or algo == 'rchash':
        # Combined hash has UINT8 type,
        # so it's more efficient to encode it as base64
        return b64encode(val).decode('ascii')
    else:
        return array_to_string(val, VISUAL_HASH_BASE)
