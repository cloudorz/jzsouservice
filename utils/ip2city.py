# coding: utf-8

import json
import pygeoip

# loading data

data_f = open('/data/backup/city_dict.txt', 'rb')
data = data_f.read()

city_dict = json.loads(data)

data_f.close()

def get_city(label):
    if label in city_dict:
        city = city_dict[label]
    else:
        city = city_dict['hangzhou']
    return city
