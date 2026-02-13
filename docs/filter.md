# Filter flag

The `--filter` flag is used in add, readd, gallery and links.<br>
It is a basic *mini language* that allows filtering a smaller number of files.

The format is very simple: `attribute expression value ;`<br>
You can use many filters, separated by `;` or `,`. The extra spaces are ignored.

Examples:

```
--filter 'bytes >= 1000000'
--filter 'format = PNG'
--filter 'mode = RGB'
--filter 'maker-model ~~ iphone'
--filter 'width > 1000 ; height > 700'
--filter 'date ~ 2[0-9]{3}-12-25'  (match images taken on Christmas, any year)
```

## attributes

Any attributes available for the images can be used, if they are available:

- pth -- the path to the original image file, should be unique
- format -- the image format (eg. JPEG, PNG, WEBP, TIFF, etc)
- mode -- the image mode (eg. RGB, RGBA, CMYK, etc)
- bytes -- the image size in bytes, as an integer
- width | height | size -- the image size in pixels
- date -- the image creation date, in ISO format (eg. "2012-11-25 11:22:33")
- maker-model -- photo camera maker and model (eg. "Canon-PowerShot-A560")
- lens -- photo camera camera lens (eg. "24.0-70.0-mm-f/2.8")
- top-colors -- top colors in the image, a list of hex color code and percentage (eg. "#999999=60.1,#333333=30.7,#666666=10.2")
- illumination | saturation | contrast -- calculated value for the respective algorithms, a number between 0 and 100
- different metadata extracted from EXIF, IPTC, XMP of the image, if that metadata was extracted on import
- content hashes (but it doesn't make much sense)
- visual hashes (again it doesn't make much sense)

## expressions

- `<` : less than
- `<=` : less than equal
- `>` : greater than
- `>=` : greater than equal
- `=` : equals
- `==` : equals
- `!=` : not equals
- `~` : REGEX match
- `!~` : the opposite of the REGEX match
- `~~` : REGEX match, case insensitive
- `!~~` : the opposite of the case insensitive REGEX match

## values

The values can be numbers, or text. The text doesn't use quotes.

If you need to use an empty text as value, you can use `''` or `""`, for example:<br>
`--filter 'date != ""'` in this case you want to make sure the date is not empty.
