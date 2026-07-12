"""Keyword list of organizations that primarily publish AI safety work.

Intended use: detect false negatives from the LLM classifier and tag papers
with associated orgs, by matching against author affiliations, emails,
acknowledgments, and (cautiously) full text of NeurIPS/ICLR/ICML papers.

Two tiers, via the `focus` field:
  safety-only     - orgs whose paper output is (almost) exclusively AI safety /
                    alignment / x-risk (MATS, Redwood, Anthropic...). Strong
                    signal: an affiliation hit alone suggests a safety paper.
  safety-adjacent - general-purpose labs with substantial safety output
                    (DeepMind, AI2, OpenAI, Meta FAIR...). Weak signal: use for
                    org tagging, not for overriding the LLM classifier.

Each org maps to:
  aliases   - strings to match. Acronyms / single common words are matched
              case-sensitively as whole words by find_orgs(); longer phrases
              case-insensitively.
  focus     - "safety-only" | "safety-adjacent" (defaults to "safety-only"
              when omitted)
  category  - lab | research | academic | government | fellowship | governance
              | funder | community
  risk      - "high" means the alias set collides with common ML vocabulary
              (e.g. "ARC", "Conjecture", "Ought", "SEAL"); only trust matches
              in the affiliation/acknowledgments fields, not body text.
  note      - status / disambiguation info.
"""

