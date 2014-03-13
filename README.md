# Hivemind
Aggregator for Bee-hive Health

## Overview
HiveMind allows any amateur bee-keeper to monitor their hives in real-time.

## Setup
To install all dependencies for the system, run the following:

    chmod +x install.sh
    ./install.sh
    
## To Run
The HiveNode daemon will start on boot, via /etc/rc.local, but can be executed
manually from the git repository:

    sudo python HiveNode.py

## Data Folder
CSV-files and json files are temporarily stored here.
* Files in this directory are ignored by git

## Static Folder
Served files are kept here
    

