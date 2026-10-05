#!/usr/bin/env python3
import argparse
from pathlib import Path
import xarray as xr
from roms_tools import Grid, ROMSOutput


def process(grid: Grid, exp_dir: Path, year: str) -> None:
    out_dir = exp_dir / "MAX_PH"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_file = out_dir / f"max_ph_{year}.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] Computing max pH for {exp_dir.name}, year={year}...")

    roms_output = ROMSOutput(
        grid=grid,
        path=str(exp_dir / f"JOINED/pacmed_bgc_dia.{year}*.nc"),
        use_dask=True,
    )
    ds = roms_output.ds

    ph = ds["PH"]
    ph_alt = ds["PH_ALT_CO2"]

    # Restart timesteps have PH == 0 everywhere due to a model bug; mask them out
    is_restart = ph.max(dim=["eta_rho", "xi_rho"]) == 0
    ph = ph.where(~is_restart)
    ph_alt = ph_alt.where(~is_restart)

    max_ph = ph.max(dim=["eta_rho", "xi_rho"])
    max_delta_ph = (ph - ph_alt).max(dim=["eta_rho", "xi_rho"])

    ds_out = xr.Dataset(
        {
            "max_ph": max_ph,
            "max_delta_ph": max_delta_ph,
        }
    )
    ds_out.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute max pH time series.")
    parser.add_argument("--exp", required=True, help="Experiment name (e.g., JP8)")
    parser.add_argument("--year", required=True, help="Year (YYYY)")
    args = parser.parse_args()

    exp_dir = Path(f"../exp{args.exp}/OUTPUT/")
    grid_file = Path("../../INPUT/pacmed12_grd.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    process(grid, exp_dir, args.year)


if __name__ == "__main__":
    main()
