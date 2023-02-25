import queue
import os
import time
import threading

import openai
import requests
import vlc 

openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if ELEVENLABS_API_KEY == '':
    print('ERROR: Missing API KEY')

logfile_path = f'logs/{time.time()}.txt'

history_q = queue.Queue()
message_q = queue.Queue()
break_q = queue.Queue()

def write_log(line):
    if os.path.exists(logfile_path):
        with open(logfile_path, "a") as myfile:
            myfile.write(f'{line}\n')
    else:
        with open(logfile_path, "w") as myfile:
            myfile.write(f'{line}\n')


def read_input():
    while break_q.empty():
        user_input = input()
        message_q.put(f'Audience: {user_input}\nYou respond with: ')
        if user_input == "q":
            break_q.put('quit')
            return

def send_message(message):
    header = "You're a Twitch Streamer known for being positive, supportive and telling lots of fun stories. You're in the \"Just Chatting\" category and you don't play videogames, you just tell stories and converse with the audience. Occasionally you like to point out something cool happening on stream. You're currently live, streaming on Twitch. "
    #header = "You're a Twitch Streamer known for being positive, supportive and funny. You're in the \"Just Chatting\" category and you don't play videogames, you just tell stories and converse with the audience. Occasionally you like to point out something cool happening on stream. You're currently live, streaming on Twitch and your goal is to be as engaging and interesting as possible with minimal input from your Audience."
    messages = '\n'.join(message)
    prompt = f"{header}{messages}"
    response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0.6,
            max_tokens=2038,
        )
    clean_response = response['choices'][0]['text'].strip()

    return clean_response

def auto_converse():
    message = f'Then you say: '
    message_q.put(message)

def tts_message(message):
    prefix = None
    if "First you say: " in message:
        prefix = "First you say: "
    elif "Then you say: " in message:
        prefix = "Then you say: "
    elif "You respond with: " in message:
        prefix = "You respond with: "
    if prefix:
        message = message.split(prefix)[1]
        print(message)
        voice_id = 'psZFe8Mqk5wBF985W8mz'
        response = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
             headers={
                'accept': 'audio/mpeg',
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
             },
             json={
                "text": message,
                  "voice_settings": {
                    "stability": 0.35,
                    "similarity_boost": 0.75
                }})
        filename = f'logs/{time.time()}.mp3'
        data = response.content
        with open(filename, 'wb') as s:
            s.write(data)
        media = vlc.MediaPlayer(filename)
        media.play()
        time.sleep(.25)
        duration = media.get_length() / 1000
        time.sleep(duration)


def eval_queue():
    message_cache = []
    message_q.put('First you say: ')
    last_time = time.time()
    while break_q.empty():
        if not message_q.empty():
            message = message_q.get()
            message_cache.append(message)
            message_cache[-1] = f'{message_cache[-1]}{send_message(message_cache)}'
            tts_message(message_cache[-1])
            write_log(message_cache[-1])
            last_time = time.time()
        if time.time() > (last_time + 10):
            auto_converse()
            last_time = time.time()
        if len(message_cache) > 10:
            message_cache = []
            message_q.put('First you say: ')
            last_time = time.time()


read_thread = threading.Thread(target=read_input, daemon=True).start()
eval_thread = threading.Thread(target=eval_queue, daemon=True).start()

print('Press q to quit')

while break_q.empty():
    pass

# Block until all tasks are done.
message_q.join()
break_q.join()
history_q.join()
read_thread.join()
eval_thread.join()