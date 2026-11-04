"""Evaluate native decision models through the TandemBench SystemOne API."""
import argparse
import concurrent.futures
import getpass
import hashlib
import json
import math
import os
import platform
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .runner import load_inputs, read_jsonl, save, sha
from .scoring import score


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


ROOT = Path(__file__).resolve().parents[1]
LETTERS = "ABCD"


def endpoint(base_url):
    url = urllib.parse.urlsplit(base_url)
    if url.scheme not in ("http", "https") or not url.netloc:
        raise ValueError("base_url must be an HTTP(S) URL")
    if url.username or url.password or url.query or url.fragment:
        raise ValueError("base_url must not contain credentials, query or fragment")
    path = url.path.rstrip("/")
    return base_url.rstrip("/") if path.endswith("/systemone") else base_url.rstrip("/") + "/systemone"


def prompt_to_request(prompt):
    try:
        state, tail = prompt.split("\n\n[Question]\n", 1)
        question, options_text = tail.split("\n\n[Options]\n", 1)
    except ValueError as exc:
        raise ValueError("Prompt does not follow the public TandemBench format") from exc
    blocks = options_text.split("\n\n")
    if len(blocks) != 4:
        raise ValueError("Prompt must contain exactly four options")
    criteria = {}
    for letter, block in zip(LETTERS, blocks):
        prefix = letter + ".\n"
        if not block.startswith(prefix):
            raise ValueError("Option labels are not in A--D order")
        criteria[letter] = block[len(prefix):]
    return {
        "state": state,
        "questions": {
            "decision": {
                "type": "choice",
                "instructions": question,
                "criteria": criteria,
            }
        },
    }


def parse_response(data):
    try:
        decision = data["answers"]["decision"]
        choice = decision.get("choice")
    except (KeyError, TypeError):
        return None, None, "invalid_response_schema"
    if choice not in LETTERS:
        return None, None, "invalid_choice"
    probabilities = decision.get("probabilities")
    if probabilities is not None:
        if not isinstance(probabilities, dict):
            probabilities = None
        else:
            try:
                probabilities = {letter: float(probabilities[letter]) for letter in LETTERS}
                if not all(math.isfinite(value) and value >= 0 for value in probabilities.values()):
                    probabilities = None
            except (KeyError, TypeError, ValueError):
                probabilities = None
    return choice, probabilities, None


def redact(value, key):
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, dict):
        return {redact(k, key): redact(v, key) for k, v in value.items()}
    return value


def request_once(config, request, key):
    body = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    req = urllib.request.Request(config["endpoint"], data=body, headers=headers, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=config["timeout"]) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            return {"kind": "error", "error": "response_too_large", "retryable": False}
        data = redact(json.loads(raw.decode("utf-8")), key)
        if not isinstance(data, dict):
            return {"kind": "error", "error": "invalid_response_schema", "retryable": False}
        return {"kind": "response", "response": data, "latency_seconds": round(time.monotonic() - started, 4)}
    except urllib.error.HTTPError as exc:
        return {"kind": "error", "error": "http_error", "http_status": exc.code,
                "retryable": exc.code in (408, 429, 500, 502, 503, 504)}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return {"kind": "error", "error": "transport_error", "retryable": True}
    except (ValueError, UnicodeError):
        return {"kind": "error", "error": "invalid_json_response", "retryable": False}


