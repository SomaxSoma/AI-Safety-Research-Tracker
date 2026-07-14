/* AI Safety Research Tracker — datasets.
   Aggregates cross-checked against github.com/SomaxSoma/AI-Safety-Research-Tracker
   (data/aggregate_plots, data/iclr/2026, data/arxiv/monthly_trend.csv). */

/* Safety share of accepted papers by year, pooled across ICLR + ICML + NeurIPS (README table). */
const BY_YEAR = [
  ['2019', 0.3], ['2020', 0.7], ['2021', 0.7], ['2022', 1.0],
  ['2023', 1.5], ['2024', 4.2], ['2025', 6.1], ['2026', 8.3],
];

/* Safety subdomains per year, all venues pooled (aggregate_plots). [year, n, [[subdomain, count]...]] */
const SD_RAW = [
  ['2019', 9, [['Interpretability', 2], ['Scalable Oversight', 2], ['Alignment Training', 1], ['Adversarial Robustness', 1], ['Red-Teaming', 1], ['Safeguards', 1], ['Multi-Agent Safety', 1]]],
  ['2020', 26, [['Adversarial Robustness', 8], ['Alignment Training', 6], ['Interpretability', 5], ['Scalable Oversight', 3], ['Red-Teaming', 1], ['Dangerous Capability Evals', 1], ['Multi-Agent Safety', 1], ['Agent Foundations', 1]]],
  ['2021', 31, [['Adversarial Robustness', 10], ['Interpretability', 9], ['Alignment Training', 4], ['Scalable Oversight', 3], ['Agent Foundations', 2], ['Red-Teaming', 1], ['Dangerous Capability Evals', 1], ['Multi-Agent Safety', 1]]],
  ['2022', 48, [['Adversarial Robustness', 18], ['Alignment Training', 11], ['Interpretability', 7], ['Red-Teaming', 4], ['Scalable Oversight', 3], ['Multi-Agent Safety', 3], ['Agent Foundations', 2]]],
  ['2023', 101, [['Interpretability', 39], ['Adversarial Robustness', 22], ['Alignment Training', 11], ['Red-Teaming', 9], ['Scalable Oversight', 5], ['Multi-Agent Safety', 4], ['Safeguards', 3], ['Agent Foundations', 3], ['Dangerous Capability Evals', 2], ['Scheming and Deception', 2], ['Policy and Governance', 1]]],
  ['2024', 370, [['Interpretability', 108], ['Alignment Training', 73], ['Red-Teaming', 52], ['Adversarial Robustness', 45], ['Scalable Oversight', 36], ['Safeguards', 19], ['Multi-Agent Safety', 8], ['Policy and Governance', 8], ['Agent Foundations', 7], ['Dangerous Capability Evals', 5], ['Control', 3], ['Strategy and Forecasting', 2], ['Monitoring', 1], ['Scheming and Deception', 1], ['Model Organisms', 1], ['AI Welfare', 1]]],
  ['2025', 744, [['Interpretability', 204], ['Alignment Training', 170], ['Red-Teaming', 104], ['Adversarial Robustness', 80], ['Safeguards', 73], ['Scalable Oversight', 56], ['Dangerous Capability Evals', 15], ['Monitoring', 14], ['Multi-Agent Safety', 8], ['Scheming and Deception', 7], ['Agent Foundations', 7], ['Control', 2], ['Model Organisms', 2], ['Strategy and Forecasting', 1], ['Biorisk', 1]]],
  ['2026', 999, [['Interpretability', 283], ['Alignment Training', 181], ['Adversarial Robustness', 114], ['Red-Teaming', 114], ['Safeguards', 103], ['Scalable Oversight', 56], ['Monitoring', 38], ['Dangerous Capability Evals', 31], ['Scheming and Deception', 24], ['Multi-Agent Safety', 19], ['Policy and Governance', 17], ['Agent Foundations', 5], ['Strategy and Forecasting', 5], ['Control', 4], ['Model Organisms', 2], ['Biorisk', 2], ['AI Welfare', 1]]],
];

