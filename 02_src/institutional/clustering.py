"""
Кластеризация юрисдикций по институциональным факторам.

Этапы:
  1. Подготовка признаков (WGI composite, log F7, стандартизация)
  2. Gower distance + hierarchical clustering (Ward, complete, average)
  3. Оптимальное число кластеров (silhouette, dendrogram)
  4. Профилирование кластеров
  5. Позиция России

Выходные файлы:
  figures/dendrogram_ward.png
  figures/silhouette_scores.png
  figures/pca_clusters.png
  figures/cluster_profiles_heatmap.png
  figures/russia_position.png
  03_data/institutional/cluster_assignments.csv
"""
import logging
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import squareform
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, silhouette_samples

PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
LOG_DIR = os.path.join(PROJECT_ROOT, "04_logs")

os.makedirs(FIGURES_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(LOG_DIR, "clustering.log"), encoding="utf-8",
        ),
    ],
)
log = logging.getLogger(__name__)

sns.set_style("whitegrid")

# =====================================================================
# 1. FEATURE ENGINEERING
# =====================================================================
log.info("=" * 70)
log.info("1. FEATURE ENGINEERING")
log.info("=" * 70)

df = pd.read_csv(os.path.join(DATA_DIR, "master_factors.csv"), index_col="country")

# WGI composite (mean of F4, F5, F6)
df["WGI_composite"] = df[["F4_reg_quality_val", "F5_rule_of_law_val",
                           "F6_pol_stability_val"]].mean(axis=1)
log.info(f"WGI composite: mean of F4+F5+F6, range [{df['WGI_composite'].min():.2f}, "
         f"{df['WGI_composite'].max():.2f}]")

# Log transform for F7 (market cap / GDP)
df["F7_log_mktcap_gdp"] = np.log1p(df["F7_mktcap_gdp_val"])

# Log transform for savings/GDP (moderate skew)
df["Fx_log_savings_gdp"] = np.log1p(df["Fx_savings_gdp_val"])

# Feature set for clustering
FEATURES = [
    "F2a_disclosure_val",
    "F2b_director_liability_val",
    "F2c_shareholder_suits_val",
    "WGI_composite",
    "F7_log_mktcap_gdp",
    "Fx_log_savings_gdp",
]

FEATURE_LABELS = [
    "F2a Disclosure",
    "F2b Director Liab.",
    "F2c Shareholder Suits",
    "WGI Composite",
    "F7 log(MktCap/GDP)",
    "Fx log(Savings/GDP)",
]

# Drop rows with any NaN in feature set
data_full = df[FEATURES].copy()
n_before = len(data_full)
data_clean = data_full.dropna()
n_after = len(data_clean)
dropped = set(data_full.index) - set(data_clean.index)

log.info(f"\nFeature matrix: {n_before} -> {n_after} jurisdictions "
         f"(dropped {n_before - n_after}: {sorted(dropped)})")

# Legal origin for coloring
legal_origin = df.loc[data_clean.index, "F1_legal_origin"]
market_group = df.loc[data_clean.index, "market_group"]

# Standardize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(data_clean.values)
X_df = pd.DataFrame(X_scaled, index=data_clean.index, columns=FEATURE_LABELS)

log.info(f"\nStandardized feature matrix: {X_df.shape}")
log.info(f"Means (should be ~0): {X_scaled.mean(axis=0).round(3)}")
log.info(f"Stds  (should be ~1): {X_scaled.std(axis=0).round(3)}")

# =====================================================================
# 2. HIERARCHICAL CLUSTERING
# =====================================================================
log.info("\n" + "=" * 70)
log.info("2. HIERARCHICAL CLUSTERING")
log.info("=" * 70)

methods = ["ward", "complete", "average"]
linkage_results = {}

for method in methods:
    Z = linkage(X_scaled, method=method, metric="euclidean")
    linkage_results[method] = Z
    log.info(f"  Linkage method: {method} -- computed")

# Dendrogram (Ward)
fig, ax = plt.subplots(figsize=(18, 10))
Z_ward = linkage_results["ward"]
dend = dendrogram(Z_ward, labels=data_clean.index.tolist(), leaf_rotation=90,
                  leaf_font_size=8, ax=ax, color_threshold=0)
ax.set_title("Hierarchical clustering dendrogram (Ward linkage)", fontsize=14)
ax.set_ylabel("Distance")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "dendrogram_ward.png"), dpi=150)
plt.close()
log.info("  Saved: dendrogram_ward.png")

