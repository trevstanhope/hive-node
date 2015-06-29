import json
import csv
import sys
import os

jsonfile_path = "samples 2015_6_29.json"
csvfile_path = "output.csv"

keys = ['time', 'hive_id', 'int_t', 'int_h', 'dht_t', 'dht_h', 'hz', 'db', 'pa']
print keys
jsonfile = open(jsonfile_path, 'r')

data = json.loads(jsonfile.read())

with open(csvfile_path, 'w') as csvfile:
    csvfile.write(','.join(keys + ['\n']))
    
    for d in data:
        newline= []
        for k in keys:
            try:
                newline.append(str(d[k]))
            except:
                newline.append('')
        csvfile.write(','.join(newline + ['\n']))