/* Major classes across all 5,352 ICLR 2026 accepted papers. */
const MAJOR = [
  ['General Capabilities', 4310],
  ['Truthfulness & Reliability', 474],
  ['Ethics & Fairness', 156],
  ['AI Safety', 412],
];

/* ICLR 2026 safety papers (n=412) — subareas, subdomains, score distribution (filtered/safety.csv). */
const SUBAREAS = [
  ['A · Interpretability & Understanding', 136],
  ['F · Robustness, Defense & Control', 93],
  ['E · Capability Control & Unlearning', 87],
  ['D · Threat Modeling & Evaluations', 68],
  ['B · Scalable Oversight & Value Learning', 27],
  ['G · Technical Governance & Policy', 1],
];
const SUBDOMAINS = [
  ['Interpretability', 122], ['Alignment Training', 87], ['Red-Teaming', 50],
  ['Adversarial Robustness', 43], ['Safeguards', 41], ['Scalable Oversight', 21],
  ['Dangerous Capability Evals', 15], ['Monitoring', 14], ['Scheming and Deception', 9],
  ['Multi-Agent Safety', 6], ['Control', 2], ['Policy and Governance', 1], ['Biorisk', 1],
];
const SCORES = [['3', 58], ['4', 51], ['5', 66], ['6', 71], ['7', 166]];

/* Highest-scoring papers per view (classifier output). URLs from data/iclr/2026/papers.csv. */
const NOTABLE_SUBAREAS = [
  { t: 'Steering Language Models with Weight Arithmetic', d: 'Interpretability', u: 'https://openreview.net/forum?id=S0D3EFWohd' },
  { t: 'Output Supervision Can Obfuscate the Chain of Thought', d: 'Monitoring', u: 'https://openreview.net/forum?id=JTX0iqxBjk' },
  { t: 'Control Tax: The Price of Keeping AI in Check', d: 'Control', u: 'https://openreview.net/forum?id=BpyR6Wkl1c' },
  { t: 'Reliable Weak-to-Strong Monitoring of LLM Agents', d: 'Scalable Oversight', u: 'https://openreview.net/forum?id=WV7xIboTDK' },
  { t: 'Deep Ignorance: Filtering Pretraining Data Builds Tamper-Resistant Safeguards', d: 'Alignment Training', u: 'https://openreview.net/forum?id=xcf0QcTcGS' },
  { t: 'Estimating Worst-Case Frontier Risks of Open-Weight LLMs', d: 'Dangerous Capability Evals', u: 'https://openreview.net/forum?id=rXLRyJXSCy' },
  { t: 'GeneBreaker: Jailbreak Attacks against DNA Language Models', d: 'Biorisk', u: 'https://openreview.net/forum?id=C5OIolrNJd' },
  { t: 'Strategic Dishonesty Can Undermine AI Safety Evaluations of Frontier LLMs', d: 'Scheming and Deception', u: 'https://openreview.net/forum?id=IbDr8xgUMW' },
];
const NOTABLE_SUBDOMAINS = [
  { t: 'Circuit Insights: Towards Interpretability Beyond Activations', d: 'Interpretability', u: 'https://openreview.net/forum?id=2Jyb1yu3nN' },
  { t: 'Self-Destructive Language Models', d: 'Alignment Training', u: 'https://openreview.net/forum?id=ERNpUGr8M5' },
  { t: 'Constitutional Classifiers++: Defenses against Universal Jailbreaks', d: 'Adversarial Robustness', u: 'https://openreview.net/forum?id=eNvsH5Ye2V' },
  { t: 'STAR: Strategy-driven Automatic Jailbreak Red-teaming', d: 'Red-Teaming', u: 'https://openreview.net/forum?id=c2BygWVqag' },
  { t: 'Building a Foundational Guardrail for General Agentic Systems', d: 'Safeguards', u: 'https://openreview.net/forum?id=M47SWYubR5' },
  { t: 'The Alignment Auditor: A Bayesian Framework for Verifying LLM Objectives', d: 'Scalable Oversight', u: 'https://openreview.net/forum?id=CH7TfRLqSF' },
  { t: 'MCP-SafetyBench: Safety Evaluation with Real-World MCP Servers', d: 'Dangerous Capability Evals', u: 'https://openreview.net/forum?id=7XYjeL46co' },
  { t: 'Beyond Prompt-Induced Lies: Investigating LLM Deception on Benign Prompts', d: 'Scheming and Deception', u: 'https://openreview.net/forum?id=PDBBYwd1LY' },
];
const NOTABLE_SCORE = [
  { t: 'Spilling the Beans: Teaching LLMs to Self-Report Their Hidden Objectives', d: '7 / 7', u: 'https://openreview.net/forum?id=sWs0cCuM8I' },
  { t: 'SafeDPO: Direct Preference Optimization with Enhanced Safety', d: '7 / 7', u: 'https://openreview.net/forum?id=PJdw4VBsXD' },
  { t: 'Any-Depth Alignment: Unlocking Innate Safety Alignment of LLMs', d: '7 / 7', u: 'https://openreview.net/forum?id=0fuYOuJyzl' },
  { t: 'RedTeamCUA: Adversarial Testing of Computer-Use Agents', d: '7 / 7', u: 'https://openreview.net/forum?id=yWwrgcBoK3' },
  { t: 'Watch the Weights: Unsupervised Monitoring of Fine-tuned LLMs', d: '7 / 7', u: 'https://openreview.net/forum?id=WZYxJhvAvD' },
  { t: 'Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols', d: '7 / 7', u: 'https://openreview.net/forum?id=wSs1Ez3aKl' },
  { t: 'Thought Branches: Interpreting LLM Reasoning Requires Resampling', d: '7 / 7', u: 'https://openreview.net/forum?id=bVsAuIOvJ5' },
  { t: 'Beyond Linear Probes: Dynamic Safety Monitoring for Language Models', d: '7 / 7', u: 'https://openreview.net/forum?id=AGWa8whf92' },
];

