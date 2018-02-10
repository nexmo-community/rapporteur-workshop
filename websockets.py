import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web


class WSHandler(tornado.websocket.WebSocketHandler):
    connections = []

    def open(self):
        print("client connected")
        # Add the connection to the list of connections
        self.connections.append(self)

    def on_message(self, message):
        # Check if message is Binary or Text
        if type(message) == str:
            print("Binary Message recieved")
            # Echo the binary message back to where it came from
            self.write_message(message, binary=True)
        else:
            print(message)
            # Send back a simple "OK"
            self.write_message('ok')

    def on_close(self):
        # Remove the connection from the list of connections
        self.connections.remove(self)
        print("client disconnected")


application = tornado.web.Application([(r'/socket', WSHandler)])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8001)
    tornado.ioloop.IOLoop.instance().start()