# =====================================================================
# 3. OPTIMAL NUMBER OF CLUSTERS
# =====================================================================
log.info("\n" + "=" * 70)
log.info("3. OPTIMAL NUMBER OF CLUSTERS")
log.info("=" * 70)

sil_scores = {}
for k in range(2, 11):
    labels = fcluster(Z_ward, t=k, criterion="maxclust")
    sil = silhouette_score(X_scaled, labels, metric="euclidean")
    sil_scores[k] = sil
    log.info(f"  k={k}: silhouette={sil:.3f}")

best_k = max(sil_scores, key=sil_scores.get)
log.info(f"\n  Best k by silhouette: {best_k} (score={sil_scores[best_k]:.3f})")

# Also check k-1 and k+1 -- if close, prefer fewer clusters (parsimony)
for k in [best_k - 1, best_k, best_k + 1]:
    if k in sil_scores:
        log.info(f"  k={k}: {sil_scores[k]:.3f}")

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(list(sil_scores.keys()), list(sil_scores.values()), "o-", color="steelblue")
ax.axvline(best_k, color="red", linestyle="--", alpha=0.7, label=f"best k={best_k}")
ax.set_xlabel("Number of clusters (k)")
ax.set_ylabel("Silhouette score")
ax.set_title("Silhouette score vs number of clusters (Ward)")
ax.legend()
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "silhouette_scores.png"), dpi=150)
plt.close()
log.info("  Saved: silhouette_scores.png")

# =====================================================================
# 4. ASSIGN CLUSTERS (use best_k, and also show k=4 for comparison)
# =====================================================================
log.info("\n" + "=" * 70)
log.info(f"4. CLUSTER ASSIGNMENTS (k={best_k})")
log.info("=" * 70)

labels_best = fcluster(Z_ward, t=best_k, criterion="maxclust")
data_clean["cluster"] = labels_best

# Also compute for a few alternative k values
for alt_k in [3, 4, 5, 6]:
    if alt_k != best_k:
        alt_labels = fcluster(Z_ward, t=alt_k, criterion="maxclust")
        data_clean[f"cluster_k{alt_k}"] = alt_labels

log.info(f"\nCluster sizes (k={best_k}):")
for cl in sorted(data_clean["cluster"].unique()):
    members = data_clean[data_clean["cluster"] == cl].index.tolist()
    log.info(f"  Cluster {cl} ({len(members)}): {members}")

# =====================================================================
# 5. CLUSTER PROFILES
# =====================================================================
log.info("\n" + "=" * 70)
log.info("5. CLUSTER PROFILES")
log.info("=" * 70)

profiles = data_clean.groupby("cluster")[FEATURE_LABELS if len(FEATURE_LABELS) == len(FEATURES) else FEATURES].mean() if False else None

# Use X_df (standardized) for profiles
X_df["cluster"] = labels_best
profiles_std = X_df.groupby("cluster")[FEATURE_LABELS].mean()
log.info("\nMean standardized values per cluster:")
log.info("\n" + profiles_std.round(2).to_string())

# Raw profiles
for col, label in zip(FEATURES, FEATURE_LABELS):
    data_clean[label] = data_clean[col]
profiles_raw = data_clean.groupby("cluster")[FEATURE_LABELS].mean()
log.info("\nMean raw values per cluster:")
log.info("\n" + profiles_raw.round(2).to_string())

# Legal origin composition
log.info("\nLegal origin composition per cluster:")
data_clean["legal_origin"] = legal_origin
data_clean["market_group"] = market_group
for cl in sorted(data_clean["cluster"].unique()):
    subset = data_clean[data_clean["cluster"] == cl]
    lo_counts = subset["legal_origin"].value_counts()
    mg_counts = subset["market_group"].value_counts()
    log.info(f"  Cluster {cl}: {dict(lo_counts)} | {dict(mg_counts)}")

# Heatmap of standardized profiles
fig, ax = plt.subplots(figsize=(10, 5))
sns.heatmap(profiles_std, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            linewidths=0.5, ax=ax, cbar_kws={"label": "Std. deviations from mean"})
ax.set_title(f"Cluster profiles (k={best_k}, standardized)", fontsize=14)
ax.set_ylabel("Cluster")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "cluster_profiles_heatmap.png"), dpi=150)
plt.close()
log.info("  Saved: cluster_profiles_heatmap.png")

# =====================================================================
# 6. PCA PROJECTION
# =====================================================================
log.info("\n" + "=" * 70)
log.info("6. PCA PROJECTION")
log.info("=" * 70)

pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)
var_explained = pca.explained_variance_ratio_
log.info(f"  PC1: {var_explained[0]*100:.1f}% variance")
log.info(f"  PC2: {var_explained[1]*100:.1f}% variance")
log.info(f"  Total: {sum(var_explained)*100:.1f}%")

log.info(f"\n  PCA loadings:")
for i, label in enumerate(FEATURE_LABELS):
    log.info(f"    {label:25s} | PC1={pca.components_[0][i]:+.3f} | PC2={pca.components_[1][i]:+.3f}")

# Color by cluster
cluster_colors = {1: "#e74c3c", 2: "#3498db", 3: "#2ecc71", 4: "#f39c12",
                  5: "#9b59b6", 6: "#1abc9c", 7: "#e67e22", 8: "#34495e"}

fig, ax = plt.subplots(figsize=(14, 10))
for cl in sorted(data_clean["cluster"].unique()):
    mask = data_clean["cluster"].values == cl
    ax.scatter(X_pca[mask, 0], X_pca[mask, 1], c=cluster_colors.get(cl, "gray"),
               label=f"Cluster {cl}", s=80, edgecolors="black", linewidth=0.5)

for i, country in enumerate(data_clean.index):
    weight = "bold" if country == "Russia" else "normal"
    color = "red" if country == "Russia" else "black"
    ax.annotate(country, (X_pca[i, 0], X_pca[i, 1]), fontsize=7,
                fontweight=weight, color=color, alpha=0.85,
                xytext=(5, 5), textcoords="offset points")

ax.set_xlabel(f"PC1 ({var_explained[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({var_explained[1]*100:.1f}%)")
ax.set_title(f"PCA projection with cluster assignments (k={best_k})", fontsize=14)
ax.legend(loc="upper right")
ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
ax.axvline(0, color="gray", linewidth=0.5, linestyle="--")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "pca_clusters.png"), dpi=150)
plt.close()
log.info("  Saved: pca_clusters.png")

# =====================================================================
# 7. RUSSIA POSITION
# =====================================================================
log.info("\n" + "=" * 70)
log.info("7. RUSSIA POSITION")
log.info("=" * 70)

if "Russia" in data_clean.index:
    ru_cluster = data_clean.loc["Russia", "cluster"]
    log.info(f"  Russia cluster: {ru_cluster}")

    # Nearest neighbors (Euclidean in standardized space)
    ru_idx = list(data_clean.index).index("Russia")
    distances = np.sqrt(((X_scaled - X_scaled[ru_idx]) ** 2).sum(axis=1))
    dist_series = pd.Series(distances, index=data_clean.index).sort_values()
    log.info(f"\n  Nearest jurisdictions to Russia (Euclidean, standardized):")
    for c in dist_series.index[1:11]:
        d = dist_series[c]
        cl = data_clean.loc[c, "cluster"]
        lo = data_clean.loc[c, "legal_origin"]
        log.info(f"    {c:25s} | dist={d:.3f} | cluster={cl} | {lo}")

    # Russia vs cluster mean
    ru_vals = X_df.loc["Russia", FEATURE_LABELS]
    cl_mean = profiles_std.loc[ru_cluster]
    log.info(f"\n  Russia vs Cluster {ru_cluster} mean (standardized):")
    for label in FEATURE_LABELS:
        rv = ru_vals[label]
        cm = cl_mean[label]
        delta = rv - cm
        log.info(f"    {label:25s} | Russia={rv:+.2f} | Cluster mean={cm:+.2f} | delta={delta:+.2f}")
else:
    log.warning("  Russia not in clustered data!")

# =====================================================================
# 8. SAVE
# =====================================================================
out_cols = ["cluster", "legal_origin", "market_group"] + FEATURE_LABELS
if "cluster_k3" in data_clean.columns:
    out_cols.append("cluster_k3")
if "cluster_k4" in data_clean.columns:
    out_cols.append("cluster_k4")
if "cluster_k5" in data_clean.columns:
    out_cols.append("cluster_k5")
if "cluster_k6" in data_clean.columns:
    out_cols.append("cluster_k6")

existing_out_cols = [c for c in out_cols if c in data_clean.columns]
out_path = os.path.join(DATA_DIR, "cluster_assignments.csv")
data_clean[existing_out_cols].to_csv(out_path, encoding="utf-8")
log.info(f"\nSaved: {out_path}")
log.info("Done.")
