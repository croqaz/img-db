# img-DB

  [![Build Status][build-image]][build-url]
  [![Code coverage][cover-image]][cover-url]
  [![Python ver][python-image]][python-url]

This is img-DB, a CLI application for organizing your images, written in Python.

Check the docs **in [Docs/readme.md](https://github.com/croqaz/img-db/blob/main/docs/readme.md)**.


## WHO is this for?
It's for anyone comfortable enough to run a CLI app with lots of options.<br>
At the moment, there are rough edges...

## WHAT'S special about it?
There's many picture organizing apps, many of them are VERY good, but the most distinctive feature of img-DB is that it generates real folders that you can explore with a regular file explorer and that the database is an HTML gallery that you can just open in any browser. To me, this idea is very powerful.

## WHY did I make this project?
Because I want to get rid of iCloud, Google Photos, Dropbox and other horrible, privacy nightmare cloud services.<br>
img-DB is open source, offline, private, it doesn't upload your pictures anywhere (but you could, if you wanted to).

## WHEN did I start this?
Probably in 2015, I started collecting all kinds of Python scripts for auto-renaming pictures, auto-resizing, converting, compressing, etc.<br>
The scripts became a mess and I thought to organize them into a proper project and also I was absolutely fascinated by the idea of creating smart folders from an archive.<br>
The DB as a HTML file was more like a debug feature initially, so I can see what I'm importing, but it looks like the LXML parser can easily handle tens of thousands of IMG elements instantly, so it became a core feature.

## BIG DISCLAINER
This is my hobby project AND I have a *full time job* AND I have a family. In other words, I may not have time to fully support this project.

Also the code is not sufficiently tested!

However, issues and PRs are welcome!


## Similar

- https://github.com/novoid/filetags -- the original inspiration of this project
- https://github.com/LycheeOrg/Lychee -- photo management server written in PHP
- https://github.com/photoprism/photoprism -- AI-powered app for browsing, organizing & sharing, powered by Go and TensorFlow
- https://github.com/zenphoto/zenphoto -- open-source gallery and CMS project
- https://wiki.gnome.org/Apps/Shotwell
- https://wiki.gnome.org/Apps/Gthumb

## License

[MIT](LICENSE) © Cristi Constantin.


[build-image]: https://github.com/croqaz/img-db/workflows/Python/badge.svg
[build-url]: https://github.com/croqaz/img-db/actions
[cover-image]: https://codecov.io/gh/croqaz/img-db/branch/main/graph/badge.svg?token=PR0PO1R23K
[cover-url]: https://codecov.io/gh/croqaz/img-db
[python-image]: https://img.shields.io/badge/Python-3.9-blue.svg
[python-url]: https://python.org
