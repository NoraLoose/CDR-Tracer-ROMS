#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 48:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=carbonate_sens
#SBATCH --output=logs/carbonate_sens_%j.out
#SBATCH --error=logs/carbonate_sens_%j.err

# Load modules
module load conda
conda activate deficit-tracer

# The experiment name comes from the first sbatch argument
EXP_NAME=$1

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch extract.slurm EXP_NAME"
    exit 1
fi

# Run the script with dynamic arguments
python compute_carbonate_sensitivity.py --exp $EXP_NAME --year 2000
python compute_carbonate_sensitivity.py --exp $EXP_NAME --year 2001

