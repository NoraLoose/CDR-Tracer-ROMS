#!/bin/bash
#SBATCH -A ees250133
#SBATCH --job-name=join_roms
#SBATCH --output=logs/join_roms_%j.out
#SBATCH --error=logs/join_roms_%j.err
#SBATCH --mem=64G
#SBATCH --time=48:00:00

# Load conda module
module load conda
conda activate romstools-test

# The experiment name comes from the first sbatch argument
EXP_NAME=$1

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch join.slurm EXP_NAME"
    exit 1
fi

# Run the Python script with the experiment name
srun -n 1 python join_anvil.py $EXP_NAME

