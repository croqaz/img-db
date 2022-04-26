# Hashes

There's 2 types of hashes:
- content hash = cryptographical hash, eg: Blake2B, SHA224, SHA256, SHA512, MD5, or whatever is available in https://docs.python.org/3/library/hashlib.html
- visual hash = perceptual hash, which represents the image luminosity, or colors, depending on the algorithm

Cryptographical hashes are pretty straight forward, so there's no point in going in too many details.

A perceptual hash is a fingerprint of an image, derived from various features from its content.
Unlike cryptographic hash functions which rely on the avalanche effect of small changes in input leading to drastic changes in the output, perceptual hashes are "close" to one another if the features are similar.
They are mainly used to detect duplicates, or see how "close" they are to some target images.
Also check: https://crlf.link/mem/visual-hash - Perceptual hash section

The visual hashes in img-DB are derived from:
- https://github.com/JohannesBuchner/imagehash - ahash, phash, diff_hash (dhash), diff_hash_vertical (vhash)
- https://github.com/benhoyt/dhash - it's called dhash here, but in img-DB I call it dhash_row_col (rchash)

There's also Blurhash from https://github.com/woltapp/blurhash-python with just a few changes, but the final hash is the same.

The default v-hash in img-DB is diff_hash (dhash) because it's very fast and decent enough.
One hash is not enough if you want to reliably detect duplicates in a large set of images.
I personally use ALL the v-hashes in my private photo collection.
