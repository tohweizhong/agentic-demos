# Jun 2025

import asyncio
import base64

import websockets
import json
import pyaudio

# needs to be rerun when token expires
BEARER_TOKEN = "<gcloud auth print-access-token>"

PROJECT_ID = "<project ID>"

MODEL_ID = f"projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp"

HOST = "us-central1-aiplatform.googleapis.com"
SERVICE_URL = f"wss://{HOST}/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent"

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = int(0.2 * RATE)

prompt = """You are an advanced speech-to-text transcription model that aims to convert spoken language into accurate, formatted, and coherent written text. Your task is to transcribe the given audio into text, ensuring accuracy of spelling, grammar, and context. Please follow the specific requirements below:

Punctuation: Add appropriate punctuation, including commas, periods, question marks, and quotation marks where appropriate.

The audio language may be in English, Chinese or Bahasa Indonesia, the transcript you output should be in english, chinese, or bahasa indonesia accordingly. Your translation must be in English.

You also have to detect the language, whether it's english, chinese or Bahasa Indonesia.

You also have to analyse the emotion in the audio, give a score between negative 5 to positive 5, positive 5 being the most positive sentiment.

You only need to output the content of the audio, and the sentiment. If no one is speaking in the audio, you can output nothing or an empty string.

The output format is {"transcript": "", "translation": "", "sentiment": "", "language": ""}"""


async def stream_audio():
    # Initialize audio stream
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Recording... Press Ctrl+C to stop.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BEARER_TOKEN}",
    }

    try:
        async with websockets.connect(SERVICE_URL, additional_headers=headers) as websocket:

            await websocket.send(json.dumps({
                "setup": {
                    "model": MODEL_ID,
                    "generation_config": {
                        "response_modalities": ["TEXT"],
                    },
                    # "system_instruction": [{"role": "user", "parts": [{"text": f"{prompt}"}]}]
                },

            }))

            await asyncio.sleep(1)

            await websocket.send(json.dumps({
                "client_content": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}],
                        },
                    ],
                    "turn_complete": True,
                }
            }))

            async def send_audio():
                print('Start transmitting audio ')
                try:
                    while True:
                        audio_data = stream.read(
                            CHUNK, exception_on_overflow=False)
                        audio_base64 = json.dumps({
                            "realtime_input": {
                                "media_chunks":
                                    [
                                        {
                                            "mime_type": "audio/pcm",
                                            "data": base64.b64encode(audio_data).decode('utf-8')
                                        }
                                    ]
                            }
                        })
                        await websocket.send(audio_base64)
                        # Small delay to prevent flooding
                        await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print('send err', e)

            async def receive_responses():
                try:
                    while True:
                        message = await websocket.recv()
                        response = json.loads(message)
                        # print(response)
                        try:
                            if response.get('setupComplete') is not None:
                                continue
                            # print('\n res: ', response, '\n')

                            is_complete = response.get(
                                'serverContent').get('turnComplete')

                            # print('\nis_complete', is_complete, '\n')

                            if is_complete is not None and is_complete:
                                print('\n')
                                continue

                            contents = response['serverContent']['modelTurn']['parts']

                            for content in contents:
                                print(content['text'], end="")

                        except Exception as e:
                            print('json parse err', e)

                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print('receive err', e)

            # Run send and receive tasks concurrently
            send_task = asyncio.create_task(send_audio())
            receive_task = asyncio.create_task(receive_responses())

            try:
                await asyncio.gather(send_task, receive_task)
            finally:
                send_task.cancel()
                receive_task.cancel()
                stream.stop_stream()
                stream.close()
                p.terminate()
    except KeyboardInterrupt:
        print('Stop transmitting audio ')
        await websocket.close()


if __name__ == "__main__":
    try:
        asyncio.run(stream_audio())
    except KeyboardInterrupt:
        print("Stopped recording.")