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

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch join_roms_outputs.slurm EXP_NAME"
    exit 1
fi

# Run the Python script with the experiment name
srun -n 1 python join.py $EXP_NAME

