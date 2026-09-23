from datetime import timedelta
import json

import numpy as np
import xarray as xr

from opendrift.readers import reader_netCDF_CF_generic
from opendrift.models.openoil import OpenOil


# ============================================================
# CONFIGURATION
# ============================================================

# Observed oil spill location
spill_lat = 60.1
spill_lon = 4.9

# How far back should we trace?
lookback_hours = 8

# Number of virtual oil particles
number_of_particles = 200

# Estimated uncertainty around detected spill
spill_radius_m = 3000

# OpenDrift calculation timestep
time_step_seconds = 900


# ============================================================
# LOAD ENVIRONMENTAL DATA
# ============================================================

data_folder = (
    r"D:\Opendrift\test_data"
    r"\16Nov2015_NorKyst_z_surface"
)

reader_arome = reader_netCDF_CF_generic.Reader(
    data_folder + r"\arome_subset_16Nov2015.nc"
)

reader_norkyst = reader_netCDF_CF_generic.Reader(
    data_folder + r"\norkyst800_subset_16Nov2015.nc"
)


# ============================================================
# CHECK AVAILABLE ENVIRONMENTAL TIME
# ============================================================

print("\n" + "=" * 70)
print("AVAILABLE ENVIRONMENT DATA")
print("=" * 70)

print("AROME:")
print("Start:", reader_arome.start_time)
print("End  :", reader_arome.end_time)

print("\nNorKyst:")
print("Start:", reader_norkyst.start_time)
print("End  :", reader_norkyst.end_time)


# ============================================================
# CHOOSE OBSERVATION TIME
# ============================================================

# For this test we use the latest time available
# in the environmental dataset.

spill_time = min(
    reader_arome.end_time,
    reader_norkyst.end_time
)

origin_time = spill_time - timedelta(
    hours=lookback_hours
)


# ============================================================
# VERIFY TIME RANGE
# ============================================================

reader_start = max(
    reader_arome.start_time,
    reader_norkyst.start_time
)

if origin_time < reader_start:

    raise ValueError(
        "\nThe requested lookback goes outside "
        "the available environmental data.\n\n"
        f"Environmental data starts at: {reader_start}\n"
        f"Requested origin time:          {origin_time}\n"
        f"Lookback:                       {lookback_hours} hours"
    )


# ============================================================
# DISPLAY EVENT INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("BACKWARD OIL-SPILL EVENT")
print("=" * 70)

print(f"Spill latitude  : {spill_lat}")
print(f"Spill longitude : {spill_lon}")

print(f"\nSpill time      : {spill_time}")
print(f"Origin time     : {origin_time}")
print(f"Lookback        : {lookback_hours} hours")


# ============================================================
# CREATE OPENOIL MODEL
# ============================================================

oil = OpenOil(loglevel=20)

oil.add_reader([
    reader_norkyst,
    reader_arome
])


# ============================================================
# SEED OIL AT OBSERVED SPILL
# ============================================================

oil.seed_elements(
    lon=spill_lon,
    lat=spill_lat,
    radius=spill_radius_m,
    number=number_of_particles,
    time=spill_time,
    z=0,
    oil_type="HEIDRUN AARE 2023"
)


# ============================================================
# BACKWARD SIMULATION
# ============================================================

print("\n" + "=" * 70)
print("RUNNING BACKWARD SIMULATION")
print("=" * 70)

oil.run(
    end_time=origin_time,
    time_step=-time_step_seconds,
    time_step_output=3600,
    outfile="oil_backward_2_1.nc"
)


# ============================================================
# LOAD TRAJECTORY
# ============================================================

ds = xr.open_dataset(
    "oil_backward_2_1.nc",
    decode_coords=False
)

lon = ds["lon"]
lat = ds["lat"]
times = ds["time"]


# ============================================================
# DISPLAY SIMULATION TIME
# ============================================================

print("\n" + "=" * 70)
print("SIMULATION TIME")
print("=" * 70)

