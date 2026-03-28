"""
Этап 3: Кластеризация траекторий WGI (2009–2024).

Подходы:
  C — DTW-кластеризация (Dynamic Time Warping)
  D — k-Shape (cross-correlation distance)
  E — Feature-based (извлечение признаков из траектории → Ward)

Вход:
  - F4-6 P_Data_Extract_From_Worldwide_Governance_Indicators_detailed.xlsx
  - master_factors.csv (для метаданных: legal origin, F2, F7)

Выход:
  - figures/traj_*.png
  - trajectory_panel.csv          — годовая панель WGI
  - trajectory_cluster_assignments.csv
"""
import json
import logging
import os
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.manifold import TSNE

import ruptures as rpt
from tslearn.clustering import TimeSeriesKMeans, KShape
from tslearn.metrics import dtw as ts_dtw
from tslearn.utils import to_time_series_dataset

warnings.filterwarnings("ignore", category=FutureWarning)

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
        logging.FileHandler(os.path.join(LOG_DIR, "clustering_trajectories.log"),
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
# 1. BUILD ANNUAL WGI PANEL
# =====================================================================
def build_annual_panel():
    """Returns DataFrame: index=country, columns=years 2009..2024, values=WGI composite."""
    log.info("=" * 70)
    log.info("STEP 1: Building annual WGI panel (2009-2024)")
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

        factor_panel = pd.DataFrame(index=sorted(JURISDICTIONS.keys()), columns=years, dtype=float)
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
        n_complete = factor_panel.dropna().shape[0]
        log.info(f"  {factor}: {n_complete}/48 complete series (16 points)")

    # WGI composite = mean(F4, F5, F6) per year
    composite = pd.DataFrame(index=sorted(JURISDICTIONS.keys()), columns=years, dtype=float)
    for c in composite.index:
        for yr in years:
            vals = [panels[f].loc[c, yr] for f in est_codes.values()
                    if pd.notna(panels[f].loc[c, yr])]
            if len(vals) == 3:
                composite.loc[c, yr] = np.mean(vals)

    n_complete = composite.dropna().shape[0]
    n_partial = composite.dropna(thresh=12).shape[0]
    log.info(f"  WGI composite: {n_complete}/48 complete, {n_partial}/48 with >=12 points")

    # Save individual factor panels too
    for factor, panel in panels.items():
        panels[factor] = panel

    return composite, panels


# =====================================================================
# 2. VISUALIZE TRAJECTORIES
# =====================================================================
def plot_trajectories(panel, panels_individual, master):
    """Spaghetti plot of all WGI composite trajectories."""
    log.info("")
    log.info("STEP 2: Visualizing trajectories")

    complete = panel.dropna()
    years = panel.columns.tolist()

    legal_origin = master["F1_legal_origin"] if "F1_legal_origin" in master.columns else None

    fig, axes = plt.subplots(1, 3, figsize=(22, 7))

    # 2a: All trajectories, colored by legal family
    ax = axes[0]
    origin_colors = {
        "English": "#2196F3", "French": "#FF9800", "German": "#4CAF50",
        "Scandinavian": "#9C27B0", "Socialist": "#F44336",
    }
    for c in complete.index:
        vals = complete.loc[c].values.astype(float)
        lo = legal_origin.get(c, "Unknown") if legal_origin is not None else "Unknown"
        color = origin_colors.get(lo, "#999999")
        alpha = 0.7 if c == "Russia" else 0.3
        lw = 2.5 if c == "Russia" else 0.8
        ax.plot(years, vals, color=color, alpha=alpha, lw=lw)
        if c == "Russia":
            ax.annotate("Russia", (years[-1], vals[-1]), fontsize=8, fontweight="bold",
                        color="#F44336", xytext=(5, 0), textcoords="offset points")
    for lo, color in origin_colors.items():
        ax.plot([], [], color=color, lw=2, label=lo)
    ax.legend(fontsize=7, loc="lower left")
    ax.set_title("WGI Composite: All Trajectories by Legal Origin", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.grid(True, alpha=0.3)

    # 2b: Highlight key groups
    ax = axes[1]
    highlights = {
        "Russia": "#F44336",
        "China": "#FF5722",
        "Turkey": "#FF9800",
        "Hong Kong": "#9C27B0",
        "Singapore": "#2196F3",
        "United Kingdom": "#1565C0",
        "Germany": "#4CAF50",
        "United States": "#0D47A1",
        "South Korea": "#00BCD4",
        "Brazil": "#795548",
    }
    for c in complete.index:
        vals = complete.loc[c].values.astype(float)
        if c in highlights:
            ax.plot(years, vals, color=highlights[c], lw=2, alpha=0.9, label=c)
        else:
            ax.plot(years, vals, color="#CCCCCC", lw=0.5, alpha=0.3)
    ax.legend(fontsize=7, loc="lower left", ncol=2)
    ax.set_title("WGI Composite: Selected Jurisdictions", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.grid(True, alpha=0.3)

    # 2c: Year-over-year changes (delta)
    ax = axes[2]
    for c in complete.index:
        vals = complete.loc[c].values.astype(float)
        deltas = np.diff(vals)
        color = "#F44336" if c == "Russia" else "#999999"
        alpha = 0.8 if c == "Russia" else 0.15
        lw = 2.0 if c == "Russia" else 0.5
        ax.plot(years[1:], deltas, color=color, alpha=alpha, lw=lw)
    ax.axhline(0, color="black", lw=0.5, ls="--")
    ax.set_title("WGI Composite: Year-over-Year Changes", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("Δ WGI Composite")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "traj_overview.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


# =====================================================================
# 3. STRUCTURAL BREAKPOINT DETECTION
# =====================================================================
def detect_breakpoints(panel):
    """Use ruptures PELT to detect changepoints in each trajectory."""
    log.info("")
    log.info("STEP 3: Structural breakpoint detection (ruptures PELT)")

    complete = panel.dropna()
    years = panel.columns.tolist()
    results = {}

    for c in complete.index:
        signal = complete.loc[c].values.astype(float)
        algo = rpt.Pelt(model="rbf", min_size=3, jump=1).fit(signal)
        bkps = algo.predict(pen=3.0)
        # bkps includes the last index (len), remove it
        change_indices = [b for b in bkps if b < len(signal)]
        change_years = [years[i] for i in change_indices]
        results[c] = {
            "breakpoint_indices": change_indices,
            "breakpoint_years": change_years,
            "n_breakpoints": len(change_indices),
        }

    # Summary
    countries_with_breaks = {c: r for c, r in results.items() if r["n_breakpoints"] > 0}
    log.info(f"  Countries with breakpoints: {len(countries_with_breaks)}/{len(complete)}")
    for c, r in sorted(countries_with_breaks.items(), key=lambda x: -x[1]["n_breakpoints"]):
        log.info(f"    {c}: {r['breakpoint_years']}")

    if "Russia" in results:
        log.info(f"  Russia breakpoints: {results['Russia']['breakpoint_years']}")

    # Visualize breakpoints for top countries
    fig, axes = plt.subplots(3, 4, figsize=(20, 12))
    axes = axes.flatten()

    show_countries = ["Russia", "Hong Kong", "Turkey", "China", "Brazil",
                      "Hungary", "Poland", "Saudi Arabia", "South Africa",
                      "United States", "United Kingdom", "Singapore"]
    show_countries = [c for c in show_countries if c in complete.index]

    for idx, c in enumerate(show_countries[:12]):
        ax = axes[idx]
        signal = complete.loc[c].values.astype(float)
        ax.plot(years, signal, "b-o", markersize=3, lw=1.5)
        if c in results and results[c]["n_breakpoints"] > 0:
            for bp_yr in results[c]["breakpoint_years"]:
                ax.axvline(bp_yr, color="red", ls="--", lw=1.5, alpha=0.7)
        ax.set_title(c, fontsize=9, fontweight="bold")
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)

    for idx in range(len(show_countries), 12):
        axes[idx].set_visible(False)

    plt.suptitle("WGI Composite Trajectories with Detected Breakpoints (PELT)", fontsize=12)
    plt.tight_layout()
    path = os.path.join(FIG_DIR, "traj_breakpoints.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")

    return results


# =====================================================================
# 4. DTW CLUSTERING (Variant C)
# =====================================================================
def dtw_clustering(panel, master):
    """DTW-based hierarchical clustering of WGI trajectories."""
    log.info("")
    log.info("STEP 4: DTW clustering (Variant C)")

    complete = panel.dropna()
    countries = complete.index.tolist()
    n = len(countries)
    years = panel.columns.tolist()

    # Z-normalize each trajectory (compare shapes, not levels)
    trajectories = []
    for c in countries:
        ts = complete.loc[c].values.astype(float)
        ts_z = (ts - ts.mean()) / (ts.std() + 1e-10)
        trajectories.append(ts_z)
    trajectories = np.array(trajectories)

    # Compute DTW distance matrix
    log.info(f"  Computing DTW distance matrix ({n}x{n})...")
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = ts_dtw(trajectories[i].reshape(-1, 1), trajectories[j].reshape(-1, 1))
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    # Hierarchical clustering on DTW distances
    condensed = squareform(dist_matrix)
    Z = linkage(condensed, method="ward")

    # Optimal k via silhouette
    sil_scores = {}
    for k in range(2, 12):
        labels = fcluster(Z, k, criterion="maxclust")
        if len(set(labels)) < 2:
            continue
        sil = silhouette_score(dist_matrix, labels, metric="precomputed")
        sil_scores[k] = sil
        log.info(f"    k={k}: silhouette={sil:.3f}")

    best_k = max(sil_scores, key=sil_scores.get)
    log.info(f"  Best k={best_k} (silhouette={sil_scores[best_k]:.3f})")

    labels_best = fcluster(Z, best_k, criterion="maxclust")
    cluster_map = dict(zip(countries, labels_best))

    # Also try tslearn TimeSeriesKMeans with DTW for comparison
    ts_dataset = to_time_series_dataset(trajectories)
    log.info(f"  Running tslearn DTW k-means (k={best_k})...")
    km = TimeSeriesKMeans(n_clusters=best_k, metric="dtw", max_iter=50,
                          random_state=42, n_jobs=-1, verbose=0)
    km_labels = km.fit_predict(ts_dataset)
    km_sil = silhouette_score(dist_matrix, km_labels, metric="precomputed")
    log.info(f"  tslearn DTW k-means silhouette: {km_sil:.3f}")

    # Use whichever gives better silhouette
    if km_sil > sil_scores[best_k]:
        log.info("  Using tslearn DTW k-means labels (better silhouette)")
        final_labels = km_labels
        final_sil = km_sil
    else:
        log.info("  Using hierarchical Ward labels")
        final_labels = labels_best - 1  # 0-indexed
        final_sil = sil_scores[best_k]

    # Also compute a more granular clustering (k=4-6 range)
    granular_k_candidates = [k for k in range(4, 7) if k in sil_scores]
    if granular_k_candidates:
        granular_k = max(granular_k_candidates, key=lambda k: sil_scores[k])
    else:
        granular_k = min(sil_scores.keys(), key=lambda k: abs(k - 5))

    granular_labels = fcluster(Z, granular_k, criterion="maxclust") - 1
    granular_sil = sil_scores.get(granular_k, 0)
    log.info(f"  Granular k={granular_k} (silhouette={granular_sil:.3f})")

    log.info(f"\n  DTW Granular clustering (k={granular_k}):")
    for cl in range(granular_k):
        cl_countries = sorted([countries[i] for i in range(n) if granular_labels[i] == cl])
        log.info(f"    Cluster C{cl+1}g ({len(cl_countries)}): {cl_countries}")

    # Visualize
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))

    # 4a: Dendrogram
    ax = axes[0, 0]
    legal_origin = master["F1_legal_origin"] if "F1_legal_origin" in master.columns else None
    origin_colors_map = {
        "English": "#2196F3", "French": "#FF9800", "German": "#4CAF50",
        "Scandinavian": "#9C27B0", "Socialist": "#F44336",
    }
    label_colors = {}
    for c in countries:
        lo = legal_origin.get(c, "Unknown") if legal_origin is not None else "Unknown"
        label_colors[c] = origin_colors_map.get(lo, "#333333")

    dn = dendrogram(Z, labels=countries, ax=ax, leaf_rotation=90, leaf_font_size=6,
                    color_threshold=0)
    ax.set_title(f"DTW Hierarchical Clustering (Ward, k={best_k})", fontsize=10)
    ax.set_ylabel("DTW Distance")

    # 4b: Silhouette plot
    ax = axes[0, 1]
    ks = sorted(sil_scores.keys())
    ax.plot(ks, [sil_scores[k] for k in ks], "bo-")
    ax.axvline(best_k, color="red", ls="--", alpha=0.7, label=f"best k={best_k}")
    ax.set_xlabel("k")
    ax.set_ylabel("Silhouette Score")
    ax.set_title("DTW Clustering: Silhouette by k", fontsize=10)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 4c: Trajectories by cluster (z-normalized)
    ax = axes[1, 0]
    cluster_colors = plt.cm.tab10(np.linspace(0, 1, best_k))
    for idx, c in enumerate(countries):
        cl = final_labels[idx]
        ax.plot(years, trajectories[idx], color=cluster_colors[cl], alpha=0.4, lw=0.8)
    for cl in range(best_k):
        mask = final_labels == cl
        mean_traj = trajectories[mask].mean(axis=0)
        ax.plot(years, mean_traj, color=cluster_colors[cl], lw=3, alpha=0.9,
                label=f"C{cl+1} (n={mask.sum()})")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_title("DTW Clusters: Z-normalized Trajectories", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite (z-score)")
    ax.grid(True, alpha=0.3)

    # 4d: Trajectories by cluster (original scale)
    ax = axes[1, 1]
    for idx, c in enumerate(countries):
        cl = final_labels[idx]
        vals = complete.loc[c].values.astype(float)
        ax.plot(years, vals, color=cluster_colors[cl], alpha=0.4, lw=0.8)
    for cl in range(best_k):
        mask = final_labels == cl
        cl_countries = [countries[i] for i in range(n) if final_labels[i] == cl]
        mean_traj = complete.loc[cl_countries].mean(axis=0).values.astype(float)
        ax.plot(years, mean_traj, color=cluster_colors[cl], lw=3, alpha=0.9,
                label=f"C{cl+1} (n={mask.sum()})")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_title("DTW Clusters: Original Scale Trajectories", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "traj_dtw_clustering.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")

    # Log cluster compositions
    log.info(f"\n  DTW Clustering results (k={best_k}, silhouette={final_sil:.3f}):")
    for cl in range(best_k):
        cl_countries = sorted([countries[i] for i in range(n) if final_labels[i] == cl])
        log.info(f"    Cluster C{cl+1} ({len(cl_countries)}): {cl_countries}")

    russia_idx = countries.index("Russia") if "Russia" in countries else None
    if russia_idx is not None:
        cl = final_labels[russia_idx]
        cl_countries = [countries[i] for i in range(n) if final_labels[i] == cl]
        log.info(f"\n  Russia: cluster C{cl+1} with {cl_countries}")

    # Additional figure: granular k clustering
    fig2, axes2 = plt.subplots(1, 2, figsize=(20, 8))

    # Granular: z-normalized
    ax = axes2[0]
    g_colors = plt.cm.tab10(np.linspace(0, 1, granular_k))
    for idx, c in enumerate(countries):
        cl = granular_labels[idx]
        ax.plot(years, trajectories[idx], color=g_colors[cl], alpha=0.35, lw=0.8)
    for cl in range(granular_k):
        mask = granular_labels == cl
        if mask.sum() > 0:
            mean_traj = trajectories[mask].mean(axis=0)
            ax.plot(years, mean_traj, color=g_colors[cl], lw=3, alpha=0.9,
                    label=f"C{cl+1}g (n={mask.sum()})")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_title(f"DTW Clusters (k={granular_k}): Z-normalized", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite (z-score)")
    ax.grid(True, alpha=0.3)

    # Granular: original scale
    ax = axes2[1]
    for idx, c in enumerate(countries):
        cl = granular_labels[idx]
        vals = complete.loc[c].values.astype(float)
        ax.plot(years, vals, color=g_colors[cl], alpha=0.35, lw=0.8)
    for cl in range(granular_k):
        mask = granular_labels == cl
        cl_c = [countries[i] for i in range(n) if granular_labels[i] == cl]
        if cl_c:
            mean_traj = complete.loc[cl_c].mean(axis=0).values.astype(float)
            ax.plot(years, mean_traj, color=g_colors[cl], lw=3, alpha=0.9,
                    label=f"C{cl+1}g (n={mask.sum()})")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_title(f"DTW Clusters (k={granular_k}): Original Scale", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path2 = os.path.join(FIG_DIR, "traj_dtw_granular.png")
    plt.savefig(path2, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path2}")

    return {
        "countries": countries,
        "labels": final_labels,
        "granular_labels": granular_labels,
        "granular_k": granular_k,
        "granular_sil": granular_sil,
        "dist_matrix": dist_matrix,
        "best_k": best_k,
        "silhouette": final_sil,
        "trajectories_z": trajectories,
        "linkage": Z,
    }


# =====================================================================
# 5. k-SHAPE CLUSTERING (Variant D)
# =====================================================================
def kshape_clustering(panel, master, dtw_k):
    """k-Shape clustering using cross-correlation distance."""
    log.info("")
    log.info("STEP 5: k-Shape clustering (Variant D)")

    complete = panel.dropna()
    countries = complete.index.tolist()
    n = len(countries)
    years = panel.columns.tolist()

    trajectories = []
    for c in countries:
        ts = complete.loc[c].values.astype(float)
        trajectories.append(ts)
    trajectories = np.array(trajectories)

    ts_dataset = to_time_series_dataset(trajectories)

    sil_scores = {}
    best_sil = -1
    best_labels = None

    for k in range(2, 12):
        try:
            ks = KShape(n_clusters=k, max_iter=100, random_state=42, verbose=0)
            labels = ks.fit_predict(ts_dataset)
            if len(set(labels)) < 2:
                continue
            # Use Euclidean on z-normalized for silhouette (k-Shape internally z-normalizes)
            z_trajs = np.array([(t - t.mean()) / (t.std() + 1e-10) for t in trajectories])
            sil = silhouette_score(z_trajs, labels, metric="euclidean")
            sil_scores[k] = sil
            log.info(f"    k={k}: silhouette={sil:.3f}")
            if sil > best_sil:
                best_sil = sil
                best_labels = labels
                best_k = k
        except Exception as e:
            log.warning(f"    k={k}: failed - {e}")
            continue

    if best_labels is None:
        log.warning("  k-Shape clustering failed for all k")
        return None

    log.info(f"  Best k={best_k} (silhouette={best_sil:.3f})")

    # Visualize
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    # 5a: Silhouette by k
    ax = axes[0]
    ks_list = sorted(sil_scores.keys())
    ax.plot(ks_list, [sil_scores[k] for k in ks_list], "go-")
    ax.axvline(best_k, color="red", ls="--", alpha=0.7, label=f"best k={best_k}")
    ax.set_xlabel("k")
    ax.set_ylabel("Silhouette Score")
    ax.set_title("k-Shape: Silhouette by k", fontsize=10)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 5b: Trajectories by cluster
    ax = axes[1]
    cluster_colors = plt.cm.tab10(np.linspace(0, 1, best_k))
    for idx, c in enumerate(countries):
        cl = best_labels[idx]
        vals = complete.loc[c].values.astype(float)
        ax.plot(years, vals, color=cluster_colors[cl], alpha=0.4, lw=0.8)
    for cl in range(best_k):
        mask = best_labels == cl
        cl_countries = [countries[i] for i in range(n) if best_labels[i] == cl]
        if cl_countries:
            mean_traj = complete.loc[cl_countries].mean(axis=0).values.astype(float)
            ax.plot(years, mean_traj, color=cluster_colors[cl], lw=3, alpha=0.9,
                    label=f"D{cl+1} (n={mask.sum()})")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_title("k-Shape Clusters: Original Scale", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "traj_kshape_clustering.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")

    log.info(f"\n  k-Shape results (k={best_k}, silhouette={best_sil:.3f}):")
    for cl in range(best_k):
        cl_countries = sorted([countries[i] for i in range(n) if best_labels[i] == cl])
        log.info(f"    Cluster D{cl+1} ({len(cl_countries)}): {cl_countries}")

    return {
        "countries": countries,
        "labels": best_labels,
        "best_k": best_k,
        "silhouette": best_sil,
    }


# =====================================================================
# 6. FEATURE-BASED CLUSTERING (Variant E)
# =====================================================================
def feature_clustering(panel, breakpoints, master):
    """Extract trajectory features → Ward clustering."""
    log.info("")
    log.info("STEP 6: Feature-based trajectory clustering (Variant E)")

    complete = panel.dropna()
    countries = complete.index.tolist()
    years = panel.columns.tolist()
    n = len(countries)

    features = pd.DataFrame(index=countries)

    for c in countries:
        ts = complete.loc[c].values.astype(float)
        xs = np.arange(len(ts), dtype=float)

        # Level features
        features.loc[c, "mean"] = ts.mean()
        features.loc[c, "std"] = ts.std()
        features.loc[c, "start"] = ts[0]
        features.loc[c, "end"] = ts[-1]
        features.loc[c, "range"] = ts.max() - ts.min()

        # Trend: OLS slope (per year)
        slope, intercept = np.polyfit(xs, ts, 1)
        features.loc[c, "slope"] = slope
        residuals = ts - (slope * xs + intercept)
        features.loc[c, "residual_std"] = residuals.std()

        # Curvature: quadratic coefficient
        coeffs = np.polyfit(xs, ts, 2)
        features.loc[c, "curvature"] = coeffs[0]

        # Volatility: mean absolute year-over-year change
        deltas = np.diff(ts)
        features.loc[c, "mean_abs_delta"] = np.abs(deltas).mean()
        features.loc[c, "max_abs_delta"] = np.abs(deltas).max()

        # Max drop (most negative year-over-year change)
        features.loc[c, "max_drop"] = deltas.min()
        features.loc[c, "max_rise"] = deltas.max()

        # Breakpoint info
        bp_info = breakpoints.get(c, {})
        features.loc[c, "n_breakpoints"] = bp_info.get("n_breakpoints", 0)

        # Trend consistency: fraction of positive year-over-year changes
        features.loc[c, "frac_positive"] = (deltas > 0).mean()

        # Split trend: first half vs second half slope
        mid = len(ts) // 2
        slope_h1 = np.polyfit(np.arange(mid), ts[:mid], 1)[0]
        slope_h2 = np.polyfit(np.arange(len(ts) - mid), ts[mid:], 1)[0]
        features.loc[c, "slope_h1"] = slope_h1
        features.loc[c, "slope_h2"] = slope_h2
        features.loc[c, "slope_change"] = slope_h2 - slope_h1

    log.info(f"  Extracted {features.shape[1]} features for {n} countries")
    log.info(f"  Features: {list(features.columns)}")

    # Standardize
    scaler = StandardScaler()
    X = scaler.fit_transform(features.values.astype(float))

    # Ward clustering
    Z = linkage(X, method="ward")
    sil_scores = {}
    for k in range(2, 12):
        labels = fcluster(Z, k, criterion="maxclust")
        if len(set(labels)) < 2:
            continue
        sil = silhouette_score(X, labels, metric="euclidean")
        sil_scores[k] = sil
        log.info(f"    k={k}: silhouette={sil:.3f}")

    best_k = max(sil_scores, key=sil_scores.get)
    best_labels = fcluster(Z, best_k, criterion="maxclust") - 1  # 0-indexed
    best_sil = sil_scores[best_k]
    log.info(f"  Best k={best_k} (silhouette={best_sil:.3f})")

    # Visualize
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))

    # 6a: Dendrogram
    ax = axes[0, 0]
    dendrogram(Z, labels=countries, ax=ax, leaf_rotation=90, leaf_font_size=6)
    ax.set_title(f"Feature-based Ward Clustering (k={best_k})", fontsize=10)
    ax.set_ylabel("Distance")

    # 6b: Silhouette
    ax = axes[0, 1]
    ks_list = sorted(sil_scores.keys())
    ax.plot(ks_list, [sil_scores[k] for k in ks_list], "ro-")
    ax.axvline(best_k, color="red", ls="--", alpha=0.7, label=f"best k={best_k}")
    ax.set_xlabel("k")
    ax.set_ylabel("Silhouette Score")
    ax.set_title("Feature-based: Silhouette by k", fontsize=10)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 6c: Trajectories by cluster
    ax = axes[1, 0]
    cluster_colors = plt.cm.tab10(np.linspace(0, 1, best_k))
    for idx, c in enumerate(countries):
        cl = best_labels[idx]
        vals = complete.loc[c].values.astype(float)
        ax.plot(years, vals, color=cluster_colors[cl], alpha=0.4, lw=0.8)
    for cl in range(best_k):
        mask = best_labels == cl
        cl_countries = [countries[i] for i in range(n) if best_labels[i] == cl]
        if cl_countries:
            mean_traj = complete.loc[cl_countries].mean(axis=0).values.astype(float)
            ax.plot(years, mean_traj, color=cluster_colors[cl], lw=3, alpha=0.9,
                    label=f"E{cl+1} (n={mask.sum()})")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_title("Feature-based Clusters: Trajectories", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.grid(True, alpha=0.3)

    # 6d: Feature importance heatmap
    ax = axes[1, 1]
    cluster_profiles = pd.DataFrame(index=range(best_k), columns=features.columns, dtype=float)
    for cl in range(best_k):
        cl_countries = [countries[i] for i in range(n) if best_labels[i] == cl]
        cluster_profiles.loc[cl] = features.loc[cl_countries].mean()
    cluster_profiles.index = [f"E{cl+1}" for cl in range(best_k)]

    # Standardize for heatmap
    prof_z = (cluster_profiles - cluster_profiles.mean()) / (cluster_profiles.std() + 1e-10)
    sns.heatmap(prof_z.T.astype(float), annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, ax=ax, cbar_kws={"shrink": 0.6})
    ax.set_title("Feature-based Cluster Profiles (z-score)", fontsize=10)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "traj_feature_clustering.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")

    log.info(f"\n  Feature-based results (k={best_k}, silhouette={best_sil:.3f}):")
    for cl in range(best_k):
        cl_countries = sorted([countries[i] for i in range(n) if best_labels[i] == cl])
        log.info(f"    Cluster E{cl+1} ({len(cl_countries)}): {cl_countries}")

    return {
        "countries": countries,
        "labels": best_labels,
        "best_k": best_k,
        "silhouette": best_sil,
        "features": features,
    }


# =====================================================================
# 7. COMPARISON & RUSSIA ANALYSIS
# =====================================================================
def compare_and_analyze(panel, dtw_res, kshape_res, feature_res, breakpoints, master):
    """Compare all approaches, analyze Russia's position."""
    log.info("")
    log.info("STEP 7: Comparison and Russia analysis")

    complete = panel.dropna()
    countries = dtw_res["countries"]
    years = panel.columns.tolist()

    # Build comparison table
    comparison = pd.DataFrame(index=countries)
    comparison["DTW_k2"] = [f"C{dtw_res['labels'][i]+1}" for i in range(len(countries))]
    comparison["DTW_granular"] = [f"Cg{dtw_res['granular_labels'][i]+1}" for i in range(len(countries))]

    if kshape_res is not None:
        comparison["kShape_cluster"] = [f"D{kshape_res['labels'][i]+1}" for i in range(len(countries))]

    comparison["Feature_cluster"] = [f"E{feature_res['labels'][i]+1}" for i in range(len(countries))]

    if "F1_legal_origin" in master.columns:
        for c in countries:
            if c in master.index:
                comparison.loc[c, "legal_origin"] = master.loc[c, "F1_legal_origin"]

    for c in countries:
        bp = breakpoints.get(c, {})
        comparison.loc[c, "n_breakpoints"] = bp.get("n_breakpoints", 0)
        bpy = bp.get("breakpoint_years", [])
        comparison.loc[c, "breakpoint_years"] = str(bpy) if bpy else ""

    # Save
    path = os.path.join(DATA_DIR, "trajectory_cluster_assignments.csv")
    comparison.to_csv(path, encoding="utf-8")
    log.info(f"  Saved: {path}")

    # Cross-tabulation DTW (k=2) vs Feature
    log.info("\n  Cross-tabulation DTW(k=2) vs Feature-based:")
    ct = pd.crosstab(comparison["DTW_k2"], comparison["Feature_cluster"])
    log.info(f"\n{ct.to_string()}")

    if kshape_res is not None:
        log.info("\n  Cross-tabulation DTW(k=2) vs k-Shape:")
        ct2 = pd.crosstab(comparison["DTW_k2"], comparison["kShape_cluster"])
        log.info(f"\n{ct2.to_string()}")

    log.info("\n  Cross-tabulation DTW granular vs Feature-based:")
    ct3 = pd.crosstab(comparison["DTW_granular"], comparison["Feature_cluster"])
    log.info(f"\n{ct3.to_string()}")

    # Russia analysis
    log.info("\n  === RUSSIA ANALYSIS ===")
    if "Russia" in countries:
        r_idx = countries.index("Russia")
        log.info(f"  DTW(k=2): C{dtw_res['labels'][r_idx]+1}")
        log.info(f"  DTW(k={dtw_res['granular_k']}): Cg{dtw_res['granular_labels'][r_idx]+1}")
        if kshape_res is not None:
            log.info(f"  k-Shape: D{kshape_res['labels'][r_idx]+1}")
        log.info(f"  Feature: E{feature_res['labels'][r_idx]+1}")

        # Russia's trajectory stats
        ts_r = complete.loc["Russia"].values.astype(float)
        deltas = np.diff(ts_r)
        log.info(f"  Trajectory: start={ts_r[0]:.3f}, end={ts_r[-1]:.3f}")
        log.info(f"  Overall slope: {np.polyfit(np.arange(len(ts_r)), ts_r, 1)[0]:.4f}/year")
        log.info(f"  Max drop: {deltas.min():.3f} ({years[np.argmin(deltas)+1]})")
        log.info(f"  Breakpoints: {breakpoints.get('Russia', {}).get('breakpoint_years', [])}")

        # DTW neighbors
        dist_row = dtw_res["dist_matrix"][r_idx]
        nearest = np.argsort(dist_row)[1:6]
        log.info(f"  DTW nearest neighbors:")
        for ni in nearest:
            log.info(f"    {countries[ni]}: DTW distance={dist_row[ni]:.3f}")

    # Visualization: t-SNE of DTW distances colored by all three clusterings
    fig, axes = plt.subplots(1, 3, figsize=(22, 7))

    tsne = TSNE(n_components=2, perplexity=min(15, len(countries) - 1),
                random_state=42, max_iter=2000, metric="precomputed", init="random")
    embedding = tsne.fit_transform(dtw_res["dist_matrix"])

    vis_panels = [
        ("DTW k=2 (Var. C)", "DTW_k2"),
        (f"DTW k={dtw_res['granular_k']} (Var. C)", "DTW_granular"),
        ("Feature (Var. E)", "Feature_cluster"),
    ]
    if kshape_res is not None:
        vis_panels[2] = ("k-Shape (Var. D)", "kShape_cluster")
        # Add feature as 4th if we have kshape
    for ax_idx, (method, label_col) in enumerate(vis_panels[:3]):
        ax = axes[ax_idx]
        if label_col not in comparison.columns:
            ax.set_visible(False)
            continue
        unique_labels = sorted(comparison[label_col].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(unique_labels)))
        color_map = dict(zip(unique_labels, colors))

        for idx, c in enumerate(countries):
            cl = comparison.loc[c, label_col]
            color = color_map[cl]
            marker = "*" if c == "Russia" else "o"
            size = 200 if c == "Russia" else 40
            ax.scatter(embedding[idx, 0], embedding[idx, 1],
                       c=[color], marker=marker, s=size, edgecolors="black",
                       linewidths=0.5 if c != "Russia" else 2, zorder=10 if c == "Russia" else 5)
            ax.annotate(c, (embedding[idx, 0], embedding[idx, 1]),
                        fontsize=5, alpha=0.7, xytext=(3, 3), textcoords="offset points")

        for cl, color in color_map.items():
            ax.scatter([], [], c=[color], label=cl, s=60)
        ax.legend(fontsize=7, loc="best")
        ax.set_title(f"t-SNE (DTW distance) — {method}", fontsize=10)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "traj_comparison_tsne.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")

    # Summary comparison
    log.info("\n  SUMMARY:")
    log.info(f"  DTW (Var. C, optimal): k={dtw_res['best_k']}, silhouette={dtw_res['silhouette']:.3f}")
    log.info(f"  DTW (Var. C, granular): k={dtw_res['granular_k']}, silhouette={dtw_res['granular_sil']:.3f}")
    if kshape_res:
        log.info(f"  k-Shape (Var. D): k={kshape_res['best_k']}, silhouette={kshape_res['silhouette']:.3f}")
    log.info(f"  Feature (Var. E): k={feature_res['best_k']}, silhouette={feature_res['silhouette']:.3f}")

    return comparison


