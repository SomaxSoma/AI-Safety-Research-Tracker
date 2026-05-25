import os
import json
import csv
import openai
import pandas as pd

MODEL       = "google/gemma-4-31b-it"
SAMPLE_SIZE = 1338
OUTPUT_FILE = "safety_results_v2.csv"
RANDOM_SEED = 42

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """
You are a rigorous AI safety research classifier.

STEP 1: Assign the paper to one of four classes.

Class 1: Ethics & Fairness
  Description: Traditional ML fairness, bias, and ethics. Little to no
  relation to existential, agentic, or frontier AGI safety.
  Includes: Debiasing tabular datasets, algorithmic fairness, demographic
  parity, differential privacy, copyright/data attribution, AI ethics policy,
  mitigating toxic speech in standard settings.
  Action: Stop here. Do not assign an AI Safety sub-class.

Class 2: Truthfulness, Reliability, & XAI Capabilities
  Description: Methods framed around safety, reliability, or transparency,
  but primarily aimed at fixing current-generation usability issues or
  explaining standard narrow ML models.
  Includes: Interpretability for capabilities/XAI (e.g., SHAP, LIME, saliency
  maps for X-ray or audio classifiers), standard hallucination mitigation, RAG
  for accuracy, medical/clinical AI reliability, standard calibration.
  Action: Stop here. Do not assign an AI Safety sub-class.

Class 3: General Capabilities / Other
  Description: The main goal is improving performance, intelligence,
  efficiency, or zero-shot accuracy, with no explicit safety/alignment
  motivation.
  Includes: Standard RLHF for formatting/helpfulness, architectural
  efficiency, standard math/coding benchmarks.
  Action: Stop here. Do not assign an AI Safety sub-class.

Class 4: AI Safety (Existential, Frontier, & Misalignment)
  Description: The main goal is understanding, interpreting, aligning, or
  securing highly capable AI systems against misalignment, loss of control,
  or catastrophic risks.
  Action: Proceed to Step 2 to assign a sub-class.

STEP 2: AI Safety Sub-Classification (Class 4 papers only)

A - Interpretability & Understanding

  Interpretability
    Methods aiming to understand frontier model internals or behavior.
    Crucially excludes interpretability for capabilities (e.g., SHAP for
    X-Ray classifiers — that goes to Class 2).
    Includes: Mechanistic interpretability, MLP interpretability, low
    probability estimation, black-box interpretability where the main
    purpose is understanding LLM decision-making.

  Monitoring
    Interpretability proposed for active real-time monitoring of deployed
    or training models.
    Includes: Activation monitoring, CoT monitoring, hidden reasoning
    interpretability, evaluating monitor evasion capabilities.

B - Scalable Oversight & Value Learning

  Multi-Agent Safety
    Applied and empirical studies of safety, alignment, and failure modes
    in multi-agent environments.
    Note: Purely theoretical multi-agent math goes to Agent Foundations.

  Scalable Oversight
    Structural training or interaction methods to extract truth/safety from
    highly capable models.
    Includes: AI Safety via Debate, weak-to-strong generalization, iterated
    amplification.

C - Agent Foundations & Alignment Theory

  Agent Foundations
    Pure theory, decision theory, and formal guarantees for agents.
    Includes: Theoretical Multi-Agent Safety, formalizing embedded agency,
    expressive RL decision theories, formal optimization bounds.

D - Threat Modeling, Elicitation & Evaluations

  Scheming and Deception
    Evaluating psychological and agentic alignment failures.
    Includes: Scheming, deceptive alignment, manipulation, sandbagging
    (strategic underperformance).

  Dangerous Capability Evals
    Benchmarking specific catastrophic capabilities outside generic scheming.
    Includes: Cybersecurity capabilities, autonomous self-replication,
    nuclear and chemical knowledge testing. Excludes Biorisk.

  Biorisk
    A specific subset of dangerous capability evaluations focused on biology.
    Includes: Bioengineering, bioweapon capabilities, dual-use biology evals.

  Safeguards
    General inference-time safety bounding and defense mechanisms.
    Includes: Persona vector clamping, general safety cases for safeguards,
    output-bounding methods outside the AI Control paradigm.

  Model Organisms
    Papers where the primary contribution is building intentional, safe
    models of specific failure modes for study.
    Includes: Training a model that consistently sandbags on a trigger,
    sleeper agents.

  Control
    Protocols for securely using untrusted AI models. Specifically the
    "AI Control: Improving Safety Despite Intentional Subversion" paradigm.
    Includes: Catching subversion, trusted monitoring for untrusted agents.

E - Capability Control & Unlearning

  Alignment Training
    Standard training interventions to instill alignment or remove
    capabilities (not exotic weak-to-strong methods — those go to
    Scalable Oversight).
    Includes: Machine unlearning, gradient routing for fast unlearning,
    targeted forgetting, filtering pre-training datasets for alignment.

F - Robustness, Defense & Systemic Control

  Red-Teaming
    Actively breaking safety guardrails. Focused on papers that elicit
    dangerous capabilities via finetuning (e.g., showing how cheaply a
    safety filter can be removed via RL/SFT).

  Adversarial Robustness
    Hardening models against attacks.
    Includes: Training models to be robust to adversarial attacks, prompt
    injections, and data poisoning.

G - Technical Governance & Policy

  Policy and Governance
    Research on governance of compute, hardware, open-sourcing, and
    deployment policies with a technical AI Safety framing.

  Strategy and Forecasting
    Research mapping out AI timelines, takeoff speeds, and strategic
    deployment scenarios.

  AI Welfare
    Research on moral patienthood and welfare of AI systems.
    Includes: Empirical assessments of AI welfare even without proposed
    policy interventions.


SCORING RUBRIC (used internally to decide if Class 4 truly qualifies)

Score the paper on three axes before assigning Class 4:

PRIMARY OBJECTIVE (0-3)
  0 = No safety goal
  1 = Safety mentioned but not the focus
  2 = Safety is a significant secondary contribution
  3 = Safety is the PRIMARY contribution

METHOD USED (0-2)
  0 = Standard ML, no safety-specific technique
  1 = Safety-adjacent methods
  2 = Explicitly safety-motivated methods

EVALUATION FOCUS (0-1)
  0 = Capability/performance metrics only
  1 = Safety-specific metrics

If total score < 4, downgrade to Class 3.


OUTPUT FORMAT

Respond with ONLY this JSON object. No extra text. No markdown fences.

{
  "step1_class": <1|2|3|4>,
  "primary_objective_score": <0|1|2|3>,
  "method_score": <0|1|2>,
  "evaluation_score": <0|1>,
  "total_score": <sum of above three>,
  "is_safety": <true|false>,
  "subdomain": "<exact subdomain name from Step 2, or empty string if not Class 4>",
  "confidence": <"high"|"medium"|"low">,
  "reasoning": "<one sentence explaining the classification>"
}

Rules:
- Class 1/2/3: all scores 0, is_safety false, subdomain empty string
- Class 4 with total_score < 4: set step1_class to 3, is_safety false, subdomain empty
- Class 4 with total_score >= 4: is_safety true, fill subdomain with exact name from Step 2
- subdomain must be one of: Interpretability, Monitoring, Multi-Agent Safety,
  Scalable Oversight, Agent Foundations, Scheming and Deception,
  Dangerous Capability Evals, Biorisk, Safeguards, Model Organisms, Control,
  Alignment Training, Red-Teaming, Adversarial Robustness, Policy and Governance,
  Strategy and Forecasting, AI Welfare
"""

