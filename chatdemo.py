#-*- coding: UTF-8 -*-
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

#-*- coding: UTF-8 -*-
"""Simplified chat demo for websockets.

Authentication, error handling, etc are left as an exercise for the reader :)
"""

import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid
import datetime

from tornado.options import define, options

# 端口配置
define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        # 路由映射
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
        ]
        # 项目的基本配置
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        # 启用父类
        super(Application, self).__init__(handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # messages=ChatSocketHandler.cache, 更新缓存
        # clients=ChatSocketHandler.waiters, 展示所有在线用户
        # username= "游客%d" % ChatSocketHandler.client_id 设置默认id
        self.render("index.html", messages=ChatSocketHandler.cache, clients=ChatSocketHandler.waiters, username= "游客%d" % ChatSocketHandler.client_id)

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 200
    client_id = 0

    def get_compression_options(self):
        # Non-None enables compression with default options.
        # Non-None使用默认选项启用压缩。
        return {}

    def open(self):
        # 客户端进行连接
        self.client_id = ChatSocketHandler.client_id
        # id自增
        ChatSocketHandler.client_id = ChatSocketHandler.client_id + 1
        self.username = "游客%d" % self.client_id
        # 将客户端添加到集合中
        ChatSocketHandler.waiters.add(self)
        # 序列化消息
        chat = {
            "id": str(uuid.uuid4()),
            "type": "online",
            "client_id": self.client_id,
            "username": self.username,
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        # 广播群成员用户上线
        ChatSocketHandler.send_updates(chat)

    def on_close(self):
        # 客户端关闭，从集合中移除
        ChatSocketHandler.waiters.remove(self)
        chat = {
            "id": str(uuid.uuid4()),
            "type": "offline",
            "client_id": self.client_id,
            "username": self.username,
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        # 广播群成员用户下线
        ChatSocketHandler.send_updates(chat)


    # 添加缓存消息
    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    # 广播更新消息
    @classmethod
    def send_updates(cls, chat):
        logging.info("sending message to %d waiters", len(cls.waiters))
        # 循环广播消息
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error("Error sending message", exc_info=True)

    # 发送消息
    def on_message(self, message):
        logging.info("got message %r", message)
        # 内容解析
        parsed = tornado.escape.json_decode(message)
        self.username = parsed["username"]
        chat = {
            "id": str(uuid.uuid4()),
            "body": parsed["body"],
            "type": "message",
            "client_id": self.client_id, 
            "username": self.username,
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        chat["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=chat))
        # 更新缓存，广播消息
        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)


def main():
    # 转换命令行参数，并将转换后的值对应的设置到全局options对象相关属性上。追加命令行参数的方式是--myoption=myvalue
    tornado.options.parse_command_line()
    # 创建一个app实例对象
    app = Application()
    # 端口监听
    app.listen(options.port)
    # 启动项目
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
