#!/bin/bash

#add any installation dependency in this file 

#following commands are used to install lighthouse
apt-get install curl
# get install script and pass it to execute: 
curl -sL https://deb.nodesource.com/setup_12.x | bash
# and install node 
apt-get install nodejs
# confirm that it was successful 
node -v
# npm installs automatically 
npm -v
npm install -g yarn
yarn add lighthouse
npm install -g rwlock

#collect resources
python3 analysis/resourceCollector.py

#start running SubRosa now

# collect lighthouse tests (this script and SubRosa should run simultaneously)
python3 analysis/runTests.py

