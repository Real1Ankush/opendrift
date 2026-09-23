import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(r"D:\Opendrift")

ORIGIN_FILE = (
    BASE_DIR
    / "bay_of_bengal"
    / "phase4_4_output"
    / "origin_result.json"
)

PHASE51_FILE = (
    BASE_DIR
    / "AIS"
    / "phase5_output"
    / "phase5_vessel_candidates.csv"
)

PHASE52_FILE = (
    BASE_DIR
    / "AIS"
    / "phase5_output"
    / "phase5_2_trajectory_analysis.csv"
)

AIS_FILE = (
    BASE_DIR
    / "AIS"
    / "phase5_output"
    / "ais_synthetic_2026.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "AIS"
    / "phase5_output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "phase5_3_final_vessel_ranking.csv"
)

OUTPUT_JSON = (
    OUTPUT_DIR
    / "phase5_3_result.json"
)

OUTPUT_MAP = (
    OUTPUT_DIR
    / "phase5_3_evidence_map.png"
)


# ============================================================
# WEIGHTS
# ============================================================

PHASE51_WEIGHT = 0.55
PHASE52_WEIGHT = 0.45


# ============================================================
# HEADER
# ============================================================

print("=" * 75)
print("PHASE 5.3 - EVIDENCE FUSION")
print("=" * 75)

print("\nCombining:")
print("  Phase 5.1 -> Spatial + temporal AIS compatibility")
print("  Phase 5.2 -> Vessel trajectory behavior")

print("\nPrototype weights:")
print(
    f"  Phase 5.1: "
    f"{PHASE51_WEIGHT * 100:.0f}%"
)

print(
    f"  Phase 5.2: "
    f"{PHASE52_WEIGHT * 100:.0f}%"
)


# ============================================================
# LOAD MODELED ORIGIN
# ============================================================

print("\n" + "=" * 75)
print("LOADING MODELED ORIGIN")
print("=" * 75)

with open(
    ORIGIN_FILE,
    "r",
    encoding="utf-8"
) as f:

    origin = json.load(f)


origin_lat = float(
    origin["candidate_origin"]["latitude"]
)

origin_lon = float(
    origin["candidate_origin"]["longitude"]
)

print(
    f"\nCandidate origin:"
    f"\nLatitude  : {origin_lat:.6f}"
    f"\nLongitude : {origin_lon:.6f}"
)


# ============================================================
# LOAD PHASE 5.1
# ============================================================

print("\n" + "=" * 75)
print("LOADING PHASE 5.1")
print("=" * 75)

phase51 = pd.read_csv(
    PHASE51_FILE
)

required_51 = [
    "mmsi",
    "vessel_name",
    "ship_type",
    "min_distance_km",
    "closest_time_difference_hours",
    "trajectory_match_score",
]

missing_51 = [
    column
    for column in required_51
    if column not in phase51.columns
]

if missing_51:

    raise ValueError(
        f"Phase 5.1 missing columns: {missing_51}"
    )

phase51["mmsi"] = (
    phase51["mmsi"]
    .astype(str)
)

print(
    f"\nPhase 5.1 candidates: "
    f"{len(phase51)}"
)


# ============================================================
# LOAD PHASE 5.2
# ============================================================

print("\n" + "=" * 75)
print("LOADING PHASE 5.2")
print("=" * 75)

phase52 = pd.read_csv(
    PHASE52_FILE
)

required_52 = [
    "mmsi",
    "min_distance_km",
    "approaching_origin",
    "departing_origin",
    "mean_sog",
    "speed_change_percent",
    "max_course_change_deg",
    "continuity_score",
    "proximity_score",
    "approach_score",
    "behavior_score",
    "trajectory_score",
]

missing_52 = [
    column
    for column in required_52
    if column not in phase52.columns
]

if missing_52:

    raise ValueError(
        f"Phase 5.2 missing columns: {missing_52}"
    )

phase52["mmsi"] = (
    phase52["mmsi"]
    .astype(str)
)

print(
    f"\nPhase 5.2 candidates: "
    f"{len(phase52)}"
)


