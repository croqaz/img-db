.PHONY: test clean update lint coverage

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*.orig' `
	rm -rf .*py*_cache
	rm -rf *.egg-info
	rm -f .coverage
	rm -r coverage.xml
	rm -rf dist

lint:
	poetry run python -m pflake8 imgdb test
	poetry run python -m mypy imgdb

coverage:
	poetry run python -m pytest --cov-report term --cov-report xml --cov=imgdb/ test/

test:
	poetry run python -m pytest -ra -sv test/
