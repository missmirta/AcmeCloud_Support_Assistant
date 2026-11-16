"""
Run every question in eval/questions.json against a running app and save the
answer and full trace for each.

    python eval/run_eval.py [--app-url http://localhost:8000] [--out eval_results]

Writes <out>/q<id>.json (question, response, trace) and <out>/summary.md.
Uses only the standard library.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

QUESTIONS = Path(__file__).resolve().parent / "questions.json"


def call(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-url", default="http://localhost:8000")
    parser.add_argument("--out", default=str(QUESTIONS.parent.parent / "eval_results"))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    run_id = time.strftime("%Y%m%d%H%M%S")

    rows, failures = [], 0
    for q in questions:
        request_id = f"eval_{run_id}_q{q['id']}"
        started = time.time()
        status, response = call(
            "POST", f"{args.app_url}/ask",
            {"question": q["question"], "customer_id": q["customer_id"], "request_id": request_id},
        )
        seconds = round(time.time() - started, 1)
        _, trace = call("GET", f"{args.app_url}/trace/{request_id}")

        (out / f"q{q['id']}.json").write_text(
            json.dumps({"question": q, "http_status": status, "seconds": seconds,
                        "response": response, "trace": trace}, indent=2),
            encoding="utf-8",
        )

        if status != 200:
            failures += 1
            print(f"Q{q['id']}: HTTP {status} {response}")
            rows.append(f"## Q{q['id']} ({q['difficulty']}) - FAILED: HTTP {status}\n\n"
                        f"**Question** ({q['customer_id']}): {q['question']}\n\n```\n{response}\n```\n")
            continue

        print(f"Q{q['id']}: {seconds}s llm={response['llm_calls']} tools={response['tool_calls']} "
              f"retries={response['retries']}")
        rows.append(
            f"## Q{q['id']} ({q['difficulty']})\n\n"
            f"**Question** ({q['customer_id']}): {q['question']}\n\n"
            f"**Answer**:\n\n{response['answer']}\n\n"
            f"- sources: {', '.join(response['sources'])}\n"
            f"- llm_calls: {response['llm_calls']}, tool_calls: {response['tool_calls']}, "
            f"retries: {response['retries']}, seconds: {seconds}\n"
            f"- trace: `q{q['id']}.json`\n"
        )

    (out / "summary.md").write_text("# Eval results\n\n" + "\n".join(rows), encoding="utf-8")
    print(f"Saved {len(questions)} results to {out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
