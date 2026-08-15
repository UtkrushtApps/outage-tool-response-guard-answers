# Solution Steps

1. Define a single conservative fallback payload that reports an unknown status, requires human assistance, and is returned as a fresh dictionary on every failure path.

2. Validate the requested area and timeout before contacting the service so blank, unsafe, or invalid inputs never reach the outage-status backend.

3. Create an absolute monotonic deadline at the start of each lookup. Use the remaining time for every attempt so retries cannot multiply the configured response limit.

4. Execute each service attempt in its own daemon thread and communicate its result through a queue. This permits the caller to return at the deadline without waiting for a blocked service function, while avoiding a shared executor whose workers could remain poisoned by previous slow calls.

5. Retry one time after a service exception when time remains. Stop immediately after a timeout because the shared request deadline has been exhausted or is about to be exhausted.

6. Explicitly validate successful payloads: require exactly the contract fields, a matching area code, an allowed status identifier, a real boolean for `needs_human`, and bounded printable message text. Reject unknown statuses that do not require human review.

7. Return a defensive copy of valid service data and never expose exceptions, incomplete payloads, mismatched-area data, or unvalidated fields to the model.

8. Validate model-generated tool arguments before invoking the reliability boundary, reject unexpected arguments or tool names, and send the same conservative fallback into the agent loop for invalid calls.

9. Keep provider configuration optional for imports and offline tests, but require `OPENAI_API_KEY` when constructing the real model client.

10. Run `./run.sh` or `python -m pytest -q` to exercise the key-free offline checks. Add a provider key to `.env` only when testing the real command-line agent loop.

