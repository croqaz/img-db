from PIL import Image


def dhash_img(img: Image.Image, base=36, hash_sz=12) -> str:
    int_hash = dhash_img_row_col(img, hash_sz)
    dhash = to_base(int_hash, base)
    return dhash[::-1]


def to_base(num, b, alpha='0123456789abcdefghijklmnopqrstuvwxyz'):
    # max base: 36
    # ref: https://stackoverflow.com/a/53675480
    return '0' if not num else to_base(num // b, b).lstrip('0') + alpha[num % b]


def dhash_img_row_col(image, size=12):
    """
    Calculate row and column difference hash for given image.
    DHash original source: https://github.com/benhoyt/dhash
    """
    width = size + 1
    grays = get_img_grays(image, width, width)

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


def get_img_grays(image, width, height):
    """
    Convert image to grayscale, downsize to width*height, and return list
    of grayscale integer pixel values (for example, 0 to 255).
    """
    gray_image = image.convert('L')
    small_image = gray_image.resize((width, height), Image.ANTIALIAS)
    return list(small_image.getdata())
