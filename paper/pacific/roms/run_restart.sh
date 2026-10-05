#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH --time=36:00:00
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=128
#SBATCH --job-name=roms-deficit
#SBATCH --output=logs/roms_run_tmp_%j.out
#SBATCH --error=logs/roms_run_tmp_%j.err

export SLURM_CPUS_PER_TASK=1
export SLURM_TRES_PER_TASK=1

set -euo pipefail

# ----------------------
# Configuration and Checks
# ----------------------
# Ensure exactly two arguments
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <TARGET_DIR> <dor|oae> <RESTART_TIME>"
  exit 1
fi

RUN_NAME="$1"
CODE_TYPE="$2"
RESTART_TIME="$3"

PACIFIC_PATH="/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/"
BASE_PATH="$PACIFIC_PATH/roms/"
TARGET_DIR="$BASE_PATH/$1"

# Print job info
echo "Starting ROMS run in directory: $TARGET_DIR"
echo "Restart time: $RESTART_TIME"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on $(hostname) with $(nproc) CPUs"


# Select code and output directories
case "$CODE_TYPE" in
  dor)
    CODE_DIR="code_dor"
    OUTPUT_DIR="OUTPUT_dor"
    ;;
  oae)
    CODE_DIR="code_oae"
    OUTPUT_DIR="OUTPUT_oae"
    ;;
  *)
    echo "ERROR: CODE_TYPE must be 'dor' or 'oae'"
    exit 1
    ;;
esac

mkdir -p "$TARGET_DIR/$OUTPUT_DIR"

# ----------------------
# Environment Setup
# ----------------------

# Copy executable into the code-type-specific output dir (not TARGET_DIR
# itself) so that dor and oae runs never share a binary/input file, even
# if they happen to run concurrently.
cp "$CODE_DIR/roms" "$TARGET_DIR/$OUTPUT_DIR/roms"

# Generate input file inside the code-type-specific output dir
sed -e "s|\$TARGET_DIR|$TARGET_DIR|g" \
    -e "s|\$BASE_PATH|$BASE_PATH|g" \
    -e "s|\$PACIFIC_PATH|$PACIFIC_PATH|g" \
    -e "s|\$OUTPUT_DIR|$OUTPUT_DIR|g" \
    -e "s|\$RESTART_TIME|$RESTART_TIME|g" \
    pacmed12km_restart_Y2000-2005.in.template > "$TARGET_DIR/$OUTPUT_DIR/roms.in"


# ----------------------
# Model Execution
# ----------------------
cd "$TARGET_DIR/$OUTPUT_DIR"

echo "Launching ROMS..."
srun -n 640 ./roms ./roms.in > output.log

# ----------------------
# Move SLURM Logs
# ----------------------

mv "$SLURM_SUBMIT_DIR/roms_run_tmp_${SLURM_JOB_ID}.out" "roms_run_${SLURM_JOB_ID}.out"
mv "$SLURM_SUBMIT_DIR/roms_run_tmp_${SLURM_JOB_ID}.err" "roms_run_${SLURM_JOB_ID}.err"

echo "✅ ROMS run completed. Output written to $TARGET_DIR/$OUTPUT_DIR/output.log"
