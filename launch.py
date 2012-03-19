# coding: utf-8

import tornado.web
import tornado.httpserver
import tornado.options
import tornado.ioloop

from tornado.options import define, options
from tornado.web import url

from apps.service import SearchEntryHandler, CityRequestHandler, \
        LocRequestHandler, CateRequestHandler

# server
define('port', default=8200, help="run on the given port", type=int)


# main logic
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
                url(r'^/(?P<city>[a-z]+)/s$', SearchEntryHandler),
                url(r'^/city/$', CityRequestHandler),
                url(r'^/cate/$', CateRequestHandler),
                ]
        settings = dict(
                # secure cookies
                cookie_secret="5b05a25df33a4609ca4c14caa6a8594b",
                token="0b8b31819a8d4c1a8da9e19847dcb36a",
                geo_url="http://l.n2u.in",
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
