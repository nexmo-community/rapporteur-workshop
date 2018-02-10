import os
import hug
import logzero
from logzero import logger
from recordings import Recording

logzero.logfile("/tmp/rapporteur-ncco-server.log", maxBytes=1e6, backupCount=3)


class CallRouter:

    def __init__(self):
        self.base_url = os.environ['NCCO_SERVER_URL']

    def proxy(self):
        logger.info('Proxy endpoint called')

        return [
            {
                'action': 'talk',
                'text': 'Please wait while we connect you'
            },
            {
                'action': 'record',
                'eventUrl': [f'{self.base_url}/recordings']
            },
            {
                'action': 'connect',
                'eventUrl': [f'{self.base_url}/events'],
                'from': os.environ['NEXMO_NUMBER'],
                'endpoint': [
                    {
                        'type': 'websocket',
                        'uri': f'{os.environ["WEBSOCKET_SERVER_URL"]}/socket',
                        'content-type': 'audio/l16;rate=16000',
                        'headers': {}
                    }
                ]
            }
        ]

    def recording(self, recording_url, recording_uuid):
        logger.info('Recording endpoint called')

        recording = Recording(recording_url, recording_uuid)
        recording.save()
        recording.transcript()
        recording.understanding()

        return recording.analysis

    def events(self, **kwargs):
        logger.info('Event endpoint called')
        return kwargs


routes = CallRouter()
server = hug.route.API(__name__)

server.get('/')(routes.proxy)
server.post('/recordings')(routes.recording)
server.post('/events')(routes.events)
