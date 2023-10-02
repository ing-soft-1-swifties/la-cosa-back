cleandb:
	rm -f app/models/la_cosa.sqlite


createdb:
	python3 app/models/__init__.py
	python3 app/models/populate_cards.py
	


