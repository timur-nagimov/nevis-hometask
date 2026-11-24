#!/usr/bin/env bash
# Both assignment examples against a running API:
#
#   docker compose up --build -d && scripts/demo.sh
#   API_PORT=8001 scripts/demo.sh                    # the API is published on another host port
#   NEVIS_API=http://127.0.0.1:8001 scripts/demo.sh  # or any base URL
#
# Creates the client John Doe (john.doe@neviswealth.com) and five documents, unless a client with that e-mail
# already exists: then it creates nothing, so running it twice duplicates nothing. Then it prints the answers to
# `NevisWealth`, `address proof` and one junk query. Needs bash, curl and python3 (python3 only reads and
# pretty-prints JSON). To start from an empty database: docker compose down -v && docker compose up -d
set -euo pipefail

API="${NEVIS_API:-http://127.0.0.1:${API_PORT:-8000}}"
EMAIL="john.doe@neviswealth.com"

# Right after `docker compose up -d` the API may still be loading the model: wait up to 120 s.
for attempt in $(seq 1 120); do
  curl -fsS -o /dev/null "$API/health" 2>/dev/null && break
  if [ "$attempt" -eq 120 ]; then
    echo "No answer from $API/health after 120 s. Is the stack up? Check with: docker compose ps" >&2
    exit 1
  fi
  sleep 1
done

# POST the JSON body $2 to the path $1 and print the response. On an HTTP error print it and stop.
post() {
  local response
  if ! response=$(printf '%s' "$2" | curl -sS --fail-with-body -X POST \
    -H 'Content-Type: application/json' --data-binary @- "$API$1"); then
    echo "POST $1 failed: $response" >&2
    exit 1
  fi
  printf '%s\n' "$response"
}

# Print a GET request as a command that can be pasted as is, then its answer. $1: the URL-encoded path.
show() {
  printf "\n\$ curl -s '%s' | python3 -m json.tool --no-ensure-ascii\n" "$API$1"
  curl -sS --fail-with-body "$API$1" | python3 -m json.tool --no-ensure-ascii
}

# Upload a document ($1: JSON with title and content) for $client_id; print its title and the tags it got.
add_document() {
  post "/clients/$client_id/documents" "$1" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("  document %-20s tags: %s" % (repr(d["title"]), ", ".join(d["tags"]) or "(none)"))'
}

echo "== Demo data on $API"
client_id=$(curl -sS --fail-with-body "$API/search?type=client&q=john.doe%40neviswealth.com" | python3 -c '
import json, sys
print(next((i["id"] for i in json.load(sys.stdin) if i.get("email") == sys.argv[1]), ""))' "$EMAIL")

if [ -n "$client_id" ]; then
  echo "John Doe ($EMAIL) already exists as client $client_id: nothing created."
else
  client_id=$(post /clients '{"first_name": "John", "last_name": "Doe", "email": "john.doe@neviswealth.com", "description": "Founder of a logistics company; prefers ESG funds.", "social_links": ["https://www.linkedin.com/in/johndoe"]}' |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
  echo "Created client John Doe ($EMAIL): $client_id"
  add_document '{"title": "Utility bill", "content": "British Gas utility bill for March 2025. Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20."}'
  add_document '{"title": "Passport", "content": "Copy of the passport of John Doe, United Kingdom. Passport number 533401372, expires 12 May 2031."}'
  add_document '{"title": "Tax return", "content": "Self Assessment tax return for the tax year 2023-24, submitted to HMRC on 14 January 2025. Total income £86,400, tax due £21,930."}'
  add_document '{"title": "Scan 0042", "content": "Scan: utility bill (electricity), 2 pages.\n\nNORTHMOOR ENERGY\nMr Tobias Hallworth\n14 Larkspur Close, Harrogate HG2 7QD\nCustomer number 8830 5512 07. Bill date 14 March 2025.\n\nYour electricity bill for 11 December 2024 to 10 March 2025 (90 days).\nMeter 21E4470913: previous reading 41,208, latest reading 42,371 (smart meter). Electricity used: 1,163 kWh.\nUnit charges 1,163 kWh at 24.86p: £289.12\nStanding charge 90 days at 60.97p: £54.87\nVAT at 5%: £17.20\nTotal charges this period: £361.19\nPayments received, thank you (3 direct debits of £95.47): £286.41\nBalance carried forward: £74.78 debit\n\nYour monthly direct debit stays at £95.47 and is collected on the 3rd of each month. Tariff: Fixed Saver 18, ends 30 September 2025. Estimated annual cost on this tariff: £1,210."}'
  add_document '{"title": "Electricity bill", "content": "Electricity bill from EDF Energy for January 2025, 7 Mill Lane, Leeds. Amount due £96.10."}'
fi

printf '\n== Example 1: NevisWealth finds the client with the e-mail %s\n' "$EMAIL"
show "/search?q=NevisWealth"
printf '\n== Example 2: address proof finds the documents that are utility bills\n'
show "/search?q=address%20proof"
printf '\n== A junk query finds nothing\n'
show "/search?q=chocolate%20cake%20recipe"
printf '\nSwagger UI: %s/docs (it loads its JavaScript from cdn.jsdelivr.net)\n' "$API"
