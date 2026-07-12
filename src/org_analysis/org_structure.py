#!/usr/bin/env python3
"""
Single safety-org class + structural typing shared by the plot and review steps.

Types: corporate / PBC / nonprofit / academic / government / funder.
  PBC        Anthropic; OpenAI from 2026 (after its late-2025 PBC conversion)
  corporate  Google DeepMind, OpenAI before 2026, safety startups
  <else>     mapped from ai_safety_orgs category: funder / government / academic,
             everything else (research / fellowship / governance / community) -> nonprofit

The retained safety-org set is every ai_safety_orgs entry that is NOT tagged
"safety-adjacent", plus OpenAI / Anthropic / Google DeepMind (the general labs
Meta, Hugging Face, Microsoft, Scale, Mila, Vector, AI2, Cohere, Shanghai, xAI,
EleutherAI are dropped).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ai_safety_orgs import ORGS  # noqa: E402

PROMOTE = {"OpenAI", "Anthropic", "Google DeepMind"}
SAFETY_ORGS = {n for n, i in ORGS.items() if i.get("focus") != "safety-adjacent"} | PROMOTE

PBC_ALWAYS = {"Anthropic"}
CORPORATE = {"Google DeepMind", "Goodfire", "Haize Labs", "Tilde Research",
             "Gray Swan AI", "Andon Labs", "Simplex", "Conjecture", "Aligned AI"}

TYPES = ["PBC", "corporate", "nonprofit", "academic", "government", "funder"]
COLOR = {"PBC": "#2a78d6", "corporate": "#eb6834", "nonprofit": "#1baf7a",
         "academic": "#eda100", "government": "#9085e9", "funder": "#e87ba4"}
LABEL = {"PBC": "PBC (Anthropic, OpenAI ≥2026)",
         "corporate": "Corporate (DeepMind, OpenAI <2026, startups)",
         "nonprofit": "Nonprofit (independent orgs)",
         "academic": "Academic centre", "government": "Government (AISI)",
         "funder": "Funder (Open Phil, LTFF…)"}
# raw-preview priority (author employer before funder); real runs use LLM primary
PRIORITY = ["PBC", "corporate", "academic", "government", "nonprofit", "funder"]


def org_type(org, year):
    if org == "OpenAI":
        return "PBC" if int(year) >= 2026 else "corporate"
    if org in PBC_ALWAYS:
        return "PBC"
    if org in CORPORATE:
        return "corporate"
    cat = ORGS.get(org, {}).get("category", "")
    if cat == "funder":
        return "funder"
    if cat == "government":
        return "government"
    if cat == "academic":
        return "academic"
    return "nonprofit"


def paper_bucket(orgs, year, primary=None):
    if primary and primary in orgs:
        return org_type(primary, year)
    types = {org_type(o, year) for o in orgs}
    for t in PRIORITY:
        if t in types:
            return t
    return None
