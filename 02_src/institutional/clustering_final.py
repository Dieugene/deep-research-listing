"""
Финальная кластеризация: feature-based на годовых траекториях WGI (2009-2024).

Ключевое отличие: Россия представлена двумя сущностями:
  Russia_1 (2009-2021) — до структурного разрыва
  Russia_2 (2022-2024) — после структурного разрыва

Итого 49 объектов: 47 стран + Russia_1 + Russia_2.

Подход: из каждой траектории извлекаются числовые признаки,
затем — иерархическая кластеризация (Ward) с подбором k по silhouette.

Выход:
  - figures/final_*.png
  - final_cluster_assignments.csv
  - final_features.csv
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# ── Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
FIG_DIR = os.path.join(DATA_DIR, "figures")
LOG_DIR = os.path.join(PROJECT_ROOT, "04_logs")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "clustering_final.log"),
                            encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

REGISTRY_PATH = os.path.join(PROJECT_ROOT, "03_data", "jurisdictions_registry.json")
with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    JURISDICTIONS = {j["name_en"]: j for j in json.load(f)}

NAME_MAP = {
    "Korea, Rep.": "South Korea",
    "Hong Kong SAR, China": "Hong Kong",
    "Hong Kong, China": "Hong Kong",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
    "Czech Republic": "Czech Republic",
    "Czechia": "Czech Republic",
    "Russian Federation": "Russia",
    "Egypt, Arab Rep.": "Egypt",
    "Taiwan, China": "Taiwan",
}

def norm(name):
    if pd.isna(name):
        return None
    s = str(name).strip().rstrip("*")
    return NAME_MAP.get(s, s)


# =====================================================================
# 1. BUILD ANNUAL WGI PANEL + SPLIT RUSSIA
# =====================================================================
def build_panel_with_split():
    log.info("=" * 70)
    log.info("STEP 1: Building annual WGI panel with Russia split")
    log.info("=" * 70)

    wgi_path = os.path.join(DATA_DIR,
        "F4-6 P_Data_Extract_From_Worldwide_Governance_Indicators_detailed.xlsx")
    wgi = pd.read_excel(wgi_path, sheet_name="Data")
    wgi = wgi[wgi["Country Code"].notna()].copy()
    wgi["country"] = wgi["Country Name"].apply(norm)

    years = list(range(2009, 2025))
    yr_cols = [f"{y} [YR{y}]" for y in years]

    est_codes = {
        "GOV_WGI_RQ.EST": "F4_reg_quality",
        "GOV_WGI_RL.EST": "F5_rule_of_law",
        "GOV_WGI_PV.EST": "F6_pol_stability",
    }

    panels = {}
    for code, factor in est_codes.items():
        subset = wgi[wgi["Series Code"] == code].copy()
        subset = subset[subset["country"].isin(JURISDICTIONS)].copy()
        subset = subset.drop_duplicates(subset="country", keep="first")
        subset = subset.set_index("country")

        factor_panel = pd.DataFrame(index=sorted(JURISDICTIONS.keys()),
                                    columns=years, dtype=float)
        for yc, yr in zip(yr_cols, years):
            for c in factor_panel.index:
                if c in subset.index:
                    raw = subset.loc[c, yc]
                    if str(raw).strip() not in ("..", "") and pd.notna(raw):
                        try:
                            factor_panel.loc[c, yr] = float(raw)
                        except (ValueError, TypeError):
                            pass
        panels[factor] = factor_panel

    # WGI composite = mean(F4, F5, F6)
    composite = pd.DataFrame(index=sorted(JURISDICTIONS.keys()),
                             columns=years, dtype=float)
    for c in composite.index:
        for yr in years:
            vals = [panels[f].loc[c, yr] for f in est_codes.values()
                    if pd.notna(panels[f].loc[c, yr])]
            if len(vals) == 3:
                composite.loc[c, yr] = np.mean(vals)

    complete = composite.dropna()
    log.info(f"  Complete series: {len(complete)}/48")

    # Split Russia
    split_year = 2022
    pre_years = [y for y in years if y < split_year]
    post_years = [y for y in years if y >= split_year]

    russia_full = complete.loc["Russia"]

    # Build entities DataFrame
    entities = complete.drop("Russia").copy()
    entities.loc["Russia_1"] = np.nan
    entities.loc["Russia_2"] = np.nan

    for yr in pre_years:
        entities.loc["Russia_1", yr] = russia_full[yr]
    for yr in post_years:
        entities.loc["Russia_2", yr] = russia_full[yr]

    log.info(f"  Entities: {len(entities)} (47 countries + Russia_1 + Russia_2)")
    log.info(f"  Russia_1: {pre_years[0]}-{pre_years[-1]} ({len(pre_years)} points)")
    log.info(f"  Russia_2: {post_years[0]}-{post_years[-1]} ({len(post_years)} points)")

    return entities, panels, complete


# =====================================================================
# 2. EXTRACT FEATURES
# =====================================================================
def extract_features(entities):
    log.info("")
    log.info("STEP 2: Extracting trajectory features")

    years = [y for y in entities.columns if isinstance(y, int)]
    feature_names = ["mean", "std", "start", "end", "range", "slope",
                     "residual_std", "mean_abs_delta", "max_abs_delta",
                     "max_drop", "max_rise", "frac_positive"]

    features = pd.DataFrame(index=entities.index, columns=feature_names, dtype=float)

    for entity in entities.index:
        row = entities.loc[entity]
        valid_years = [y for y in years if pd.notna(row[y])]
        ts = np.array([row[y] for y in valid_years], dtype=float)
        n = len(ts)

        if n < 2:
            continue

        xs = np.arange(n, dtype=float)
        features.loc[entity, "mean"] = ts.mean()
        features.loc[entity, "std"] = ts.std()
        features.loc[entity, "start"] = ts[0]
        features.loc[entity, "end"] = ts[-1]
        features.loc[entity, "range"] = ts.max() - ts.min()

        slope, intercept = np.polyfit(xs, ts, 1)
        features.loc[entity, "slope"] = slope
        residuals = ts - (slope * xs + intercept)
        features.loc[entity, "residual_std"] = residuals.std()

        deltas = np.diff(ts)
        features.loc[entity, "mean_abs_delta"] = np.abs(deltas).mean()
        features.loc[entity, "max_abs_delta"] = np.abs(deltas).max()
        features.loc[entity, "max_drop"] = deltas.min()
        features.loc[entity, "max_rise"] = deltas.max()
        features.loc[entity, "frac_positive"] = (deltas > 0).mean()

    features = features.dropna()
    log.info(f"  Features extracted: {features.shape[1]} for {features.shape[0]} entities")

    for col in features.columns:
        log.info(f"    {col:20s} | mean={features[col].mean():.4f} "
                 f"std={features[col].std():.4f} "
                 f"min={features[col].min():.4f} max={features[col].max():.4f}")

    # Log Russia_1 and Russia_2 features
    for r_name in ["Russia_1", "Russia_2"]:
        if r_name in features.index:
            log.info(f"\n  {r_name} features:")
            for col in features.columns:
                val = features.loc[r_name, col]
                log.info(f"    {col:20s} = {val:.4f}")

    return features


# =====================================================================
# 3. CLUSTERING
# =====================================================================
def cluster_analysis(features, master):
    log.info("")
    log.info("STEP 3: Hierarchical clustering (Ward)")

    scaler = StandardScaler()
    X = scaler.fit_transform(features.values.astype(float))
    entities = features.index.tolist()
    n = len(entities)

    Z = linkage(X, method="ward")

    # Silhouette for k=2..15
    sil_scores = {}
    for k in range(2, min(16, n)):
        labels = fcluster(Z, k, criterion="maxclust")
        if len(set(labels)) < 2:
            continue
        sil = silhouette_score(X, labels, metric="euclidean")
        sil_scores[k] = sil
        log.info(f"    k={k}: silhouette={sil:.3f}")

    best_k = max(sil_scores, key=sil_scores.get)
    best_labels = fcluster(Z, best_k, criterion="maxclust")
    best_sil = sil_scores[best_k]
    log.info(f"  Best k={best_k} (silhouette={best_sil:.3f})")

    # Also check k in 5-8 range for more granular interpretation
    granular_candidates = {k: s for k, s in sil_scores.items() if 5 <= k <= 9}
    if granular_candidates:
        gran_k = max(granular_candidates, key=granular_candidates.get)
        gran_labels = fcluster(Z, gran_k, criterion="maxclust")
        gran_sil = granular_candidates[gran_k]
        log.info(f"  Granular k={gran_k} (silhouette={gran_sil:.3f})")
    else:
        gran_k = best_k
        gran_labels = best_labels
        gran_sil = best_sil

    # Use the granular k for detailed analysis (more informative)
    use_k = gran_k
    use_labels = gran_labels
    use_sil = gran_sil
    log.info(f"\n  Using k={use_k} for detailed analysis (silhouette={use_sil:.3f})")

    # === VISUALIZATIONS ===

    # Legal origins for coloring
    legal_origin = {}
    if "F1_legal_origin" in master.columns:
        for c in master.index:
            if pd.notna(master.loc[c, "F1_legal_origin"]):
                legal_origin[c] = master.loc[c, "F1_legal_origin"]

    origin_colors = {
        "English": "#2196F3", "French": "#FF9800", "German": "#4CAF50",
        "Scandinavian": "#9C27B0", "Socialist": "#F44336",
    }

    # ── Fig 1: Dendrogram ──────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(22, 8))
    dn = dendrogram(Z, labels=entities, ax=ax, leaf_rotation=90, leaf_font_size=7,
                    color_threshold=0)
    # Color labels by legal origin
    xlbls = ax.get_xticklabels()
    for lbl in xlbls:
        name = lbl.get_text()
        base = name.replace("_1", "").replace("_2", "")
        lo = legal_origin.get(base, "Unknown")
        lbl.set_color(origin_colors.get(lo, "#333333"))
        if name.startswith("Russia"):
            lbl.set_fontweight("bold")
            lbl.set_fontsize(9)

    ax.set_title(f"Feature-based Ward Clustering (k={use_k}, silhouette={use_sil:.3f})", fontsize=12)
    ax.set_ylabel("Distance")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_dendrogram.png"), dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_dendrogram.png")

    # ── Fig 2: Silhouette by k ─────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    ks = sorted(sil_scores.keys())
    ax.plot(ks, [sil_scores[k] for k in ks], "bo-", markersize=6)
    ax.axvline(use_k, color="red", ls="--", alpha=0.7, label=f"selected k={use_k}")
    if best_k != use_k:
        ax.axvline(best_k, color="green", ls=":", alpha=0.7, label=f"optimal k={best_k}")
    ax.set_xlabel("k", fontsize=11)
    ax.set_ylabel("Silhouette Score", fontsize=11)
    ax.set_title("Silhouette Score by Number of Clusters", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_silhouette_k.png"), dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_silhouette_k.png")

    # ── Fig 3: Silhouette per entity ───────────────────────────────
    sample_sils = silhouette_samples(X, use_labels, metric="euclidean")
    sil_df = pd.DataFrame({"entity": entities, "cluster": use_labels, "silhouette": sample_sils})
    sil_df = sil_df.sort_values(["cluster", "silhouette"], ascending=[True, False])

    fig, ax = plt.subplots(figsize=(12, 14))
    y_lower = 0
    cluster_colors = plt.cm.tab10(np.linspace(0, 1, use_k))
    for cl in sorted(set(use_labels)):
        cl_sils = sil_df[sil_df["cluster"] == cl]["silhouette"].values
        cl_names = sil_df[sil_df["cluster"] == cl]["entity"].values
        y_upper = y_lower + len(cl_sils)
        color = cluster_colors[cl - 1]
        ax.barh(range(y_lower, y_upper), cl_sils, height=0.8, color=color,
                edgecolor="none", alpha=0.8)
        for yi, name in zip(range(y_lower, y_upper), cl_names):
            fontweight = "bold" if name.startswith("Russia") else "normal"
            fontsize = 7 if not name.startswith("Russia") else 8
            ax.text(-0.02, yi, name, ha="right", va="center",
                    fontsize=fontsize, fontweight=fontweight)
        ax.text(0.5, (y_lower + y_upper) / 2, f"F{cl}",
                fontsize=12, fontweight="bold", va="center", alpha=0.5)
        y_lower = y_upper + 2

    ax.axvline(use_sil, color="red", ls="--", lw=1, alpha=0.7,
               label=f"Mean silhouette = {use_sil:.3f}")
    ax.set_xlabel("Silhouette Coefficient", fontsize=11)
    ax.set_title(f"Silhouette per Entity (k={use_k})", fontsize=12)
    ax.legend(fontsize=9)
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_silhouette_entities.png"), dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_silhouette_entities.png")

    # ── Fig 4: Cluster profiles heatmap ────────────────────────────
    profiles = pd.DataFrame(dtype=float)
    for cl in sorted(set(use_labels)):
        cl_entities = [entities[i] for i in range(n) if use_labels[i] == cl]
        cl_features = features.loc[cl_entities]
        profiles[f"F{cl} (n={len(cl_entities)})"] = cl_features.mean()

    profiles_z = (profiles.T - features.mean()) / (features.std() + 1e-10)

    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(profiles_z.astype(float), annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, ax=ax, cbar_kws={"shrink": 0.7}, linewidths=0.5)
    ax.set_title(f"Cluster Profiles — z-scores (k={use_k})", fontsize=12)
    ax.set_ylabel("Cluster")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_profiles_heatmap.png"), dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_profiles_heatmap.png")

    # ── Fig 5: PCA ─────────────────────────────────────────────────
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)
    ev1, ev2 = pca.explained_variance_ratio_

    fig, ax = plt.subplots(figsize=(14, 10))
    for i, entity in enumerate(entities):
        cl = use_labels[i]
        color = cluster_colors[cl - 1]
        base = entity.replace("_1", "").replace("_2", "")
        lo = legal_origin.get(base, "Unknown")
        marker = "o"
        size = 60
        if entity.startswith("Russia"):
            marker = "*"
            size = 300
        ax.scatter(X_pca[i, 0], X_pca[i, 1], c=[color], marker=marker, s=size,
                   edgecolors="black", linewidths=0.5 if not entity.startswith("Russia") else 2,
                   zorder=10 if entity.startswith("Russia") else 5)
        fontweight = "bold" if entity.startswith("Russia") else "normal"
        fontsize = 8 if entity.startswith("Russia") else 6
        ax.annotate(entity, (X_pca[i, 0], X_pca[i, 1]),
                    fontsize=fontsize, fontweight=fontweight, alpha=0.8,
                    xytext=(4, 4), textcoords="offset points")

    for cl in sorted(set(use_labels)):
        cl_entities_list = [entities[i] for i in range(n) if use_labels[i] == cl]
        ax.scatter([], [], c=[cluster_colors[cl - 1]], label=f"F{cl} (n={len(cl_entities_list)})", s=80)
    ax.legend(fontsize=8, loc="best")
    ax.set_xlabel(f"PC1 ({ev1:.1%} variance)", fontsize=11)
    ax.set_ylabel(f"PC2 ({ev2:.1%} variance)", fontsize=11)
    ax.set_title(f"PCA Projection (k={use_k})", fontsize=12)
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_pca.png"), dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_pca.png")

    # ── Fig 6: t-SNE ──────────────────────────────────────────────
    tsne = TSNE(n_components=2, perplexity=min(15, n - 1), random_state=42,
                max_iter=2000, learning_rate="auto", init="pca")
    X_tsne = tsne.fit_transform(X)

    fig, ax = plt.subplots(figsize=(14, 10))
    for i, entity in enumerate(entities):
        cl = use_labels[i]
        color = cluster_colors[cl - 1]
        marker = "*" if entity.startswith("Russia") else "o"
        size = 300 if entity.startswith("Russia") else 60
        ax.scatter(X_tsne[i, 0], X_tsne[i, 1], c=[color], marker=marker, s=size,
                   edgecolors="black", linewidths=0.5 if not entity.startswith("Russia") else 2,
                   zorder=10 if entity.startswith("Russia") else 5)
        fontweight = "bold" if entity.startswith("Russia") else "normal"
        fontsize = 8 if entity.startswith("Russia") else 6
        ax.annotate(entity, (X_tsne[i, 0], X_tsne[i, 1]),
                    fontsize=fontsize, fontweight=fontweight, alpha=0.8,
                    xytext=(4, 4), textcoords="offset points")

    for cl in sorted(set(use_labels)):
        cl_entities_list = [entities[i] for i in range(n) if use_labels[i] == cl]
        ax.scatter([], [], c=[cluster_colors[cl - 1]], label=f"F{cl} (n={len(cl_entities_list)})", s=80)
    ax.legend(fontsize=8, loc="best")
    ax.set_title(f"t-SNE Projection (k={use_k})", fontsize=12)
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_tsne.png"), dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_tsne.png")

    # ── Log detailed cluster compositions ──────────────────────────
    log.info(f"\n{'=' * 70}")
    log.info(f"CLUSTER COMPOSITIONS (k={use_k}, silhouette={use_sil:.3f})")
    log.info(f"{'=' * 70}")

    for cl in sorted(set(use_labels)):
        cl_entities = sorted([entities[i] for i in range(n) if use_labels[i] == cl])
        origins = {}
        for e in cl_entities:
            base = e.replace("_1", "").replace("_2", "")
            lo = legal_origin.get(base, "n/a")
            origins[lo] = origins.get(lo, 0) + 1

        log.info(f"\n  Cluster F{cl} ({len(cl_entities)}):")
        log.info(f"    Members: {cl_entities}")
        log.info(f"    Legal origins: {origins}")

        # Cluster feature profile
        cl_features = features.loc[cl_entities]
        log.info(f"    Feature means:")
        for col in features.columns:
            val = cl_features[col].mean()
            log.info(f"      {col:20s} = {val:.4f}")

    # ── Russia analysis ────────────────────────────────────────────
    log.info(f"\n{'=' * 70}")
    log.info("RUSSIA ANALYSIS")
    log.info(f"{'=' * 70}")

    for r_name in ["Russia_1", "Russia_2"]:
        if r_name not in entities:
            continue
        r_idx = entities.index(r_name) if isinstance(entities, list) else list(features.index).index(r_name)
        r_cl = use_labels[r_idx]
        r_sil = sample_sils[r_idx]
        cl_entities = [entities[i] for i in range(n) if use_labels[i] == r_cl]

        log.info(f"\n  {r_name}:")
        log.info(f"    Cluster: F{r_cl}")
        log.info(f"    Silhouette: {r_sil:.3f}")
        log.info(f"    Cluster members: {sorted(cl_entities)}")

        # Euclidean distances to all other entities
        r_X = X[r_idx]
        distances = {}
        for j, e in enumerate(list(features.index)):
            if e == r_name:
                continue
            distances[e] = np.linalg.norm(r_X - X[j])

        log.info(f"    Nearest neighbors (Euclidean in feature space):")
        for e, d in sorted(distances.items(), key=lambda x: x[1])[:8]:
            e_cl = use_labels[list(features.index).index(e)]
            log.info(f"      {e:25s} dist={d:.3f} (cluster F{e_cl})")

    # Distance between Russia_1 and Russia_2
    if "Russia_1" in features.index and "Russia_2" in features.index:
        idx1 = list(features.index).index("Russia_1")
        idx2 = list(features.index).index("Russia_2")
        d12 = np.linalg.norm(X[idx1] - X[idx2])
        log.info(f"\n  Distance Russia_1 <-> Russia_2: {d12:.3f}")
        all_dists = []
        for i in range(n):
            for j in range(i+1, n):
                all_dists.append(np.linalg.norm(X[i] - X[j]))
        log.info(f"  Mean pairwise distance: {np.mean(all_dists):.3f}")
        log.info(f"  Median pairwise distance: {np.median(all_dists):.3f}")
        pctile = np.searchsorted(np.sort(all_dists), d12) / len(all_dists) * 100
        log.info(f"  Russia_1-Russia_2 distance percentile: {pctile:.1f}%")

    # ── Save assignments ───────────────────────────────────────────
    assignments = pd.DataFrame({
        "entity": list(features.index),
        "cluster": [f"F{use_labels[i]}" for i in range(n)],
        "silhouette": sample_sils,
    })
    for col in features.columns:
        assignments[col] = features[col].values
    assignments = assignments.set_index("entity")
    assignments.to_csv(os.path.join(DATA_DIR, "final_cluster_assignments.csv"), encoding="utf-8")
    log.info(f"\n  Saved: final_cluster_assignments.csv")

    features.to_csv(os.path.join(DATA_DIR, "final_features.csv"), encoding="utf-8")
    log.info(f"  Saved: final_features.csv")

    return {
        "entities": list(features.index),
        "labels": use_labels,
        "k": use_k,
        "silhouette": use_sil,
        "features": features,
        "X": X,
        "linkage": Z,
        "pca_coords": X_pca,
        "pca_variance": (ev1, ev2),
        "sil_scores": sil_scores,
        "profiles": profiles,
        "sample_sils": sample_sils,
    }


# =====================================================================
# 4. TRAJECTORY VISUALIZATION WITH CLUSTERS
# =====================================================================
def plot_trajectories_by_cluster(entities_panel, full_russia, result, master):
    log.info("")
    log.info("STEP 4: Trajectory plots by cluster")

    entities = result["entities"]
    labels = result["labels"]
    k = result["k"]
    years_all = [y for y in entities_panel.columns if isinstance(y, int)]

    cluster_colors = plt.cm.tab10(np.linspace(0, 1, k))

    # Reconstruct full trajectories for plotting
    fig, axes = plt.subplots(2, (k + 1) // 2, figsize=(7 * ((k + 1) // 2), 12))
    if k <= 2:
        axes = np.array(axes).reshape(2, -1)
    axes = axes.flatten()

    for cl_idx in range(k):
        ax = axes[cl_idx]
        cl = cl_idx + 1
        cl_entities = [entities[i] for i in range(len(entities)) if labels[i] == cl]

        for entity in cl_entities:
            if entity == "Russia_1":
                pre_years = [y for y in years_all if y < 2022]
                vals = [full_russia[y] for y in pre_years]
                ax.plot(pre_years, vals, "r-o", markersize=3, lw=2, alpha=0.9, label="Russia_1")
            elif entity == "Russia_2":
                post_years = [y for y in years_all if y >= 2022]
                vals = [full_russia[y] for y in post_years]
                ax.plot(post_years, vals, "r--s", markersize=4, lw=2, alpha=0.9, label="Russia_2")
            else:
                row = entities_panel.loc[entity]
                valid_years = [y for y in years_all if pd.notna(row[y])]
                vals = [row[y] for y in valid_years]
                ax.plot(valid_years, vals, "-", lw=1, alpha=0.5,
                        color=cluster_colors[cl_idx])
                ax.annotate(entity, (valid_years[-1], vals[-1]),
                            fontsize=5, alpha=0.6)

        ax.set_title(f"Cluster F{cl} ({len(cl_entities)} entities)", fontsize=10,
                     color=cluster_colors[cl_idx])
        ax.set_xlabel("Year")
        ax.set_ylabel("WGI Composite")
        ax.grid(True, alpha=0.3)
        if any(e.startswith("Russia") for e in cl_entities):
            ax.legend(fontsize=7)

    for idx in range(k, len(axes)):
        axes[idx].set_visible(False)

    plt.suptitle(f"Trajectories by Cluster (k={k})", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_trajectories_by_cluster.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_trajectories_by_cluster.png")

    # Russia comparison plot
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    # Russia_1 cluster neighbors
    r1_idx = entities.index("Russia_1") if "Russia_1" in entities else None
    r2_idx = entities.index("Russia_2") if "Russia_2" in entities else None

    X = result["X"]
    for ax_pos, r_name, r_idx_val in [(0, "Russia_1", r1_idx), (1, "Russia_2", r2_idx)]:
        ax = axes[ax_pos]
        if r_idx_val is None:
            ax.set_visible(False)
            continue

        # Find 5 nearest neighbors
        dists = {}
        for j, e in enumerate(entities):
            if e == r_name:
                continue
            dists[e] = np.linalg.norm(X[r_idx_val] - X[j])
        nearest = sorted(dists.items(), key=lambda x: x[1])[:5]

        # Plot Russia segment
        if r_name == "Russia_1":
            pre_years = [y for y in years_all if y < 2022]
            ax.plot(pre_years, [full_russia[y] for y in pre_years],
                    "r-o", markersize=4, lw=2.5, label=r_name)
        else:
            post_years = [y for y in years_all if y >= 2022]
            ax.plot(post_years, [full_russia[y] for y in post_years],
                    "r-o", markersize=4, lw=2.5, label=r_name)

        # Plot neighbors (full trajectories)
        for e, d in nearest:
            if e.startswith("Russia"):
                continue
            row = entities_panel.loc[e] if e in entities_panel.index else None
            if row is not None:
                valid_years = [y for y in years_all if pd.notna(row[y])]
                vals = [row[y] for y in valid_years]
                ax.plot(valid_years, vals, "-", lw=1.5, alpha=0.7,
                        label=f"{e} (d={d:.2f})")

        ax.set_title(f"{r_name}: Nearest Neighbors", fontsize=10)
        ax.set_xlabel("Year")
        ax.set_ylabel("WGI Composite")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "final_russia_neighbors.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  Saved: final_russia_neighbors.png")


# =====================================================================
# 5. CROSS-REFERENCE WITH STATIC CLUSTERING
# =====================================================================
def cross_reference(result, master):
    log.info("")
    log.info("STEP 5: Cross-reference with static clustering and metadata")

    entities = result["entities"]
    labels = result["labels"]
    k = result["k"]

    # Load previous cluster assignments if available
    prev_path = os.path.join(DATA_DIR, "cluster_assignments.csv")
    prev = None
    if os.path.exists(prev_path):
        prev = pd.read_csv(prev_path, index_col=0)
        log.info(f"  Loaded previous assignments: {prev.shape}")

    for cl in sorted(set(labels)):
        cl_entities = [entities[i] for i in range(len(entities)) if labels[i] == cl]
        log.info(f"\n  Cluster F{cl}:")

        for entity in sorted(cl_entities):
            base = entity.replace("_1", "").replace("_2", "")
            info = []

            # Legal origin
            if base in master.index and pd.notna(master.loc[base, "F1_legal_origin"]):
                info.append(f"law={master.loc[base, 'F1_legal_origin']}")

            # Market group
            if base in master.index and pd.notna(master.loc[base, "market_group"]):
                info.append(f"market={master.loc[base, 'market_group']}")

            # Previous clustering
            if prev is not None and base in prev.index:
                if "cluster_A" in prev.columns:
                    info.append(f"A={prev.loc[base, 'cluster_A']}")
                if "cluster_B" in prev.columns:
                    info.append(f"B={prev.loc[base, 'cluster_B']}")

            # WGI composite level
            if base in master.index:
                wgi_cols = [c for c in master.columns if c.startswith("WGI_composite_202")]
                if wgi_cols:
                    val = master.loc[base, wgi_cols[0]]
                    if pd.notna(val):
                        info.append(f"WGI={val:.2f}")

            info_str = ", ".join(info)
            log.info(f"    {entity:25s} | {info_str}")


# =====================================================================
# MAIN
# =====================================================================
def main():
    log.info("=" * 70)
    log.info("FINAL CLUSTERING: Feature-based with Russia_1/Russia_2 split")
    log.info("=" * 70)

    master_path = os.path.join(DATA_DIR, "master_factors.csv")
    master = pd.read_csv(master_path, index_col="country")
    log.info(f"Master table loaded: {master.shape}")

    # Step 1
    entities_panel, panels, full_composite = build_panel_with_split()

    # Step 2
    features = extract_features(entities_panel)

    # Step 3
    result = cluster_analysis(features, master)

    # Step 4
    full_russia = full_composite.loc["Russia"]
    plot_trajectories_by_cluster(entities_panel, full_russia, result, master)

    # Step 5
    cross_reference(result, master)

    log.info("")
    log.info("=" * 70)
    log.info("FINAL CLUSTERING COMPLETE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
