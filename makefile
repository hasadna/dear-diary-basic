init:
	virtualenv venv
	venv/bin/pip install -r requirements.txt
freeze:
	venv/bin/pip freeze >requirements.txt
output/reapings:
	curl 'https://www.odata.org.il/api/3/action/resource_search?query=name:יומן' -s | jq '.result.results[] | select(.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") | "mkdir -p output/reapings/\(.id) && curl -s \(.url) -o \"output/reapings/\(.id)/\(.name)\""' -r | parallel

output/raw.json: output/reapings/*/*.xlsx
	ls output/reapings/*/*.xlsx | parallel venv/bin/python chew.py > output/raw.json || true
	test -f output/raw.json

output/records.json: output/raw.json
	venv/bin/python digest.py output/raw.json -o output/records.json
