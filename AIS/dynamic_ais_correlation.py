from pathlib import Path
from datetime import timedelta
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

BASE = Path(r"D:\Opendrift")

ORIGIN_FILE = (
    BASE
    / "bay_of_bengal"
    / "phase4_4_output"
    / "origin_result.json"
)

AIS_FILE = (
    BASE
    / "AIS"
    / "phase5_output"
    / "ais_synthetic_2026.csv"
)

OUTPUT_DIR = (
    BASE
    / "AIS"
    / "phase5_output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RESULT_FILE = (
    OUTPUT_DIR
    / "phase5_result.json"
)

CANDIDATE_FILE = (
    OUTPUT_DIR
    / "phase5_vessel_candidates.csv"
)

MAP_FILE = (
    OUTPUT_DIR
    / "phase5_ais_origin_map.png"
)


# ============================================================
# CONFIGURATION
# ============================================================

TIME_WINDOW_HOURS = 8


# ============================================================
# HAVERSINE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 6371.0

    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    dlat = np.radians(
        lat2 - lat1
    )

    dlon = np.radians(
        lon2 - lon1
    )

    a = (
        np.sin(dlat / 2) ** 2
        +
        np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return (
        2
        * R
        * np.arcsin(
            np.sqrt(a)
        )
    )


# ============================================================
# LOAD PHASE 4.4 RESULT
# ============================================================

print("=" * 75)
print("PHASE 5.1 - DYNAMIC ORIGIN → AIS CORRELATION")
print("=" * 75)

print("\nLoading Phase 4.4 origin result...")

if not ORIGIN_FILE.exists():

    raise FileNotFoundError(
        f"Origin result not found:\n{ORIGIN_FILE}"
    )


with open(
    ORIGIN_FILE,
    "r"
) as f:

    origin_result = json.load(f)


# ============================================================
# EXTRACT SPILL INFORMATION
# ============================================================

spill = (
    origin_result[
        "spill_detection"
    ]
)

origin = (
    origin_result[
        "candidate_origin"
    ]
)

region = (
    origin_result[
        "region_50_percent"
    ]
)


spill_lat = float(
    spill["latitude"]
)

spill_lon = float(
    spill["longitude"]
)

spill_time = pd.to_datetime(
    spill["timestamp"],
    utc=True
)


origin_lat = float(
    origin["latitude"]
)

origin_lon = float(
    origin["longitude"]
)


print("\n" + "=" * 75)
print("MODELED SPILL / ORIGIN")
print("=" * 75)

print(
    f"\nSpill location:"
)

print(
    f"Latitude  : {spill_lat:.6f}"
)

print(
    f"Longitude : {spill_lon:.6f}"
)

print(
    f"Timestamp : {spill_time}"
)

print(
    f"\nCandidate origin:"
)

print(
    f"Latitude  : {origin_lat:.6f}"
)

print(
    f"Longitude : {origin_lon:.6f}"
)


# ============================================================
# DYNAMIC 50% REGION
# ============================================================

lat_min = float(
    region["latitude_min"]
)

lat_max = float(
    region["latitude_max"]
)

lon_min = float(
    region["longitude_min"]
)

lon_max = float(
    region["longitude_max"]
)


print(
    "\n50% origin region:"
)

print(
    f"Latitude : "
    f"{lat_min:.6f} → {lat_max:.6f}"
)

print(
    f"Longitude: "
    f"{lon_min:.6f} → {lon_max:.6f}"
)


# ============================================================
# LOAD AIS
# ============================================================

print("\n" + "=" * 75)
print("LOADING AIS")
print("=" * 75)

if not AIS_FILE.exists():

    raise FileNotFoundError(
        f"AIS file not found:\n{AIS_FILE}"
    )


ais = pd.read_csv(
    AIS_FILE
)


required_columns = [
    "mmsi",
    "vessel_name",
    "timestamp",
    "latitude",
    "longitude",
    "sog",
    "cog",
    "ship_type"
]


missing = [
    c
    for c in required_columns
    if c not in ais.columns
]


if missing:

    raise ValueError(
        f"Missing AIS columns: {missing}"
    )


ais["timestamp"] = pd.to_datetime(
    ais["timestamp"],
    utc=True
)


print(
    f"\nAIS observations: "
    f"{len(ais)}"
)

print(
    f"Unique vessels: "
    f"{ais['mmsi'].nunique()}"
)

print(
    f"AIS time range:"
)

print(
    f"{ais['timestamp'].min()}"
    f" → "
    f"{ais['timestamp'].max()}"
)


# ============================================================
# TIME COMPATIBILITY CHECK
# ============================================================

print("\n" + "=" * 75)
print("STEP 1 - TIME COMPATIBILITY")
print("=" * 75)


ais_start = ais["timestamp"].min()
ais_end = ais["timestamp"].max()


window_start = (
    spill_time
    - pd.Timedelta(
        hours=TIME_WINDOW_HOURS
    )
)

window_end = (
    spill_time
    + pd.Timedelta(
        hours=TIME_WINDOW_HOURS
    )
)


print(
    f"\nRequired AIS window:"
)

print(
    f"{window_start}"
    f" → "
    f"{window_end}"
)


print(
    f"\nAvailable AIS:"
)

print(
    f"{ais_start}"
    f" → "
    f"{ais_end}"
)


time_overlap = not (
    ais_end < window_start
    or
    ais_start > window_end
)


if not time_overlap:

    print(
        "\nWARNING:"
    )

    print(
        "AIS data does not overlap the "
        "Phase 4.4 spill time."
    )

    print(
        "\nThis is expected because:"
    )

    print(
        "Phase 4.4 = 2026-09-01"
    )

    print(
        "AIS sample = 2015-11-15"
    )

    print(
        "\nNo vessel responsibility/candidate "
        "claim will be generated."
    )


    result = {

        "status":
            "time_mismatch",

        "spill": {
            "latitude":
                spill_lat,

            "longitude":
                spill_lon,

            "timestamp":
                str(spill_time)
        },

        "candidate_origin": {
            "latitude":
                origin_lat,

            "longitude":
                origin_lon
        },

        "origin_region_50_percent":
            region,

        "ais": {
            "file":
                str(AIS_FILE),

            "start":
                str(ais_start),

            "end":
                str(ais_end),

            "observations":
                int(len(ais)),

            "unique_vessels":
                int(
                    ais["mmsi"].nunique()
                )
        },

        "message":
            "AIS observations do not overlap "
            "the modeled spill time."
    }


    with open(
        RESULT_FILE,
        "w"
    ) as f:

        json.dump(
            result,
            f,
            indent=4
        )


    print(
        f"\nSaved:"
    )

    print(
        RESULT_FILE
    )

    raise SystemExit(0)


# ============================================================
# SPATIAL FILTER
# ============================================================

print("\n" + "=" * 75)
print("STEP 2 - SPATIAL FILTER")
print("=" * 75)


spatial = ais[
    (ais["latitude"] >= lat_min)
    &
    (ais["latitude"] <= lat_max)
    &
    (ais["longitude"] >= lon_min)
    &
    (ais["longitude"] <= lon_max)
].copy()


print(
    f"\nObservations inside 50% "
    f"origin region: {len(spatial)}"
)

print(
    f"Candidate vessels: "
    f"{spatial['mmsi'].nunique()}"
)


# ============================================================
# TEMPORAL FILTER
# ============================================================

print("\n" + "=" * 75)
print("STEP 3 - TEMPORAL FILTER")
print("=" * 75)


temporal = spatial[
    (
        spatial["timestamp"]
        >= window_start
    )
    &
    (
        spatial["timestamp"]
        <= window_end
    )
].copy()


print(
    f"\nObservations after filtering:"
    f" {len(temporal)}"
)

print(
    f"Candidate vessels:"
    f" {temporal['mmsi'].nunique()}"
)


# ============================================================
# TRAJECTORY ANALYSIS
# ============================================================

results = []


for mmsi, vessel in (
    temporal.groupby("mmsi")
):

    vessel = (
        vessel
        .sort_values("timestamp")
        .copy()
    )

    first_row = vessel.iloc[0]

    last_row = vessel.iloc[-1]

    # --------------------------------------------------------
    # DISTANCES
    # --------------------------------------------------------

    distances = haversine_km(
        vessel["latitude"].values,
        vessel["longitude"].values,
        origin_lat,
        origin_lon
    )

    min_distance = float(
        np.min(distances)
    )

    first_distance = float(
        distances[0]
    )

    last_distance = float(
        distances[-1]
    )

    closest_index = int(
        np.argmin(distances)
    )

    closest_row = (
        vessel.iloc[
            closest_index
        ]
    )

    closest_time = (
        closest_row["timestamp"]
    )

    time_difference = abs(
        (
            closest_time
            - spill_time
        ).total_seconds()
        / 3600
    )

    # --------------------------------------------------------
    # REGION OBSERVATIONS
    # --------------------------------------------------------

    region_observations = len(
        vessel
    )

    entered_region = (
        region_observations > 0
    )

    # --------------------------------------------------------
    # APPROACH / DEPARTURE
    # --------------------------------------------------------

    approaching = (
        last_distance
        < first_distance
    )

    if len(vessel) >= 3:

        departing = (
            last_distance
            > distances[
                closest_index
            ]
        )

    else:

        departing = False

    # --------------------------------------------------------
    # SPEED
    # --------------------------------------------------------

    mean_sog = float(
        vessel["sog"].mean()
    )

    closest_sog = float(
        closest_row["sog"]
    )

    if mean_sog != 0:

        speed_change = (
            abs(
                closest_sog
                - mean_sog
            )
            / mean_sog
            * 100
        )

    else:

        speed_change = 0.0

    # --------------------------------------------------------
    # COURSE CHANGE
    # --------------------------------------------------------

    cog_values = (
        vessel["cog"]
        .astype(float)
        .values
    )

    if len(cog_values) > 1:

        course_diffs = np.abs(
            np.diff(cog_values)
        )

        course_diffs = np.minimum(
            course_diffs,
            360 - course_diffs
        )

        mean_course_change = float(
            np.mean(course_diffs)
        )

        max_course_change = float(
            np.max(course_diffs)
        )

    else:

        mean_course_change = 0.0

        max_course_change = 0.0

    # --------------------------------------------------------
    # TIME CONTINUITY
    # --------------------------------------------------------

    if len(vessel) > 1:

        gaps = (
            vessel["timestamp"]
            .diff()
            .dt.total_seconds()
            / 3600
        )

        median_gap = float(
            gaps.dropna().median()
        )

    else:

        median_gap = np.nan

    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    # Distance score:
    # 100 at 0 km, decreasing with distance.

    distance_score = max(
        0.0,
        100.0
        * (
            1
            - min_distance / 5.0
        )
    )

    # Temporal score:
    # 100 at exact time, decreasing
    # over the configured window.

    temporal_score = max(
        0.0,
        100.0
        * (
            1
            - time_difference
            / TIME_WINDOW_HOURS
        )
    )

    # Region score based on number
    # of observations in the region.

    if len(vessel) >= 5:

        region_score = 100.0

    elif len(vessel) >= 3:

        region_score = 60.0

    elif len(vessel) >= 2:

        region_score = 50.0

    else:

        region_score = 25.0

    # Approach score

    approach_score = (
        100.0
        if approaching
        else 40.0
    )

    # Continuity score

    if len(vessel) >= 2:

        if (
            np.isnan(median_gap)
            or median_gap <= 2
        ):

            continuity_score = 100.0

        elif median_gap <= 4:

            continuity_score = 70.0

        else:

            continuity_score = 40.0

    else:

        continuity_score = 20.0

    # Behavior score

    behavior_score = max(
        0.0,
        100.0
        - speed_change
        - max_course_change
    )

    # Final prototype score

    trajectory_match_score = (
        0.30 * distance_score
        +
        0.20 * temporal_score
        +
        0.15 * region_score
        +
        0.15 * approach_score
        +
        0.10 * continuity_score
        +
        0.10 * behavior_score
    )

    results.append({

        "mmsi":
            mmsi,

        "vessel_name":
            first_row["vessel_name"],

        "ship_type":
            first_row["ship_type"],

        "observations":
            len(vessel),

        "entered_50pct_origin_region":
            entered_region,

        "region_observations":
            region_observations,

        "min_distance_km":
            min_distance,

        "closest_timestamp":
            str(closest_time),

        "closest_time_difference_hours":
            time_difference,

        "first_distance_km":
            first_distance,

        "last_distance_km":
            last_distance,

        "approaching_origin":
            approaching,

        "departing_origin":
            departing,

        "mean_sog":
            mean_sog,

        "closest_sog":
            closest_sog,

        "speed_change_percent":
            speed_change,

        "mean_course_change":
            mean_course_change,

        "max_course_change":
            max_course_change,

        "median_time_gap_hours":
            median_gap,

        "distance_score":
            distance_score,

        "temporal_score":
            temporal_score,

        "region_score":
            region_score,

        "approach_score":
            approach_score,

        "continuity_score":
            continuity_score,

        "behavior_score":
            behavior_score,

        "trajectory_match_score":
            trajectory_match_score
    })


# ============================================================
# RESULTS
# ============================================================

result_df = pd.DataFrame(
    results
)


if not result_df.empty:

    result_df = (
        result_df
        .sort_values(
            "trajectory_match_score",
            ascending=False
        )
        .reset_index(drop=True)
    )

    result_df.insert(
        0,
        "rank",
        np.arange(
            1,
            len(result_df) + 1
        )
    )


print("\n" + "=" * 75)
print("PHASE 5.1 RESULTS")
print("=" * 75)


if result_df.empty:

    print(
        "\nNo potential source vessels "
        "found."
    )

else:

    print(
        result_df[
            [
                "rank",
                "vessel_name",
                "mmsi",
                "ship_type",
                "min_distance_km",
                "closest_time_difference_hours",
                "trajectory_match_score"
            ]
        ].to_string(
            index=False
        )
    )


# ============================================================
# SAVE CSV
# ============================================================

result_df.to_csv(
    CANDIDATE_FILE,
    index=False
)


# ============================================================
# SAVE JSON
# ============================================================

summary = {

    "status":
        "success",

    "spill": {
        "latitude":
            spill_lat,

        "longitude":
            spill_lon,

        "timestamp":
            str(spill_time)
    },

    "candidate_origin": {
        "latitude":
            origin_lat,

        "longitude":
            origin_lon
    },

    "origin_region_50_percent":
        region,

    "ais_observations":
        int(len(ais)),

    "candidate_vessels":
        int(
            result_df["mmsi"].nunique()
            if not result_df.empty
            else 0
        ),

    "vessels": (
        result_df.to_dict(
            orient="records"
        )
        if not result_df.empty
        else []
    ),

    "note":
        "Scores are prototype screening "
        "metrics and do not establish "
        "legal responsibility."
}


with open(
    RESULT_FILE,
    "w"
) as f:

    json.dump(
        summary,
        f,
        indent=4
    )


# ============================================================
# MAP
# ============================================================

plt.figure(
    figsize=(12, 9)
)

# Origin region

plt.plot(
    [
        lon_min,
        lon_max,
        lon_max,
        lon_min,
        lon_min
    ],
    [
        lat_min,
        lat_min,
        lat_max,
        lat_max,
        lat_min
    ],
    linestyle="--",
    linewidth=2,
    label="50% origin region"
)


# Candidate vessel tracks

for mmsi, vessel in (
    temporal.groupby("mmsi")
):

    vessel = (
        vessel
        .sort_values("timestamp")
    )

    plt.plot(
        vessel["longitude"],
        vessel["latitude"],
        marker="o",
        label=str(
            vessel["vessel_name"].iloc[0]
        )
    )


# Candidate origin

plt.scatter(
    origin_lon,
    origin_lat,
    marker="X",
    s=250,
    linewidths=2,
    label="Candidate origin"
)


plt.xlabel(
    "Longitude"
)

plt.ylabel(
    "Latitude"
)

plt.title(
    "SpillTrace - AIS vs Modeled Oil Origin"
)

plt.grid(
    True,
    alpha=0.3
)

plt.legend()

plt.tight_layout()

plt.savefig(
    MAP_FILE,
    dpi=200
)

plt.show()


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 75)
print("PHASE 5.1 COMPLETE")
print("=" * 75)

print("\nSaved:")

print(
    CANDIDATE_FILE
)

print(
    RESULT_FILE
)

print(
    MAP_FILE
)