ORGS = {
    # ---------------- frontier labs (safety-focused) ----------------
    "Anthropic": {
        "aliases": ["Anthropic"],
        "category": "lab", "risk": "low", "focus": "safety-adjacent",
        "note": "Safety-heavy but also publishes capability work. Beware the adjective 'anthropic principle' in rare cases.",
    },
    "OpenAI": {
        "aliases": ["OpenAI"],
        "category": "lab", "risk": "low", "focus": "safety-adjacent",
        "note": "Substantial safety output (preparedness, alignment) but mostly general capability work.",
    },
    # ---------------- independent safety research orgs ----------------
    "Redwood Research": {
        "aliases": ["Redwood Research"],
        "category": "research", "risk": "low",
        "note": "AI control agenda. Don't match bare 'Redwood'.",
    },
    "Alignment Research Center": {
        "aliases": ["Alignment Research Center", "ARC Theory"],
        "category": "research", "risk": "high",
        "note": "Never match bare 'ARC': collides with ARC-AGI benchmark, ARC dataset (AI2 Reasoning Challenge).",
    },
    "METR": {
        "aliases": ["METR", "Model Evaluation and Threat Research",
                    "Model Evaluation & Threat Research", "ARC Evals"],
        "category": "research", "risk": "medium",
        "note": "Formerly ARC Evals. 'METR' uppercase whole-word is fairly safe.",
    },
    "Apollo Research": {
        "aliases": ["Apollo Research"],
        "category": "research", "risk": "low",
        "note": "Scheming/deception evals, interpretability. Don't match bare 'Apollo'.",
    },
    "Machine Intelligence Research Institute": {
        "aliases": ["Machine Intelligence Research Institute", "MIRI"],
        "category": "research", "risk": "medium",
        "note": "'MIRI' also = JWST mid-infrared instrument; rare in ML venues.",
    },
    "Center for AI Safety": {
        "aliases": ["Center for AI Safety", "CAIS"],
        "category": "research", "risk": "medium",
        "note": "'CAIS' collides with CAiSE conf and Stanford 'Center for AI Safety' (separate entry below) abbreviations.",
    },
    "FAR.AI": {
        "aliases": ["FAR.AI", "FAR AI", "Fund for Alignment Research"],
        "category": "research", "risk": "medium",
        "note": "Never match bare 'FAR'. Runs the Alignment Workshop at NeurIPS.",
    },
    "Conjecture": {
        "aliases": ["Conjecture"],
        "category": "research", "risk": "high",
        "note": "Common noun in theory papers ('Conjecture 3.1') - affiliation field only. Pivoted toward product (~2024) but legacy papers exist.",
    },
    "Timaeus": {
        "aliases": ["Timaeus"],
        "category": "research", "risk": "medium",
        "note": "Developmental interpretability / singular learning theory. Also a Plato dialogue - low risk in ML venues.",
    },
    "LawZero": {
        "aliases": ["LawZero"],
        "category": "research", "risk": "low",
        "note": "Yoshua Bengio's safety nonprofit (founded 2025); non-agentic 'Scientist AI' agenda.",
    },
    "Transluce": {
        "aliases": ["Transluce"],
        "category": "research", "risk": "low",
        "note": "Interpretability/observability nonprofit (Jacob Steinhardt).",
    },
    "Goodfire": {
        "aliases": ["Goodfire"],
        "category": "research", "risk": "low",
        "note": "Mechanistic interpretability startup (Ember platform).",
    },
    "Tilde Research": {
        "aliases": ["Tilde Research"],
        "category": "research", "risk": "low",
        "note": "Interpretability startup. Don't match bare 'Tilde'.",
    },
    "Simplex": {
        "aliases": ["Simplex AI Safety"],
        "category": "research", "risk": "high",
        "note": "Computational-mechanics interpretability. Never match bare 'Simplex' (ubiquitous math term).",
    },
    "EleutherAI": {
        "aliases": ["EleutherAI"],
        "category": "research", "risk": "low", "focus": "safety-adjacent",
        "note": "Lots of interpretability work but also general open-source LLM research.",
    },
    "Truthful AI": {
        "aliases": ["Truthful AI"],
        "category": "research", "risk": "medium",
        "note": "Owain Evans's org (Berkeley). Phrase can appear generically; prefer affiliation field.",
    },
    "Eleos AI": {
        "aliases": ["Eleos AI"],
        "category": "research", "risk": "low",
        "note": "AI welfare / moral patienthood research.",
    },
    "Palisade Research": {
        "aliases": ["Palisade Research"],
        "category": "research", "risk": "low",
        "note": "Dangerous-capability demos (e.g. shutdown resistance).",
    },
    "Apart Research": {
        "aliases": ["Apart Research"],
        "category": "research", "risk": "low",
        "note": "Distributed safety research org + hackathons (Apart Sprints).",
    },
    "Aligned AI": {
        "aliases": ["Aligned AI"],
        "category": "research", "risk": "high",
        "note": "Stuart Armstrong's company. 'aligned AI' is a generic phrase - require capitalization + affiliation context.",
    },
    "Orthogonal": {
        "aliases": ["Orthogonal"],
        "category": "research", "risk": "high",
        "note": "Agent-foundations org (Tamsin Leake). Extremely common math word - affiliation field only.",
    },
    "AE Studio": {
        "aliases": ["AE Studio"],
        "category": "research", "risk": "low", "focus": "safety-adjacent",
        "note": "Consultancy with a dedicated alignment research team that publishes safety papers.",
    },
    "AI Impacts": {
        "aliases": ["AI Impacts"],
        "category": "research", "risk": "medium",
        "note": "Forecasting/surveys (e.g. expert surveys on AI progress).",
    },
    "Center on Long-Term Risk": {
        "aliases": ["Center on Long-Term Risk", "Centre on Long-Term Risk"],
        "category": "research", "risk": "low",
        "note": "S-risk, multi-agent/cooperation safety. Don't match bare 'CLR'.",
    },
    "CARMA": {
        "aliases": ["Center for AI Risk Management & Alignment",
                    "Center for AI Risk Management and Alignment"],
        "category": "research", "risk": "medium",
        "note": "Bare 'CARMA' collides with other orgs/datasets.",
    },
    "Cooperative AI Foundation": {
        "aliases": ["Cooperative AI Foundation", "CAIF"],
        "category": "research", "risk": "medium",
        "note": "Funds/coordinates cooperative AI research; co-authors benchmarks.",
    },
    "Cavendish Labs": {
        "aliases": ["Cavendish Labs"],
        "category": "research", "risk": "low",
        "note": "Borderline: AI safety + pandemic prevention.",
    },
    "Andon Labs": {
        "aliases": ["Andon Labs"],
        "category": "research", "risk": "low",
        "note": "Agent safety evals (e.g. Vending-Bench).",
    },
    "Gray Swan AI": {
        "aliases": ["Gray Swan"],
        "category": "research", "risk": "low",
        "note": "Adversarial robustness / jailbreak arenas; publishes with frontier labs.",
    },
    "Haize Labs": {
        "aliases": ["Haize Labs"],
        "category": "research", "risk": "low",
        "note": "Automated red-teaming startup.",
    },
    "Ought": {
        "aliases": ["Ought"],
        "category": "research", "risk": "high",
        "note": "Wound down (-> Elicit). Common English modal verb - affiliation field only, case-sensitive.",
    },
    "Neuronpedia": {
        "aliases": ["Neuronpedia", "Decode Research"],
        "category": "research", "risk": "low",
        "note": "Interpretability platform; often credited in acknowledgments.",
    },

    # ---------------- government safety institutes ----------------
    "UK AI Security Institute": {
        "aliases": ["AI Security Institute", "UK AI Safety Institute", "UK AISI"],
        "category": "government", "risk": "medium",
        "note": "Renamed from 'AI Safety Institute' Feb 2025. Generic 'AI Safety Institute' also catches the international AISI network (Japan, Canada, etc.) - keep as its own alias if you want that.",
    },
    "US CAISI": {
        "aliases": ["Center for AI Standards and Innovation", "US AI Safety Institute",
                    "U.S. AI Safety Institute", "US AISI"],
        "category": "government", "risk": "medium",
        "note": "US AISI renamed to CAISI (June 2025); housed in NIST. Bare 'CAISI' also = Canadian AI Safety Institute.",
    },
    "AI Safety Institute (generic)": {
        "aliases": ["AI Safety Institute"],
        "category": "government", "risk": "medium",
        "note": "Catch-all for the AISI network (Japan, Canada, Korea, Singapore...). Disambiguate by country in postprocessing.",
    },

    # ---------------- academic safety labs & centers ----------------
    "Center for Human-Compatible AI": {
        "aliases": ["Center for Human-Compatible AI", "Center for Human Compatible AI", "CHAI"],
        "category": "academic", "risk": "medium",
        "note": "UC Berkeley (Stuart Russell). 'CHAI' collides with Chai Research (chatbot co) and the chai test library.",
    },
    "Stanford Center for AI Safety": {
        "aliases": ["Stanford Center for AI Safety"],
        "category": "academic", "risk": "low",
        "note": "Mostly formal verification/robustness flavor, distinct from CAIS.",
    },
    "NYU Alignment Research Group": {
        "aliases": ["NYU Alignment Research Group", "NYU ARG"],
        "category": "academic", "risk": "low",
        "note": "Sam Bowman's group (largely moved to Anthropic; legacy papers).",
    },
    "MIT Algorithmic Alignment Group": {
        "aliases": ["Algorithmic Alignment Group"],
        "category": "academic", "risk": "low",
        "note": "Dylan Hadfield-Menell's lab at MIT CSAIL.",
    },
    "Krueger AI Safety Lab": {
        "aliases": ["Krueger AI Safety Lab", "KASL"],
        "category": "academic", "risk": "low",
        "note": "David Krueger (Cambridge/Mila).",
    },
    "FOCAL": {
        "aliases": ["Foundations of Cooperative AI Lab"],
        "category": "academic", "risk": "medium",
        "note": "CMU (Vincent Conitzer). Bare 'FOCAL' too generic.",
    },
    "Future of Humanity Institute": {
        "aliases": ["Future of Humanity Institute", "FHI"],
        "category": "academic", "risk": "medium",
        "note": "Closed April 2024; legacy affiliations still appear. 'FHI' collides with FHI 360.",
    },
    "Centre for the Study of Existential Risk": {
        "aliases": ["Centre for the Study of Existential Risk",
                    "Center for the Study of Existential Risk", "CSER"],
        "category": "academic", "risk": "low",
        "note": "Cambridge.",
    },
    "Leverhulme Centre for the Future of Intelligence": {
        "aliases": ["Leverhulme Centre", "Leverhulme Center",
                    "Centre for the Future of Intelligence"],
        "category": "academic", "risk": "low",
        "note": "Cambridge. Don't use bare 'CFI'.",
    },
    "Stanford Existential Risks Initiative": {
        "aliases": ["Stanford Existential Risks Initiative", "SERI"],
        "category": "academic", "risk": "high",
        "note": "Mostly inactive. 'SERI' alone is risky; 'SERI MATS' belongs to MATS.",
    },

    # ---------------- fellowships & training programs ----------------
    "MATS": {
        "aliases": ["MATS", "ML Alignment Theory Scholars",
                    "ML Alignment & Theory Scholars", "SERI MATS"],
        "category": "fellowship", "risk": "medium",
        "note": "Largest alignment training program; very common in acknowledgments. Whole-word uppercase 'MATS' only.",
    },
    "SPAR": {
        "aliases": ["SPAR", "Supervised Program for Alignment Research"],
        "category": "fellowship", "risk": "high",
        "note": "Run by Kairos. Uppercase whole-word only; collides with SPAR/SpaR method names.",
    },
    "Kairos": {
        "aliases": ["Kairos"],
        "category": "fellowship", "risk": "high",
        "note": "Parent org of SPAR and FSP fellowships. Common word/name - acknowledgments only.",
    },
    "LASR Labs": {
        "aliases": ["LASR Labs", "LASR"],
        "category": "fellowship", "risk": "medium",
        "note": "London AI Safety Research; many NeurIPS/ICLR workshop papers.",
    },
    "Pivotal Research": {
        "aliases": ["Pivotal Research", "Pivotal Fellowship"],
        "category": "fellowship", "risk": "medium",
        "note": "Don't match bare 'Pivotal'.",
    },
    "Astra Fellowship": {
        "aliases": ["Astra Fellowship"],
        "category": "fellowship", "risk": "medium",
        "note": "Run by Constellation. Never bare 'Astra' (Project Astra, AstraZeneca).",
    },
    "Constellation": {
        "aliases": ["Constellation"],
        "category": "fellowship", "risk": "high",
        "note": "Berkeley research center (residency/incubator). Common word - affiliation/acknowledgments only.",
    },
    "AI Safety Camp": {
        "aliases": ["AI Safety Camp"],
        "category": "fellowship", "risk": "low",
        "note": "'AISC' alone is risky.",
    },
    "ARENA": {
        "aliases": ["Alignment Research Engineer Accelerator"],
        "category": "fellowship", "risk": "high",
        "note": "Never bare 'ARENA' (Chatbot Arena!).",
    },
    "PIBBSS": {
        "aliases": ["PIBBSS",
                    "Principles of Intelligent Behavior in Biological and Social Systems"],
        "category": "fellowship", "risk": "low",
        "note": "Distinctive acronym, safe to match.",
    },
    "ERA Fellowship": {
        "aliases": ["ERA Fellowship", "ERA:AI"],
        "category": "fellowship", "risk": "high",
        "note": "Cambridge existential-risk fellowship. Never bare 'ERA'.",
    },
    "BlueDot Impact": {
        "aliases": ["BlueDot Impact", "AI Safety Fundamentals"],
        "category": "fellowship", "risk": "low",
        "note": "Courses, not research, but appears in acknowledgments/bios.",
    },
    "CBAI": {
        "aliases": ["Cambridge Boston Alignment Initiative", "CBAI"],
        "category": "fellowship", "risk": "medium",
        "note": "Runs HAIST/MAIA-adjacent fellowships.",
    },
    "LISA": {
        "aliases": ["London Initiative for Safe AI"],
        "category": "fellowship", "risk": "high",
        "note": "Coworking/research hub. Never bare 'LISA' (common name, LISA satellite, optimizer).",
    },
    "Arcadia Impact": {
        "aliases": ["Arcadia Impact"],
        "category": "fellowship", "risk": "low",
        "note": "UK field-building org; runs AI safety engineering projects (Inspect ecosystem work).",
    },
    "Impact Academy": {
        "aliases": ["Global AI Safety Fellowship", "Impact Academy"],
        "category": "fellowship", "risk": "low",
        "note": "",
    },
    "Anthropic Fellows Program": {
        "aliases": ["Anthropic Fellows"],
        "category": "fellowship", "risk": "low", "focus": "safety-adjacent",
        "note": "Originally alignment-focused, but now includes non-safety tracks (e.g. RL fellowship). Subsumed by 'Anthropic' match but useful for program-level tagging.",
    },
    "Athena": {
        "aliases": ["Athena Fellowship"],
        "category": "fellowship", "risk": "medium",
        "note": "Alignment mentorship program for women. Never bare 'Athena'.",
    },

    # ---------------- governance / policy research ----------------
    "Centre for the Governance of AI": {
        "aliases": ["Centre for the Governance of AI", "Center for the Governance of AI", "GovAI"],
        "category": "governance", "risk": "low",
        "note": "",
    },
    "Institute for AI Policy and Strategy": {
        "aliases": ["Institute for AI Policy and Strategy", "IAPS"],
        "category": "governance", "risk": "medium",
        "note": "",
    },
    "Centre for Long-Term Resilience": {
        "aliases": ["Centre for Long-Term Resilience", "Center for Long-Term Resilience"],
        "category": "governance", "risk": "low",
        "note": "Don't use bare 'CLTR'.",
    },
    "SaferAI": {
        "aliases": ["SaferAI"],
        "category": "governance", "risk": "medium",
        "note": "French risk-management/governance org. Watch for generic 'safer AI' phrase - case-sensitive single token.",
    },
    "Concordia AI": {
        "aliases": ["Concordia AI"],
        "category": "governance", "risk": "low",
        "note": "Beijing-based safety governance org.",
    },
    "Institute for Law & AI": {
        "aliases": ["Institute for Law & AI", "Institute for Law and AI",
                    "Legal Priorities Project"],
        "category": "governance", "risk": "low",
        "note": "",
    },
    "Oxford Martin AI Governance Initiative": {
        "aliases": ["Oxford Martin AI Governance Initiative"],
        "category": "governance", "risk": "low",
        "note": "",
    },
    "Forethought": {
        "aliases": ["Forethought Research", "Forethought Foundation"],
        "category": "governance", "risk": "medium",
        "note": "Macrostrategy research (Will MacAskill). Don't match bare 'Forethought'.",
    },
    "Convergence Analysis": {
        "aliases": ["Convergence Analysis"],
        "category": "governance", "risk": "medium",
        "note": "Phrase can occur in optimization papers - affiliation field only.",
    },
    "Global Catastrophic Risk Institute": {
        "aliases": ["Global Catastrophic Risk Institute", "GCRI"],
        "category": "governance", "risk": "medium",
        "note": "",
    },
    "ALTER": {
        "aliases": ["Association for Long Term Existence and Resilience"],
        "category": "governance", "risk": "high",
        "note": "Israel-based. Never bare 'ALTER'.",
    },
    "Center for AI Policy": {
        "aliases": ["Center for AI Policy"],
        "category": "governance", "risk": "medium",
        "note": "US advocacy org; distinct from Center for AI Safety.",
    },
    "Safeguarded AI": {
        "aliases": ["Safeguarded AI", "ARIA Safeguarded AI"],
        "category": "governance", "risk": "medium",
        "note": "UK ARIA programme (davidad); funds formal-verification safety work.",
    },
    "Epoch AI": {
        "aliases": ["Epoch AI"],
        "category": "governance", "risk": "medium",
        "note": "Borderline: AI forecasting/trends, FrontierMath. Match 'Epoch AI' exactly, never 'epoch'.",
    },
    "Existential Risk Observatory": {
        "aliases": ["Existential Risk Observatory"],
        "category": "governance", "risk": "low",
        "note": "",
    },
    "Frontier Model Forum": {
        "aliases": ["Frontier Model Forum"],
        "category": "governance", "risk": "low",
        "note": "Industry body (Anthropic/Google/Microsoft/OpenAI); publishes safety best practices.",
    },

    # ---------------- funders (mostly acknowledgments matches) ----------------
    "Open Philanthropy": {
        "aliases": ["Open Philanthropy", "Coefficient Giving"],
        "category": "funder", "risk": "low",
        "note": "Renamed to Coefficient Giving in late 2025 - keep both.",
    },
    "Long-Term Future Fund": {
        "aliases": ["Long-Term Future Fund", "Long Term Future Fund", "LTFF", "EA Funds"],
        "category": "funder", "risk": "low",
        "note": "",
    },
    "Survival and Flourishing Fund": {
        "aliases": ["Survival and Flourishing Fund", "SFF"],
        "category": "funder", "risk": "medium",
        "note": "'SFF' has collisions; prefer full name.",
    },
    "Longview Philanthropy": {
        "aliases": ["Longview Philanthropy"],
        "category": "funder", "risk": "low",
        "note": "",
    },
    "Foresight Institute": {
        "aliases": ["Foresight Institute"],
        "category": "funder", "risk": "low",
        "note": "AI safety grants + workshops (also nanotech legacy).",
    },
    "Manifund": {
        "aliases": ["Manifund"],
        "category": "funder", "risk": "low",
        "note": "Regranting platform; appears in acknowledgments.",
    },
    "Future of Life Institute": {
        "aliases": ["Future of Life Institute", "FLI"],
        "category": "funder", "risk": "medium",
        "note": "Grants + advocacy. 'FLI' has minor collisions.",
    },

    # ---------------- community / infrastructure ----------------
    "LessWrong / Alignment Forum": {
        "aliases": ["LessWrong", "Less Wrong", "Alignment Forum", "AI Alignment Forum",
                    "Lightcone Infrastructure"],
        "category": "community", "risk": "low",
        "note": "Citations to alignmentforum.org / lesswrong.com are themselves a strong safety signal.",
    },
    "Center for Applied Rationality": {
        "aliases": ["Center for Applied Rationality", "CFAR"],
        "category": "community", "risk": "high",
        "note": "Not really a research org. 'CFAR' = constant false alarm rate in signal processing - full name only.",
    },
    "Scale AI SEAL": {
        "aliases": ["Scale AI"],
        "category": "lab", "risk": "high", "focus": "safety-adjacent",
        "note": "Only the SEAL lab is safety-focused; Scale overall is a data company. Never bare 'SEAL' (MIT SEAL, Meta SEAL benchmark).",
    },

    # ---------------- safety-adjacent: general labs with real safety output ----
    "Google DeepMind": {
        "aliases": ["DeepMind"],
        "category": "lab", "risk": "low", "focus": "safety-adjacent",
        "note": "AGI Safety & Alignment team, interpretability, dangerous-capability evals.",
    },
    "Allen Institute for AI": {
        "aliases": ["Allen Institute for AI", "Allen Institute for Artificial Intelligence",
                    "AI2", "Ai2"],
        "category": "lab", "risk": "medium", "focus": "safety-adjacent",
        "note": "Open models + some safety/evals work. 'AI2'/'Ai2' whole-word, affiliation field only.",
    },
    "Meta AI": {
        "aliases": ["Meta AI", "Meta FAIR", "FAIR"],
        "category": "lab", "risk": "high", "focus": "safety-adjacent",
        "note": "Bare 'FAIR' is very risky (FAIR data principles, fairness papers) - affiliation field only.",
    },
    "Microsoft Research": {
        "aliases": ["Microsoft Research"],
        "category": "lab", "risk": "low", "focus": "safety-adjacent",
        "note": "Weakest signal in this tier: safety is a small share of a huge output.",
    },
    "xAI": {
        "aliases": ["xAI"],
        "category": "lab", "risk": "medium", "focus": "safety-adjacent",
        "note": "Case-sensitive whole word; rarely publishes papers.",
    },
    "Mila": {
        "aliases": ["Mila"],
        "category": "academic", "risk": "medium", "focus": "safety-adjacent",
        "note": "General ML institute, but hosts active safety groups (Bengio, Krueger). Whole-word case-sensitive.",
    },
    "Vector Institute": {
        "aliases": ["Vector Institute"],
        "category": "academic", "risk": "low", "focus": "safety-adjacent",
        "note": "Some safety/robustness work among general ML.",
    },
    "Hugging Face": {
        "aliases": ["Hugging Face", "HuggingFace"],
        "category": "lab", "risk": "low", "focus": "safety-adjacent",
        "note": "Evals/policy/societal-impact work among general tooling. Mostly noise unless combined with other signals.",
    },
    "Cohere Labs": {
        "aliases": ["Cohere Labs", "Cohere For AI"],
        "category": "lab", "risk": "low", "focus": "safety-adjacent",
        "note": "Safety/multilingual-harms work among general research.",
    },
    "Shanghai AI Laboratory": {
        "aliases": ["Shanghai AI Laboratory", "Shanghai Artificial Intelligence Laboratory"],
        "category": "lab", "risk": "low", "focus": "safety-adjacent",
        "note": "General lab with a substantial frontier-safety/eval program (SafeWork).",
    },
}

