#!/bin/bash
#SBATCH -A <account>
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 10:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=carbonate_sens
#SBATCH --output=logs/carbonate_sens_%j.out
#SBATCH --error=logs/carbonate_sens_%j.err

# Load modules
module load conda
conda activate cdr-tracer-roms

# Run the script with dynamic arguments
python compute_carbonate_sensitivity_ctrl.py --year 2000 --months 10 11 12

