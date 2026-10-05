import sys
from pathlib import Path
import fnmatch
import xarray as xr

if len(sys.argv) != 3:
    sys.exit("Usage: python join_roms_outputs.py EXP_NAME dor|oae")

exp_name = sys.argv[1]
mode = sys.argv[2].lower()

if mode not in {"dor", "oae"}:
    sys.exit("Second argument must be 'dor' or 'oae'")

exp_name = sys.argv[1]

# Directories
base_dir = Path("/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/roms")
input_dir = base_dir / exp_name / f"OUTPUT_{mode}/JOINED"
output_dir = Path("../") / exp_name / f"OUTPUT_{mode}" / "JOINED"
output_dir.mkdir(parents=True, exist_ok=True)

groups = ["pacmed_his"]
vars_to_keep = ["zeta", "*_CONSERVED", "*_DEFICIT", "*_OAE_DEF", "ocean_time"]

for group in groups:
    files = sorted(input_dir.glob(f"{group}.*.nc"))
    if not files:
        print(f"[WARN] No files found for group '{group}' in {input_dir}")
        continue

    for infile in files:
        outfile = output_dir / infile.name
        if outfile.exists():
            print(f"[SKIP] {outfile} already exists")
            continue

        print(f"[FILTER] {infile} -> {outfile}")
        with xr.open_dataset(infile) as ds:
            # Match variables using wildcards
            keep_vars = [
                v for v in ds.variables
                if any(fnmatch.fnmatch(v, pattern) for pattern in vars_to_keep)
            ]

            if not keep_vars:
                print(f"[WARN] No matching variables found in {infile}")
                continue

            filtered = ds[keep_vars].load()  # load before writing
            filtered.to_netcdf(outfile)

print("[DONE] All files filtered.")
