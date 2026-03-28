"""
Корреляционный анализ количественных факторов.

Выходные файлы:
  figures/correlation_matrix.png
  figures/distributions_boxplots.png
  figures/correlation_matrix_spearman.png
  figures/wgi_internal_corr.png
  figures/f2_internal_corr.png
"""
import logging
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
LOG_DIR = os.path.join(PROJECT_ROOT, "04_logs")

os.makedirs(FIGURES_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(LOG_DIR, "correlation_analysis.log"), encoding="utf-8",
        ),
    ],
)
log = logging.getLogger(__name__)

plt.rcParams["figure.figsize"] = (14, 10)
plt.rcParams["font.size"] = 11
sns.set_style("whitegrid")

# ── Load data ────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(DATA_DIR, "master_factors.csv"), index_col="country")

# Core quantitative factors for clustering (excluding ASDI per decision)
CORE_FACTORS = [
    "F2a_disclosure_val",
    "F2b_director_liability_val",
    "F2c_shareholder_suits_val",
    "F4_reg_quality_val",
    "F5_rule_of_law_val",
    "F6_pol_stability_val",
    "F7_mktcap_gdp_val",
    "Fx_savings_gdp_val",
]

LABELS = {
    "F2a_disclosure_val": "F2a Disclosure",
    "F2b_director_liability_val": "F2b Director Liab.",
    "F2c_shareholder_suits_val": "F2c Shareholder Suits",
    "F4_reg_quality_val": "F4 Regulatory Quality",
    "F5_rule_of_law_val": "F5 Rule of Law",
    "F6_pol_stability_val": "F6 Political Stability",
    "F7_mktcap_gdp_val": "F7 MktCap/GDP",
    "Fx_savings_gdp_val": "Fx Savings/GDP",
}

data = df[CORE_FACTORS].copy()
data.columns = [LABELS.get(c, c) for c in data.columns]

# =====================================================================
# 1. Distribution analysis
# =====================================================================
log.info("=" * 70)
log.info("1. DISTRIBUTION ANALYSIS")
log.info("=" * 70)

for col in data.columns:
    vals = data[col].dropna()
    skew = vals.skew()
    kurt = vals.kurtosis()
    q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
    iqr = q3 - q1
    outliers_hi = vals[vals > q3 + 1.5 * iqr]
    outliers_lo = vals[vals < q1 - 1.5 * iqr]
    n_outliers = len(outliers_hi) + len(outliers_lo)

    log.info(f"  {col:25s} | range: [{vals.min():.1f}, {vals.max():.1f}] | "
             f"skew={skew:+.2f} | kurtosis={kurt:+.2f} | outliers: {n_outliers}")
    if not outliers_hi.empty:
        for idx in outliers_hi.index:
            log.info(f"    HIGH outlier: {idx} = {outliers_hi[idx]:.1f}")
    if not outliers_lo.empty:
        for idx in outliers_lo.index:
            log.info(f"    LOW outlier: {idx} = {outliers_lo[idx]:.1f}")

# Boxplots
fig, axes = plt.subplots(2, 4, figsize=(18, 9))
axes = axes.flatten()
for i, col in enumerate(data.columns):
    ax = axes[i]
    vals = data[col].dropna()
    bp = ax.boxplot(vals, vert=True, patch_artist=True,
                    boxprops=dict(facecolor="steelblue", alpha=0.7))
    ru_val = data.loc["Russia", col] if "Russia" in data.index and pd.notna(data.loc["Russia", col]) else None
    if ru_val is not None:
        ax.axhline(ru_val, color="red", linewidth=1.5, linestyle="--")
        ax.text(1.15, ru_val, "RU", color="red", fontsize=9, va="center")
    ax.set_title(col, fontsize=9)
    ax.set_xticklabels([])

plt.suptitle("Factor distributions (red line = Russia)", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "distributions_boxplots.png"), dpi=150)
log.info(f"  Saved: distributions_boxplots.png")

# =====================================================================
# 2. Pearson correlation
# =====================================================================
log.info("")
log.info("=" * 70)
log.info("2. PEARSON CORRELATION")
log.info("=" * 70)

corr_pearson = data.corr(method="pearson")
log.info("\n" + corr_pearson.round(3).to_string())

fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr_pearson, dtype=bool), k=1)
sns.heatmap(corr_pearson, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
            center=0, vmin=-1, vmax=1, square=True, ax=ax,
            linewidths=0.5, cbar_kws={"shrink": 0.8})
