.PHONY: test clean update lint coverage

ENV=

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*.orig' `
	rm -f `find . -type f -name '*.rej' `
	rm -rf *.egg-info
	rm -f .coverage
	rm -rf coverage
	rm -rf build
	rm -rf cover
	# python3 setup.py clean

update:
	${ENV}pip install -U -r requirements.txt

lint:
	${ENV}flake8 --statistics imgdb
	${ENV}mypy --ignore-missing-imports imgdb

coverage:
	${ENV}pytest --cov-report term --cov-report xml --cov=imgdb/ test/

test:
	${ENV}pytest -ra -sv test/
