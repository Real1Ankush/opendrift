from pathlib import Path
import json
import pandas as pd
import numpy as np


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

OUTPUT_DIR = (
    BASE
    / "AIS"
    / "phase5_output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "ais_synthetic_2026.csv"
)


# ============================================================
# LOAD ACTUAL PHASE 4.4 RESULT
# ============================================================

print("=" * 75)
print("PHASE 5.2 - SYNTHETIC AIS GENERATION")
print("=" * 75)

with open(
    ORIGIN_FILE,
    "r"
) as f:

    result = json.load(f)


spill = result["spill_detection"]

origin = result["candidate_origin"]

region = result["region_50_percent"]


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

region_lat_min = float(
    region["latitude_min"]
)

region_lat_max = float(
    region["latitude_max"]
)

region_lon_min = float(
    region["longitude_min"]
)

region_lon_max = float(
    region["longitude_max"]
)


print("\nUsing actual Phase 4.4 result:")

print(
    f"Candidate origin: "
    f"{origin_lat:.6f}, "
    f"{origin_lon:.6f}"
)

print(
    f"Spill time: {spill_time}"
)


# ============================================================
# HELPER
# ============================================================

rows = []


def add_vessel(
    mmsi,
    name,
    ship_type,
    start_lat,
    start_lon,
    end_lat,
    end_lon,
    start_time,
    hours,
    sog,
    cog
):

    lats = np.linspace(
        start_lat,
        end_lat,
        hours + 1
    )

    lons = np.linspace(
        start_lon,
        end_lon,
        hours + 1
    )

    for i in range(hours + 1):

        rows.append({

            "mmsi":
                mmsi,

            "vessel_name":
                name,

            "timestamp":
                start_time
                + pd.Timedelta(
                    hours=i
                ),

            "latitude":
                round(
                    lats[i],
                    6
                ),

            "longitude":
                round(
                    lons[i],
                    6
                ),

            "sog":
                sog,

            "cog":
                cog,

            "ship_type":
                ship_type
        })


# ============================================================
# TIME RANGE
# ============================================================

start_time = (
    spill_time
    - pd.Timedelta(
        hours=8
    )
)


# ============================================================
# VESSEL 1
# STRONG TRAJECTORY MATCH
# ============================================================

# Passes directly through the modeled
# origin region close to the spill time.

add_vessel(
    mmsi="700000001",
    name="Synthetic Alpha",
    ship_type="Tanker",

    start_lat=14.88,
    start_lon=87.72,

    end_lat=15.04,
    end_lon=88.08,

    start_time=start_time,
    hours=8,

    sog=9.5,
    cog=60.0
)


# ============================================================
# VESSEL 2
# NEARBY BUT POORER SPATIAL MATCH
# ============================================================

add_vessel(
    mmsi="700000002",
    name="Synthetic Bravo",
    ship_type="Cargo",

    start_lat=14.65,
    start_lon=88.35,

    end_lat=14.85,
    end_lon=88.55,

    start_time=start_time,
    hours=8,

    sog=11.5,
    cog=135.0
)


# ============================================================
# VESSEL 3
# PASSES THROUGH REGION
# BUT AT A DIFFERENT TIME / WEAKER MATCH
# ============================================================

add_vessel(
    mmsi="700000003",
    name="Synthetic Charlie",
    ship_type="Tanker",

    start_lat=15.10,
    start_lon=87.80,

    end_lat=14.90,
    end_lon=88.12,

    start_time=(
        spill_time
        - pd.Timedelta(
            hours=12
        )
    ),

    hours=8,

    sog=7.0,
    cog=220.0
)


# ============================================================
# VESSEL 4
# COMPLETELY IRRELEVANT
# ============================================================

add_vessel(
    mmsi="700000004",
    name="Synthetic Delta",
    ship_type="Cargo",

    start_lat=13.50,
    start_lon=86.00,

    end_lat=13.80,
    end_lon=86.30,

    start_time=start_time,
    hours=8,

    sog=13.0,
    cog=45.0
)


# ============================================================
# VESSEL 5
# SLOW VESSEL NEAR ORIGIN
# ============================================================

add_vessel(
    mmsi="700000005",
    name="Synthetic Echo",
    ship_type="Tanker",

    start_lat=14.94,
    start_lon=87.95,

    end_lat=14.98,
    end_lon=87.99,

    start_time=start_time,
    hours=8,

    sog=1.5,
    cog=50.0
)


# ============================================================
# SAVE
# ============================================================

df = pd.DataFrame(
    rows
)

df = (
    df
    .sort_values(
        [
            "mmsi",
            "timestamp"
        ]
    )
    .reset_index(
        drop=True
    )
)


df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("SYNTHETIC AIS CREATED")
print("=" * 75)

print(
    f"\nObservations: "
    f"{len(df)}"
)

print(
    f"Vessels: "
    f"{df['mmsi'].nunique()}"
)

print(
    f"Time range:"
)

print(
    f"{df['timestamp'].min()}"
    f" → "
    f"{df['timestamp'].max()}"
)

print(
    "\nVessels:"
)

for (
    mmsi,
    vessel
) in df.groupby("mmsi"):

    print(
        f"{mmsi} - "
        f"{vessel['vessel_name'].iloc[0]} - "
        f"{vessel['ship_type'].iloc[0]}"
    )


print("\nSaved:")

print(
    OUTPUT_FILE
)


print("\nIMPORTANT:")

print(
    "This AIS dataset is SYNTHETIC."
)

print(
    "It exists only to validate the "
    "SpillTrace Phase 5 pipeline."
)