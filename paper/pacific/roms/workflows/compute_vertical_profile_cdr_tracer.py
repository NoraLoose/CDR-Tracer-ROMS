#!/usr/bin/env python3
"""Precompute the domain-total vertical profile of the *CDR tracer reconstruction* (the
deficit / conserved tracers carried in the control run) for one release site and date, the
counterpart to the *truth* profiles from
``roms_marbl_{dic,alk}/workflows/compute_vertical_profile.py``. Used by
``../../deltaDIC_deltaALK_vertical_profile.ipynb`` to compare truth vs. CDR tracer estimate.

The reconstruction fields live in the control run's history output:

    mode "dor":  -{exp}_DEFICIT   (roms/exp0/OUTPUT_dor)            -> dic_dor
    mode "oae":  -{exp}_OAE_DEF   (roms/exp0/OUTPUT_oae_perlmutter) -> dic_oae
                  {exp}_CONSERVED (roms/exp0/OUTPUT_oae_perlmutter) -> alk_oae

(signs chosen so the field equals the reconstructed delta-tracer, matching
``compute_deltas`` in deltaDIC_deltaALK.ipynb).

The vertical remap onto a fixed-depth grid is identical to the truth script: the model's
native s_rho levels are terrain-following, so the same s_rho index sits at different
physical depths in different water columns and summing "at index k" mixes depths. Instead we
build the cumulative (dz-weighted) column mass down to each sigma-layer interface, linearly
interpolate that cumulative mass -- in physical depth -- onto a fixed target depth grid, and
difference consecutive edges to get the mass per fixed-depth bin (a mass-conserving remap of
piecewise-constant sigma-layer data using only linear interpolation; mask_edges=True keeps a
column from contributing beyond its own local depth range). Finally sum over the horizontal
domain and divide by dz_target to give mmol/m.

The output netCDF layout mirrors the truth caches (same variable and depth-coordinate names)
so the notebook can load truth and reconstruction the same way.
"""
import argparse
from pathlib import Path

import numpy as np
import xarray as xr
import xgcm
from roms_tools import Grid
from roms_tools.vertical_coordinate import compute_depth

# mode -> control OUTPUT subdir, depth-coord name, and the (out_var, control_var, sign)
# reconstructions to write for that mode.
MODES = {
    "dor": {
        "subdir": "OUTPUT_dor",
        "depth_name": "depth_dor",
        "recons": [("dic_dor", "{exp}_DEFICIT", -1.0)],
    },
    "oae": {
        "subdir": "OUTPUT_oae_perlmutter",
        "depth_name": "depth_oae",
        "recons": [
            ("dic_oae", "{exp}_OAE_DEF", -1.0),
            ("alk_oae", "{exp}_CONSERVED", 1.0),
        ],
    },
}


def cell_area(grid: Grid) -> xr.DataArray:
    """Ocean cell area (m^2) at each horizontal grid point."""
    return (1 / (grid.ds.pm * grid.ds.pn)).where(grid.ds.mask_rho)


def layer_thickness(depth_w: xr.DataArray) -> xr.DataArray:
    """Local layer thickness (m) at each s_rho level, from interface depths on s_w."""
    return (depth_w.isel(s_w=slice(0, -1)) - depth_w.isel(s_w=slice(1, None))).rename(s_w="s_rho")


def domain_profile_on_depth_grid(
    grid: Grid,
    conc: xr.DataArray,
    depth_w: xr.DataArray,
    target_depth_edges: np.ndarray,
    dz_target: float,
) -> xr.DataArray:
    """Domain-total mmol/m profile of a tracer on a fixed-depth grid.

    See module docstring for the cumulative-mass / linear-interpolation approach.
    """
    dz = layer_thickness(depth_w)
    mass_per_layer = (conc * dz).drop_vars("s_rho", errors="ignore").rename(s_rho="s_w")

    # Cumulative mass (mmol/m^2) from the seafloor (0 at the bottom interface) up to each
    # sigma-layer interface -- decreases monotonically with depth, reaching the full column
    # total at the sea surface.
    cum_mass = mass_per_layer.cumsum(dim="s_w")
    cum_mass = xr.concat(
        [xr.zeros_like(cum_mass.isel(s_w=0)), cum_mass], dim="s_w"
    ).drop_vars("s_w", errors="ignore")
    # xr.concat keeps the two pieces' original chunks (size 1 + size N) instead of merging
    # them, but s_w must be a single chunk since it's a core dim for xgcm's transform below.
    cum_mass = cum_mass.chunk({"s_w": -1})

    xgrid = xgcm.Grid(
        grid.ds, coords={"s_w": {"center": "s_w"}}, periodic=False, autoparse_metadata=False
    )
    cum_mass_target = xgrid.transform(
        cum_mass,
        "s_w",
        target=target_depth_edges,
        target_data=depth_w.rename("depth"),
        method="linear",
        mask_edges=True,
    )
    bin_mass = -cum_mass_target.diff("depth")  # cumulative mass decreases with depth
    bin_mass = bin_mass.assign_coords(depth=0.5 * (target_depth_edges[:-1] + target_depth_edges[1:]))

    area = cell_area(grid)
    return (bin_mass * area).sum(dim=["eta_rho", "xi_rho"]) / dz_target


