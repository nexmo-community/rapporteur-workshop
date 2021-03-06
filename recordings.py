import os
import time
import uuid
import jwt
import requests
import logzero
from logzero import logger
from watson_developer_cloud import SpeechToTextV1, NaturalLanguageUnderstandingV1
from watson_developer_cloud.natural_language_understanding_v1 import (
    Features, EntitiesOptions, KeywordsOptions, CategoriesOptions, ConceptsOptions,
    EmotionOptions, RelationsOptions, SentimentOptions
)
from exceptions import RecordingNotFoundException

logzero.logfile("/tmp/rapporteur-recordings.log", maxBytes=1e6, backupCount=3)


class Recording:

    content = None
    transcription = None
    analysis = None

    def __init__(self, recording_url, recording_uuid):
        self.recording_url = recording_url
        self.recording_uuid = recording_uuid

        self.base_url = os.environ['NCCO_SERVER_URL']
        with open('private.key', 'rb') as key_file:
            self.private_key = key_file.read()

    def _nexmo_headers(self):
        iat = int(time.time())
        payload = {
            'application_id': os.environ['APPLICATION_ID'],
            'iat': iat,
            'exp': iat + 60,
            'jti': str(uuid.uuid4()),
        }

        token = jwt.encode(payload, self.private_key, algorithm='RS256')

        return {
            'Authorization': b'Bearer ' + token,
            'User-Agent': 'python/rapporteur'
        }

    def _fetch_recording(self):
        recording_response = requests.get(
            self.recording_url,
            headers=self._nexmo_headers()
        )

        if recording_response.status_code == 200:
            logger.info('Recording file content got')
            self.content = recording_response.content
            return True
        else:
            logger.exception(RecordingNotFoundException)
            raise RecordingNotFoundException

    def save(self):
        if not self.content:
            self._fetch_recording()

        with open(f'./media/{self.recording_uuid}.mp3', 'wb') as f:
            f.write(self.content)

        logger.info(f'Saved recording as ./media/{self.recording_uuid}.mp3')

    def transcript(self):
        if not self.content:
            self._fetch_recording()

        speech_to_text = SpeechToTextV1(
            username=os.environ['TRANSCRIPTION_USERNAME'],
            password=os.environ['TRANSCRIPTION_PASSWORD'],
            x_watson_learning_opt_out=False
        )

        self.transcription = speech_to_text.recognize(
            self.content,
            content_type='audio/mp3',
            timestamps=False,
            word_confidence=False
        )

        logger.info('Got recording transcript from IBM Watson')
        return self.transcription

    def understanding(self):
        if not self.transcription:
            self.transcript()

        natural_language_understanding = NaturalLanguageUnderstandingV1(
            version='2017-02-27',
            username=os.environ['UNDERSTANDING_USERNAME'],
            password=os.environ['UNDERSTANDING_PASSWORD']
        )

        self.analysis = natural_language_understanding.analyze(
            text=self.transcription['results'][0]['alternatives'][0]['transcript'],
            features=Features(
                categories=CategoriesOptions(),
                concepts=ConceptsOptions(),
                emotion=EmotionOptions(),
                entities=EntitiesOptions(
                    emotion=True,
                    sentiment=True,
                    mentions=True
                ),
                keywords=KeywordsOptions(
                    emotion=True,
                    sentiment=True
                ),
                relations=RelationsOptions(),
                sentiment=SentimentOptions()
            )
        )

        logger.info('Completed analysis of recorded file')
        return self.analysis
