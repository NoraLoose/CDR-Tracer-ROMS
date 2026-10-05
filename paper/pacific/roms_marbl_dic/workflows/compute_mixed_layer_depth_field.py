#!/usr/bin/env python3
"""Precompute a monthly-climatology mixed layer depth (MLD) field over 2000-2001, over the full
domain, from the physics-only control run, used by ../../concentration_differences.ipynb.

Same MLD definition as compute_mixed_layer_depth.py (single-point time series): the deepest
level where the potential density anomaly (sigma0, from gsw) differs from the surface value by
less than 0.03 kg/m^3. Unlike that script, this computes a full 2D field rather than a single
point, over the whole domain (same footprint as compute_mean_surface_velocity.py's field) rather
than being restricted to each site's zoom box -- so panels built from it (plot_mld_map) fully
cover their zoom box with no missing corners, the way plot_mean_speed_map's do.

Rather than saving all 731 daily fields (which the notebook would then have to load and
groupby-average every time), each daily field is folded directly into a running per-calendar-month
sum/count as it's computed, so the output is just 12 fields (Jan..Dec, averaged across both 2000
and 2001) over the whole domain. The notebook can then plot the mean over any subset of months (a
single month, or all 12 for the overall climatological mean) with no further heavy computation.

Physics is unaffected by the passive tracer release, so this reuses expVI8's JOINED_full
history output as the control run (same as compute_mean_surface_velocity.py). This is a much
bigger job than compute_mixed_layer_depth.py (full vertical profile over ~1.2M ocean grid points,
per day, for 731 days) -- expect on the order of a day; run via compute_mixed_layer_depth_field.sh.
"""
import glob
from pathlib import Path

import gsw
import numpy as np
import xarray as xr
from roms_tools import Grid
from roms_tools.vertical_coordinate import compute_depth

DELTA_SIGMA0_THRESHOLD = 0.03  # kg/m^3, de Boyer Montegut-style density criterion


def daily_mld_field(his: xr.Dataset, grid: Grid, hc: float,
                     lon: np.ndarray, lat: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """MLD (m) field over the whole domain from one daily his file. NaN over land."""
    col = his[["temp", "salt", "zeta"]].isel(time=0).load()
    h = grid.ds.h

    depth = compute_depth(col.zeta, h, hc, grid.ds.Cs_r, grid.ds.sigma_r)
    depth = depth.transpose("eta_rho", "xi_rho", "s_rho").values
    temp = col.temp.transpose("eta_rho", "xi_rho", "s_rho").values
    salt = col.salt.transpose("eta_rho", "xi_rho", "s_rho").values

    p = gsw.p_from_z(-depth, lat[:, :, None])
    SA = gsw.SA_from_SP(salt, p, lon[:, :, None], lat[:, :, None])
    CT = gsw.CT_from_pt(SA, temp)
    sigma0 = gsw.sigma0(SA, CT)

    delta = np.abs(sigma0 - sigma0[:, :, -1:])
    mixed = delta < DELTA_SIGMA0_THRESHOLD
    mld = np.where(mixed, depth, -np.inf).max(axis=2)
    return np.where(mask, mld, np.nan).astype(np.float32)


def process(grid: Grid, hc: float, physics_dir: Path, years, output_file: Path) -> None:
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    lon = grid.ds.lon_rho.values
    lat = grid.ds.lat_rho.values
    mask = grid.ds.mask_rho.values.astype(bool)
    # Running per-calendar-month sum (land cells contribute 0, masked out at the end) and day
    # count, folded in day by day instead of keeping all 731 daily fields around.
    month_sum = {m: np.zeros(mask.shape, dtype=np.float64) for m in range(1, 13)}
    month_count = {m: 0 for m in range(1, 13)}

    files = sorted(
        f for year in years for f in glob.glob(str(physics_dir / f"pacmed_his.{year}*.nc"))
    )
    print(f"[PROCESS] {len(files)} daily files in {', '.join(years)}, "
          f"full domain ({mask.shape[0]}x{mask.shape[1]})...")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    def save(final):
        months = sorted(month_count)
        climatology = np.stack([
            np.where(mask, month_sum[m] / max(month_count[m], 1), np.nan) for m in months
        ])
        ds_out = xr.Dataset(
            {"mld": (("month", "eta_rho", "xi_rho"), climatology.astype(np.float32))},
            coords={
                "month": months,
                "n_days": ("month", [month_count[m] for m in months]),
                "lon": (("eta_rho", "xi_rho"), lon),
                "lat": (("eta_rho", "xi_rho"), lat),
            },
        )
        ds_out["mld"].attrs = {
            "long_name": "Monthly-climatology mixed layer depth (deepest level where "
                          f"|sigma0 - sigma0_surface| < {DELTA_SIGMA0_THRESHOLD} kg/m^3), "
                          "averaged over 2000-2001 within each calendar month",
            "units": "m",
        }
        target = output_file if final else output_file.with_suffix(".partial.nc")
        ds_out.to_netcdf(target, encoding={"mld": {"zlib": True, "complevel": 4}})
        if final:
            partial = output_file.with_suffix(".partial.nc")
            if partial.exists():
                partial.unlink()
            print(f"[DONE] Saved {target}")
        else:
            n_total = sum(month_count.values())
            print(f"[CHECKPOINT] Saved {target} ({n_total} days folded in so far)")

    # Checkpoint periodically (as a "*.partial.nc" file) so a job that times out or gets killed
    # partway through still leaves a usable, resumable-in-spirit partial climatology.
    checkpoint_every = 50
    for i, f in enumerate(files):
        his = xr.open_dataset(f)
        # ocean_time's "second" units attr isn't CF-standard ("seconds since ..."), so xarray
        # leaves it as a raw float rather than decoding it to datetime64 -- convert manually.
        seconds = float(his.ocean_time.isel(time=0).values)
        date = np.datetime64("1995-01-01") + np.timedelta64(int(seconds), "s")
        month = int(date.astype("datetime64[M]").astype(int) % 12) + 1

        field = daily_mld_field(his, grid, hc, lon, lat, mask)
        month_sum[month] += np.nan_to_num(field, nan=0.0)
        month_count[month] += 1
        his.close()

        if (i + 1) % 10 == 0:
            print(f"  ...{i + 1}/{len(files)}")
        if (i + 1) % checkpoint_every == 0:
            save(final=False)

    save(final=True)


def main() -> None:
    grid_file = Path("../../INPUT/pacmed12_grd.nc")
    physics_dir = Path("../expVI8/OUTPUT/JOINED_full/")
    output_file = Path("../expCTRL/MIXED_LAYER_DEPTH/FIELD/mld_field_climatology.nc")
    theta_s, theta_b, hc, N = 6.0, 6.0, 250.0, 100

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=theta_s, theta_b=theta_b, hc=hc, N=N)

    process(grid, hc, physics_dir, ["2000", "2001"], output_file)


if __name__ == "__main__":
    main()
