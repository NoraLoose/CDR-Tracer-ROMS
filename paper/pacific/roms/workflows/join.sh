#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 48:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 32
#SBATCH -J join-roms
#SBATCH -o logs/join-roms.%j.out
#SBATCH -e logs/join-roms.%j.err

# Load conda module
module load conda
conda activate romstools-test

# The experiment name comes from the first sbatch argument
EXP_NAME=$1
MODE=$2   # dor or oae

if [ -z "$EXP_NAME" ] || [ -z "$MODE" ]; then
    echo "Usage: sbatch join_roms_outputs.slurm EXP_NAME dor|oae"
    exit 1
fi

# Run the Python script
srun -n 1 python join.py "$EXP_NAME" "$MODE"

