#!/bin/bash

# Find the latest directory
LogDir=$(ls -td C:/Users/96446/Documents/GitHub/data/mmkg/dump/0403-EA_exp/MCLEA_FBDB15K_0.2_seed_42/tensorboard/* | head -n 1)
echo "TensorBoard LogDir: $LogDir"
tensorboard --logdir="$LogDir" --port 6006 &