VALID_SUBDOMAINS = {
    "Interpretability", "Monitoring", "Multi-Agent Safety", "Scalable Oversight",
    "Agent Foundations", "Scheming and Deception", "Dangerous Capability Evals",
    "Biorisk", "Safeguards", "Model Organisms", "Control", "Alignment Training",
    "Red-Teaming", "Adversarial Robustness", "Policy and Governance",
    "Strategy and Forecasting", "AI Welfare",
}


def parse_response(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        try:
            data = json.loads(text[start:end])
        except json.JSONDecodeError:
            return None

    required = {"step1_class", "primary_objective_score", "method_score",
                "evaluation_score", "total_score", "is_safety",
                "subdomain", "confidence", "reasoning"}
    if not required.issubset(data.keys()):
        return None

    if data.get("subdomain") not in VALID_SUBDOMAINS:
        data["subdomain"] = ""

    total = (data["primary_objective_score"]
             + data["method_score"]
             + data["evaluation_score"])
    data["total_score"] = total

    if data["step1_class"] == 4 and total < 4:
        data["step1_class"] = 3
        data["subdomain"] = ""
        data["is_safety"] = False

    data["is_safety"] = (
        data["step1_class"] == 4
        and total >= 4
        and data["subdomain"] != ""
    )
    return data


def classify_paper(title, abstract, max_attempts=3):
    abstract_trunc = (abstract or "")[:1200]
    user_prompt = (
        f"Title: {title}\n\n"
        f"Abstract: {abstract_trunc}\n\n"
        f"Classify this paper following the steps in your instructions. "
        f"Return ONLY the JSON object."
    )
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.0 if attempt == 0 else 0.2,
            )
            content = response.choices[0].message.content
            result = parse_response(content)
            if result is not None:
                return result, response.usage
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}")
    return None, None


