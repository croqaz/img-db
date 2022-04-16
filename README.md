# img-DB

This is img-DB, a CLI application for organizing your images, written in Python.<br>
I made this app to organize my photo collection from 2007, up to today. When I ran the import for the first time on all my folders, there were 80k picture with duplicates, now there are almost 50k pictures, no duplicates.

There are 3 main features, currently:
1. You can import your pictures into img-DB. The import can either *copy*, *move* or *link* your pics into a IMGDB archive, which will rename them with these weird long names. But don't worry, these names are not made for your, they represent the content of the file, and they are just to make sure you don't have duplicate images. Renaming the pictures is optional, but recommended, because it makes it much easier to create smart folders, as you'll see in the next feature.<br>
Just be careful with the MOVE operation, if you pass wrong params and you don't know what you're doing, you can overwrite and lose all your pics, you have been WARNED.<br>
When renaming the pics, you also have the option to convert them, eg: to WEBP, or compress them, eg: with JPEGoptim.<br>
The second thing the import does, is create a database with information about every picture, things like: type, size, date, and different perceptual hashes -- numerical representations of the image.<br>
The import is a CPU intensive operation, it takes a really long time on a raspberry PI, but the other features can be run on a low end machine.<br>
The DB is actually a HTML file that you could open in your browser, but if you imported tons of pictures (more than 10k), this can actually crash your browser, so maybe don't do it, because this file is also not for you... which leads into the second feature.

2. The second feature is linking your pictures from the DB and archive to create "smart folders". img-DB can create folders of links like: "all pictures from year 2020", or "all pictures from march-2020", or "all pictures from a very specific day", or "all Christmas pictures from all the years", or "all pictures taken with a specific device like the iPhone 8". Basically img-DB uses the database from the import step to generate folders and links to the imported pictures.<br>
This feature is pretty customizable and could be used with other apps, for example you could have an app that detects people, or animals, or objects in your pictures and tag them, and then later pick-up the tags in img-DB and create smart folders for each.

3. The third feature is creating HTML galleries from the DB. A gallery is a web page that you can open in the browser, you can see the thumbnails of the pics (potentially in the future: sort them, group them, filter them).<br>
The gallery is generated with a HTML template, so there's lots of room to improve and customize here, like creating themes, to view the gallery in different ways.<br>
I'm storing all my pics and galleries in an old raspberry PI, and they're just static HTML files, which makes it really efficient with limited computing power, but you still have the advanced features that you expect from a native application.

These are the most important features of img-DB. Of course there's other smaller features like exporting the DB in different formats to process it, and so on.

## Usage

``` sh
# basic import command
# by default this will copy the images from 'Pictures/iPhone8/' into 'Pictures/archive/'
# and also create the 'imgdb.htm' file, which contains info about the imported pictures
python -m imgdb add 'Pictures/iPhone8/' -o 'Pictures/archive/' --dbname imgdb.htm

# you can import the same folder again if you want to refresh the DB with extra info,
# or maybe you want to change the size of the embedded thumbnail to a larger size
# this command will NOT copy the files again, if they were imported previously,
# only the content of the DB will be updated
python -m imgdb add 'Pictures/iPhone8/' -o 'Pictures/archive/' --dbname imgdb.htm --thumb-sz 256 --v-hashes 'dhash, bhash, rchash' --metadata 'shutter-speed, aperture, iso' --verbose


# create hard links from the archive, into the folder 'xlinks/'
# inside this folder it will generate folders with the camera Maker and Model from the EXIF of the photos
# the folder 'xlinks/' can be deleted safely, the images from the archive will not be lost
python -m imgdb links 'xlinks/{make-model}/{pth.name}' --dbname imgdb.htm --verbose

# create year-month-day folders, keeping the original file name
# the default DB name used is 'imgdb.htm'
python -m imgdb links 'xlinks/{date:%Y-%m-%d}/{pth.name}'

# create year-month folders, using the date in the file name and ignoring date older than 2000
python -m imgdb links 'xlinks/Sorted-{date:%Y-%m}/{date:%Y-%m-%d-%X}-{id:.6s}{pth.suffix}' --filter 'date > 2000' --verbose


# create HTML galleries from your DB, wrapped to 1000 images
# this will generate several 'img_gallery-01.htm' files, depending on how many pics you have
python -m imgdb gallery img_gallery --filter 'bytes > 10000'

# gallery idea: all the pictures from specific years
python -m imgdb gallery gallery_2020_2021 --filter 'date >= 2020 ; date <= 2021'

# gallery idea: all the pictures taken with a Sony camera
python -m imgdb gallery gallery_sony --filter 'make-model ~ Sony' --verbose
```

## WHAT'S special about it?
There's many picture organizing apps, many of them are VERY good, but the most distinctive feature of img-DB is that it generates real folders that you can explore with a regular file explorer and that the database is an HTML gallery that you can just open in any browser. To me, this idea is very powerful.

## WHY did I make this project?
Because I want to get rid of iCloud, Google Photos, Dropbox and other horrible, privacy nightmare cloud services.<br>
img-DB is open source, it's offline, it doesn't upload your pictures anywhere (but you could, if you wanted to).

## WHEN did I start this?
Probably in 2015, I started collecting all kinds of Python scripts for auto-renaming pictures, auto-resizing, converting, compressing, etc.<br>
The scripts became a mess and I thought to organize them into a proper project and also I was absolutely fascinated by the idea of creating smart folders from an archive.<br>
The DB as a HTML file was more like a debug feature initially, so I can see what I'm importing, but it looks like the LXML parser can easily handle tens of thousands of IMG elements instantly, so it became a core feature.

## BIG DISCLAINER
This is my hobby project AND I have a full time job AND I have a family. In other words, I may not have time to support this project.

Also the code is not sufficiently tested!

However, issues and PRs are welcome!

## Similar

- https://github.com/novoid/filetags -- the original inspiration of this project
- https://github.com/LycheeOrg/Lychee -- photo management server written in PHP
- https://github.com/photoprism/photoprism -- AI-powered app for browsing, organizing & sharing, powered by Go and TensorFlow
- https://github.com/zenphoto/zenphoto -- open-source gallery and CMS project
- https://wiki.gnome.org/Apps/Shotwell

## License

[MIT](LICENSE) © Cristi Constantin.
