import sys
from pathlib import Path
import xarray as xr
from sensitivities import CONTROL_DIR

if len(sys.argv) != 2:
    sys.exit("Usage: extract.py EXP_NAME")

exp_name = sys.argv[1]

# Raw ROMS/MARBL control-run output (large, lives on purgeable scratch).
# This is a separate location from sensitivities.CONTROL_DIR (archived,
# persistent project storage), which is where the extracted surface
# fields below get written.
CONTROL_RUN_RAW_DIR = Path("/path/to/scratch/pacific/roms_marbl_dic")

# Directories
input_dir = CONTROL_RUN_RAW_DIR / exp_name / "OUTPUT/JOINED"
output_dir = CONTROL_DIR / "expCTRL" / "SURFACE"
output_dir.mkdir(parents=True, exist_ok=True)

groups = ["pacmed_bgc", "pacmed_his"]
vars_to_keep = ["temp", "salt", "ALK_ALT_CO2", "DIC_ALT_CO2", "PO4", "SiO3", "ocean_time"]

for group in groups:
    # Collect all joined NetCDF files for this group
    files = sorted(input_dir.glob(f"{group}.*.nc"))

    for infile in files:
        outfile = output_dir / infile.name
        if outfile.exists():
            print(f"[SKIP] {outfile} already exists")
            continue

        print(f"[FILTER] {infile} -> {outfile}")
        with xr.open_dataset(infile) as ds:
            keep_vars = [v for v in vars_to_keep if v in ds.variables]
            filtered = ds[keep_vars].isel(s_rho=-1).load()  # ensure data is in memory before writing
            filtered.to_netcdf(outfile)

print("[DONE] All files filtered.")

