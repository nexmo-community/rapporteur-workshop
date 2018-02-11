import os
import json
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
from tornado import gen
import requests
import logzero
from logzero import logger
from watson_developer_cloud import ToneAnalyzerV3

logzero.logfile("/tmp/rapporteur-websocket-server.log", maxBytes=1e6, backupCount=3)


class DashboardHandler(tornado.websocket.WebSocketHandler):

    waiters = set()

    def check_origin(self, origin):
        return True

    def open(self):
        logger.info('Dashboard socket open')
        DashboardHandler.waiters.add(self)

    def on_close(self):
        logger.info('Dashboard socket closed')
        DashboardHandler.waiters.remove(self)

    @classmethod
    def send_updates(cls, tones):
        logger.info('Sending dashboard update')
        logger.warning(tones)

        for waiter in cls.waiters:
            try:
                waiter.write_message(tones)
            except:
                pass


class WSHandler(tornado.websocket.WebSocketHandler):

    connections = []

    def initialize(self, **kwargs):
        self.transcriber = tornado.websocket.websocket_connect(
            'wss://stream.watsonplatform.net/speech-to-text/api/v1/recognize?watson-token={token}&model={model}'.format(
                token=self.transcriber_token,
                model=os.environ['REALTIME_TRANSCRIBER_MODEL']
            ),
            on_message_callback=self.on_transcriber_message
        )

        self.tone_analyzer = ToneAnalyzerV3(
            username=os.environ['TONE_ANALYZER_USERNAME'],
            password=os.environ['TONE_ANALYZER_PASSWORD'],
            version='2016-05-19'
        )

    @property
    def transcriber_token(self):
        resp = requests.get(
            'https://stream.watsonplatform.net/authorization/api/v1/token',
            auth=(os.environ['TRANSCRIPTION_USERNAME'], os.environ['TRANSCRIPTION_PASSWORD']),
            params={'url': "https://stream.watsonplatform.net/speech-to-text/api"}
        )

        logger.info('Transcriber token generated')
        return resp.content.decode('utf-8')

    def open(self):
        logger.info('Client connected')
        self.connections.append(self)

    @gen.coroutine
    def on_message(self, message):
        transcriber = yield self.transcriber

        if type(message) != str:
            transcriber.write_message(message, binary=True)
        else:
            logger.info(message)
            data = json.loads(message)
            data['action'] = "start"
            data['continuous'] = True
            data['interim_results'] = True
            transcriber.write_message(json.dumps(data), binary=False)

    def on_transcriber_message(self, message):
        if message:
            message = json.loads(message)
            if 'results' in message:
                transcript = message['results'][0]['alternatives'][0]['transcript']
                tone_results = self.tone_analyzer.tone(tone_input=transcript, content_type="text/plain")
                tones = tone_results['document_tone']['tone_categories'][0]['tones']

                DashboardHandler.send_updates(json.dumps(tones))

    @gen.coroutine
    def on_close(self):
        # Remove the connection from the list of connections
        self.connections.remove(self)
        transcriber = yield self.transcriber
        data = {'action': 'stop'}
        transcriber.write_message(json.dumps(data), binary=False)
        transcriber.close()
        logger.info("client disconnected")


if __name__ == "__main__":
    application = tornado.web.Application([
        (r'/socket', WSHandler),
        (r'/dashboard', DashboardHandler)
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8001)
    tornado.ioloop.IOLoop.instance().start()
