# coding: utf-8

import re, datetime

from pymongo import errors

from apps import BaseRequestHandler
from core.ext import db, ASCENDING, DESCENDING

from utils.decorator import authenticated, validclient
from utils.tools import QDict, pretty_time_str, generate_secret

now = datetime.datetime.utcnow

class EntryRequestHandler(BaseRequestHandler):

    @validclient
    def get(self, eid):
        entry = db.entries.find_one({'_id': eid})

        if entry:
            self.make_rest(entry)
            self.render_json(entry)
        else:
            raise HTTPError(404)

    @authenticated
    def post(self):
        required = set(
                'title',
                'brief',
                'city',
                'tags',
                'address',
                'worktime',
                'serviceitems',
                'servicearea',
                'contract',
                'manager',
                'block',
                'location',
                'updated',
                'created',
                )
        data = self.get_data()
        data['updated'] = now()
        data['created'] = now()
        if not required <= set(data):
            raise HTTPError(400, 'Miss required args.')

        try:
            _id = db.entries.insert(data)
        except errors.OperationFailure:
            raise HTTPError(400, 'entry attributes error')

        self.set_status(201)
        self.set_header('Location',
                self.full_uri_path(self.reverse_url('entries', _id)))
        self.finish()

    @authenticated
    def put(self, eid):
        data = self.get_data()
        data['updated'] = now()
        try:
            db.entries.update({'_id': eid}, {'$set': data})
        except errors.OperationFailure:
            raise HTTPError(400, 'Arguments error')

        self.set_status(200)
        self.finish()

    @authenticated
    def delete(self, eid):
        try:
            db.entries.remove({'_id': eid})
        except errors.OperationFailure:
            raise HTTPError(500)

        self.set_status(200)
        self.finish()


class SearchEntryHandler(BaseRequestHandler):

    @validclient
    def get(self, city):
        query_dict = {'city': city}

        condition = self.get_argument('q')
        if ':' in condition:
            field, value = condition.split(':')
        else:
            raise HTTPError(400, "condition's format field:value")

        # process functions
        def do_tag(tag):
            query_dict['tags'] = tag
            return db.entries.find(query_dict)

        def do_position(pos):
            lat, lon = pos.split(',')
            query_dict['location'] = {'$near': [lon, lat], '$maxDistance': 5000}
            return db.entries.find(query_dict)

        def do_key(data):
            rqs = [e.lower() for e in re.split('\s+', data) if e]
            regex = re.compile(r'%s' % '|'.join(rqs), re.IGNORECASE)
            query_dict['$or'] = [{'title': regex}, {'brief': regex},
                    {'desc': regex}, {'tags': {'$in': rqs}}] 
            return db.entries.find(query_dict)

        handle_q = {
                'tag': do_tag, 
                'position': do_position,
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
                    'q': q.q,
                    'st': q.start,
                    'qn': q.num,
                    }

            entries = cur_entry.sort({'created': DESCENDING}).\
                                skip(q.start).\
                                limit(q.num)
            self.make_list_rest(entries, )

            entry_collection = {
                    'entries': entries,
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
