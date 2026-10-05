#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular 
#SBATCH -t 4:00:00
#SBATCH -J extract
#SBATCH -o logs/extract.%j.out
#SBATCH -e logs/extract.%j.err

# Load conda module
module load conda
conda activate romstools-test

# The experiment name comes from the first sbatch argument
EXP_NAME=$1

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch extract.slurm EXP_NAME"
    exit 1
fi

# Run the Python script with the experiment name
srun -n 1 python extract.py $EXP_NAME