# ============================================================
# MERGE PHASE 5.1 + PHASE 5.2
# ============================================================

print("\n" + "=" * 75)
print("FUSING EVIDENCE")
print("=" * 75)

merged = pd.merge(
    phase51,
    phase52,
    on="mmsi",
    how="inner",
    suffixes=(
        "_phase51",
        "_phase52"
    )
)

if merged.empty:

    raise RuntimeError(
        "No common candidates between "
        "Phase 5.1 and Phase 5.2."
    )

print(
    f"\nCandidates available in both phases: "
    f"{len(merged)}"
)


# ============================================================
# COLUMN RESOLUTION HELPERS
# ============================================================

def get_phase51_column(df, name):
    """
    Return the Phase 5.1 version of a column.
    """

    suffixed = f"{name}_phase51"

    if suffixed in df.columns:
        return suffixed

    if name in df.columns:
        return name

    raise KeyError(
        f"Could not find Phase 5.1 column: {name}"
    )


def get_phase52_column(df, name):
    """
    Return the Phase 5.2 version of a column.
    """

    suffixed = f"{name}_phase52"

    if suffixed in df.columns:
        return suffixed

    if name in df.columns:
        return name

    raise KeyError(
        f"Could not find Phase 5.2 column: {name}"
    )


# ============================================================
# RESOLVE PHASE 5.1 COLUMNS
# ============================================================

phase51_name_col = get_phase51_column(
    merged,
    "vessel_name"
)

phase51_type_col = get_phase51_column(
    merged,
    "ship_type"
)

phase51_distance_col = get_phase51_column(
    merged,
    "min_distance_km"
)

phase51_time_diff_col = get_phase51_column(
    merged,
    "closest_time_difference_hours"
)

phase51_score_col = get_phase51_column(
    merged,
    "trajectory_match_score"
)


# ============================================================
# RESOLVE PHASE 5.2 COLUMNS
# ============================================================

approaching_col = get_phase52_column(
    merged,
    "approaching_origin"
)

departing_col = get_phase52_column(
    merged,
    "departing_origin"
)

speed_change_col = get_phase52_column(
    merged,
    "speed_change_percent"
)

course_change_col = get_phase52_column(
    merged,
    "max_course_change_deg"
)

continuity_col = get_phase52_column(
    merged,
    "continuity_score"
)

proximity_col = get_phase52_column(
    merged,
    "proximity_score"
)

approach_score_col = get_phase52_column(
    merged,
    "approach_score"
)

behavior_score_col = get_phase52_column(
    merged,
    "behavior_score"
)

trajectory_score_col = get_phase52_column(
    merged,
    "trajectory_score"
)

phase52_distance_col = get_phase52_column(
    merged,
    "min_distance_km"
)

mean_sog_col = get_phase52_column(
    merged,
    "mean_sog"
)


# ============================================================
# PHASE 5.1 SCORE
# ============================================================

merged["phase51_score"] = (
    merged[phase51_score_col]
    .astype(float)
)


# ============================================================
# PHASE 5.2 SCORE
# ============================================================

merged["phase52_score"] = (
    merged[trajectory_score_col]
    .astype(float)
)


# ============================================================
# FINAL EVIDENCE SCORE
# ============================================================

merged["final_evidence_score"] = (
    PHASE51_WEIGHT
    * merged["phase51_score"]
    +
    PHASE52_WEIGHT
    * merged["phase52_score"]
)


# ============================================================
# EVIDENCE LEVEL
# ============================================================

def evidence_level(score):

    if score >= 80:
        return "Strong screening match"

    elif score >= 60:
        return "Moderate screening match"

    elif score >= 40:
        return "Weak screening match"

    else:
        return "Low screening match"


merged["evidence_level"] = (
    merged["final_evidence_score"]
    .apply(evidence_level)
)


# ============================================================
# EVIDENCE SUMMARY
# ============================================================

