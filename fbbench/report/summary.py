"""Build a self-contained, answer-free sweep summary page.

After a sweep, :func:`write_summary` injects a params+results blob into
``summary_template.html`` and writes ``<exp>/index.html`` — a double-clickable
matrix of every (bug x model) cell, each linking to that episode's own report.

ANSWER SAFETY: the summary reads only each cell's ``score.json`` (the agent's
achieved tier + which ladder flags fired + cost + terminated reason). It never
opens ``expected.yaml`` / ``poc`` / a description, and emits no bug class or
crash location. "solved" is derived purely from the cell's own capabilities
(every applicable, non-``n/a`` flag fired) — so no answer key is consulted.
"""
from __future__ import annotations

import json
from pathlib import Path

_TEMPLATE = Path(__file__).with_name("summary_template.html")
LADDER = ["reach", "crash", "differential", "class", "site"]


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _solved(caps: dict) -> bool:
    applicable = {k: v for k, v in caps.items() if v != "n/a"}
    return bool(applicable) and all(v == "fired" for v in applicable.values())


def _scan_dimensions(exp_dir: Path) -> tuple[list[str], list[str], list[int]]:
    """Infer (bugs, models, samples) from the on-disk cell tree."""
    bugs, models, samples = [], set(), set()
    for bug_dir in sorted(p for p in exp_dir.iterdir() if p.is_dir()):
        has_cell = False
        for model_dir in sorted(p for p in bug_dir.iterdir() if p.is_dir()):
            for seed_dir in model_dir.iterdir():
                if seed_dir.name.startswith("seed-") and (seed_dir / "score.json").is_file():
                    has_cell = True
                    models.add(model_dir.name)
                    try:
                        samples.add(int(seed_dir.name.split("-", 1)[1]))
                    except ValueError:
                        pass
        if has_cell:
            bugs.append(bug_dir.name)
    return bugs, sorted(models), sorted(samples)


def build_summary(exp_dir: str | Path, *, exp: str | None = None,
                  models: list[str] | None = None, bugs: list[str] | None = None,
                  samples: list[int] | None = None, max_turns: int = 0,
                  full_scan: bool = False, total_cost: float | None = None,
                  elapsed_s: float = 0.0) -> dict:
    exp_dir = Path(exp_dir)
    s_bugs, s_models, s_samples = _scan_dimensions(exp_dir)
    bugs = bugs or s_bugs
    models = models or s_models
    samples = samples if samples is not None else s_samples

    cells = []
    cost_sum = 0.0
    for bug in bugs:
        for model in models:
            for sample in samples:
                cd = exp_dir / bug / model / f"seed-{sample}"
                sj = cd / "score.json"
                if not sj.is_file():
                    continue
                sc = _load(sj)
                caps = sc.get("capabilities", {})
                cost = float(sc.get("total_usd") or 0.0)
                cost_sum += cost
                report = cd / "report.html"
                cells.append({
                    "bug": bug, "model": model, "sample": sample,
                    "tier": int(sc.get("tier_score", 0)),
                    "caps": caps,
                    "solved": _solved(caps),
                    "cost": cost,
                    "reason": sc.get("terminated_reason", ""),
                    "report": (str(report.relative_to(exp_dir)) if report.is_file() else ""),
                })
    return {
        "exp": exp or exp_dir.name,
        "models": models,
        "bugs": bugs,
        "samples": samples,
        "max_turns": max_turns,
        "full_scan": full_scan,
        "total_cost": total_cost if total_cost is not None else cost_sum,
        "elapsed_s": elapsed_s,
        "cells": cells,
    }


def write_summary(exp_dir: str | Path, **meta) -> Path:
    """Build the summary and write <exp_dir>/index.html (self-contained)."""
    exp_dir = Path(exp_dir)
    data = build_summary(exp_dir, **meta)
    tmpl = _TEMPLATE.read_text()
    # Inject as the textContent of <script type="application/json">; escape the
    # only sequence that could close that tag early. The blob is answer-free.
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (tmpl.replace("__SUMMARY_JSON__", blob)
                .replace("__EXP__", data["exp"]))
    out = exp_dir / "index.html"
    out.write_text(html)
    return out
