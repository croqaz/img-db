# Filter flag

The --filter flag is used in add, readd, gallery and links.<br>
It is a *mini language* that allows selecting a smaller number of files, only those that match.

The format is very simple: `attribute expression value ;`
You can use many filters, separated by `;` or `,`.

Examples:

```
--filter 'bytes >= 1000000'
--filter 'format = PNG'
--filter 'mode = RGB'
--filter 'make-model ~~ iphone'
--filter 'width > 1000 ; height > 700'
```

## attributes

Any attributes available for the images can be used, if they are available:

- pth
- format
- mode
- bytes
- width
- height
- date
- make-model
- top-colors
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
- `~~` : REGEX match, case insensitive
- `!~` : the opposite of the REGEX match
- `!~~` : the opposite of the case insensitive REGEX match

## values

The values can be numbers, or text. The text doesn't need quotes.<br>
If you need to use an empty text as value, you can use `''` or `""`, for example:<br>
`--filter 'date != ""'` in this case you want to make sure the date is not empty.
