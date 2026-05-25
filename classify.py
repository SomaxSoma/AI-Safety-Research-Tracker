#!/usr/bin/env python3
"""
ICLR 2026 AI Safety Paper Classifier

Classifies papers into safety-relevant categories using an LLM with reasoning.
Supports parallel inference, automatic resume, and incremental CSV writes.

Usage:
    python classify.py                        # classify all papers
    python classify.py --sample 100           # classify a random sample
    python classify.py --sample 100 --seed 42 # reproducible sample
    python classify.py --workers 32           # custom parallelism
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL       = "deepseek/deepseek-v4-flash"
INPUT_FILE  = "iclr2026_papers.csv"
OUTPUT_FILE = "safety_results_v3.csv"
MAX_RETRIES = 3
WORKERS     = 50
ABSTRACT_MAX_CHARS = 2000

PRICING = {"input": 0.10, "output": 0.20}  # per 1M tokens

VALID_SUBDOMAINS = frozenset({
    "Interpretability", "Monitoring", "Multi-Agent Safety", "Scalable Oversight",
    "Agent Foundations", "Scheming and Deception", "Dangerous Capability Evals",
    "Biorisk", "Safeguards", "Model Organisms", "Control", "Alignment Training",
    "Red-Teaming", "Adversarial Robustness", "Policy and Governance",
    "Strategy and Forecasting", "AI Welfare",
})

FIELDNAMES = [
    "id", "title", "class", "is_safety",
    "motivation_score", "methodology_score", "evaluation_score",
    "total_score", "subdomain", "confidence", "reasoning",
]

PROMPT_FILE = Path(__file__).parent / "prompt.txt"
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_response(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        try:
            data = json.loads(text[start:end])
        except json.JSONDecodeError:
            return None

    if "step1_class" in data and "class" not in data:
        data["class"] = data.pop("step1_class")

    if not {"class", "is_safety", "subdomain", "confidence", "reasoning"}.issubset(data):
        return None

    if data.get("subdomain") not in VALID_SUBDOMAINS:
        data["subdomain"] = ""

    if data["class"] == 4:
        mot  = data.get("motivation_score") or 0
        meth = data.get("methodology_score") or 0
        evl  = data.get("evaluation_score") or 0
        total = mot + meth + evl
        data.update(motivation_score=mot, methodology_score=meth,
                    evaluation_score=evl, total_score=total)
        if total < 3:
            data.update({"class": 3, "subdomain": "", "is_safety": False})
        else:
            data["is_safety"] = data["subdomain"] != ""
    else:
        data.update(motivation_score=None, methodology_score=None,
                    evaluation_score=None, total_score=None,
                    is_safety=False, subdomain="")
    return data


def default_result() -> dict:
    return {
        "class": 3, "motivation_score": None, "methodology_score": None,
        "evaluation_score": None, "total_score": None, "is_safety": False,
        "subdomain": "", "confidence": "low",
        "reasoning": "Classification failed after all retries.",
    }

# ---------------------------------------------------------------------------
# Async inference
# ---------------------------------------------------------------------------

async def classify_one(
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    model: str,
    paper_id: str,
    title: str,
    abstract: str,
) -> tuple[dict, int, int]:
    """Classify a single paper, returning (result, input_tokens, output_tokens)."""
    abstract_trunc = (abstract or "")[:ABSTRACT_MAX_CHARS]
    user_prompt = (
        f"Title: {title}\n\n"
        f"Abstract: {abstract_trunc}\n\n"
        f"Classify this paper. Return ONLY the JSON object."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ]

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=1.0,
                    extra_body={"reasoning": {"effort": "high"}},
                )
                result = parse_response(resp.choices[0].message.content)
                if result is not None:
                    inp = resp.usage.prompt_tokens if resp.usage else 0
                    out = resp.usage.completion_tokens if resp.usage else 0
                    return result, inp, out
            except Exception as e:
                wait = 2 ** attempt
                print(f"  [{paper_id}] attempt {attempt+1} failed: {e} (retry in {wait}s)")
                await asyncio.sleep(wait)

    return default_result(), 0, 0

# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------

def load_completed(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    try:
        df = pd.read_csv(output_path, usecols=["id"], dtype=str)
        return set(df["id"].dropna())
    except Exception:
        return set()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Error: OPENROUTER_API_KEY environment variable not set.")

    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    output_path = Path(args.output)

    df = pd.read_csv(args.input, dtype={"id": str})
    if args.sample:
        df = df.sample(n=min(args.sample, len(df)), random_state=args.seed).reset_index(drop=True)

    completed = load_completed(output_path)
    pending = df[~df["id"].isin(completed)].reset_index(drop=True)
    total = len(df)
    done_prior = len(completed)

    if done_prior > 0:
        print(f"Resuming: {done_prior}/{total} already done, {len(pending)} remaining")
    model = args.model
    print(f"Classifying {len(pending)} papers using {model} ({args.workers} workers)")
    print("-" * 60)

    if len(pending) == 0:
        print("Nothing to do.")
        return

    write_header = not output_path.exists() or done_prior == 0
    csvfile = open(output_path, "a" if not write_header else "w", newline="", encoding="utf-8")
    import csv
    writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
    if write_header:
        writer.writeheader()

    semaphore = asyncio.Semaphore(args.workers)
    total_in = total_out = safety_count = 0
    done_count = done_prior
    t0 = time.monotonic()

    async def process(row):
        nonlocal total_in, total_out, safety_count, done_count
        paper_id = str(row.get("id", "") or "")
        title    = str(row.get("title", "") or "")
        abstract = str(row.get("abstract", "") or "")

        result, inp, out = await classify_one(client, semaphore, model, paper_id, title, abstract)
        total_in += inp
        total_out += out
        if result["is_safety"]:
            safety_count += 1
        done_count += 1

        writer.writerow({
            "id": paper_id, "title": title, "class": result["class"],
            "is_safety": result["is_safety"],
            "motivation_score": result["motivation_score"],
            "methodology_score": result["methodology_score"],
            "evaluation_score": result["evaluation_score"],
            "total_score": result["total_score"],
            "subdomain": result["subdomain"],
            "confidence": result["confidence"],
            "reasoning": result["reasoning"],
        })
        csvfile.flush()

        elapsed = time.monotonic() - t0
        rate = (done_count - done_prior) / elapsed if elapsed > 0 else 0
        remaining = (len(pending) - (done_count - done_prior)) / rate if rate > 0 else 0
        label = f"[SAFETY: {result['subdomain']}]" if result["is_safety"] else f"[Class {result['class']}]"
        print(
            f"[{done_count:>5}/{total}] {label:<35} "
            f"{title[:45]:<45}  "
            f"({rate:.1f}/s, ~{remaining/60:.0f}m left)"
        )

    tasks = [process(row) for _, row in pending.iterrows()]
    await asyncio.gather(*tasks)

    csvfile.close()

    elapsed = time.monotonic() - t0
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Papers classified : {done_count}")
    print(f"AI Safety papers  : {safety_count} ({safety_count/total*100:.1f}%)")
    print(f"Wall time         : {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"Throughput        : {(done_count - done_prior)/elapsed:.1f} papers/s")
    print()
    print(f"Tokens  — input: {total_in:,}  output: {total_out:,}")
    if done_count - done_prior > 0:
        n = done_count - done_prior
        print(f"Per-paper avg: {total_in//n} in / {total_out//n} out")
    cost = (total_in / 1e6 * PRICING["input"]) + (total_out / 1e6 * PRICING["output"])
    print(f"Cost (this run)   : ${cost:.4f}")
    print()
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Classify ICLR 2026 papers for AI safety relevance")
    parser.add_argument("--input",   default=INPUT_FILE,  help=f"Input CSV (default: {INPUT_FILE})")
    parser.add_argument("--output",  default=OUTPUT_FILE, help=f"Output CSV (default: {OUTPUT_FILE})")
    parser.add_argument("--sample",  type=int, default=None, help="Classify a random sample of N papers")
    parser.add_argument("--seed",    type=int, default=42,   help="Random seed for sampling (default: 42)")
    parser.add_argument("--workers", type=int, default=WORKERS, help=f"Concurrent API calls (default: {WORKERS})")
    parser.add_argument("--model",   default=MODEL, help=f"Model ID (default: {MODEL})")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
