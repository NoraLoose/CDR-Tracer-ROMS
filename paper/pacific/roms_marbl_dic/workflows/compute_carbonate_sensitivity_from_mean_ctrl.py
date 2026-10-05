#!/usr/bin/env python3
import argparse
from pathlib import Path
import carbonate
import xarray as xr
from roms_tools import Grid

def process(grid: Grid, outputs_dir: Path) -> None:

    output_file = outputs_dir / f"../BETA/carbonate_sensitivity_from_mean_data.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] Computing carbonate sensitivity...")
    
    bgc_path = str(outputs_dir / f"pacmed_bgc.2000*.nc")
    phys_path = str(outputs_dir / f"pacmed_his.2000*.nc")
    ds_2000 = carbonate.load_bgc_phys(grid, bgc_path, phys_path)
    
    bgc_path = str(outputs_dir / f"pacmed_bgc.2001*.nc")
    phys_path = str(outputs_dir / f"pacmed_his.2001*.nc")
    ds_2001 = carbonate.load_bgc_phys(grid, bgc_path, phys_path)

    ds = xr.concat([ds_2000, ds_2001], dim="time")

    ds = ds.mean(dim="time")
    
    beta, eta = carbonate.compute_sensitivities(ds, ds, "ALK_ALT_CO2", "DIC_ALT_CO2")

    ds_carbonate_sensitivity = xr.Dataset(
        {
            "dDICdCO2": xr.DataArray(
                beta, dims=["eta_rho", "xi_rho"]
            ),
            "dDICdALK": xr.DataArray(
                eta, dims=["eta_rho", "xi_rho"]
            ),
        }
    )
    ds_carbonate_sensitivity.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")

def main() -> None:

    outputs_dir = Path(f"../expCTRL/SURFACE/")
    grid_file = Path(f"../expCTRL/pacmed12_grd.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    process(grid, outputs_dir)


if __name__ == "__main__":
    main()
