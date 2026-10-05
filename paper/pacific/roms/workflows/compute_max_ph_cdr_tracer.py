#!/usr/bin/env python3
"""Spatial-max surface-pH time series from the CDR-tracer pH reconstruction.

Reads the daily, full-domain surface-pH files written by ``compute_pH.py``
(``roms/exp<EXP>/OUTPUT_<MODE>/pH/pH_<YYYYMM>.nc``, each holding ``pH_ctrl`` and
``pH_<exp>`` for every release experiment) and reduces them to small
per-experiment time series:

    max_ph_ctrl              max over (eta_rho, xi_rho) of pH_ctrl
    max_ph_<exp>             max over (eta_rho, xi_rho) of pH_<exp>
    max_delta_ph_<exp>       max over (eta_rho, xi_rho) of (pH_<exp> - pH_ctrl)
    max_delta_ph_lon_<exp>   grid longitude where that daily maximum occurs
    max_delta_ph_lat_<exp>   grid latitude  where that daily maximum occurs

One file per year, written to a ``MAX_PH/`` sibling of the ``pH/`` directory, so
it can be compared directly against the truth series produced by
``roms_marbl_dic/workflows/compute_max_ph.py``.
"""
import argparse
from pathlib import Path

import numpy as np
import xarray as xr
from roms_tools import Grid

SPATIAL_DIMS = ["eta_rho", "xi_rho"]


def _spatial_max_with_loc(da, lon_stacked, lat_stacked):
    """Return (daily max, lon at max, lat at max) reducing over the spatial dims.

    Land points are NaN in ``da``; fill them with -inf so ``argmax`` skips them.
    """
    stacked = da.stack(cell=SPATIAL_DIMS)
    idx = stacked.fillna(-np.inf).argmax("cell")

    def _bare(arr):
        # keep only the time-indexed values, dropping the stacked-cell identity
        return xr.DataArray(np.asarray(arr.isel(cell=idx).values), dims=["time"])

    return _bare(stacked), _bare(lon_stacked), _bare(lat_stacked)


def process_file(path, exps, lon_stacked, lat_stacked):
    ds = xr.open_dataset(path)
    ph_ctrl = ds["pH_ctrl"]

    out = {"max_ph_ctrl": ph_ctrl.max(dim=SPATIAL_DIMS)}
    for exp in exps:
        ph_exp = ds[f"pH_{exp}"]
        out[f"max_ph_{exp}"] = ph_exp.max(dim=SPATIAL_DIMS)

        vals, lon, lat = _spatial_max_with_loc(
            ph_exp - ph_ctrl, lon_stacked, lat_stacked
        )
        out[f"max_delta_ph_{exp}"] = vals
        out[f"max_delta_ph_lon_{exp}"] = lon
        out[f"max_delta_ph_lat_{exp}"] = lat

    ds_out = xr.Dataset(out).compute()
    ds.close()
    return ds_out


def process_year(pH_dir, out_dir, year, grid):
    out_file = out_dir / f"max_ph_{year}.nc"
    if out_file.exists():
        print(f"[SKIP] {out_file} already exists.")
        return

    files = sorted(pH_dir.glob(f"pH_{year}*.nc"))
    if not files:
        print(f"[WARN] no pH files for {year} in {pH_dir}")
        return

    ds0 = xr.open_dataset(files[0])
    exps = sorted(
        v[len("pH_"):] for v in ds0.data_vars
        if v.startswith("pH_") and v != "pH_ctrl"
    )
    ds0.close()
    print(f"[INFO] {year}: {len(files)} files, {len(exps)} experiments: {exps}")

    lon_stacked = grid.ds["lon_rho"].stack(cell=SPATIAL_DIMS)
    lat_stacked = grid.ds["lat_rho"].stack(cell=SPATIAL_DIMS)

    per_month = []
    for path in files:
        print(f"[PROCESS] {path.name}")
        per_month.append(process_file(path, exps, lon_stacked, lat_stacked))

    ds_out = xr.concat(per_month, dim="time")
    out_dir.mkdir(parents=True, exist_ok=True)
    ds_out.to_netcdf(out_file)
    print(f"[DONE] Saved {out_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute spatial-max CDR-tracer surface-pH time series."
    )
    parser.add_argument("--exp", default="0", help="ROMS experiment name (default: 0)")
    parser.add_argument("--mode", default="dor", help="dor | oae (default: dor)")
    parser.add_argument("--year", required=True, help="Year (YYYY)")
    args = parser.parse_args()

    outputs_dir = Path(f"../exp{args.exp}/OUTPUT_{args.mode}")
    pH_dir = outputs_dir / "pH"
    out_dir = outputs_dir / "MAX_PH"
    grid_file = Path("../../INPUT/pacmed12_grd.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    process_year(pH_dir, out_dir, args.year, grid)


if __name__ == "__main__":
    main()
