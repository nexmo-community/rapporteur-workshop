import os
import hug


class CallRouter:

    def __init__(self):
        self.base_url = os.environ['NGROK_URL']

    def proxy(self):
        return [
            {
                'action': 'record',
                'eventUrl': [f'{self.base_url}/recordings'],
                'endOnSilence': 3
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


routes = CallRouter()
server = hug.route.API(__name__)

server.get('/')(routes.proxy)
