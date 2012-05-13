# coding: utf-8

import httplib, traceback

import tornado.web
import tornado.httpclient

from tornado.httputil import url_concat

from core.ext import db
from utils.escape import json_encode, json_decode


class BaseRequestHandler(tornado.web.RequestHandler):
    """the base RequestHandler for All."""

    @property
    def is_json(self):
        return self.request.headers.get('Content-Type', '').split(';').pop(0).strip().lower() == 'application/json'

    def get_data(self):
        ''' parse the data from request body
        now, only convert json data to python type
        '''
        # the content type is not "application/json"
        if not self.is_json:
            raise HTTPError(415)

        try:
            data = json_decode(self.request.body)
        except (ValueError, TypeError), e:
            raise HTTPError(415) # the data is not the right json format

        return data

    def write_error(self, status_code, **kwargs):
        if self.settings.get("debug") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
        else:
            self.write("code: %s \n " % status_code)
            self.write("message: %s \n " % httplib.responses[status_code])

        self.set_header('Content-Type', 'text/plain')
        self.finish()

    def render_json(self, data, **kwargs):
        ''' Render data string(json) for response.
        '''
        self.set_header('Content-Type', 'Application/json; charset=UTF-8')
        self.write(json_encode(data))

    def get_current_user(self):

        self.require_setting('token', "Access jzsou token")
        token = self.settings['token']
        out_token = self.request.headers.get('Authorization', None)

        if  token == out_token:
            return True

        return False

    def make_rest(self, data, name):
        _id = str(data['_id'])
        data['id'] = 'urn:%s:%s' % (name, _id)
        del data['_id']
        # conert the set of the phone id to ids number 
        for k,v in data.items():
            if k[:2] == 'c_':
                data[k] = len(v)

        req = self.request
        data['link'] = "%s://%s%s" % (
                req.protocol,
                req.host,
                self.reverse_url(name, _id),
                )
        return data

    def full_uri_path(self, path):
        req = self.request
        return "%s://%s%s" % (req.protocol, req.host, path)

    def full_uri(self, query_dict=None):
        req = self.request
        full_url = "%s://%s%s" % (req.protocol, req.host, req.path)
        return url_concat(full_url, query_dict)
