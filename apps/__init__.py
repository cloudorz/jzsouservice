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

        return True
        if  token == out_token:
            return True

        return False

    def make_rest(self, data, name):
        data['id'] = 'urn:%s:%s' % (name, str(data['_id']))
        req = self.request
        data['link'] = "%s://%s%s" % (
                req.protocol,
                req.host,
                self.reverse_url(name)
                )

    def make_list_rest(self, data_list, name):
        for e in data_list:
            self.make_rest(e, name)

    def full_uri_path(self, path):
        req = self.request
        return "%s://%s%s" % (req.protocol, req.host, path)

    def full_uri(self, query_dict=None):
        return url_concat(self.get_normalized_http_url(), query_dict)