for t in times.values:
    print(t)


# ============================================================
# GET EARLIEST TIME = CANDIDATE ORIGIN
# ============================================================

origin_lon = lon[:, -1].values
origin_lat = lat[:, -1].values


# Remove NaN values
valid = (
    np.isfinite(origin_lon)
    & np.isfinite(origin_lat)
)

origin_lon = origin_lon[valid]
origin_lat = origin_lat[valid]


print("\n" + "=" * 70)
print("ORIGIN PARTICLE CLOUD")
print("=" * 70)

print("Valid particles:", len(origin_lon))

print(
    f"Latitude range  : "
    f"{origin_lat.min():.5f} → {origin_lat.max():.5f}"
)

print(
    f"Longitude range : "
    f"{origin_lon.min():.5f} → {origin_lon.max():.5f}"
)


# ============================================================
# SIMPLE CENTER
# ============================================================

mean_lat = float(np.mean(origin_lat))
mean_lon = float(np.mean(origin_lon))

median_lat = float(np.median(origin_lat))
median_lon = float(np.median(origin_lon))


print("\nSimple mean center:")
print(f"Latitude  : {mean_lat:.5f}")
print(f"Longitude : {mean_lon:.5f}")

print("\nMedian center:")
print(f"Latitude  : {median_lat:.5f}")
print(f"Longitude : {median_lon:.5f}")


# ============================================================
# FIND HIGHEST-DENSITY REGION
# ============================================================

# Divide the origin particle cloud into a grid.
# The grid cell containing the most particles
# represents the highest-density candidate region.

grid_size = 10

hist, lat_edges, lon_edges = np.histogram2d(
    origin_lat,
    origin_lon,
    bins=grid_size
)


# Find cell containing the largest number of particles
max_index = np.unravel_index(
    np.argmax(hist),
    hist.shape
)

lat_index = max_index[0]
lon_index = max_index[1]


# Center of highest-density cell
density_lat = (
    lat_edges[lat_index]
    + lat_edges[lat_index + 1]
) / 2

density_lon = (
    lon_edges[lon_index]
    + lon_edges[lon_index + 1]
) / 2


particles_in_cell = int(
    hist[lat_index, lon_index]
)


# ============================================================
# DENSITY RESULT
# ============================================================

print("\n" + "=" * 70)
print("HIGHEST-DENSITY ORIGIN REGION")
print("=" * 70)

print(
    f"Latitude  : {density_lat:.5f}"
)

print(
    f"Longitude : {density_lon:.5f}"
)

print(
    f"Particles in region : {particles_in_cell}"
)


# ============================================================
# CREATE JSON RESULT
# ============================================================

result = {

    "spill": {
        "latitude": spill_lat,
        "longitude": spill_lon,
        "time": str(spill_time)
    },

    "simulation": {
        "lookback_hours": lookback_hours,
        "origin_time": str(origin_time),
        "particles": number_of_particles
    },

    "origin_region": {

        "mean_center": {
            "latitude": mean_lat,
            "longitude": mean_lon
        },

        "median_center": {
            "latitude": median_lat,
            "longitude": median_lon
        },

        "bounds": {
            "min_latitude": float(origin_lat.min()),
            "max_latitude": float(origin_lat.max()),
            "min_longitude": float(origin_lon.min()),
            "max_longitude": float(origin_lon.max())
        },

        "highest_density_point": {
            "latitude": float(density_lat),
            "longitude": float(density_lon),
            "particles": particles_in_cell
        }
    }
}


# ============================================================
# SAVE JSON
# ============================================================

with open(
    "backward_origin_2_1.json",
    "w"
) as f:

    json.dump(
        result,
        f,
        indent=4
    )


print("\n" + "=" * 70)
print("RESULT SAVED")
print("=" * 70)

print("oil_backward_2_1.nc")
print("backward_origin_2_1.json")


# ============================================================
# PLOT
# ============================================================

oil.plot(
    fast=True
)