# =====================================================================
# 8. RUSSIA PRE/POST BREAK ANALYSIS
# =====================================================================
def russia_split_analysis(panel, breakpoints, dtw_res):
    """Analyze Russia as two segments: pre-break and post-break."""
    log.info("")
    log.info("STEP 8: Russia pre/post structural break analysis")

    complete = panel.dropna()
    countries = complete.index.tolist()
    years = panel.columns.tolist()

    bp_russia = breakpoints.get("Russia", {})
    bp_years = bp_russia.get("breakpoint_years", [])

    if not bp_years:
        log.info("  No breakpoints detected for Russia, skipping split analysis")
        return

    # Use the most significant breakpoint
    ts_r = complete.loc["Russia"].values.astype(float)
    deltas = np.diff(ts_r)
    # Find the year with max absolute change
    max_drop_idx = np.argmin(deltas)
    split_year = years[max_drop_idx + 1]
    log.info(f"  Split year (max drop): {split_year}")

    split_idx = years.index(split_year)

    pre_years = years[:split_idx]
    post_years = years[split_idx:]
    pre_ts = ts_r[:split_idx]
    post_ts = ts_r[split_idx:]

    log.info(f"  Pre-break ({pre_years[0]}-{pre_years[-1]}): mean={pre_ts.mean():.3f}, "
             f"slope={np.polyfit(np.arange(len(pre_ts)), pre_ts, 1)[0]:.4f}/yr")
    log.info(f"  Post-break ({post_years[0]}-{post_years[-1]}): mean={post_ts.mean():.3f}, "
             f"slope={np.polyfit(np.arange(len(post_ts)), post_ts, 1)[0]:.4f}/yr")

    # Find which other countries' FULL trajectories are most similar to
    # Russia's PRE-break trajectory (using DTW on z-normalized)
    pre_z = (pre_ts - pre_ts.mean()) / (pre_ts.std() + 1e-10)

    log.info("\n  Countries most similar to Russia PRE-break trajectory:")
    pre_distances = {}
    for c in countries:
        if c == "Russia":
            continue
        other_ts = complete.loc[c].values.astype(float)
        # Compare Russia's pre-break with other country's same-period segment
        other_pre = other_ts[:split_idx]
        other_pre_z = (other_pre - other_pre.mean()) / (other_pre.std() + 1e-10)
        d = ts_dtw(pre_z.reshape(-1, 1), other_pre_z.reshape(-1, 1))
        pre_distances[c] = d

    for c, d in sorted(pre_distances.items(), key=lambda x: x[1])[:8]:
        other_pre = complete.loc[c].values[:split_idx].astype(float)
        log.info(f"    {c}: DTW={d:.3f} (pre-period mean={other_pre.mean():.3f})")

    # Visualization
    fig, axes = plt.subplots(1, 3, figsize=(22, 7))

    # 8a: Russia split visualization
    ax = axes[0]
    ax.plot(pre_years, pre_ts, "b-o", markersize=4, lw=2, label=f"Pre-break ({pre_years[0]}-{pre_years[-1]})")
    ax.plot(post_years, post_ts, "r-o", markersize=4, lw=2, label=f"Post-break ({post_years[0]}-{post_years[-1]})")
    ax.axvline(split_year, color="gray", ls="--", lw=2, alpha=0.5)
    ax.set_title("Russia: WGI Composite — Structural Break", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 8b: Russia pre-break vs similar countries (same period)
    ax = axes[1]
    ax.plot(pre_years, pre_ts, "r-o", markersize=4, lw=2.5, label="Russia")
    top_similar = sorted(pre_distances.items(), key=lambda x: x[1])[:5]
    for c, d in top_similar:
        other_pre = complete.loc[c].values[:split_idx].astype(float)
        ax.plot(pre_years, other_pre, "-", lw=1.5, alpha=0.7, label=f"{c} (DTW={d:.2f})")
    ax.set_title(f"Pre-break Period ({pre_years[0]}-{pre_years[-1]}): Russia vs Similar", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Composite")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # 8c: Component-level breakdown around break
    ax = axes[2]
    # Plot F4, F5, F6 for Russia individually
    wgi_path = os.path.join(DATA_DIR,
        "F4-6 P_Data_Extract_From_Worldwide_Governance_Indicators_detailed.xlsx")
    wgi = pd.read_excel(wgi_path, sheet_name="Data")
    wgi["country"] = wgi["Country Name"].apply(norm)
    russia_wgi = wgi[wgi["country"] == "Russia"]

    est_codes = {
        "GOV_WGI_RQ.EST": "F4 Reg. Quality",
        "GOV_WGI_RL.EST": "F5 Rule of Law",
        "GOV_WGI_PV.EST": "F6 Pol. Stability",
    }
    colors_comp = {"GOV_WGI_RQ.EST": "#2196F3", "GOV_WGI_RL.EST": "#4CAF50", "GOV_WGI_PV.EST": "#FF9800"}

    yr_cols = [f"{y} [YR{y}]" for y in years]
    for code, label in est_codes.items():
        row = russia_wgi[russia_wgi["Series Code"] == code]
        if row.empty:
            continue
        vals = []
        for yc in yr_cols:
            raw = row.iloc[0][yc]
            if str(raw).strip() in ("..", "") or pd.isna(raw):
                vals.append(np.nan)
            else:
                vals.append(float(raw))
        ax.plot(years, vals, "-o", markersize=3, lw=1.5, label=label, color=colors_comp[code])
    ax.axvline(split_year, color="gray", ls="--", lw=2, alpha=0.5)
    ax.set_title("Russia: WGI Components Around Break", fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("WGI Estimate")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "traj_russia_break.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


# =====================================================================
# MAIN
# =====================================================================
def main():
    log.info("=" * 70)
    log.info("TRAJECTORY CLUSTERING ANALYSIS (Stage 3)")
    log.info("=" * 70)

    # Load master for metadata
    master_path = os.path.join(DATA_DIR, "master_factors.csv")
    master = pd.read_csv(master_path, index_col="country")
    log.info(f"Master table loaded: {master.shape}")

    # Step 1: Build annual panel
    panel, panels_individual = build_annual_panel()

    # Save panel
    panel_path = os.path.join(DATA_DIR, "trajectory_panel.csv")
    panel.to_csv(panel_path, encoding="utf-8")
    log.info(f"Saved: {panel_path}")

    # Step 2: Visualize
    plot_trajectories(panel, panels_individual, master)

    # Step 3: Breakpoints
    breakpoints = detect_breakpoints(panel)

    # Step 4: DTW clustering
    dtw_res = dtw_clustering(panel, master)

    # Step 5: k-Shape
    kshape_res = kshape_clustering(panel, master, dtw_res["best_k"])

    # Step 6: Feature-based
    feature_res = feature_clustering(panel, breakpoints, master)

    # Step 7: Comparison
    comparison = compare_and_analyze(panel, dtw_res, kshape_res, feature_res, breakpoints, master)

    # Step 8: Russia analysis
    russia_split_analysis(panel, breakpoints, dtw_res)

    log.info("")
    log.info("=" * 70)
    log.info("TRAJECTORY CLUSTERING COMPLETE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