def build_evidence_summary(row):

    evidence = []

    distance = float(
        row[phase52_distance_col]
    )

    # --------------------------------------------------------
    # PROXIMITY
    # --------------------------------------------------------

    if distance <= 0.5:

        evidence.append(
            "very close to modeled origin"
        )

    elif distance <= 2.0:

        evidence.append(
            "within 2 km of modeled origin"
        )

    # --------------------------------------------------------
    # APPROACH
    # --------------------------------------------------------

    if bool(
        row[approaching_col]
    ):

        evidence.append(
            "approaches modeled origin"
        )

    # --------------------------------------------------------
    # DEPARTURE
    # --------------------------------------------------------

    if bool(
        row[departing_col]
    ):

        evidence.append(
            "departs after closest approach"
        )

    # --------------------------------------------------------
    # SPEED
    # --------------------------------------------------------

    if float(
        row[speed_change_col]
    ) <= 10:

        evidence.append(
            "stable speed"
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    if float(
        row[course_change_col]
    ) <= 10:

        evidence.append(
            "stable course"
        )

    # --------------------------------------------------------
    # AIS CONTINUITY
    # --------------------------------------------------------

    if float(
        row[continuity_col]
    ) >= 70:

        evidence.append(
            "good AIS continuity"
        )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not evidence:

        return (
            "Limited trajectory evidence"
        )

    return "; ".join(evidence)


# ============================================================
# IMPORTANT FIX
# ============================================================
#
# The previous version defined build_evidence_summary()
# but never executed it.
#
# This line creates the missing evidence_summary column.
# ============================================================

merged["evidence_summary"] = merged.apply(
    build_evidence_summary,
    axis=1
)


# ============================================================
# FINAL RANKING
# ============================================================

merged = merged.sort_values(
    "final_evidence_score",
    ascending=False
).reset_index(
    drop=True
)

merged.insert(
    0,
    "rank",
    range(
        1,
        len(merged) + 1
    )
)


# ============================================================
# BUILD FINAL OUTPUT DATAFRAME
# ============================================================

final_df = pd.DataFrame({

    "rank":
        merged["rank"].astype(int),

    "vessel_name":
        merged[phase51_name_col],

    "mmsi":
        merged["mmsi"].astype(str),

    "ship_type":
        merged[phase51_type_col],

    "phase51_score":
        merged["phase51_score"].astype(float),

    "phase52_score":
        merged["phase52_score"].astype(float),

    "final_evidence_score":
        merged[
            "final_evidence_score"
        ].astype(float),

    "evidence_level":
        merged[
            "evidence_level"
        ].astype(str),

    "evidence_summary":
        merged[
            "evidence_summary"
        ].astype(str),

    "phase51_min_distance_km":
        merged[
            phase51_distance_col
        ].astype(float),

    "closest_time_difference_hours":
        merged[
            phase51_time_diff_col
        ].astype(float),

    "phase52_min_distance_km":
        merged[
            phase52_distance_col
        ].astype(float),

    "approaching_origin":
        merged[
            approaching_col
        ],

    "departing_origin":
        merged[
            departing_col
        ],

    "mean_sog":
        merged[
            mean_sog_col
        ].astype(float),

    "speed_change_percent":
        merged[
            speed_change_col
        ].astype(float),

    "max_course_change_deg":
        merged[
            course_change_col
        ].astype(float),

    "continuity_score":
        merged[
            continuity_col
        ].astype(float),

    "proximity_score":
        merged[
            proximity_col
        ].astype(float),

    "approach_score":
        merged[
            approach_score_col
        ].astype(float),

    "behavior_score":
        merged[
            behavior_score_col
        ].astype(float),
})


# ============================================================
# SAVE CSV
# ============================================================

final_df.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# SAVE JSON
# ============================================================

candidates_json = []

for _, row in final_df.iterrows():

    item = {}

    for key, value in row.items():

        if isinstance(
            value,
            (
                np.integer,
                np.int64
            )
        ):

            value = int(value)

        elif isinstance(
            value,
            (
                np.floating,
                np.float64
            )
        ):

            value = float(value)

        elif pd.isna(value):

            value = None

        item[key] = value

    candidates_json.append(
        item
    )


result_json = {

    "status":
        "success",

    "pipeline_stage":
        "Phase 5.3 - Evidence Fusion",

    "synthetic_data":
        True,

    "note":
        "Scores are screening scores for potential "
        "source-vessel identification. They are not "
        "probabilities and do not establish legal "
        "responsibility.",

    "modeled_origin": {

        "latitude":
            origin_lat,

        "longitude":
            origin_lon
    },

    "weights": {

        "phase51_spatial_temporal":
            PHASE51_WEIGHT,

        "phase52_trajectory_behavior":
            PHASE52_WEIGHT
    },

    "candidate_count":
        len(final_df),

    "candidates":
        candidates_json
}


with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result_json,
        f,
        indent=2
    )


