import os
import time
import uuid
import jwt
import requests
import hug


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

    def recording(self, recording_url, recording_uuid, response):
        iat = int(time.time())
        payload = {
            'application_id': os.environ['APPLICATION_ID'],
            'iat': iat,
            'exp': iat + 60,
            'jti': str(uuid.uuid4()),
        }

        token = jwt.encode(payload, self.private_key, algorithm='RS256')

        headers = {
            'Authorization': b'Bearer ' + token,
            'User-Agent': 'python/rapporteur'
        }

        recording_response = requests.get(recording_url, headers=headers)
        if recording_response.status_code == 200:
            with open(f'./recordings/{recording_uuid}.mp3', 'wb') as f:
                f.write(recording_response.content)

            return {}

        response.status = recording_response.status_code
        return response



routes = CallRouter()
server = hug.route.API(__name__)

server.get('/')(routes.proxy)
server.post('/recordings')(routes.recording)
