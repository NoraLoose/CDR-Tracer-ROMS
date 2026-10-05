#!/usr/bin/env python3
import sys
import glob as glob_module
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import xarray as xr
from dask.diagnostics import ProgressBar
from roms_tools import Grid, ROMSOutput


def _is_readable(path: str) -> bool:
    """Return False if the file cannot be opened (e.g. HDF corruption)."""
    try:
        ds = xr.open_dataset(path, engine="netcdf4")
        ds.close()
        return True
    except Exception:
        return False

# List of tracer locations
LOCS = ["VI7", "VI8", "VI10", "BC7", "BC8", "BC10", "EC7", "EC8", "EC10", "JP7", "JP8", "JP10"]

def integrate_output(exp: str, mode: str, year: str, month: str) -> None:
    """
    Integrate ROMS output vertically and horizontally for each location,
    writing a single monthly file.

    Parameters
    ----------
    exp : str
        Experiment ID or name (e.g. "0", "A1", etc.)
    mode: str
        oae or dor
    year : str
        Year of the output files (e.g. "2000")
    month : str
        Month of the output files (e.g. "02")
    """
    grid_file = Path("../../INPUT/pacmed12_grd.nc")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    input_dir = Path(f"../exp{exp}/OUTPUT_{mode}/JOINED")
    output_dir = Path(f"../exp{exp}/OUTPUT_{mode}/INTEGRATED")
    output_dir.mkdir(exist_ok=True, parents=True)

    output_file = output_dir / f"integrated.{year}{month}.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists")
        return
    else:
        print(f"[PROCESS] Creating {output_file}")

    # Probe each file; skip any that cannot be opened.
    all_files = sorted(glob_module.glob(str(input_dir / f"pacmed_his.{year}{month}*.nc")))
    good_files, bad_in_month = [], []
    for f in all_files:
        if _is_readable(f):
            good_files.append(f)
        else:
            bad_in_month.append(f)
            print(f"[WARN] Unreadable file: {f} — will insert NaN for that timestamp")

    if not good_files:
        print(f"[ERROR] No good files for {year}{month}, cannot integrate.")
        return

    # Open ROMS output for the month (good files only)
    roms_output = ROMSOutput(
        grid=grid,
        path=good_files,
        use_dask=True
    )

    # Compute depth and layer thickness
    roms_output._get_depth_coordinates(depth_type="interface", locations=["rho"])
    roms_output.ds["h_rho"] = (
        -roms_output.ds_depth_coords["interface_depth_rho"]
        .diff("s_w")
        .rename({"s_w": "s_rho"})
    )

    area = 1 / grid.ds.pm / grid.ds.pn
    ds = roms_output.ds
    ds_integrated = xr.Dataset()

    for loc in LOCS:
        print(f"[INFO] Processing {loc}")
        with ProgressBar():
            for var_suffix in ["CONSERVED", "DEFICIT", "OAE_DEF"]:
                var_name = f"{loc}_{var_suffix}"
                ds_var = ds.get(var_name)
                if ds_var is not None:
                    ds_integrated[f"{loc}_{var_suffix.lower()}"] = (
                        (ds_var * ds["h_rho"] * area)
                        .sum(dim=["s_rho", "eta_rho", "xi_rho"])
                        .compute()
                    )
                else:
                    print(f"[WARNING] Variable {var_name} not found, skipping.")

    # Insert NaN rows for bad files, inferring ocean_time from filenames.
    if bad_in_month:
        # Detect the actual time dimension name (may be 'ocean_time' or 'time').
        time_dim = next(iter(ds_integrated.dims))

        # Parse timestamps from bad filenames.
        ref = datetime(1995, 1, 1, tzinfo=timezone.utc)
        nan_datetimes = []
        for bf in bad_in_month:
            stem = Path(bf).stem  # e.g. "pacmed_his.20010925113008"
            ts_str = stem.split(".")[-1]  # "20010925113008"
            ts = datetime(
                int(ts_str[0:4]), int(ts_str[4:6]), int(ts_str[6:8]),
                int(ts_str[8:10]), int(ts_str[10:12]), int(ts_str[12:14]),
                tzinfo=timezone.utc,
            )
            nan_datetimes.append(ts)

        # Match the dtype of the existing time coordinate (datetime64 or float).
        time_values = ds_integrated[time_dim].values
        if np.issubdtype(time_values.dtype, np.datetime64):
            nan_times = np.array(nan_datetimes, dtype=time_values.dtype)
        else:
            nan_times = np.array([(ts - ref).total_seconds() for ts in nan_datetimes])

        nan_ds = xr.Dataset(
            {
                var: xr.DataArray(
                    np.full(len(nan_times), np.nan),
                    dims=[time_dim],
                    coords={time_dim: (time_dim, nan_times)},
                )
                for var in ds_integrated.data_vars
            }
        )
        # Preserve time attributes from the integrated dataset.
        nan_ds[time_dim].attrs = ds_integrated[time_dim].attrs
        ds_integrated = xr.concat([ds_integrated, nan_ds], dim=time_dim).sortby(time_dim)

    ds_integrated.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main():
    """Command-line interface: run over multiple months if requested."""
    if len(sys.argv) < 4:
        sys.exit("Usage: python integrate_output.py EXP dor|oae YEAR [MONTH1 MONTH2 ...]")

    exp = sys.argv[1]
    mode = sys.argv[2].lower()
    year = sys.argv[3]
    months = sys.argv[4:] or [f"{m:02d}" for m in range(1, 13)]

    for month in months:
        integrate_output(exp, mode, year, month)


if __name__ == "__main__":
    main()