/* Per-venue safety share by year — computed from data/{conf}/{year}/results.csv.
   Each entry: [share %, safety papers, total papers]; null = conference not yet held. */
const VENUE_SHARES = {
  years: ['2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026'],
  venues: [
    { key: 'ICLR', fill: '#f2f2f2', rows: [[1.2, 6, 500], [0.9, 6, 687], [1.0, 9, 859], [0.9, 10, 1094], [1.3, 21, 1573], [3.8, 86, 2260], [6.8, 250, 3703], [7.7, 412, 5352]] },
    { key: 'ICML', fill: 'rgba(255,255,255,.55)', rows: [[0.4, 3, 773], [0.8, 9, 1084], [0.5, 6, 1183], [1.0, 12, 1233], [1.1, 20, 1828], [4.2, 109, 2610], [6.3, 207, 3260], [8.9, 587, 6627]] },
    { key: 'NEURIPS', fill: 'rgba(255,255,255,.28)', rows: [[0.0, 0, 1428], [0.6, 11, 1898], [0.6, 16, 2632], [1.0, 26, 2671], [1.9, 60, 3218], [4.3, 175, 4035], [5.4, 287, 5286], null] },
  ],
};

/* Taxonomy definitions, condensed from src/prompt.txt (the classification rubric). */
const GLOSSARY = {
  'Interpretability': 'Understanding frontier model internals or behavior — mechanistic interpretability, sparse autoencoders, circuit analysis, probing representations.',
  'Monitoring': 'Interpretability applied to real-time monitoring of deployed or training models — activation monitoring, CoT monitoring, hidden-reasoning detection.',
  'Multi-Agent Safety': 'Empirical studies of safety, alignment, and failure modes in multi-agent environments.',
  'Scalable Oversight': 'Extracting truth/safety from models smarter than their supervisors — debate, weak-to-strong generalization, iterated amplification.',
  'Agent Foundations': 'Pure theory: decision theory, formal guarantees for agents, embedded agency, formal optimization bounds.',
  'Scheming and Deception': 'Evaluating agentic alignment failures — scheming, deceptive alignment, manipulation, sandbagging.',
  'Dangerous Capability Evals': 'Benchmarking catastrophic capabilities (cybersecurity, autonomous replication, CBRN); biology-focused evals are Biorisk.',
  'Biorisk': 'Dangerous-capability evaluations focused on biology — bioengineering, bioweapon capabilities, dual-use biology.',
  'Safeguards': 'Inference-time safety bounding and defense — persona clamping, safety cases, output-bounding, over-refusal calibration.',
  'Model Organisms': 'Building intentional models of failure modes for study — sleeper agents, triggered sandbagging.',
  'Control': 'Protocols for securely using untrusted AI — the "AI Control: safety despite intentional subversion" paradigm.',
  'Alignment Training': 'Training interventions to instill alignment or remove capabilities — unlearning, gradient routing, pre-training data filtering.',
  'Red-Teaming': 'Actively breaking safety guardrails — eliciting dangerous capabilities via finetuning, jailbreak discovery, filter removal.',
  'Adversarial Robustness': 'Hardening frontier models against attacks — prompt-injection defense, adversarial training, data-poisoning defense.',
  'Policy and Governance': 'Governance of compute, hardware, open-sourcing, and deployment with a technical AI-safety framing.',
  'Strategy and Forecasting': 'AI timelines, takeoff speeds, strategic deployment scenarios.',
  'AI Welfare': 'Moral patienthood and welfare of AI systems.',
  'Interpretability & Understanding': 'Understanding model internals and applying it to monitoring: Interpretability, Monitoring.',
  'Scalable Oversight & Value Learning': 'Supervising models beyond human evaluation capacity: Scalable Oversight, Multi-Agent Safety.',
  'Agent Foundations & Alignment Theory': 'Theory of agency and alignment: Agent Foundations.',
  'Threat Modeling & Evaluations': 'Eliciting and measuring dangerous behavior: Scheming & Deception, Dangerous Capability Evals, Biorisk, Safeguards, Model Organisms, Control.',
  'Capability Control & Unlearning': 'Training-time control of what models know and do: Alignment Training.',
  'Robustness, Defense & Control': 'Attacking and hardening guardrails: Red-Teaming, Adversarial Robustness.',
  'Technical Governance & Policy': 'Technical governance: Policy and Governance, Strategy and Forecasting, AI Welfare.',
};

