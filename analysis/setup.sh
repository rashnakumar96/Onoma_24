#!/bin/bash

conda env create -q -f environment.yml --prefix ./envs
conda activate subrosa_env
npm install