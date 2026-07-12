import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv('safety_results_v2.csv')

class_labels = {
    1: 'Ethics &\nFairness',
    2: 'Truthfulness &\nReliability',
    3: 'General\nCapabilities',
    4: 'AI Safety'
}

subarea_labels = {
    'A': 'Interpretability &\nUnderstanding',
    'B': 'Scalable Oversight &\nValue Learning',
    'C': 'Agent Foundations &\nAlignment Theory',
    'D': 'Threat Modeling &\nEvaluations',
    'E': 'Capability Control &\nUnlearning',
    'F': 'Robustness, Defense &\nSystemic Control',
}

subdomain_to_subarea = {
    'Interpretability': 'A',
    'Monitoring': 'A',
    'Multi-Agent Safety': 'B',
    'Scalable Oversight': 'B',
    'Agent Foundations': 'C',
    'Scheming and Deception': 'D',
    'Dangerous Capability Evals': 'D',
    'Biorisk': 'D',
    'Safeguards': 'D',
    'Model Organisms': 'D',
    'Control': 'D',
    'Alignment Training': 'E',
    'Red-Teaming': 'F',
    'Adversarial Robustness': 'F',
}

# --- Data prep ---
major_counts = df['step1_class'].value_counts().sort_index()
major_names = [class_labels[i] for i in major_counts.index]

safety_df = df[df['is_safety'] == True].copy()
safety_df['subarea'] = safety_df['subdomain'].map(subdomain_to_subarea)
subarea_counts = safety_df['subarea'].value_counts().reindex(['A', 'B', 'C', 'D', 'E', 'F'], fill_value=0)
subarea_names = [subarea_labels[k] for k in subarea_counts.index]

subdomain_counts = safety_df['subdomain'].value_counts()

colors_major = ['#4e79a7', '#f28e2b', '#76b7b2', '#e15759']
colors_subarea = ['#59a14f', '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac']
colors_detail = plt.cm.Set3(np.linspace(0, 1, len(subdomain_counts)))


def style_ax(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


def plot_major(ax):
    bars = ax.bar(major_names, major_counts.values, color=colors_major, edgecolor='white', linewidth=0.8)
    ax.set_title('Major Classification', fontsize=14, fontweight='bold', pad=12)
    ax.set_ylabel('Number of Papers', fontsize=11)
    for bar, val in zip(bars, major_counts.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8, str(val),
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    ax.set_ylim(0, max(major_counts.values) * 1.15)
    ax.tick_params(axis='x', labelsize=11)
    style_ax(ax)


def plot_subareas(ax):
    bars = ax.barh(subarea_names[::-1], subarea_counts.values[::-1],
                   color=colors_subarea[::-1], edgecolor='white', linewidth=0.8)
    ax.set_title('Safety Subareas', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Number of Papers', fontsize=11)
    for bar, val in zip(bars, subarea_counts.values[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, str(val),
                ha='left', va='center', fontsize=11, fontweight='bold')
    ax.set_xlim(0, max(subarea_counts.values) * 1.25)
    ax.tick_params(axis='y', labelsize=10)
    style_ax(ax)


def plot_detailed(ax):
    bars = ax.barh(subdomain_counts.index[::-1], subdomain_counts.values[::-1],
                   color=colors_detail[::-1], edgecolor='white', linewidth=0.8)
    ax.set_title('Detailed Safety Classes', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Number of Papers', fontsize=11)
    for bar, val in zip(bars, subdomain_counts.values[::-1]):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, str(val),
                ha='left', va='center', fontsize=11, fontweight='bold')
    ax.set_xlim(0, max(subdomain_counts.values) * 1.25)
    ax.tick_params(axis='y', labelsize=10)
    style_ax(ax)


# --- Individual plots ---
fig1, ax1 = plt.subplots(figsize=(7, 5))
plot_major(ax1)
fig1.suptitle('ICLR 2026 — Major Classification', fontsize=15, fontweight='bold', y=0.98)
fig1.tight_layout(rect=[0, 0, 1, 0.95])
fig1.savefig('plot_major_classes.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig1)
print("Saved: plot_major_classes.png")

fig2, ax2 = plt.subplots(figsize=(8, 5))
plot_subareas(ax2)
fig2.suptitle('ICLR 2026 — Safety Subareas', fontsize=15, fontweight='bold', y=0.98)
fig2.tight_layout(rect=[0, 0, 1, 0.95])
fig2.savefig('plot_safety_subareas.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig2)
print("Saved: plot_safety_subareas.png")

fig3, ax3 = plt.subplots(figsize=(8, 5))
plot_detailed(ax3)
fig3.suptitle('ICLR 2026 — Detailed Safety Classes', fontsize=15, fontweight='bold', y=0.98)
fig3.tight_layout(rect=[0, 0, 1, 0.95])
fig3.savefig('plot_detailed_classes.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig3)
print("Saved: plot_detailed_classes.png")

# --- Combined side-by-side ---
fig, axes = plt.subplots(1, 3, figsize=(22, 7),
                          gridspec_kw={'width_ratios': [1, 1.2, 1.2]})
plot_major(axes[0])
plot_subareas(axes[1])
plot_detailed(axes[2])
fig.suptitle('ICLR 2026 AI Safety Paper Classification', fontsize=17, fontweight='bold', y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig('classification_overview.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close(fig)
print("Saved: classification_overview.png")

# --- CSVs ---
def make_csv(mask, filename):
    subset = df[mask][['title']].copy()
    subset = subset.rename(columns={'title': 'Paper Title'})
    subset.to_csv(filename, index=False)
    print(f"Saved: {filename} ({len(subset)} papers)")

# Safety papers (with subarea + detailed class)
safety_out = safety_df[['title', 'subdomain']].copy()
safety_out['subarea'] = safety_df['subdomain'].map(subdomain_to_subarea).map(
    lambda k: subarea_labels.get(k, '').replace('\n', ' '))
safety_out = safety_out.rename(columns={
    'title': 'Paper Title',
    'subarea': 'Subarea',
    'subdomain': 'Detailed Class'
})
safety_out = safety_out[['Paper Title', 'Subarea', 'Detailed Class']]
safety_out.to_csv('safety_papers_only.csv', index=False)
print(f"Saved: safety_papers_only.csv ({len(safety_out)} papers)")

# Ethics & Fairness
make_csv(df['step1_class'] == 1, 'ethics_fairness_papers.csv')

# Truthfulness & Reliability
make_csv(df['step1_class'] == 2, 'truthfulness_reliability_papers.csv')
