from datetime import timedelta
import json
import xarray as xr

from opendrift.readers import reader_netCDF_CF_generic
from opendrift.models.openoil import OpenOil


# ==================================================
# 1. CREATE OPENOIL MODEL
# ==================================================

oil = OpenOil(loglevel=20)


# ==================================================
# 2. LOAD ENVIRONMENTAL DATA
# ==================================================

data_folder = r"D:\Opendrift\test_data\16Nov2015_NorKyst_z_surface"

reader_arome = reader_netCDF_CF_generic.Reader(
    data_folder + r"\arome_subset_16Nov2015.nc"
)

reader_norkyst = reader_netCDF_CF_generic.Reader(
    data_folder + r"\norkyst800_subset_16Nov2015.nc"
)

oil.add_reader([
    reader_norkyst,
    reader_arome
])


# ==================================================
# 3. SEED VIRTUAL OIL PARTICLES
# ==================================================

spill_lon = 4.9
spill_lat = 60.1

oil.seed_elements(
    lon=spill_lon,
    lat=spill_lat,
    radius=3000,
    number=200,
    time=reader_arome.start_time,
    z=0,
    oil_type="HEIDRUN AARE 2023"
)


# ==================================================
# 4. RUN SIMULATION
# ==================================================

oil.run(
    steps=4 * 8,
    time_step=900,
    time_step_output=3600,
    outfile="oil_trajectory.nc"
)


# ==================================================
# 5. LOAD TRAJECTORY DATA
# ==================================================

ds = xr.open_dataset(
    "oil_trajectory.nc",
    decode_coords=False
)


lon = ds["lon"]
lat = ds["lat"]
status = ds["status"]
times = ds["time"]


# ==================================================
# 6. CALCULATE OIL-SLICK SUMMARY
# ==================================================

trajectory_summary = []


for i, time in enumerate(times.values):

    # Get all particles at this time
    current_lon = lon[:, i]
    current_lat = lat[:, i]
    current_status = status[:, i]

    # Remove invalid / missing coordinates
    valid = (
        current_lon.notnull()
        & current_lat.notnull()
    )

    current_lon = current_lon.where(valid, drop=True)
    current_lat = current_lat.where(valid, drop=True)

    # If no particles remain
    if len(current_lon) == 0:
        continue

    # ------------------------------------------------
    # Center of oil slick
    # ------------------------------------------------

    center_lon = float(current_lon.mean().values)
    center_lat = float(current_lat.mean().values)

    # ------------------------------------------------
    # Bounding box of oil slick
    # ------------------------------------------------

    min_lon = float(current_lon.min().values)
    max_lon = float(current_lon.max().values)

    min_lat = float(current_lat.min().values)
    max_lat = float(current_lat.max().values)

    # ------------------------------------------------
    # Number of particles
    # ------------------------------------------------

    particle_count = len(current_lon)

    # ------------------------------------------------
    # Store result
    # ------------------------------------------------

    result = {
        "time": str(time),
        "center": {
            "latitude": center_lat,
            "longitude": center_lon
        },
        "bounding_box": {
            "min_latitude": min_lat,
            "max_latitude": max_lat,
            "min_longitude": min_lon,
            "max_longitude": max_lon
        },
        "particle_count": particle_count
    }

    trajectory_summary.append(result)


# ==================================================
# 7. PRINT RESULTS
# ==================================================

print("\n")
print("=" * 70)
print("OIL SLICK MOVEMENT SUMMARY")
print("=" * 70)

for point in trajectory_summary:

    print("\nTime:", point["time"])

    print(
        "Center:",
        f'{point["center"]["latitude"]:.5f}, '
        f'{point["center"]["longitude"]:.5f}'
    )

    print(
        "Latitude range:",
        f'{point["bounding_box"]["min_latitude"]:.5f}',
        "→",
        f'{point["bounding_box"]["max_latitude"]:.5f}'
    )

    print(
        "Longitude range:",
        f'{point["bounding_box"]["min_longitude"]:.5f}',
        "→",
        f'{point["bounding_box"]["max_longitude"]:.5f}'
    )

    print(
        "Particles:",
        point["particle_count"]
    )


# ==================================================
# 8. SAVE SUMMARY AS JSON
# ==================================================

with open("oil_trajectory_summary.json", "w") as f:

    json.dump(
        trajectory_summary,
        f,
        indent=4
    )


print("\n")
print("=" * 70)
print("Saved: oil_trajectory_summary.json")
print("=" * 70)


# ==================================================
# 9. PLOT ORIGINAL OPENOIL TRAJECTORY
# ==================================================

oil.plot(fast=True)