# ============================================================
# LOAD AIS FOR MAP
# ============================================================

ais = pd.read_csv(
    AIS_FILE
)

ais["timestamp"] = pd.to_datetime(
    ais["timestamp"],
    utc=True
)

ais["mmsi"] = (
    ais["mmsi"]
    .astype(str)
)


# ============================================================
# MAP
# ============================================================

plt.figure(
    figsize=(12, 8)
)


# ------------------------------------------------------------
# MODELED ORIGIN
# ------------------------------------------------------------

plt.scatter(
    origin_lon,
    origin_lat,
    marker="X",
    s=280,
    label="Modeled candidate origin"
)


# ------------------------------------------------------------
# CANDIDATE TRAJECTORIES
# ------------------------------------------------------------

for _, row in final_df.iterrows():

    mmsi = str(
        row["mmsi"]
    )

    vessel = (
        ais[
            ais["mmsi"] == mmsi
        ]
        .sort_values(
            "timestamp"
        )
    )

    if vessel.empty:
        continue

    label = (
        f'{row["vessel_name"]} '
        f'({row["final_evidence_score"]:.1f})'
    )

    plt.plot(
        vessel["longitude"],
        vessel["latitude"],
        marker="o",
        label=label
    )


# ------------------------------------------------------------
# LABELS
# ------------------------------------------------------------

plt.xlabel(
    "Longitude"
)

plt.ylabel(
    "Latitude"
)

plt.title(
    "SpillTrace - AIS Evidence Fusion"
)

plt.grid(
    True,
    alpha=0.3
)

plt.legend()

plt.tight_layout()


# ------------------------------------------------------------
# SAVE MAP
# ------------------------------------------------------------

plt.savefig(
    OUTPUT_MAP,
    dpi=200
)

plt.show()


# ============================================================
# TERMINAL RESULTS
# ============================================================

print(
    "\n" + "=" * 75
)

print(
    "PHASE 5.3 FINAL RESULTS"
)

print(
    "=" * 75
)


display_columns = [
    "rank",
    "vessel_name",
    "mmsi",
    "phase51_score",
    "phase52_score",
    "final_evidence_score",
    "evidence_level"
]


print(
    final_df[
        display_columns
    ].to_string(
        index=False
    )
)


# ============================================================
# EVIDENCE DETAILS
# ============================================================

print(
    "\n" + "=" * 75
)

print(
    "EVIDENCE DETAILS"
)

print(
    "=" * 75
)


for _, row in final_df.iterrows():

    print(
        f"\n#{int(row['rank'])} "
        f"{row['vessel_name']}"
    )

    print(
        f"  Phase 5.1 score : "
        f"{row['phase51_score']:.2f}"
    )

    print(
        f"  Phase 5.2 score : "
        f"{row['phase52_score']:.2f}"
    )

    print(
        f"  Final score     : "
        f"{row['final_evidence_score']:.2f}"
    )

    print(
        f"  Evidence level  : "
        f"{row['evidence_level']}"
    )

    print(
        f"  Evidence        : "
        f"{row['evidence_summary']}"
    )


# ============================================================
# COMPLETE
# ============================================================

print(
    "\n" + "=" * 75
)

print(
    "PHASE 5.3 COMPLETE"
)

print(
    "=" * 75
)

print(
    "\nSaved:"
)

print(
    OUTPUT_CSV
)

print(
    OUTPUT_JSON
)

print(
    OUTPUT_MAP
)