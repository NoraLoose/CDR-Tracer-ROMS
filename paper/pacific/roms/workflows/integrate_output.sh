#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular 
#SBATCH -t 4:00:00
#SBATCH -J integrate
#SBATCH -o logs/integrate.%j.out
#SBATCH -e logs/integrate.%j.err
#SBATCH --cpus-per-task=1

# Load conda module
module load conda
conda activate romstools-test

# The experiment name comes from the first sbatch argument
EXP_NAME=$1
MODE=$2

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch extract.slurm EXP_NAME"
    exit 1
fi

# Run the Python script with the experiment name
srun -n 1 python integrate_output.py $EXP_NAME $MODE 2000
srun -n 1 python integrate_output.py $EXP_NAME $MODE 2001