# Student safety groups - optional, mostly useful for acknowledgments/bios.
STUDENT_GROUPS = [
    "Harvard AI Safety Team",          # HAIST
    "MIT AI Alignment",                # MAIA
    "Stanford AI Alignment",
    "OxAI Safety Hub",
    "Cambridge AI Safety Hub",
    "Wisconsin AI Safety Initiative",
]

# Aliases that must ONLY be matched case-sensitively as whole words, and ideally
# only inside affiliation/acknowledgment fields (not paper body text).
AFFILIATION_ONLY = {
    "ARC", "MATS", "SPAR", "CAIS", "CHAI", "MIRI", "FHI", "FLI", "SERI",
    "CFAR", "SEAL", "SFF", "LASR", "KASL", "CAIF", "GCRI", "IAPS", "CBAI",
    "PIBBSS", "LTFF", "METR", "Ought", "Conjecture", "Orthogonal",
    "Constellation", "Kairos", "Aligned AI", "Truthful AI", "Convergence Analysis",
    "AI2", "Ai2", "FAIR", "xAI", "Mila",
}


import re

def _pattern(alias: str) -> re.Pattern:
    escaped = re.escape(alias)
    # Short/all-caps aliases and known-risky words: case-sensitive whole word.
    if alias in AFFILIATION_ONLY or alias.isupper():
        return re.compile(rf"(?<![\w.]){escaped}(?![\w.])")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)