def collect_metrics(out, config, items, completed):
    result = {
        "status": "complete" if len(completed) == len(items) else "incomplete",
        "scope": "smoke_subset" if config["limit"] else "full_selected_parts",
        "planned_requests": len(items),
        "completed_responses": len(completed),
        "metrics": {},
        "invalid": dict(Counter(x["parse_error"] for x in completed.values() if x["parse_error"])),
    }
    for part in config["parts"]:
        selected = {item["id"] for item in items if item["part"] == part}
        predictions = [
            {"id": item_id, "sample": 0, "choice": record["choice"]}
            for (item_id, sample), record in completed.items()
            if sample == 0 and item_id in selected
        ]
        if len(predictions) != len(selected):
            result["metrics"][part] = {
                "status": "incomplete", "completed": len(predictions), "expected": len(selected)
            }
            continue
        answers = [x for x in read_jsonl(ROOT / f"evaluation/{part}/answers.jsonl") if x["id"] in selected]
        result["metrics"][part] = score(answers, predictions, 1)
    save(out / "metrics.json", result)
    rows = [{"id": item_id, "sample": sample, **record}
            for (item_id, sample), record in sorted(completed.items())]
    (out / "predictions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    report = ["# TandemBench native decision evaluation", "",
              f"Status: {result['status']}; scope: {result['scope']}",
              f"Responses: {len(completed)} / {result['planned_requests']}", "", "| Metric | Percent |",
              "|---|---:|"]
    for part_value in result["metrics"].values():
        for name in ("DA", "VA"):
            if name in part_value:
                report.append(f"| {name} | {100 * part_value[name]:.2f} |")
    report += ["", "Native choices are scored from answers.decision.choice. If probabilities are returned, they are preserved in predictions.jsonl.", ""]
    (out / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return result


def evaluate(config, items, out, key, resume):
    if out.exists() and not resume:
        raise ValueError("Output directory exists; use --resume or a new --output")
    if resume and not (out / "config.json").exists():
        raise ValueError("No resumable configuration at --output")
    out.mkdir(parents=True, exist_ok=True)
    lock = out / ".running.lock"
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    completed = {}
    attempts = Counter()
    recovery_validated = False
    exit_status = None
    try:
        if resume:
            if json.loads((out / "config.json").read_text()) != config:
                raise ValueError("Resume configuration/code/data differs; use the original settings or a new output")
            manifest = json.loads((out / "run_manifest.json").read_text())
            if not isinstance(manifest, dict) or "started_at" not in manifest:
                raise ValueError("Invalid run manifest; restore it before resuming")
        else:
            save(out / "config.json", config)
            save(out / "run_manifest.json", {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "python": platform.python_version(), "protocol": "native-systemone-v1", "status": "running",
                "model": config["model"], "endpoint": config["endpoint"],
            })
        logfile = out / "attempts.jsonl"
        if logfile.exists():
            for row in read_jsonl(logfile):
                if not isinstance(row, dict) or row.get("kind") not in ("response", "error"):
                    raise ValueError("Invalid attempt log record")
                job = (row.get("id"), row.get("sample"))
                if row.get("kind") == "response":
                    if job in completed:
                        raise ValueError("Duplicate completed response in attempt log")
                    choice, probabilities, error = parse_response(row["response"])
                    completed[job] = {"choice": choice, "probabilities": probabilities, "parse_error": error,
                                      "part": row["part"]}
                attempts[job] += 1
        valid = {(item["id"], 0) for item in items}
        if not set(attempts) <= valid:
            raise ValueError("Unknown job in saved log")
        recovery_validated = True
        jobs = [(item, 0) for item in items if (item["id"], 0) not in completed]
        fatal_status = None
        with logfile.open("a", encoding="utf-8") as log, concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            for start in range(0, len(jobs), config["workers"]):
                if fatal_status:
                    break
                batch = jobs[start:start + config["workers"]]
                pending = batch
                for retry in range(config["retries"] + 1):
                    futures = {pool.submit(request_once, config, item["request"], key): (item, sample)
                               for item, sample in pending}
                    pending = []
                    for future in concurrent.futures.as_completed(futures):
                        item, sample = futures[future]
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = {"kind": "error", "error": "worker_exception",
                                      "exception_type": type(exc).__name__, "retryable": False}
                        job = (item["id"], sample)
                        attempts[job] += 1
                        row = {"id": item["id"], "part": item["part"], "sample": sample,
                               "attempt": attempts[job], "request_sha256": item["request_sha256"],
                               "timestamp": datetime.now(timezone.utc).isoformat(), **result}
                        log.write(json.dumps(row, ensure_ascii=False) + "\n")
                        log.flush()
                        if result.get("http_status") in (400, 401, 403, 404, 405, 413, 422):
                            fatal_status = result["http_status"]
                        if result["kind"] == "response":
                            choice, probabilities, error = parse_response(result["response"])
                            completed[job] = {"choice": choice, "probabilities": probabilities,
                                              "parse_error": error, "part": item["part"]}
                        elif result.get("retryable") and retry < config["retries"]:
                            pending.append((item, sample))
                    if not pending:
                        break
                    time.sleep(min(2 ** retry, 8))
                print(f"Responses {len(completed)}/{len(valid)}", flush=True)
        result = collect_metrics(out, config, items, completed)
        exit_status = result["status"]
    except BaseException as exc:
        exit_status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        raise
    finally:
        try:
            if recovery_validated and (out / "attempts.jsonl").exists():
                result = collect_metrics(out, config, items, completed)
                manifest = json.loads((out / "run_manifest.json").read_text())
                manifest.update(status=exit_status or result["status"], updated_at=datetime.now(timezone.utc).isoformat(),
                               attempt_log_sha256=sha(out / "attempts.jsonl"), metrics_sha256=sha(out / "metrics.json"))
                save(out / "run_manifest.json", manifest)
        finally:
            lock.unlink(missing_ok=True)
    return 0 if json.loads((out / "metrics.json").read_text())["status"] == "complete" else 2


def main():
    parser = argparse.ArgumentParser(description="Run a native decision model through the TandemBench SystemOne API.")
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--api-key-env", default="TANDEMBENCH_API_KEY")
    parser.add_argument("--output", type=Path, default=Path("runs") / datetime.now().strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--part", choices=["all", "decision", "verification"], default="all")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if min(args.workers, args.timeout) <= 0 or args.retries < 0 or args.limit < 0:
        parser.error("workers/timeout must be positive; retries/limit must be nonnegative")
    parts = ["decision", "verification"] if args.part == "all" else [args.part]
    items, manifest = load_inputs(parts, args.limit)
    for item in items:
        item["request"] = prompt_to_request(item["prompt"])
        item["request_sha256"] = hashlib.sha256(json.dumps(item["request"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if args.dry_run:
        print(json.dumps({"protocol": "native-systemone-v1", "parts": parts, "presentations": len(items),
                          "planned_requests": len(items), "data_hashes_verified": True}, indent=2))
        return 0
    base = args.base_url or input("Native API base URL (including /v1 if required): ").strip()
    model = args.model or input("Model name: ").strip()
    if not model:
        raise ValueError("Model name is required")
    key = os.environ.get(args.api_key_env) or getpass.getpass("API key (hidden; not saved): ")
    if not key:
        raise ValueError("API key is required (local no-auth servers can use a dummy value)")
    config = {
        "protocol": "native-systemone-v1", "endpoint": endpoint(base), "model": model,
        "parts": parts, "workers": args.workers, "timeout": args.timeout, "retries": args.retries,
        "limit": args.limit, "data_manifest_sha256": sha(ROOT / "data/manifest.json"),
        "code_sha256": {path.name: sha(path) for path in sorted((ROOT / "tandembench").glob("*.py"))},
    }
    print(f"Planned native requests: {len(items)}; output: {args.output}")
    return evaluate(config, items, args.output, key, args.resume)
