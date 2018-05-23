.PHONY: run prepare venv requirements

run:
	FLASK_APP=application.py venv/bin/python -m flask run

prepare: venv requirements

venv:
	virtualenv venv

requirements:
	venv/bin/pip install -r requirements.txt