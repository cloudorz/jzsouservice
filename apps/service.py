# coding: utf-8

import re, datetime, hashlib

import tornado.httpclient
from tornado import gen
from tornado.web import asynchronous, HTTPError

from apps import BaseRequestHandler
from core.ext import db, ASCENDING, DESCENDING

from utils.decorator import authenticated
from utils.tools import QDict, pretty_time_str


class SearchEntryHandler(BaseRequestHandler):

    @authenticated
    def get(self, city):
        query_dict = {'city_label': city}

        condition = self.get_argument('q')
        if ':' in condition:
            field, value = condition.split(':')
        else:
            raise HTTPError(400, "condition's format field:value")

        # process functions
        def do_tag(tag):
            query_dict['tags'] = tag
            return db.Entry.find(query_dict)

        def do_position(pos):
            lat, lon = pos.split(',')
            query_dict['_location'] = {'$near': [lon, lat], '$maxDistance': 5000}
            return db.Entry.find(query_dict)

        def do_key(data):
            rqs = [e.lower() for e in re.split('\s+', data) if e]
            regex = re.compile(r'%s' % '|'.join(rqs), re.IGNORECASE)
            query_dict['$or'] = [{'title': regex}, {'brief': regex},
                    {'desc': regex}, {'tags': {'$in': rqs}}] 
            return db.Entry.find(query_dict)

        handle_q = {
                'tag': do_tag, 
                'position': do_position,
                'key': do_key,
                }

        print query_dict
        if field in handle_q:
            q = QDict(
                    q=condition,
                    v=value,
                    start=int(self.get_argument('st')),
                    num=int(self.get_argument('qn')),
                    )
            cur_entry = handle_q[field](q.v)


            # composite the results collection
            total = cur_entry.count()
            query_dict = {
                    'q': q.q,
                    'st': q.start,
                    'qn': q.num,
                    }

            entries = cur_entry.sort('created', DESCENDING).\
                                skip(q.start).\
                                limit(q.num)
                                
            entry_collection = {
                    'entries': [self.make_rest(e, 'entries') for e in entries],
                    'total': total,
                    'link': self.full_uri(query_dict),
                    }

            if q.start + q.num < total:
                query_dict['st'] = q.start + q.num
                entry_collection['next'] = self.full_uri(query_dict)

            if q.start > 0:
                query_dict['st'] = max(q.start - q.num, 0)
                entry_collection['prev'] = self.full_uri(query_dict)

            gmt_now = datetime.datetime.utcnow()
            self.set_header('Last-Modified', pretty_time_str(gmt_now))

            # make etag prepare
            self.cur_entries = entry_collection['entries']

        else:
            raise HTTPError(400, "Bad Request, search condtion is not allowed.")

        self.render_json(entry_collection)

    def compute_etag(self):
        hasher = hashlib.sha1()
        if 'cur_entries' in self.__dict__:
            any(hasher.update(e) for e in sorted("%s-%s" % (str(entry['_id']),
                entry['updated']) for entry in self.cur_entries))

        return '"%s"' % hasher.hexdigest()


class EntryHandler(BaseRequestHandler):

    @authenticated
    def put(self, eid):
        pass


class CityRequestHandler(BaseRequestHandler):

    @authenticated
    def get(self):
        cities = db.City.find().sort('no', ASCENDING)
        self.render_json(cities)


class CateRequestHandler(BaseRequestHandler):

    @authenticated
    def get(self):
        cates = db.Cate.find().sort('no', ASCENDING)
        self.render_json(cates)