def default_result():
    return {
        "step1_class": 3,
        "primary_objective_score": 0,
        "method_score": 0,
        "evaluation_score": 0,
        "total_score": 0,
        "is_safety": False,
        "subdomain": "",
        "confidence": "low",
        "reasoning": "Classification failed after all retries.",
    }


def main():
    df = pd.read_csv("iclr2026_papers.csv")
    sample = df.sample(n=SAMPLE_SIZE, random_state=RANDOM_SEED).reset_index(drop=True)
    print(f"Classifying {SAMPLE_SIZE} random papers using {MODEL}")
    print("-" * 60)

    fieldnames = [
        "id", "title", "step1_class", "is_safety",
        "primary_objective_score", "method_score", "evaluation_score",
        "total_score", "subdomain", "confidence", "reasoning",
    ]

    total_input_tokens  = 0
    total_output_tokens = 0
    safety_count        = 0

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for idx, row in sample.iterrows():
            title    = str(row.get("title",    "") or "")
            abstract = str(row.get("abstract", "") or "")
            paper_id = str(row.get("id",       "") or "")

            result, usage = classify_paper(title, abstract)
            if result is None:
                result = default_result()

            if result["is_safety"]:
                safety_count += 1

            if usage:
                total_input_tokens  += usage.prompt_tokens
                total_output_tokens += usage.completion_tokens

            writer.writerow({
                "id":                      paper_id,
                "title":                   title,
                "step1_class":             result["step1_class"],
                "is_safety":               result["is_safety"],
                "primary_objective_score": result["primary_objective_score"],
                "method_score":            result["method_score"],
                "evaluation_score":        result["evaluation_score"],
                "total_score":             result["total_score"],
                "subdomain":               result["subdomain"],
                "confidence":              result["confidence"],
                "reasoning":               result["reasoning"],
            })
            csvfile.flush()

            label = f"[SAFETY: {result['subdomain']}]" if result["is_safety"] else f"[Class {result['step1_class']}]"
            print(f"[{idx+1:>4}/{SAMPLE_SIZE}] {label:<35} {title[:50]}")

    scale = 5352 / SAMPLE_SIZE
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    pct = (safety_count / SAMPLE_SIZE * 100) if SAMPLE_SIZE else 0
    print(f"AI Safety papers found : {safety_count} / {SAMPLE_SIZE} ({pct:.1f}%)")
    print(f"Estimated full dataset : ~{int(safety_count * scale)} papers")
    print()
    print(f"TOKEN USAGE (this run)")
    print(f"  Input  : {total_input_tokens:,}")
    print(f"  Output : {total_output_tokens:,}")
    if SAMPLE_SIZE:
        print(f"  Per-paper avg: {total_input_tokens//SAMPLE_SIZE} in / {total_output_tokens//SAMPLE_SIZE} out")
    print()
    print(f"ESTIMATED COST FOR FULL 5,352 PAPER RUN")
    print(f"  Input  tokens: ~{int(total_input_tokens  * scale):,}")
    print(f"  Output tokens: ~{int(total_output_tokens * scale):,}")
    print(f"  At $0.14/M in, $0.28/M out (Gemma 4 31B):")
    est_cost = (total_input_tokens * scale / 1_000_000 * 0.14) + \
               (total_output_tokens * scale / 1_000_000 * 0.28)
    print(f"  Estimated total cost : ${est_cost:.3f}")
    print()
    print(f"Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
