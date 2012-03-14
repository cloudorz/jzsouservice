# coding: utf-8

import re

from pymongo import errors

from apps import BaseRequestHandler
from core.ext import db, ASCENDING, DESCENDING

from utils.decorator import authenticated, validclient
from utils.tools import QDict, pretty_time_str


class CityRequestHandler(BaseRequestHandler):

    @validclient
    def get(self, cid):
        cities = db.cities.find().sort({'no': ASCENDING})
        self.make_list_rest(cities, 'cities')

        self.render_json(cities)

    @authenticated
    def post(self, cid):
        required = set(
                'name',
                'label',
                'no',
                'created',
                )
        data = self.get_data()
        data['created'] = now()
        if not required <= set(data):
            raise HTTPError(400, 'Miss required args.')

        try:
            _id = db.cities.insert(data)
        except errors.OperationFailure:
            raise HTTPError(400, 'Entry attributes error')

        self.set_status(201)
        self.set_header('Location',
                self.full_uri_path(self.reverse_url('cities', _id)))
        self.finish()

    @authenticated
    def put(self, cid):
        data = self.get_data()
        try:
            db.cities.update({'_id': cid}, {'$set': data})
        except errors.OperationFailure:
            raise HTTPError(400, 'Arguments error')

        self.set_status(200)
        self.finish()

    @authenticated
    def delete(self, cid):
        try:
            db.cities.remove({'_id': cid})
        except errors.OperationFailure:
            raise HTTPError(500)

        self.set_status(200)
        self.finish()
