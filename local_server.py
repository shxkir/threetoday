#!/usr/bin/env python3
"""
Local dev server for ThreeToday (no AWS deploy required to test the UI).

Usage:
  # UI only / mock AI (no AWS):
  python3 local_server.py

  # Real Bedrock (needs AWS creds + model access):
  USE_BEDROCK=1 AWS_REGION=us-east-1 python3 local_server.py
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from lambda_function import HTML_PAGE, enforce_three  # noqa: E402

USE_BEDROCK = os.environ.get("USE_BEDROCK", "0") == "1"
PORT = int(os.environ.get("PORT", "8080"))


def mock_model(brain_dump: str, hours: float, energy: str, context: str) -> dict:
    """Offline mock so the UI can be demoed without Bedrock."""
    lines = [
        ln.strip("-•* \t")
        for ln in brain_dump.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not lines:
        parts = [p.strip() for p in brain_dump.replace("\n", ". ").split(".") if p.strip()]
        lines = parts[:10]

    kill_words = ("maybe", "eventually", "someday", "watch", "learn", "clean downloads", "browse")
    high_words = ("rewrite", "build", "research", "proposal", "architect", "migrate")
    impact_words = ("client", "lead", "invoice", "deadline", "ship", "deploy", "fix", "reply", "send")

    candidates = []
    for i, line in enumerate(lines[:12]):
        title = line[:100]
        low = title.lower()
        score = 82 - i * 4
        if any(w in low for w in impact_words):
            score += 12
        if context and any(w in low for w in context.lower().split()[:6]):
            score += 8
        if any(w in low for w in kill_words):
            score -= 35
            bucket = "killed" if score < 48 else "parked"
        elif score >= 70:
            bucket = "today"
        else:
            bucket = "parked"
        effort = "high" if any(w in low for w in high_words) else "medium"
        if any(w in low for w in ("reply", "send", "email", "pay", "book")):
            effort = "low"
        hrs = 1.5 if effort == "high" else (0.5 if effort == "low" else 0.75)
        nice = title[0].upper() + title[1:] if title else f"Task {i+1}"
        if effort == "low":
            move = f"Open the thread/tool and complete the first send for: {nice[:50]}"
        elif effort == "high":
            move = f"Create a blank doc titled '{nice[:40]}' and write 3 bullets of the outcome"
        else:
            move = f"Block 25 minutes and start the first concrete step on: {nice[:50]}"
        candidates.append(
            {
                "title": nice,
                "hours": hrs,
                "effort": effort,
                "priority_score": score,
                "bucket_suggestion": bucket,
                "why": "Ranked from wording, position, and your day context (mock mode).",
                "first_move": move,
            }
        )

    return {
        "rationale": (
            f"[Mock AI] Energy={energy}, budget={hours}h"
            + (f", context={context}" if context else "")
            + ". Code still enforces max 3 today + hour budget."
        ),
        "candidates": candidates,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {args[0] if args else fmt}")

    def _send(self, code: int, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/threetoday"):
            body = HTML_PAGE.encode("utf-8")
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path == "/health":
            self._send(200, b'{"ok":true}', "application/json")
            return
        self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._send(400, b'{"error":"Invalid JSON"}', "application/json")
            return

        brain_dump = str(data.get("brain_dump") or "").strip()
        if not brain_dump:
            self._send(400, b'{"error":"brain_dump is required"}', "application/json")
            return
        try:
            hours = float(data.get("hours") or 4)
        except (TypeError, ValueError):
            self._send(400, b'{"error":"hours must be a number"}', "application/json")
            return
        hours = max(0.5, min(12.0, hours))
        energy = str(data.get("energy") or "medium").lower()
        if energy not in ("low", "medium", "high"):
            energy = "medium"
        context = str(data.get("context") or "").strip()[:120]

        try:
            if USE_BEDROCK:
                from lambda_function import call_nova

                model_out = call_nova(brain_dump, hours, energy, context)
            else:
                model_out = mock_model(brain_dump, hours, energy, context)
            plan = enforce_three(model_out, hours, energy)
            if not USE_BEDROCK:
                plan["model"] = "mock-local"
            body = json.dumps(plan).encode("utf-8")
            self._send(200, body, "application/json")
        except Exception as exc:
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self._send(500, body, "application/json")


def main():
    mode = "Bedrock" if USE_BEDROCK else "mock AI (offline)"
    print(f"ThreeToday local server on http://127.0.0.1:{PORT}  [{mode}]")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
