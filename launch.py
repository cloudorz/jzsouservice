# coding: utf-8

import os.path

import tornado.web
import tornado.httpserver
import tornado.database
import tornado.options
import tornado.ioloop

from tornado.options import define, options
from tornado.web import url
from core.ext import db

from apps.entry import SearchEntryHandler, EntryRequestHandler
from apps.city import CityRequestHandler
from apps.cate import CateRequestHandler


# server
define('port', default=8000, help="run on the given port", type=int)


# main logic
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
                url(r'^/(?P<city>[a-z]+)/s$', SearchEntryHandler,
                    name='entries'),
                url(r'^/entry/(?P<eid>[a-z0-9]+|)$', SearchEntryHandler),
                url(r'^/pos/(?P<lat>\d+\.\d+),(?P<lon>\d+\.\d+)$',
                    CityRequestHandler),
                url(r'^/city/(?P<cid>[a-z0-9]+|)$', CityRequestHandler,
                    name='cities'),
                url(r'^/cate/(?P<cid>[a-z0-9]+|)$', CateRequestHandler,
                    name='cates'),
                ]
        settings = dict(
                static_path=os.path.join(os.path.dirname(__file__), 'static'),
                # secure cookies
                cookie_secret="5b05a25df33a4609ca4c14caa6a8594b",
                debug=True,
                )
        super(Application, self).__init__(handlers, **settings)


def main():
    tornado.options.parse_command_line()

    app = Application()

    # server 
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
