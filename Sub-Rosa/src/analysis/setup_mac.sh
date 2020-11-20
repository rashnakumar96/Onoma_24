#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

conda env create -q -f environment_mac.yml --prefix $DIR/envs
npm install