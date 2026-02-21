.PHONY: test clean update lint coverage

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*.orig' `
	rm -rf .*py*_cache
	rm -rf *.egg-info
	rm -f .coverage*
	rm -r coverage.xml
	rm -rf dist

lint:
	uv run ruff check imgdb/ test/

coverage:
	uv run pytest --cov-report term --cov-report xml --cov=imgdb/ test/

test:
	uv run pytest -ra -sv test/

build:
	uv run pyinstaller imgdb/__main__.py --name imgdb --optimize 2 \
	--add-data imgdb/tmpl:imgdb/tmpl --add-data imgdb/server/static:imgdb/server/static --add-data imgdb/server/views:imgdb/server/views \
	--onefile --nowindow
