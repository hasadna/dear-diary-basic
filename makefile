init:
	virtualenv venv
	venv/bin/pip install -r requirements.txt
freeze:
	venv/bin/pip freeze >requirements.txt
reapings:
	curl 'https://www.odata.org.il/api/3/action/resource_search?query=name:יומן' -s | jq '.result.results[] | select(.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") | "mkdir -p reapings/\(.id) && curl -s \(.url) -o \"reapings/\(.id)/\(.name)\""' -r | parallel

raw.json: reapings/*/*.xlsx
	ls reapings/*/*.xlsx | parallel venv/bin/python chew.py > raw.json || true
	test -f raw.json

records.json: raw.json
	venv/bin/python digest.py raw.json -o records.json
