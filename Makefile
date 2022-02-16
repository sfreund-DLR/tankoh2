# SPDX-FileCopyrightText: 2022 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: MIT

PROGRAM_VERSION = $(lastword $(shell poetry version --no-ansi))
ALL_PYTHON_FILES = $(shell find src/tankoh2 test doc -type f -name "*.py")


all: audit

clean:
	rm -rf build
	rm -rf dist
	poetry run coverage erase

prepare:
	mkdir -p build

test: prepare
	poetry run pytest --doctest-modules --junit-xml=build/tests.xml src/tankoh2/ test/

doctest: prepare
	poetry run pytest --doctest-modules --junit-xml=build/doctests.xml src/tankoh2/

formatting:
	poetry run black src/tankoh2 test
	poetry run isort src/tankoh2 test

license-metadata:
	poetry run reuse addheader --copyright="German Aerospace Center (DLR)" --license="MIT" $(ALL_PYTHON_FILES)
	poetry run black src/tankoh2 test

check-formatting:
	poetry run black src/tankoh2 test --check
	poetry run isort src/tankoh2 test --check-only

check-license-metadata:
	poetry run reuse lint

check-code: prepare
	poetry run flake8 src/tankoh2 test --exit-zero --output-file=build/flake8.txt

check-coverage: prepare
	poetry run pytest --cov=src/tankoh2 --cov-fail-under=15 --cov-report=term-missing --cov-report=html --cov-report=xml

check-security:
	poetry run bandit -r --exit-zero src/tankoh2/
	poetry run bandit -r -ll -x fecall.py,buildcommands.py src/tankoh2/

audit: check-code check-coverage check-formatting check-license-metadata check-security

docs: prepare
	poetry run sphinx-apidoc --force --output-dir=doc/ --no-toc src/tankoh2 *abq_cae* *control_doe*
	poetry run sphinx-build -w build/sphinxwarn.txt -D version="$(PROGRAM_VERSION)" -D release="$(PROGRAM_VERSION)" -b html doc/ build/html/

doc: docs

package: prepare
	poetry build -f sdist
	poetry build -f wheel