def process(
    grid: Grid,
    hc: float,
    mode: str,
    exp: str,
    date: str,
    ctrl_dir: Path,
    output_file: Path,
    dz_target: float = 5.0,
) -> None:
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    spec = MODES[mode]
    his_file = ctrl_dir / spec["subdir"] / f"JOINED/pacmed_his.{date}113008.nc"
    print(f"[PROCESS] {mode} {exp} @ {date}  <-  {his_file}")

    his = xr.open_dataset(his_file).isel(time=0)
    depth_w = compute_depth(his.zeta, grid.ds.h, hc, grid.ds.Cs_w, grid.ds.sigma_w)

    # Fixed-depth bin edges (m, positive down), with a small buffer above z=0 for locations
    # where zeta > 0, and spanning the full water column so no mass is lost off the bottom.
    target_depth_edges = np.arange(-5.0, float(grid.ds.h.max()) + dz_target, dz_target)

    # xgcm's transform turns each column's ~100 s_rho levels into len(target_depth_edges)
    # fixed-depth levels (thousands, for a domain with several-km-deep water), so a chunk
    # that's a comfortable size *before* the transform can be 1-2 orders of magnitude too
    # big *after* it. xarray's "auto" chunking only looks at the pre-transform array and
    # doesn't know about that expansion -- so size the chunks ourselves for a bounded
    # post-transform footprint instead.
    max_chunk_bytes = 64 * 1024**2  # ~64 MiB per chunk after the vertical transform
    n_depth = len(target_depth_edges) - 1
    chunk_side = max(1, int(np.sqrt(max_chunk_bytes / (n_depth * 8))))
    chunks = {"eta_rho": chunk_side, "xi_rho": chunk_side}
    depth_w = depth_w.chunk(chunks)

    ds_out = xr.Dataset()
    for out_var, ctrl_var_tmpl, sign in spec["recons"]:
        ctrl_var = ctrl_var_tmpl.format(exp=exp)
        if ctrl_var not in his:
            raise KeyError(f"{ctrl_var} not found in {his_file}")
        recon = (sign * his[ctrl_var]).chunk(chunks)
        ds_out[out_var] = domain_profile_on_depth_grid(
            grid, recon, depth_w, target_depth_edges, dz_target
        )

    ds_out[spec["depth_name"]] = ds_out["depth"]
    ds_out = ds_out.compute()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    ds_out.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute the domain-total vertical CDR-tracer-reconstruction inventory profiles."
    )
    parser.add_argument("--exp", required=True, help="Release site + amplitude (e.g. VI8)")
    parser.add_argument("--date", required=True, help="Release date (YYYYMMDD)")
    parser.add_argument(
        "--mode", default="both", choices=["dor", "oae", "both"],
        help="Which CDR scenario(s) to process (default: both)",
    )
    args = parser.parse_args()

    ctrl_dir = Path("../exp0")
    grid_file = Path("../../INPUT/pacmed12_grd.nc")
    theta_s, theta_b, hc, N = 6.0, 6.0, 250.0, 100

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=theta_s, theta_b=theta_b, hc=hc, N=N)

    modes = ["dor", "oae"] if args.mode == "both" else [args.mode]
    for mode in modes:
        output_file = (
            ctrl_dir / MODES[mode]["subdir"]
            / f"VERTICAL_PROFILE/vertical_profile_{args.exp}_{args.date}.nc"
        )
        process(grid, hc, mode, args.exp, args.date, ctrl_dir, output_file)


if __name__ == "__main__":
    main()
