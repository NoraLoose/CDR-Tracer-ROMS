import sys
from pathlib import Path
from roms_tools import join_netcdf

if len(sys.argv) != 3:
    sys.exit("Usage: python join_roms_outputs.py EXP_NAME dor|oae")

exp_name = sys.argv[1]
mode = sys.argv[2].lower()

if mode not in {"dor", "oae"}:
    sys.exit("Second argument must be 'dor' or 'oae'")

# Directories
base_dir = Path("/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/roms")
input_dir = base_dir / exp_name / f"OUTPUT_{mode}"
output_dir = input_dir / "JOINED"
output_dir.mkdir(exist_ok=True)

groups = ["pacmed_his"]

for group in groups:
    # Collect unique prefixes (everything except the last 3-digit tile index and extension)
    prefixes = sorted({
        ".".join(f.name.split(".")[:-2])
        for f in input_dir.glob(f"{group}.*.???.nc")
    })

    print(f"[INFO] Found {len(prefixes)} '{group}' tiled outputs to join in {input_dir}")

    for prefix in prefixes:
        joined_file = output_dir / f"{prefix}.nc"  # Remove the .### tile index in output
        if joined_file.exists():
            print(f"[SKIP] {joined_file} already exists")
            continue

        pattern = str(input_dir / f"{prefix}.???.nc")  # Match all tiles
        print(f"[JOIN] {prefix} -> {joined_file}")

        joined_path = join_netcdf(pattern)
        Path(joined_path).rename(joined_file)

print("[DONE] All files joined.")