ax.set_title("Pearson correlation matrix", fontsize=14)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "correlation_matrix_pearson.png"), dpi=150)
log.info(f"  Saved: correlation_matrix_pearson.png")

# =====================================================================
# 3. Spearman rank correlation (robust to outliers + nonlinearity)
# =====================================================================
log.info("")
log.info("=" * 70)
log.info("3. SPEARMAN RANK CORRELATION")
log.info("=" * 70)

corr_spearman = data.corr(method="spearman")
log.info("\n" + corr_spearman.round(3).to_string())

fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr_spearman, dtype=bool), k=1)
sns.heatmap(corr_spearman, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
            center=0, vmin=-1, vmax=1, square=True, ax=ax,
            linewidths=0.5, cbar_kws={"shrink": 0.8})
ax.set_title("Spearman rank correlation matrix", fontsize=14)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "correlation_matrix_spearman.png"), dpi=150)
log.info(f"  Saved: correlation_matrix_spearman.png")

# =====================================================================
# 4. Pearson vs Spearman divergence (signals nonlinearity / outliers)
# =====================================================================
log.info("")
log.info("=" * 70)
log.info("4. PEARSON vs SPEARMAN DIVERGENCE")
log.info("=" * 70)

diff = (corr_pearson - corr_spearman).abs()
pairs_sorted = []
for i in range(len(diff.columns)):
    for j in range(i + 1, len(diff.columns)):
        c1, c2 = diff.columns[i], diff.columns[j]
        d = diff.iloc[i, j]
        p = corr_pearson.iloc[i, j]
        s = corr_spearman.iloc[i, j]
        pairs_sorted.append((c1, c2, p, s, d))

pairs_sorted.sort(key=lambda x: x[4], reverse=True)
log.info("  Pairs with largest Pearson-Spearman divergence (outlier/nonlinearity signal):")
for c1, c2, p, s, d in pairs_sorted[:10]:
    flag = " <<<" if d > 0.10 else ""
    log.info(f"    {c1:25s} x {c2:25s} | P={p:+.3f} S={s:+.3f} | diff={d:.3f}{flag}")

# =====================================================================
# 5. WGI internal correlation (F4, F5, F6)
# =====================================================================
log.info("")
log.info("=" * 70)
log.info("5. WGI INTERNAL CORRELATION (multicollinearity check)")
log.info("=" * 70)

wgi_cols = ["F4 Regulatory Quality", "F5 Rule of Law", "F6 Political Stability"]
wgi_corr = data[wgi_cols].corr()
log.info("\n" + wgi_corr.round(3).to_string())

eigenvalues = np.linalg.eigvals(wgi_corr.values)
log.info(f"\n  Eigenvalues: {np.sort(eigenvalues)[::-1].round(4)}")
log.info(f"  Variance explained by PC1: {max(eigenvalues)/sum(eigenvalues)*100:.1f}%")
log.info(f"  Condition number: {max(eigenvalues)/min(eigenvalues):.1f}")

# =====================================================================
# 6. F2 internal correlation
# =====================================================================
log.info("")
log.info("=" * 70)
log.info("6. F2 INTERNAL CORRELATION")
log.info("=" * 70)

f2_cols = ["F2a Disclosure", "F2b Director Liab.", "F2c Shareholder Suits"]
f2_corr = data[f2_cols].corr()
log.info("\n" + f2_corr.round(3).to_string())

eigenvalues_f2 = np.linalg.eigvals(f2_corr.values)
log.info(f"\n  Eigenvalues: {np.sort(eigenvalues_f2)[::-1].round(4)}")
log.info(f"  Variance explained by PC1: {max(eigenvalues_f2)/sum(eigenvalues_f2)*100:.1f}%")

# =====================================================================
# 7. Key findings summary
# =====================================================================
log.info("")
log.info("=" * 70)
log.info("7. KEY FINDINGS")
log.info("=" * 70)

# Highly correlated pairs (|r| > 0.7)
log.info("\n  Highly correlated pairs (Spearman |r| > 0.7):")
for c1, c2, p, s, d in pairs_sorted:
    if abs(s) > 0.7:
        log.info(f"    {c1} x {c2}: Spearman r={s:+.3f}")

# Weakly correlated with others (potential unique info)
log.info("\n  Mean absolute Spearman correlation per factor:")
for col in data.columns:
    mean_r = corr_spearman[col].drop(col).abs().mean()
    log.info(f"    {col:25s}: mean |r| = {mean_r:.3f}")

plt.close("all")
log.info("\nDone.")
