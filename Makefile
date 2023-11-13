all:
	rm -f app/models/la_cosa.sqlite
	make populate_cards
	python3 main.py
	
cleandb:
	rm -f app/models/la_cosa.sqlite

populate_cards:
	# python3 app/models/populate_cards.py
	python3 -m app.models.populate_cards
	
run:
	python3 main.py


test:
	pytest -W ignore::DeprecationWarning -k $(arg) -s

test-all:
	pytest -W ignore::DeprecationWarning --cov

ta:
	make test-all


test-report:
	pytest -W ignore::DeprecationWarning --cov --cov-report=html