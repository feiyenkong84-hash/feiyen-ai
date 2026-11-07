# StudyLead Radar collection

Python 3.12; standard library only. Run tests with:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v

Run collection without touching repository data:

    python3 collect_leads.py --output /tmp/studylead-leads.json --report /tmp/studylead-report.json

Default execution writes leads.json and collection-report.json in the current directory.
RSS 2.0 and Atom are supported. Original question links, publication dates,
source and author attribution are retained. Review source licensing before reusing
full text outside this tool (Stack Exchange posts use CC BY-SA with version depending
on publication date). No paid API or authentication is used.

## Candidate sources and validation status

The two native public Expatriates Stack Exchange country-tag Atom feeds replace
the failing Reddit configuration. These are candidates, NOT verified reliable
production sources in this environment:

- https://expatriates.stackexchange.com/feeds/tag?tagnames=malaysia&sort=newest
- https://expatriates.stackexchange.com/feeds/tag?tagnames=singapore&sort=newest

2026-11-07 live probes of both feeds were rejected by the cloud egress proxy
with CONNECT 403. Reddit and OurSteps were also rejected by this proxy.
This does not establish the HTTP status returned by the actual websites.
Network domain requirements have been saved separately in the environment draft.
After allowing the destinations, rerun collection and inspect actual feed entries
and original question links before treating this integration as production ready.
No genuine question links were obtained during this run, and no test fixtures were
written to leads.json. Country-tag feeds can have low volume and old questions;
they are not a guaranteed daily source of new education demand. This collector
uses country plus education keywords; human review remains required.

## Outcomes and safety

Each source reports status, scanned entries, matches and newly added records.
A valid feed with no matches succeeds with matched=0. Malformed/unsupported feeds,
HTTP 403/429 and network failures fail; they are never reported as empty successes.
Any failed source makes the command exit 1 (partial successes are still saved).
An empty but valid feed is an observed success, not evidence of useful coverage.
No retries or alternative endpoints bypass site restrictions. Respect 429 and
retry on a later scheduled run; do not increase traffic to evade limits.

The workflow uploads the JSON report, saves genuine additions even for partial
failure, and then marks the job failed if collection failed. Invalid existing JSON
aborts without replacing history. Deduplication strips fragments from original
URLs. Atomic writes protect data; no-new-data runs leave leads.json unchanged.
The web page is unchanged: it stores its own data in browser localStorage and
does not automatically consume leads.json.

Tests use explicitly synthetic in-memory feeds to validate parsers and failure
handling; those tests are not evidence of real collection or real lead volume.
