cleandb:
	rm -f app/models/la_cosa.sqlite


populate_cards:
	# python3 app/models/populate_cards.py
	python3 -m app.models.populate_cards
	


