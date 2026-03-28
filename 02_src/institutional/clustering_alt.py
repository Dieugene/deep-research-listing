"""
Альтернативные методы кластеризации и визуализации:
  - DBSCAN (density-based, для выявления noise/outliers)
  - t-SNE (нелинейная визуализация, сетка perplexity)

Выходные файлы:
  figures/dbscan_knn_distance.png
  figures/dbscan_results.png
  figures/tsne_perplexity_grid.png
  figures/tsne_best_annotated.png
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
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.cluster import DBSCAN
from sklearn.manifold import TSNE
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
LOG_DIR = os.path.join(PROJECT_ROOT, "04_logs")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "clustering_alt.log"),
                            encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)
sns.set_style("whitegrid")

# ── Load & prepare ─────────────────────────────────────────────────
df = pd.read_csv(os.path.join(DATA_DIR, "master_factors.csv"), index_col="country")

df["WGI_composite"] = df[["F4_reg_quality_val", "F5_rule_of_law_val",
                           "F6_pol_stability_val"]].mean(axis=1)
df["F7_log_mktcap_gdp"] = np.log1p(df["F7_mktcap_gdp_val"])
df["Fx_log_savings_gdp"] = np.log1p(df["Fx_savings_gdp_val"])

FEATURES = [
    "F2a_disclosure_val", "F2b_director_liability_val",
    "F2c_shareholder_suits_val", "WGI_composite",
    "F7_log_mktcap_gdp", "Fx_log_savings_gdp",
]
LABELS = [
    "F2a Disclosure", "F2b Dir.Liab.", "F2c Shareh.Suits",
    "WGI Composite", "log(MktCap/GDP)", "log(Savings/GDP)",
]

data = df[FEATURES].dropna().copy()
countries = data.index.tolist()
n = len(countries)
log.info(f"Data: {n} jurisdictions, {len(FEATURES)} features")

scaler = StandardScaler()
X = scaler.fit_transform(data.values)

# Ward labels (from main clustering, k=7)
Z = linkage(X, method="ward", metric="euclidean")
ward_labels = fcluster(Z, t=7, criterion="maxclust")

legal_origin = df.loc[countries, "F1_legal_origin"]

# =====================================================================
# 1. DBSCAN
# =====================================================================
log.info("\n" + "=" * 70)
log.info("1. DBSCAN ANALYSIS")
log.info("=" * 70)

# k-NN distance plot for eps selection
min_samples_values = [3, 4, 5, 6, 7]
fig, axes = plt.subplots(1, len(min_samples_values), figsize=(20, 4),
                         sharey=True)

for ax, ms in zip(axes, min_samples_values):
    nn = NearestNeighbors(n_neighbors=ms)
    nn.fit(X)
    distances, _ = nn.kneighbors(X)
    k_dist = np.sort(distances[:, -1])[::-1]
    ax.plot(range(n), k_dist, "o-", markersize=3)
    ax.set_title(f"min_samples={ms}")
    ax.set_xlabel("Points (sorted)")
    if ax == axes[0]:
        ax.set_ylabel("k-NN distance")
    ax.grid(True, alpha=0.3)

fig.suptitle("k-NN distance plots for DBSCAN eps selection", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "dbscan_knn_distance.png"), dpi=150)
plt.close()
log.info("  Saved: dbscan_knn_distance.png")

# Run DBSCAN across a grid of (eps, min_samples)
eps_values = np.arange(1.0, 4.1, 0.5)
results = []

log.info("\n  DBSCAN grid search:")
log.info(f"  {'eps':>5s} | {'min_s':>5s} | {'n_clusters':>10s} | {'n_noise':>7s} | noise points")
log.info("  " + "-" * 80)

for eps in eps_values:
    for ms in [3, 4, 5]:
        db = DBSCAN(eps=eps, min_samples=ms).fit(X)
        labels = db.labels_
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = (labels == -1).sum()
        noise_countries = [countries[i] for i in range(n) if labels[i] == -1]
        results.append({
            "eps": eps, "min_samples": ms,
            "n_clusters": n_clusters, "n_noise": n_noise,
            "labels": labels.copy(), "noise": noise_countries,
        })
        noise_str = ", ".join(noise_countries[:8])
        if len(noise_countries) > 8:
            noise_str += f"... (+{len(noise_countries)-8})"
        log.info(f"  {eps:5.1f} | {ms:5d} | {n_clusters:10d} | {n_noise:7d} | {noise_str}")

# Select a representative DBSCAN result for visualization
# Pick eps/min_samples with 2-5 clusters and moderate noise
good_results = [r for r in results
                if 2 <= r["n_clusters"] <= 6 and 1 <= r["n_noise"] <= 10]
if not good_results:
    good_results = [r for r in results if r["n_clusters"] >= 1]

if good_results:
    best_db = min(good_results, key=lambda r: abs(r["n_clusters"] - 4))
    log.info(f"\n  Selected DBSCAN: eps={best_db['eps']}, min_samples={best_db['min_samples']}")
    log.info(f"    clusters={best_db['n_clusters']}, noise={best_db['n_noise']}")
    log.info(f"    noise points: {best_db['noise']}")

    # Cluster composition
    for cl in sorted(set(best_db["labels"])):
        members = [countries[i] for i in range(n) if best_db["labels"][i] == cl]
        label_name = f"Cluster {cl}" if cl != -1 else "NOISE"
        log.info(f"    {label_name} ({len(members)}): {members}")
else:
    best_db = None
    log.info("\n  No suitable DBSCAN parameterization found.")

# =====================================================================
# 2. t-SNE PERPLEXITY GRID
# =====================================================================
log.info("\n" + "=" * 70)
log.info("2. t-SNE PERPLEXITY GRID")
log.info("=" * 70)

perplexities = [5, 8, 12, 15, 20, 30]
n_seeds = 3  # multiple seeds to check stability

cluster_colors = {1: "#e74c3c", 2: "#3498db", 3: "#2ecc71", 4: "#f39c12",
                  5: "#9b59b6", 6: "#1abc9c", 7: "#e67e22"}

fig, axes = plt.subplots(len(perplexities), n_seeds,
                         figsize=(5 * n_seeds, 4.5 * len(perplexities)))

tsne_embeddings = {}

for row, perp in enumerate(perplexities):
    for col, seed in enumerate(range(42, 42 + n_seeds)):
        ax = axes[row, col]
        tsne = TSNE(n_components=2, perplexity=perp, random_state=seed,
                     max_iter=2000, learning_rate="auto", init="pca")
        X_tsne = tsne.fit_transform(X)
        tsne_embeddings[(perp, seed)] = X_tsne

        for cl in sorted(set(ward_labels)):
            mask = ward_labels == cl
            ax.scatter(X_tsne[mask, 0], X_tsne[mask, 1],
                       c=cluster_colors.get(cl, "gray"), s=40,
                       edgecolors="black", linewidth=0.3,
                       label=f"C{cl}" if col == 0 and row == 0 else "")

        # Label Russia
        ru_idx = countries.index("Russia") if "Russia" in countries else None
        if ru_idx is not None:
            ax.scatter(X_tsne[ru_idx, 0], X_tsne[ru_idx, 1],
                       c="red", s=100, marker="*", zorder=10)
            ax.annotate("Russia", (X_tsne[ru_idx, 0], X_tsne[ru_idx, 1]),
                        fontsize=7, fontweight="bold", color="red",
                        xytext=(5, 5), textcoords="offset points")

        ax.set_title(f"perp={perp}, seed={seed}", fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])

fig.suptitle("t-SNE: perplexity grid x random seeds (colored by Ward k=7)",
             fontsize=14, y=1.01)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "tsne_perplexity_grid.png"),
            dpi=130, bbox_inches="tight")
plt.close()
log.info("  Saved: tsne_perplexity_grid.png")

# Best single t-SNE (perplexity ~10-15 is usually sweet spot for n~40)
best_perp = 12
best_seed = 42
X_best = tsne_embeddings[(best_perp, best_seed)]

fig, ax = plt.subplots(figsize=(14, 10))
for cl in sorted(set(ward_labels)):
    mask = ward_labels == cl
    ax.scatter(X_best[mask, 0], X_best[mask, 1],
               c=cluster_colors.get(cl, "gray"), s=80,
               edgecolors="black", linewidth=0.5, label=f"Cluster {cl}")

for i, country in enumerate(countries):
    weight = "bold" if country == "Russia" else "normal"
    color = "red" if country == "Russia" else "black"
    size = 9 if country == "Russia" else 7
    ax.annotate(country, (X_best[i, 0], X_best[i, 1]),
                fontsize=size, fontweight=weight, color=color,
                alpha=0.85, xytext=(5, 5), textcoords="offset points")

ax.set_title(f"t-SNE projection (perplexity={best_perp}, colored by Ward k=7)",
             fontsize=14)
ax.legend(loc="upper right", fontsize=9)
ax.set_xticks([])
ax.set_yticks([])
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "tsne_best_annotated.png"), dpi=150)
plt.close()
log.info("  Saved: tsne_best_annotated.png")

# =====================================================================
# 3. DBSCAN on t-SNE (bonus: density in 2D embedding)
# =====================================================================
if best_db is not None:
    log.info("\n" + "=" * 70)
    log.info("3. DBSCAN ON t-SNE EMBEDDING")
    log.info("=" * 70)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # Panel 1: Ward clusters on t-SNE
    ax = axes[0]
    for cl in sorted(set(ward_labels)):
        mask = ward_labels == cl
        ax.scatter(X_best[mask, 0], X_best[mask, 1],
                   c=cluster_colors.get(cl, "gray"), s=60,
                   edgecolors="black", linewidth=0.3)
    for i, c in enumerate(countries):
        ax.annotate(c, (X_best[i, 0], X_best[i, 1]), fontsize=5.5, alpha=0.7)
    ax.set_title("Ward k=7", fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])

    # Panel 2: DBSCAN on original 6D
    ax = axes[1]
    db_colors = {-1: "#cccccc", 0: "#e74c3c", 1: "#3498db", 2: "#2ecc71",
                 3: "#f39c12", 4: "#9b59b6", 5: "#1abc9c"}
    for cl in sorted(set(best_db["labels"])):
        mask = best_db["labels"] == cl
        marker = "x" if cl == -1 else "o"
        label = "Noise" if cl == -1 else f"DBSCAN {cl}"
        ax.scatter(X_best[mask, 0], X_best[mask, 1],
                   c=db_colors.get(cl, "gray"), s=60, marker=marker,
                   edgecolors="black" if cl != -1 else "none",
                   linewidth=0.3, label=label)
    for i, c in enumerate(countries):
        ax.annotate(c, (X_best[i, 0], X_best[i, 1]), fontsize=5.5, alpha=0.7)
    ax.set_title(f"DBSCAN (eps={best_db['eps']}, ms={best_db['min_samples']})",
                 fontsize=11)
    ax.legend(fontsize=7, loc="upper right")
    ax.set_xticks([]); ax.set_yticks([])

    # Panel 3: Legal origin on t-SNE
    ax = axes[2]
    lo_colors = {"English": "#e74c3c", "French": "#3498db",
                 "German": "#2ecc71", "Scandinavian": "#f39c12"}
    for lo in sorted(legal_origin.unique()):
        if pd.isna(lo):
            continue
        mask = (legal_origin == lo).values
        ax.scatter(X_best[mask, 0], X_best[mask, 1],
                   c=lo_colors.get(lo, "gray"), s=60,
                   edgecolors="black", linewidth=0.3, label=lo)
    for i, c in enumerate(countries):
        ax.annotate(c, (X_best[i, 0], X_best[i, 1]), fontsize=5.5, alpha=0.7)
    ax.set_title("Legal origin", fontsize=11)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_xticks([]); ax.set_yticks([])

    fig.suptitle("t-SNE (perp=12): comparison of clusterings", fontsize=13)
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "dbscan_results.png"), dpi=150)
    plt.close()
    log.info("  Saved: dbscan_results.png")

log.info("\nDone.")