/* Research orgs behind safety papers — data/org_plots/orgs.csv (LLM-verified affiliations).
   ORGS_ASSOC: any confirmed affiliation (one paper can add to several orgs), excl.
   University/Independent. ORGS_PRIMARY: each paper once, under its primary affiliation
   (incl. Independent/University). [name, papers, legal type]. */
const ORGS_ASSOC = [
  ['Google DeepMind', 107, 'corporate'],
  ['OpenAI', 74, 'corporate → PBC (2026)'],
  ['MATS', 61, 'nonprofit fellowship'],
  ['Anthropic', 51, 'public-benefit corporation'],
  ['Mila', 50, 'academic centre'],
  ['Microsoft Research', 41, 'corporate'],
  ['Center for AI Safety', 32, 'nonprofit'],
  ['Shanghai AI Laboratory', 29, 'nonprofit'],
  ['Meta AI', 27, 'corporate'],
  ['FAR.AI', 24, 'nonprofit'],
  ['Vector Institute', 24, 'academic centre'],
  ['UK AI Security Institute', 22, 'government'],
  ['Allen Institute for AI', 16, 'nonprofit'],
  ['Center for Human-Compatible AI', 13, 'academic centre'],
  ['Constellation', 11, 'nonprofit'],
  ['Anthropic Fellows Program', 10, 'nonprofit'],
  ['EleutherAI', 9, 'nonprofit'],
  ['Redwood Research', 9, 'nonprofit'],
  ['Scale AI SEAL', 9, 'corporate'],
  ['Cooperative AI Foundation', 8, 'nonprofit'],
  ['Goodfire', 8, 'corporate'],
  ['Apollo Research', 7, 'nonprofit'],
  ['Center on Long-Term Risk', 6, 'nonprofit'],
  ['Timaeus', 6, 'nonprofit'],
  ['Apart Research', 5, 'nonprofit'],
  ['Gray Swan AI', 5, 'corporate'],
  ['SPAR', 5, 'nonprofit'],
  ['Frontier Model Forum', 4, 'nonprofit'],
  ['LASR Labs', 4, 'nonprofit'],
  ['LawZero', 4, 'nonprofit'],
  ['Stanford Existential Risks Initiative', 4, 'academic centre'],
  ['AI Safety Camp', 3, 'nonprofit'],
  ['Alignment Research Center', 3, 'nonprofit'],
  ['Astra Fellowship', 3, 'nonprofit'],
  ['PIBBSS', 3, 'nonprofit'],
  ['Truthful AI', 3, 'nonprofit'],
  ['AE Studio', 2, 'corporate'],
  ['CBAI', 2, 'nonprofit'],
  ['FOCAL', 2, 'academic centre'],
  ['Future of Humanity Institute', 2, 'academic centre'],
  ['Haize Labs', 2, 'corporate'],
  ['Hugging Face', 2, 'corporate'],
  ['LISA', 2, 'nonprofit'],
  ['METR', 2, 'nonprofit'],
  ['Transluce', 2, 'nonprofit'],
  ['AI Safety Institute (generic)', 1, 'government'],
  ['Arcadia Impact', 1, 'nonprofit'],
  ['Cavendish Labs', 1, 'nonprofit'],
  ['Center for Applied Rationality', 1, 'nonprofit'],
  ['Concordia AI', 1, 'nonprofit'],
  ['Conjecture', 1, 'corporate'],
  ['ERA Fellowship', 1, 'nonprofit'],
  ['NYU Alignment Research Group', 1, 'academic centre'],
  ['Stanford Center for AI Safety', 1, 'academic centre'],
  ['US CAISI', 1, 'government'],
];
const ORGS_PRIMARY = [
  ['Independent / University', 251, 'no tracked org'],
  ['MATS', 48, 'nonprofit fellowship'],
  ['Mila', 46, 'academic centre'],
  ['Google DeepMind', 42, 'corporate'],
  ['Shanghai AI Laboratory', 27, 'nonprofit'],
  ['Vector Institute', 21, 'academic centre'],
  ['Meta AI', 16, 'corporate'],
  ['Allen Institute for AI', 15, 'nonprofit'],
  ['FAR.AI', 13, 'nonprofit'],
  ['Microsoft Research', 13, 'corporate'],
  ['OpenAI', 11, 'corporate → PBC (2026)'],
  ['Center for AI Safety', 9, 'nonprofit'],
  ['Anthropic Fellows Program', 8, 'nonprofit'],
  ['Redwood Research', 8, 'nonprofit'],
  ['UK AI Security Institute', 8, 'government'],
  ['Anthropic', 7, 'public-benefit corporation'],
  ['EleutherAI', 6, 'nonprofit'],
  ['Center for Human-Compatible AI', 5, 'academic centre'],
  ['LASR Labs', 4, 'nonprofit'],
  ['SPAR', 4, 'nonprofit'],
  ['Timaeus', 4, 'nonprofit'],
  ['Apart Research', 3, 'nonprofit'],
  ['Apollo Research', 3, 'nonprofit'],
  ['Center on Long-Term Risk', 3, 'nonprofit'],
  ['AE Studio', 2, 'corporate'],
  ['Alignment Research Center', 2, 'nonprofit'],
  ['Astra Fellowship', 2, 'nonprofit'],
  ['Future of Humanity Institute', 2, 'academic centre'],
  ['LawZero', 2, 'nonprofit'],
  ['PIBBSS', 2, 'nonprofit'],
  ['Transluce', 2, 'nonprofit'],
  ['AI Safety Camp', 1, 'nonprofit'],
  ['Center for Applied Rationality', 1, 'nonprofit'],
  ['Concordia AI', 1, 'nonprofit'],
  ['Constellation', 1, 'nonprofit'],
  ['Goodfire', 1, 'corporate'],
  ['Gray Swan AI', 1, 'corporate'],
  ['Haize Labs', 1, 'corporate'],
  ['Hugging Face', 1, 'corporate'],
  ['METR', 1, 'nonprofit'],
  ['NYU Alignment Research Group', 1, 'academic centre'],
  ['Scale AI SEAL', 1, 'corporate'],
  ['Truthful AI', 1, 'nonprofit'],
];
/* Funders acknowledged in safety papers (funding credits, not affiliations) — funders.csv. */
const FUNDERS_LIST = [
  ['Open Philanthropy', 120, 'funder'],
  ['Long-Term Future Fund', 10, 'funder'],
  ['Future of Life Institute', 8, 'funder'],
  ['Foresight Institute', 4, 'funder'],
  ['Manifund', 4, 'funder'],
  ['Survival and Flourishing Fund', 3, 'funder'],
  ['Longview Philanthropy', 1, 'funder'],
];

