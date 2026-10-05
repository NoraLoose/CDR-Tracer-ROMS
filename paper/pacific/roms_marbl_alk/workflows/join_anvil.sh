#!/bin/bash
#SBATCH -A ees250133
#SBATCH --partition=wholenode
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=join-run
#SBATCH --output=logs/join_run_tmp_%j.out
#SBATCH --error=logs/join_run_tmp_%j.err

# Load conda module
module load conda
conda activate romstools-test

# The experiment name comes from the first sbatch argument
EXP_NAME=$1

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch join_roms_outputs.slurm EXP_NAME"
    exit 1
fi

# Run the Python script with the experiment name
srun -n 1 python join_anvil.py $EXP_NAME

