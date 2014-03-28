# HiveNode
A HiveNode is a wireless linux device for remotely monitoring beehive health.
With HiveNode, any amateur bee-keeper can monitor their hives in real-time.

## Setup (DEBIAN)
To install all dependencies for the HiveNode, run the following:

    chmod +x install.sh
    ./install.sh
    
## To Run
The HiveNode daemon will start on boot, via /etc/rc.local, but can be executed
manually from the git repository:

    sudo python HiveNode.py

## /data
* CSV-files and JSON-files are temporarily stored here.
* Files in this directory are ignored by git.

## /static
* Files served by the webserver are kept here
* Customization of these files is encouraged.
    

