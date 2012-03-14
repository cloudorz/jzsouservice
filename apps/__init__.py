# coding: utf-8

import httplib, urlparse, urllib, base64, hmac, hashlib
import logging

import tornado.web
import tornado.httpclient

from tornado.web import HTTPError
from tornado.options import options
from tornado.httputil import url_concat
from tornado.escape import url_escape, utf8
from core.ext import db

from utils.escape import json_encode, json_decode

class AuthHeader(object):
    def parse_auth_header(self):

        auth_value = self.request.headers.get('Authorization', None)
        if auth_value and auth_value.startswith('Auth '):
            prefix, value = auth_value.split(" ", 1)
            value = value.strip()

            res = {}
            for e in value.split(','):
                k, v = e.strip().split('=', 1)
                res[k] = v.strip('"')
            return res

        return None

    def get_normalized_http_method(self):
        res = self.request.method.upper()
        return res
    
    def get_normalized_http_url(self):
        req = self.request
        res = "%s://%s%s" % (req.protocol, req.host, req.path)
        return res

    def _query_args_a0(self, s):
        query_args = urlparse.parse_qs(s, keep_blank_values=False)
        return {k: urllib.unquote(v[0]) for k, v in query_args.items()}

    def get_normalized_parameters(self, auth_header):
        # from header 
        args = self._query_args_a0(self.request.query)
        args.update({k: v for k, v in auth_header.items()
            if k[:5] == 'auth_' and k != 'auth_signature'})
        key_values = args.items()
        key_values.sort()

        res = '&'.join('%s=%s' % (self._url_escape(str(k)), self._url_escape(str(v))) for k, v in key_values)
        return res

    def build_signature(self, auth_header, client, token=None):
        sig = (
                self._url_escape(self.get_normalized_http_method()),
                self._url_escape(self.get_normalized_http_url()),
                self._url_escape(self.get_normalized_parameters(auth_header)),
                )
        if token:
            key = '%s&%s' % (self._url_escape(client['secret']), self._url_escape(token['secret']))
        else:
            key = '%s' % self._url_escape(client['secret'])

        raw = '&'.join(sig)

        # hmac object
        hashed = hmac.new(key, raw, hashlib.sha1)

        return base64.b64encode(hashed.digest())

    def _url_escape(self, s):
        return urllib.quote(s, safe='~')

    def full_uri(self, query_dict=None):
        return url_concat(self.get_normalized_http_url(), query_dict)

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

class BaseRequestHandler(tornado.web.RequestHandler, AuthHeader):
    """the base RequestHandler for All."""

    def get_data(self):
        ''' parse the data from request body
        now, only convert json data to python type
        '''
        # the content type is not "application/json"
        if not self.is_json:
            raise HTTPError(415)

        try:
            data = self.dejson(self.request.body)
        except (ValueError, TypeError), e:
            raise HTTPError(415) # the data is not the right json format

        return data

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

        auth_header = self.parse_auth_header()

        if auth_header:
            required_params = {
                    "auth_app_key",
                    "auth_user_key",
                    "auth_once",
                    "auth_timestamp",
                    "auth_signature_method",
                    "auth_signature",
                    }
            given_params = set(auth_header)

            if not (required_params <= given_params):
                raise HTTPError(400, "Bad Request. Lack params: %s" % 
                        ', '.join(required_params - given_params)
                        )

            app = App.query.get(auth_header['auth_app_key'])
            app = db.apps.find_one({'_id': auth_header['auth_app_key']})
            user = User.query.get_by_userkey(auth_header['auth_user_key'])
            app = db.users.find_one({'_id': auth_header['auth_app_key']})

            if not (user and app):
                raise HTTPError(400, "Bad Reques, user not exists.")

            token = {
                    'key': user.userkey,
                    'secret': user.secret
                    }

            client = {
                    'key': app.pk,
                    'secret': app.secret,
                    }

            reauth_signature = self.build_signature(client, token, auth_header)
            auth_signature = urllib.unquote(auth_header['auth_signature'])
            if auth_signature == reauth_signature:
                return user
            else:
                raise HTTPError(400,
                        "Bad Request. signature dismatch, expect %s, but given %s" %
                        (reauth_signature, auth_header['auth_signature'])
                        )

        return None

    def get_client(self):
        auth_header = self.parse_auth_header()

        if auth_header:
            required_params = {
                    "auth_app_key",
                    "auth_once",
                    "auth_timestamp",
                    "auth_signature_method",
                    "auth_signature",
                    }
            given_params = set(auth_header)

            if not (required_params <= given_params):
                raise HTTPError(400, "Bad Request. Lack params: %s" % 
                        ', '.join(required_params - given_params)
                        )

            app = db.apps.find_one({'_id': auth_header['auth_app_key']})

            if not (user and app):
                raise HTTPError(400, "Bad Reques, user not exists.")

            client = {
                    'key': auth_app_key,
                    'secret': app['secret'],
                    }

            reauth_signature = self.build_signature(auth_header, client)
            auth_signature = urllib.unquote(auth_header['auth_signature'])
            if auth_signature == reauth_signature:
                return QDict(app)
            else:
                raise HTTPError(400,
                        "Bad Request. signature dismatch, expect %s, but given %s" %
                        (reauth_signature, auth_header['auth_signature'])
                        )

        return None