/* Papers with a tracked-org PRIMARY affiliation OR a funder, per year —
   [year, org-or-funder, checked] from org_verified.csv. A paper counts if a named
   research org is its primary affiliation OR it acknowledges a funder; papers that
   are independent apart from a lone company author (e.g. one DeepMind author on an
   otherwise-academic paper) are excluded. "checked" = safety papers with
   retrievable full text scanned. */
const ORG_BY_YEAR = [
  ['2019', 5, 9], ['2020', 9, 26], ['2021', 6, 31], ['2022', 8, 48], ['2023', 32, 101], ['2024', 94, 370], ['2025', 139, 744], ['2026', 150, 954],
];

const GH_REPO = 'SomaxSoma/AI-Safety-Research-Tracker';
const GH_URL = 'https://github.com/' + GH_REPO;

const PIPELINE = [
  { step: 'STEP 01', name: 'fetch.py', desc: 'Pull accepted papers from OpenReview, PMLR, icml.cc and papers.nips.cc — 55,794 papers across 23 conference-years, with title, abstract, keywords.' },
  { step: 'STEP 02', name: 'classify.py', desc: 'DeepSeek V4 Flash (a reasoning LLM) reads each paper\'s title + abstract — 50 async workers — and assigns a class, subdomain and 1–7 safety score.' },
  { step: 'STEP 03', name: 'visualize.py', desc: 'Aggregate into major classes, 7 subareas, 17 subdomains and score distribution; emit filtered CSVs and plots.' },
];
const CLASS_DEFS = [
  { n: '01', name: 'Ethics & Fairness', desc: 'Bias, fairness, privacy, ethics with little tie to frontier or existential risk. — 156 papers' },
  { n: '02', name: 'Truthfulness & XAI', desc: 'Reliability / transparency fixing current-gen usability: hallucination, calibration, saliency. — 474' },
  { n: '03', name: 'General Capabilities', desc: 'Performance / efficiency / generalization with no explicit safety motivation. — 4,310' },
  { n: '04', name: 'AI Safety', desc: 'Understanding, aligning or securing highly capable systems against misalignment. — 412' },
];

