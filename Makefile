cleandb:
	rm -f app/models/la_cosa.sqlite


populate_cards:
	# python3 app/models/populate_cards.py
	python3 -m app.models.populate_cards
	

run:
	python3 main.py

test:
	pytest -W ignore::DeprecationWarning


test-cov:
	pytest --cov -W ignore::DeprecationWarning