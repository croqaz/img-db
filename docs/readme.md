# img-DB CLI

Below is the list of commands you can use.

## add

Add (import) images into img-DB.<br>
By default, this will copy all images into an archive folder and create a DB with all attributes extracted for each image.<br>
You can optionally move, or hard-link the images from their original location, into the archive folder.<br>
The images are renamed with an UID that represents their content hash (Blake2b hash, or SHA256, etc).

The DB contains all kinds or props about each image:

- the UID, which is a unique name within the archive
- the full path, which is used when creating links and checking missing images
- image format (eg: JPEG, PNG, GIF)
- image mode (eg: RGB, RGBA, CMYK, LAB)
- bytes: the image size on disk
- size: the width and height of the image
- date when image was created (this may be empty in some cases)
- make-model: the camera maker and model, if the photo was created with a phone, or a camera (this will be empty if the image doesn't have this info)
- top-colors: a list of dominant colors from the image. Eg: "#000000=50" (this means the image has 50% black, so it's very dark)
- different [content hashes](hashes.md) like: BLAKE2B, SHA224, SHA256, SHA512, MD5, which are not useful unless you are paranoia about having absolutely unique images
- different [visual hashes](hashes.md) like: ahash, dhash, vhash, bhash, etc, which are useful for detecting duplicates in the archive
- different EXIF, IPTC, XMP metadata extracted from a photo like: ISO, aperture, shutter speed, rating, keywords, labels, headline, caption

The DB is actually a HTML file that you could open in your browser, but if you imported tons of images (more than 10k), you coult crash your browser, so maybe don't do it because this file is not for you, unless you want to debug it. To make it useful for you, it's better to use the "gallery" feature to export the DB into a user friendly HTML file, limited to 1000 images per file.

Import flags:

- config='' : a JSON config file, so you don't have to type so many flags
- operation='copy' : the operation used when creating the archive. Options: copy, move, link
- hashes='blake2b' : different [content hashes](hashes.md) you can add in the DB. Not that useful really
- v_hashes='dhash' : different [visual hashes](hashes.md) you can add in the DB. Useful for comparing against duplicates
- metadata=''  : extra metadata that you can extract from an image. Options: aperture, shutter-speed, iso, rating, label, keywords, headline, caption
- filter=''    : check [filter.md doc](filter.md)
- exts=''      : only import images that match specified extensions. Eg: 'JPG, JPEG, PNG'
- limit=0      : stop after importing X limit images
- thumb_sz=64  : the thumbnail size included in the DB. This is useful when generating the galleries
- thumb_qual=70 : the image quality of the thumb in DB. The bigger, the more space it will take
- thumb_type='webp' : the image format of the thumb in DB. WEBP is a great format
- dbname='imgdb.htm' : the name of the DB where to save the images
- workers=4 : how many threads to use when importing. More threads make the import faster, but they use more CPU and memory
- skip_imported=False : skip files that are already imported in the DB
- deep=False    : deep search of files
- force=False   : use the force
- shuffle=False : randomize file order before import, makes sense when using limit
- silent=False  : only show error logs
- verbose=False : show all debug logs


Examples:

```sh
# basic import command
# this will copy the images from 'Pictures/iPhone8/' into 'Pictures/archive/' and also create the 'imgdb.htm' DB file
python -m imgdb add 'Pictures/iPhone8/' -o 'Pictures/archive/' --dbname imgdb.htm

# you can import the same folder again if you want to refresh the DB with extra info, or change the size of the embedded thumbnail
# this command will NOT copy the files again, if they were imported previously, only the content of the DB will be updated
python -m imgdb add 'Pictures/iPhone8/' -o 'Pictures/archive/' --dbname imgdb.htm --thumb-sz 256 --v-hashes 'dhash, bhash, rchash' --metadata 'shutter-speed, aperture, iso' --verbose
```


## readd

Re-import images to normalize your existing DB:

- if you want all your images to have the same thumb size, same content hashes, same visual hashes, same metadata
- if the already imported images don't have enough props, maybe you want to calculate all visual hashes for all the images
- if you want to change the UID of the images (if you know what you're doing)
- it's also possible that some images from the archive don't have the same content hash anymore, because they were edited, eg: in an external image editor.


## rename

Rename (and move) images. This command doesn't use, and doesn't create a DB.<br>
**BE CAREFUL** WITH RENAME! If you provide a bad name template, you WILL OVERWRITE AND LOSE your images!<br>
By default the search is not deep, only the images in the immediate folder are renamed.<br>
If you want to create dynamic folders, specify them in the --name flag.<br>
Useful if you have folders with all kinds of images, random names, and you want to normalize all names by using different properties extracted from the images.<br>
The most useful example is to move all images into folders organized by date, or camera model.

Flags:

- input  : one or more folders to rename from
- output : the output folder path
- o=''   : alias for output
- name   : the base name used to rename all imgs
- exts='' : only process images that match specified extensions
- limit=0 : stop after processing X imgs
- hashes='blake2b'
- v_hashes='dhash'
- metadata=''   : extra metadata that you can extract from an image
- deep=False    : deep search of files
- force=False   : use the force
- shuffle=False : randomize file order before import, makes sense when using limit
- silent=False  : only show error logs
- verbose=False : show all debug logs

Examples:

```sh
# the most boring rename, use the content hash as the new name of the image
python -m imgdb rename 'Pictures/Fujifilm/' -o 'Pictures/normalized/' --name '"{blake2b}"'

# deep rename using the date and a small part of the UID as file name
python -m imgdb rename 'Pictures/Fujifilm/' -o 'Pictures/normalized/' --deep --name '"{Date:%Y-%m-%d-%X}-{dhash:.8s}{Pth.suffix}"'
```


## gallery

Use the DB and created with the ADD command to generate HTML galleries that you can view in your browser.<br>
This command basically extracts the images from DB as they are, and exports them using a template, wrapped to 1000 images per page.<br>
Because the gallery is generated from a template, there's lots of room to improve and customize here, like creating themes, to view the gallery in different ways.

Flags:

- name : the base name of the HTML file, including path. Eg: img_gallery
- config='' : a JSON config file, so you don't have to type so many flags
- tmpl='img_gallery.html' : a custom Jinja2 template file; it will be loaded from tmpl/ folder;
- wrap_at=1000 : create another gallery file every X images
- filter='' : check [filter.md doc](filter.md)
- exts=''   : only process images that match specified extensions. Eg: 'JPG, PNG'
- limit=0   : stop after processing X limit images
- dbname= 'imgdb.htm' : the name of the DB where to load the images
- silent=False  : only show error logs
- verbose=False : show all debug logs

Examples:

```sh
# the most basic command, export all your images into several 'img_gallery-xx.htm' files,
# depending on the size of your DB
python -m imgdb gallery ~/Documents/img_gallery --filter 'bytes > 10000'

# gallery idea: all the pictures from specific years
python -m imgdb gallery gallery_2020_2021 --filter 'date >= 2020 ; date <= 2021'

# gallery idea: all the pictures taken with a Sony camera (case sensitive)
python -m imgdb gallery gallery_sony --filter 'make-model ~ Sony' --verbose

# gallery idea: all huge pictures
python -m imgdb gallery gallery_xx_large --filter 'width > 3800 ; height >= 2160' --verbose
```


## links

Use the DB and the archive created with the ADD command to generate hard-links (or sym-links) with "smart folders" that point to the archive.<br>
img-DB can create folders of links like:

- all pictures grouped by year, or year-month, or year-month-day, or week day
- all pictures from a very specific day (like Christmas, or a birthday) from all the years
- all pictures grouped by device, like separate folders for: iPhone 8, Canon 70D, Nikon D500, etc
- this is pretty flexible, so imagination is the only limit

Flags:

- name : the template for creating the folder and file links, will use the properties for each image.
    Note: The lower-case meta are either text, or number. The Title-case meta are Python native objects, eg: Date, Pth.
- config='' : a JSON config file, so you don't have to type so many flags
- sym_links=False : use sym-links (soft links) instead or hard-links
- filter='' : check [filter.md doc](filter.md)
- exts=''   : only process images that match specified extensions. Eg: 'JPG, PNG'
- limit=0   : stop after processing X limit images
- dbname= 'imgdb.htm' : the name of the DB where to load the images
- silent=False  : only show error logs
- verbose=False : show all debug logs

Examples:

```sh
# create year-month-day folders, keeping the original file name
# the default DB name used is 'imgdb.htm' and the links are pointing to the archive
python -m imgdb links 'xlinks/{Date:%Y-%m-%d}/{Pth.name}'

# create year-month folders, using the date and a small part of the UID as file name,
# and ignoring date older than 2000 and small images
python -m imgdb links 'xlinks/Sorted-{Date:%Y-%m}/{Date:%Y-%m-%d-%X}-{id:.6s}{Pth.suffix}' --filter 'date > 2000 ; width > 1020' --verbose
```


## db

DB command can be used to interact with the DB in command line, or export it to JSON, JL (JSON lines), CSV or HTML table.<br>
The export is streamed into STDOUT, so it's easy to pipe into other apps.

Examples:

```sh
# export all DB images as JL and pipe into JQ to display all image sizes in bytes
python -m imgdb db export --silent | jq '.bytes'

# export all DB images as JSON and pipe into JQ to display [mode, format]
python -m imgdb db export --silent --format json | jq '.[] | [.mode, .format]'

# export all DB images as a HTML table
python -m imgdb db export --format table > img_table.html

# enter debug mode using iPython
python -m imgdb db debug --verbose
```
