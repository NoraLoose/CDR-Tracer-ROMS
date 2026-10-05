#!/usr/bin/env python3
import argparse
from pathlib import Path
import carbonate
import xarray as xr
from roms_tools import Grid

def process_month(grid: Grid, outputs_dir: Path, year: str, month: str):
    """Compute carbonate sensitivity for a single month."""
    output_file = outputs_dir / f"../BETA/carbonate_sensitivity_{year}{month}.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] Computing carbonate sensitivity for {year}-{month}...")

    bgc_path = str(outputs_dir / f"pacmed_bgc.{year}{month}*.nc")
    phys_path = str(outputs_dir / f"pacmed_his.{year}{month}*.nc")

    ds = carbonate.load_bgc_phys(grid, bgc_path, phys_path)

    beta, eta = carbonate.compute_sensitivities(ds, ds, "ALK_ALT_CO2", "DIC_ALT_CO2")

    ds_carbonate_sensitivity = xr.Dataset(
        {
            "ocean_time": ds["ocean_time"],
            "dDICdCO2": xr.DataArray(
                beta, dims=["time", "eta_rho", "xi_rho"]
            ),
            "dDICdALK": xr.DataArray(
                eta, dims=["time", "eta_rho", "xi_rho"]
            ),
        }
    )
    ds_carbonate_sensitivity.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Compute carbonate sensitivity for multiple months.")
    parser.add_argument("--year", required=True, help="Year (YYYY)")
    parser.add_argument("--months", nargs="+", default=[f"{m:02d}" for m in range(1, 13)], help="Months to process")
    parser.add_argument("--exp", default="CTRL", help="Experiment name")
    args = parser.parse_args()

    outputs_dir = Path(f"../exp{args.exp}/SURFACE/")
    grid_file = Path(f"../../INPUT/pacmed12_grd.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    for month in args.months:
        process_month(grid, outputs_dir, args.year, month)

if __name__ == "__main__":
    main()
