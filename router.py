import os
import hug
from recordings import Recording


class CallRouter:

    def __init__(self):
        self.base_url = os.environ['NGROK_URL']
        with open('private.key', 'rb') as key_file:
            self.private_key = key_file.read()

    def proxy(self):
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
                        'type': 'phone',
                        'number': os.environ['TEST_NUMBER']
                    }
                ]
            }
        ]

    def recording(self, recording_url, recording_uuid):
        recording = Recording(recording_url, recording_uuid)
        recording.save()
        recording.transcript()
        recording.understanding()

        return recording.analysis


routes = CallRouter()
server = hug.route.API(__name__)

server.get('/')(routes.proxy)
server.post('/recordings')(routes.recording)
