# coding: utf-8

import logger
import re, datetime, hashlib
import pygeoip

import tornado.httpclient

from pymongo.objectid import ObjectId
from tornado import gen
from tornado.web import asynchronous, HTTPError
from tornado.escape import utf8

from apps import BaseRequestHandler
from core.ext import db, ASCENDING, DESCENDING

from utils.decorator import authenticated
from utils.tools import QDict, pretty_time_str
from utils.ip2city import get_city


# consists
gic = pygeoip.GeoIP('/data/backup/GeoLiteCity.dat', pygeoip.MEMORY_CACHE)


class SearchEntryHandler(BaseRequestHandler):

    @authenticated
    def get(self, city):

        query_dict = {'city_label': city, 'status': 'show'}
        pos = self.get_argument('pos', None)
        if pos:
            lat, lon = pos.split(',')
            query_dict['_location'] = {'$maxDistance': 0.091, '$near': [float(lon), float(lat)]}

        condition = self.get_argument('q')
        if ':' in condition:
            field, value = condition.split(':')
        else:
            raise HTTPError(400, "condition's format field:value")

        # process functions
        def do_tag(tag):
            query_dict['tags'] = tag
            return db.Entry.find(query_dict)

        def do_key(data):
            rqs = [e.lower() for e in re.split('\s+', data) if e]
            regex = re.compile(r'%s' % '|'.join(rqs), re.IGNORECASE)
            query_dict['$or'] = [{'title': regex}, {'brief': regex},
                    {'desc': regex}, {'tags': {'$in': rqs}}] 
            return db.Entry.find(query_dict)

        handle_q = {
                'tag': do_tag, 
                'key': do_key,
                }

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
                    'q': utf8(q.q),
                    'st': q.start,
                    'qn': q.num,
                    }

            entries = cur_entry.skip(q.start).\
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
            any(hasher.update(e) for e in sorted("%s-%s" % (entry['id'],
                entry['updated']) for entry in self.cur_entries))

        return '"%s"' % hasher.hexdigest()


class EntryHandler(BaseRequestHandler):

    @authenticated
    def put(self, eid):
        entry = db.Entry.find_one({'_id': ObjectId(eid)})
        if not entry: raise HTTPError(404)

        data = self.get_data()
        logger.warning(data)

        if set(data) <= set(entry):
            for k, v in data.items():
                if k[:2] == 'c_':
                    set_data = set(entry[k])
                    logger.warning(set_data)
                    data[k] = list(set_data.add(v))

            db.Entry.update({'_id': ObjectId(eid)}, {'$set': data})

        self.set_status(200)
        self.finish()


class CityRequestHandler(BaseRequestHandler):

    @authenticated
    @asynchronous
    @gen.engine
    def get(self, latlon=None):
        if latlon:
            http_client = tornado.httpclient.AsyncHTTPClient()
            url = 'http://l.n2u.in/city/%s' % latlon
            city_label = yield gen.Task(http_client.fetch, url)
        else:
            city_label = self.get_city_by_ip()

        self.render_json(get_city(city_label))
        self.finish()

    def get_city_by_ip(self):
        ip = self.request.headers['X-Real-IP']
        city = 'hangzhou'
        if ip:
            record = gic.record_by_addr(ip)
            if record:
                city_ = record.get('city', None)
                if city_:
                    city = city_.lower()
        return city


class CateRequestHandler(BaseRequestHandler):

    @authenticated
    def get(self):
        cates = db.Cate.find().sort('no', ASCENDING)
        self.render_json(cates)
