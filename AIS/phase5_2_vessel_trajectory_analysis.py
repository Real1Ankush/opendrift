import json
import math
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

AIS_FILE = (
    BASE_DIR
    / "AIS"
    / "phase5_output"
    / "ais_synthetic_2026.csv"
)

CANDIDATE_FILE = (
    BASE_DIR
    / "AIS"
    / "phase5_output"
    / "phase5_vessel_candidates.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "AIS"
    / "phase5_output"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "phase5_2_trajectory_analysis.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase5_2_result.json"
OUTPUT_MAP = OUTPUT_DIR / "phase5_2_trajectory_map.png"


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate great-circle distance in kilometers.
    """

    R = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


# ============================================================
# ANGLE DIFFERENCE
# ============================================================

def angle_difference(a, b):
    """
    Smallest absolute difference between two compass headings.
    """

    diff = abs(a - b) % 360

    if diff > 180:
        diff = 360 - diff

    return diff


# ============================================================
# LOAD ORIGIN
# ============================================================

print("=" * 75)
print("PHASE 5.2 - VESSEL TRAJECTORY BEHAVIOR ANALYSIS")
print("=" * 75)

print("\nLoading dynamic origin...")

with open(ORIGIN_FILE, "r", encoding="utf-8") as f:
    origin = json.load(f)


origin_lat = float(origin["candidate_origin"]["latitude"])
origin_lon = float(origin["candidate_origin"]["longitude"])

print(f"\nCandidate origin:")
print(f"Latitude  : {origin_lat:.6f}")
print(f"Longitude : {origin_lon:.6f}")


# ============================================================
# LOAD AIS
# ============================================================

print("\n" + "=" * 75)
print("LOADING AIS")
print("=" * 75)

ais = pd.read_csv(AIS_FILE)

required_columns = [
    "mmsi",
    "vessel_name",
    "timestamp",
    "latitude",
    "longitude",
    "sog",
    "cog",
    "ship_type",
]

missing = [
    col for col in required_columns
    if col not in ais.columns
]

if missing:
    raise ValueError(
        f"Missing AIS columns: {missing}"
    )

ais["timestamp"] = pd.to_datetime(
    ais["timestamp"],
    utc=True
)

ais["latitude"] = pd.to_numeric(
    ais["latitude"],
    errors="coerce"
)

ais["longitude"] = pd.to_numeric(
    ais["longitude"],
    errors="coerce"
)

ais["sog"] = pd.to_numeric(
    ais["sog"],
    errors="coerce"
)

ais["cog"] = pd.to_numeric(
    ais["cog"],
    errors="coerce"
)

ais = ais.dropna(
    subset=[
        "latitude",
        "longitude",
        "timestamp"
    ]
)

print(f"\nAIS observations: {len(ais)}")
print(f"Unique vessels: {ais['mmsi'].nunique()}")


# ============================================================
# LOAD PHASE 5.1 CANDIDATES
# ============================================================

print("\n" + "=" * 75)
print("LOADING PHASE 5.1 CANDIDATES")
print("=" * 75)

candidates = pd.read_csv(CANDIDATE_FILE)

if "mmsi" not in candidates.columns:
    raise ValueError(
        "Phase 5.1 candidate file does not contain MMSI."
    )

candidate_mmsis = candidates["mmsi"].astype(str).tolist()

print(f"\nCandidates from Phase 5.1: {len(candidate_mmsis)}")

print(candidates[
    [
        c for c in
        ["rank", "vessel_name", "mmsi",
         "ship_type", "min_distance_km",
         "trajectory_match_score"]
        if c in candidates.columns
    ]
].to_string(index=False))


# ============================================================
# ANALYZE EACH CANDIDATE
# ============================================================

results = []

print("\n" + "=" * 75)
print("TRAJECTORY ANALYSIS")
print("=" * 75)

for mmsi in candidate_mmsis:

    vessel = ais[
        ais["mmsi"].astype(str) == str(mmsi)
    ].copy()

    vessel = vessel.sort_values("timestamp")

    if len(vessel) == 0:
        continue

    vessel_name = vessel.iloc[0]["vessel_name"]
    ship_type = vessel.iloc[0]["ship_type"]

    print(f"\nAnalyzing: {vessel_name}")
    print(f"MMSI: {mmsi}")
    print(f"Observations: {len(vessel)}")

    # --------------------------------------------------------
    # DISTANCE FROM MODELED ORIGIN
    # --------------------------------------------------------

    vessel["distance_km"] = vessel.apply(
        lambda row: haversine_km(
            row["latitude"],
            row["longitude"],
            origin_lat,
            origin_lon
        ),
        axis=1
    )

    closest_idx = vessel["distance_km"].idxmin()

    closest_row = vessel.loc[closest_idx]

    min_distance = float(
        closest_row["distance_km"]
    )

    closest_time = closest_row["timestamp"]

    # --------------------------------------------------------
    # APPROACHING / DEPARTING
    # --------------------------------------------------------

    closest_position = vessel.index.get_loc(
        closest_idx
    )

    before = vessel.iloc[:closest_position + 1]
    after = vessel.iloc[closest_position:]

    approaching = False
    departing = False

    if len(before) >= 2:

        first_before = float(
            before.iloc[0]["distance_km"]
        )

        closest_before = float(
            before.iloc[-1]["distance_km"]
        )

        if first_before > closest_before:
            approaching = True

    if len(after) >= 2:

        closest_after = float(
            after.iloc[0]["distance_km"]
        )

        last_after = float(
            after.iloc[-1]["distance_km"]
        )

        if last_after > closest_after:
            departing = True

    # --------------------------------------------------------
    # DISTANCE TREND
    # --------------------------------------------------------

    first_distance = float(
        vessel.iloc[0]["distance_km"]
    )

    last_distance = float(
        vessel.iloc[-1]["distance_km"]
    )

    # --------------------------------------------------------
    # SPEED ANALYSIS
    # --------------------------------------------------------

    speeds = vessel["sog"].dropna()

    if len(speeds) > 0:

        mean_speed = float(
            speeds.mean()
        )

        max_speed = float(
            speeds.max()
        )

        min_speed = float(
            speeds.min()
        )

        if mean_speed > 0:

            speed_change_percent = (
                (max_speed - min_speed)
                / mean_speed
                * 100
            )

        else:
            speed_change_percent = 0.0

    else:

        mean_speed = 0.0
        max_speed = 0.0
        min_speed = 0.0
        speed_change_percent = 0.0

    # --------------------------------------------------------
    # COURSE ANALYSIS
    # --------------------------------------------------------

    courses = vessel["cog"].dropna().tolist()

    course_changes = []

    for i in range(1, len(courses)):

        course_changes.append(
            angle_difference(
                courses[i],
                courses[i - 1]
            )
        )

    if course_changes:

        mean_course_change = float(
            np.mean(course_changes)
        )

        max_course_change = float(
            np.max(course_changes)
        )

    else:

        mean_course_change = 0.0
        max_course_change = 0.0

    # --------------------------------------------------------
    # OBSERVATION CONTINUITY
    # --------------------------------------------------------

    timestamps = vessel["timestamp"].sort_values()

    if len(timestamps) >= 2:

        gaps = (
            timestamps.diff()
            .dt.total_seconds()
            / 3600
        ).dropna()

        median_gap_hours = float(
            gaps.median()
        )

        max_gap_hours = float(
            gaps.max()
        )

        # Continuous if observations are reasonably close.
        continuity_score = max(
            0.0,
            min(
                100.0,
                100.0
                * (1.0 - median_gap_hours / 4.0)
            )
        )

    else:

        median_gap_hours = None
        max_gap_hours = None
        continuity_score = 0.0

    # --------------------------------------------------------
    # APPROACH SCORE
    # --------------------------------------------------------

    if approaching and departing:
        approach_score = 100.0

    elif approaching:
        approach_score = 75.0

    elif departing:
        approach_score = 60.0

    else:
        approach_score = 25.0

    # --------------------------------------------------------
    # PROXIMITY SCORE
    # --------------------------------------------------------

    proximity_score = max(
        0.0,
        100.0 * (
            1.0 - min_distance / 5.0
        )
    )

    # --------------------------------------------------------
    # BEHAVIOR SCORE
    # --------------------------------------------------------

    speed_penalty = min(
        50.0,
        speed_change_percent
    )

    course_penalty = min(
        50.0,
        max_course_change
    )

    behavior_score = max(
        0.0,
        100.0
        - speed_penalty
        - course_penalty
    )

    # --------------------------------------------------------
    # TRAJECTORY SCORE
    # --------------------------------------------------------

    trajectory_score = (
        0.35 * proximity_score
        + 0.25 * approach_score
        + 0.15 * continuity_score
        + 0.25 * behavior_score
    )

    result = {
        "mmsi": str(mmsi),
        "vessel_name": vessel_name,
        "ship_type": ship_type,

        "observations": int(len(vessel)),

        "first_timestamp": (
            vessel.iloc[0]["timestamp"]
            .isoformat()
        ),

        "last_timestamp": (
            vessel.iloc[-1]["timestamp"]
            .isoformat()
        ),

        "min_distance_km": min_distance,

        "closest_timestamp": (
            closest_time.isoformat()
        ),

        "first_distance_km": first_distance,
        "last_distance_km": last_distance,

        "approaching_origin": bool(approaching),
        "departing_origin": bool(departing),

        "mean_sog": mean_speed,
        "min_sog": min_speed,
        "max_sog": max_speed,
        "speed_change_percent": speed_change_percent,

        "mean_course_change_deg": mean_course_change,
        "max_course_change_deg": max_course_change,

        "median_observation_gap_hours": (
            median_gap_hours
        ),

        "max_observation_gap_hours": (
            max_gap_hours
        ),

        "continuity_score": continuity_score,
        "proximity_score": proximity_score,
        "approach_score": approach_score,
        "behavior_score": behavior_score,
        "trajectory_score": trajectory_score,
    }

    results.append(result)

    print(
        f"  Minimum distance : "
        f"{min_distance:.3f} km"
    )

    print(
        f"  Closest time     : "
        f"{closest_time}"
    )

    print(
        f"  Approaching      : "
        f"{approaching}"
    )

    print(
        f"  Departing        : "
        f"{departing}"
    )

    print(
        f"  Mean SOG         : "
        f"{mean_speed:.2f} kn"
    )

    print(
        f"  Speed variation  : "
        f"{speed_change_percent:.2f}%"
    )

    print(
        f"  Course variation : "
        f"{max_course_change:.2f}°"
    )

    print(
        f"  Continuity score : "
        f"{continuity_score:.2f}"
    )

    print(
        f"  Trajectory score : "
        f"{trajectory_score:.2f}"
    )


# ============================================================
# SORT RESULTS
# ============================================================

results_df = pd.DataFrame(results)

if len(results_df) == 0:

    print("\nNo candidate trajectories available.")

    result_json = {
        "status": "no_candidates",
        "candidate_count": 0,
        "candidates": []
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

    raise SystemExit


results_df = results_df.sort_values(
    "trajectory_score",
    ascending=False
).reset_index(drop=True)

results_df.insert(
    0,
    "rank",
    range(1, len(results_df) + 1)
)


# ============================================================
# SAVE CSV
# ============================================================

results_df.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# SAVE JSON
# ============================================================

json_results = []

for _, row in results_df.iterrows():

    item = {}

    for key, value in row.to_dict().items():

        if isinstance(value, np.integer):
            value = int(value)

        elif isinstance(value, np.floating):
            value = float(value)

        elif pd.isna(value):
            value = None

        item[key] = value

    json_results.append(item)


output_json = {
    "status": "success",

    "analysis": (
        "Dynamic AIS vessel trajectory behavior "
        "analysis using the Phase 4.4 modeled origin."
    ),

    "synthetic_data": True,

    "modeled_origin": {
        "latitude": origin_lat,
        "longitude": origin_lon
    },

    "candidates_analyzed": len(results_df),

    "candidates": json_results
}

with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output_json,
        f,
        indent=2
    )


# ============================================================
# MAP
# ============================================================

plt.figure(figsize=(12, 8))

# Origin
plt.scatter(
    origin_lon,
    origin_lat,
    marker="X",
    s=250,
    label="Candidate origin"
)

# Plot candidate trajectories
for mmsi in candidate_mmsis:

    vessel = ais[
        ais["mmsi"].astype(str) == str(mmsi)
    ].copy()

    vessel = vessel.sort_values("timestamp")

    if len(vessel) == 0:
        continue

    name = vessel.iloc[0]["vessel_name"]

    plt.plot(
        vessel["longitude"],
        vessel["latitude"],
        marker="o",
        label=name
    )

# Origin point
plt.scatter(
    origin_lon,
    origin_lat,
    marker="X",
    s=250
)

plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.title(
    "SpillTrace - Candidate Vessel Trajectory Analysis"
)

plt.grid(True, alpha=0.3)

plt.legend()

plt.tight_layout()

plt.savefig(
    OUTPUT_MAP,
    dpi=200
)

plt.show()


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\n" + "=" * 75)
print("PHASE 5.2 RESULTS")
print("=" * 75)

display_columns = [
    "rank",
    "vessel_name",
    "mmsi",
    "min_distance_km",
    "approaching_origin",
    "departing_origin",
    "mean_sog",
    "speed_change_percent",
    "max_course_change_deg",
    "trajectory_score"
]

print(
    results_df[display_columns]
    .to_string(index=False)
)

print("\n" + "=" * 75)
print("PHASE 5.2 COMPLETE")
print("=" * 75)

print("\nSaved:")

print(OUTPUT_CSV)
print(OUTPUT_JSON)
print(OUTPUT_MAP)