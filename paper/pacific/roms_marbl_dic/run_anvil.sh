#!/bin/bash
#SBATCH -A ees250133
#SBATCH --partition=wholenode
#SBATCH --time=48:00:00
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=128
#SBATCH --job-name=roms-run
#SBATCH --output=logs/roms_run_tmp_%j.out
#SBATCH --error=logs/roms_run_tmp_%j.err

export SLURM_CPUS_PER_TASK=1
export SLURM_TRES_PER_TASK=1

set -euo pipefail

# ----------------------
# Configuration and Checks
# ----------------------

# Ensure exactly one argument is given
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <TARGET_DIR>"
  exit 1
fi

PACIFIC_PATH="/anvil/scratch/x-nloose/DeficitTracer/experiments/pacific/"
BASE_PATH="$PACIFIC_PATH/roms_marbl_dic/"
TARGET_DIR="$BASE_PATH/$1"

# Print job info
echo "Starting ROMS run in directory: $TARGET_DIR"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on $(hostname) with $(nproc) CPUs"

mkdir -p "$TARGET_DIR/OUTPUT"

# ----------------------
# Environment Setup
# ----------------------

# Copy executable into target dir
cp code/roms "$TARGET_DIR/roms"

# Generate input file inside target dir
sed "s|\$TARGET_DIR|$TARGET_DIR|g; s|\$BASE_PATH|$BASE_PATH|g; s|\$PACIFIC_PATH|$PACIFIC_PATH|g" pacmed12km_Y2000-2005.in.template.shortened > "$TARGET_DIR/roms.in"

# ----------------------
# Model Execution
# ----------------------
cd "$TARGET_DIR"

echo "Launching ROMS..."
srun -n 640 ./roms ./roms.in > output.log

# ----------------------
# Move SLURM Logs
# ----------------------

mv "$SLURM_SUBMIT_DIR/roms_run_tmp_${SLURM_JOB_ID}.out" "roms_run_${SLURM_JOB_ID}.out"
mv "$SLURM_SUBMIT_DIR/roms_run_tmp_${SLURM_JOB_ID}.err" "roms_run_${SLURM_JOB_ID}.err"

echo "✅ ROMS run completed. Output written to $TARGET_DIR/output.log"
