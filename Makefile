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
	pflake8 imgdb test
	mypy imgdb

coverage:
	pytest --cov-report term --cov-report xml --cov=imgdb/ test/

test:
	pytest -ra -sv test/