_COMPILED = [
    (org, _pattern(alias), alias)
    for org, info in ORGS.items()
    for alias in info["aliases"]
]

def find_orgs(text: str, affiliation_field: bool = False) -> dict:
    """Return orgs found in `text`, split by safety focus:

        {"safety_only": {org_name: [matched aliases]},
         "safety_adjacent": {org_name: [matched aliases]}}

    A safety_only hit is a strong signal (candidate classifier false negative);
    a safety_adjacent hit is for org tagging only. If affiliation_field is
    False (i.e. matching body text), aliases listed in AFFILIATION_ONLY are
    skipped to avoid false positives.
    """
    hits = {"safety_only": {}, "safety_adjacent": {}}
    for org, pattern, alias in _COMPILED:
        if not affiliation_field and alias in AFFILIATION_ONLY:
            continue
        if pattern.search(text):
            tier = ("safety_adjacent"
                    if ORGS[org].get("focus") == "safety-adjacent"
                    else "safety_only")
            hits[tier].setdefault(org, []).append(alias)
    return hits


if __name__ == "__main__":
    sample = (
        "We thank the ML Alignment Theory Scholars (MATS) program and Open "
        "Philanthropy for funding. Authors are affiliated with Redwood Research, "
        "Google DeepMind, Ai2, and the Center for Human-Compatible AI. By "
        "Conjecture 3.1, the spar between orthogonal arcs ought to converge "
        "to a fair xai baseline."
    )
    from pprint import pprint
    print("affiliation mode:")
    pprint(find_orgs(sample, affiliation_field=True))
    print("body-text mode:")
    pprint(find_orgs(sample, affiliation_field=False))
