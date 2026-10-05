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
source /anvil/projects/x-ees250129/x-nloose/DeficitTracer/.ROMSMARBL_anvil

# ----------------------
# Configuration and Checks
# ----------------------

# Ensure exactly two arguments are given
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <EXPERIMENT_DIR> <RESTART_TIME>"
  exit 1
fi

EXPERIMENT_DIR="$1"
RESTART_TIME="$2"

PACIFIC_PATH="/anvil/scratch/x-nloose/DeficitTracer/experiments/pacific/"
BASE_PATH="$PACIFIC_PATH/roms_marbl_alk/"
TARGET_DIR="$BASE_PATH/$EXPERIMENT_DIR"

# Print job info
echo "Starting ROMS run in directory: $TARGET_DIR"
echo "Restart time: $RESTART_TIME"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on $(hostname) with $(nproc) CPUs"

mkdir -p "$TARGET_DIR/OUTPUT"

# ----------------------
# Environment Setup
# ----------------------

# Copy executable into target dir
cp code/roms "$TARGET_DIR/roms"

# Copy MARBL input and configuration files
for f in marbl_in marbl_diagnostic_output_list marbl_tracer_output_list; do
    if [ -f "$f" ]; then
        cp "$f" "$TARGET_DIR/"
    else
        echo "Warning: $f not found in current directory"
    fi
done

# Generate input file inside target dir, replacing both placeholders
sed \
  -e "s|\$TARGET_DIR|$TARGET_DIR|g" \
  -e "s|\$BASE_PATH|$BASE_PATH|g" \
  -e "s|\$PACIFIC_PATH|$PACIFIC_PATH|g" \
  -e "s|\$RESTART_TIME|$RESTART_TIME|g" \
  pacmed12km_restart_Y2000-2005.in.template > "$TARGET_DIR/roms.in"

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