/* arXiv AI-safety trend — REAL data from data/arxiv/monthly_trend.csv (cs.LG · cs.AI · cs.CL · stat.ML).
   frac = monthly safety share %, roll = 7-mo rolling mean %, vol = papers/month. Jan 2019 – Jun 2026. */
const ARXIV = {"months":["2019-01","2019-02","2019-03","2019-04","2019-05","2019-06","2019-07","2019-08","2019-09","2019-10","2019-11","2019-12","2020-01","2020-02","2020-03","2020-04","2020-05","2020-06","2020-07","2020-08","2020-09","2020-10","2020-11","2020-12","2021-01","2021-02","2021-03","2021-04","2021-05","2021-06","2021-07","2021-08","2021-09","2021-10","2021-11","2021-12","2022-01","2022-02","2022-03","2022-04","2022-05","2022-06","2022-07","2022-08","2022-09","2022-10","2022-11","2022-12","2023-01","2023-02","2023-03","2023-04","2023-05","2023-06","2023-07","2023-08","2023-09","2023-10","2023-11","2023-12","2024-01","2024-02","2024-03","2024-04","2024-05","2024-06","2024-07","2024-08","2024-09","2024-10","2024-11","2024-12","2025-01","2025-02","2025-03","2025-04","2025-05","2025-06","2025-07","2025-08","2025-09","2025-10","2025-11","2025-12","2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"],"frac":[0.213,0.651,0.469,0.374,0.392,0.512,0.502,0.333,0.241,0.398,0.38,0.873,0.223,0.555,0.348,0.856,0.432,0.75,0.48,0.473,0.606,0.52,0.466,0.594,0.884,0.722,0.624,0.755,0.689,0.65,0.733,0.487,0.577,0.707,0.729,0.914,1.189,0.885,0.761,0.765,1.035,0.892,0.572,0.633,0.846,0.912,1.105,1.223,1.449,1.473,1.212,1.525,1.81,1.433,1.928,2.084,2.222,3.409,3.007,2.786,2.99,4.438,2.953,3.498,4.083,4.663,4.054,3.705,3.553,5.769,4.087,4.41,4.527,6.381,5.089,6.064,7.368,6.459,5.841,5.88,6.324,7.454,6.12,6.876,7.746,8.376,7.713,9.432,9.251,9.362],"roll":[0.432,0.444,0.498,0.412,0.426,0.468,0.449,0.359,0.324,0.339,0.55,0.492,0.55,0.375,0.586,0.545,0.679,0.554,0.568,0.52,0.533,0.531,0.526,0.648,0.733,0.743,0.7,0.69,0.698,0.691,0.623,0.599,0.59,0.671,0.784,0.944,0.996,0.945,0.803,0.854,0.897,0.833,0.699,0.683,0.797,0.954,1.08,1.259,1.382,1.378,1.403,1.516,1.589,1.723,1.815,2.078,2.572,2.879,3.067,2.928,3.405,3.46,3.63,3.511,4.081,4.266,4.14,3.77,4.342,4.47,4.755,4.341,5.106,5.332,5.845,6.174,6.631,6.556,6.06,6.015,6.553,6.633,6.817,6.914,7.666,7.945,8.507,8.799,9.349,9.307],"vol":[1408,1536,1492,1872,2552,2541,1993,1800,2488,2767,2633,2062,1791,2702,2302,2804,2780,3866,2915,2328,2641,4230,3006,3032,2376,3046,3043,3180,3046,4152,2866,2463,3469,4100,3016,3063,2607,3276,3681,3139,3960,3812,2974,2686,3193,4933,3893,3108,2761,3733,3962,3344,6077,4816,3839,3838,4185,6014,4789,4415,4114,6241,5453,4888,6001,6713,5304,4616,5292,8077,5334,5987,5037,7475,6701,5689,9324,7524,6437,6752,7938,9029,7108,6108,7617,8262,8726,8651,12398,9464]};

