# HiveNode
A HiveNode is a wireless linux device for remotely monitoring beehive health.
With HiveNode, any amateur bee-keeper can monitor their hives in real-time.

## Setup (DEBIAN)
To install all dependencies for the HiveNode, run the following:

    chmod +x install.sh
    ./install.sh
    
## Running the Node
The HiveNode daemon will start on boot, via /etc/rc.local, but can be executed
manually from the git repository:

    sudo python hive-node.py
    
## Updating
All changes to the repository will be automatically pulled whenever a node boots while 
connected to a WAN connection (i.e. "online"). The boot process automatically fetches
the latest version of the git repository and forces the local code on the node to be overwritten.
Any local changes to a nodes software will only last until it is rebooted while on a internet
connection (e.g. temporary changes can be tested, but the node will update to the git version
when rebooted with WAN)

## /data
* CSV-files and JSON-files are temporarily stored here.
* Files in this directory are ignored by git.

## /static
* Files served by the webserver are kept here
* Customization of these files is encouraged.
    

