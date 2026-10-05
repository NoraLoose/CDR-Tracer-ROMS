#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q debug
#SBATCH -t 00:30:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=carbonate_sens
#SBATCH --output=logs/carbonate_sens_%j.out
#SBATCH --error=logs/carbonate_sens_%j.err

# Load modules
module load conda
conda activate deficit-tracer

# Run the script with dynamic arguments
python compute_carbonate_sensitivity_from_monthly_ctrl.py --year 2002