/* Distilled TF-IDF classifier metrics (src/arxiv_trend, random 80/20 split, n=11,159). */
/* View definitions for the tab panel. */
const VIEWS = {
  overview: {
    key: 'overview', label: 'OVERVIEW',
  },
  conferences: {
    key: 'conferences', label: 'CONFERENCES', chartTitle: 'AI-safety share of accepted papers, by year', chartUnit: 'ICLR + ICML + NeurIPS, pooled',
    kicker: 'ACROSS ALL VENUES', big: { num: 8.3, dec: 1, suf: '%' }, bigUnit: 'in 2026', bigLabel: 'of accepted papers are safety (0.3% in 2019)',
    brief: 'Pooled across three venues and eight years, the safety share rose roughly 28× — from 0.3% in 2019 to 8.3% in 2026. Highest single conference: ICML 2026 at 8.9%.',
    stats: [{ k: 'Conference-years', v: '23' }, { k: 'Total papers', v: '55,794' }, { k: 'Safety papers', v: '2,328' }],
    type: 'vbar', entries: BY_YEAR, suf: '%',
    note: 'Pooled across ICLR, ICML and NeurIPS. 2026 = ICLR + ICML only — NeurIPS 2026 not yet held.',
  },
  arxiv: {
    key: 'arxiv', label: 'ARXIV TREND', chartTitle: 'AI-safety share of arXiv, monthly', chartUnit: '2019–2026 · 7-mo rolling avg',
    kicker: 'ARXIV-WIDE TREND', big: { num: 9.3, dec: 1, suf: '%' }, bigUnit: 'mid-2026', bigLabel: 'of monthly arXiv AI papers are safety-related',
    brief: 'For arXiv-scale coverage, a lightweight keyword-based classifier (TF-IDF, traditional ML) scores every paper, calibrated so its overall safety rate matches the LLM\'s on a labeled subsample. At ~72% precision / 74% recall, read it as a rough trend estimate. Safety rose from 0.4% of AI papers in 2019 to over 9% in 2026.',
    stats: [{ k: '2019 → 2026', v: '0.4% → 9.3%' }, { k: 'Classifier', v: 'TF-IDF (calibrated)' }, { k: 'Precision / recall', v: '72% / 74%' }],
    type: 'line',
  },
  subdomains: {
    key: 'subdomains', label: 'DETAILED CLASSES', chartTitle: 'Safety papers by subdomain', chartUnit: 'ICLR 2026 · 13 of 17 · n=412',
    kicker: 'DETAILED CLASSES', big: { num: 122 }, bigUnit: 'papers', bigLabel: 'in Interpretability, the top subdomain',
    brief: 'Thirteen of the seventeen defined subdomains appear. Interpretability, Alignment Training and Red-Teaming account for nearly two-thirds of all safety papers.',
    stats: [{ k: 'Distinct subdomains', v: '13 / 17' }, { k: 'Top-3 share', v: '63%' }, { k: 'Rarest (Biorisk, Policy)', v: '1 each' }],
    type: 'hbar', entries: SUBDOMAINS, notable: NOTABLE_SUBDOMAINS, countLabel: '13 subdomains',
    hasDrill: true,
  },
  orgs: {
    key: 'orgs', label: 'WHO PUBLISHES', chartTitle: 'Research orgs behind safety papers', chartUnit: 'every affiliation counted',
    kicker: 'ORG AFFILIATIONS', big: { num: 55 }, bigUnit: 'orgs', bigLabel: 'have authors on the safety papers',
    brief: 'The organizations behind AI-safety research — the labs, academic groups and nonprofits whose people write the papers, and the funders whose money shows up in the acknowledgments.',
    stats: [{ k: 'Research orgs', v: '55' }, { k: 'Funders', v: '7' }, { k: 'Top org', v: 'DeepMind · 107' }],
    type: 'orgs',
    note: 'Every org an author belongs to counts, so a co-authored paper lands on several bars. Switch to PRIMARY to count each paper once, under the org that led it.',
  },
  papers: {
    key: 'papers', label: 'PAPERS', chartTitle: 'All safety papers', chartUnit: 'search · filter · sorted by score, then year',
    kicker: 'PAPER EXPLORER', big: { num: 2328 }, bigUnit: 'papers', bigLabel: 'every safety paper, all venues and years',
    brief: 'The full classified corpus. Search titles, filter by venue, year or subdomain — every row links to the paper page, and clicking a row reveals the classifier\'s verbatim reasoning and per-axis scores, so any label can be audited.',
    stats: [{ k: 'Venues', v: 'ICLR · ICML · NeurIPS' }, { k: 'Years', v: '2019–2026' }, { k: 'Subdomains', v: '17' }],
    type: 'papers',
  },
  implementation: {
    key: 'implementation', label: 'IMPLEMENTATION', chartTitle: 'Classification pipeline', chartUnit: 'open source · reproducible',
    kicker: 'HOW IT WORKS', big: { num: 4 }, bigUnit: 'major classes', bigLabel: 'assigned to every accepted paper',
    brief: 'Every accepted paper is classified by DeepSeek V4 Flash — a reasoning LLM — from its title and abstract alone. For each one it returns a JSON verdict: major class, safety subdomain, three score axes, a confidence and its reasoning. Boundary rules disambiguate the hard cases.',
    stats: [{ k: 'Model', v: 'DeepSeek V4 Flash' }, { k: 'Reads', v: 'title + abstract' }, { k: 'Sources', v: 'OpenReview + 3 scrapers' }],
    type: 'method',
  },
};

const VIEW_ORDER = ['overview', 'conferences', 'subdomains', 'orgs', 'papers', 'arxiv', 'implementation'];
