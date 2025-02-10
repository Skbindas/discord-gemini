import shareithub
import json
import time
import os
import random
import requests
from shareithub import shareithub
from dotenv import load_dotenv
from datetime import datetime

shareithub()
load_dotenv()

discord_token = os.getenv('DISCORD_TOKEN')
google_api_key = os.getenv('GOOGLE_API_KEY')

last_message_id = None
bot_user_id = None

def log_message(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def generate_reply(prompt, google_api_key, use_google_ai=True):
    if use_google_ai:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={google_api_key}'
        headers = {'Content-Type': 'application/json'}
        data = {'contents': [{'parts': [{'text': prompt}]}]}

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log_message(f"Request failed: {e}")
            return None
    else:
        return {"candidates": [{"content": {"parts": [{"text": get_random_message()}]}}]}

def get_random_message():
    try:
        with open('pesan.txt', 'r') as file:
            lines = file.readlines()
            if lines:
                return random.choice(lines).strip()
            else:
                log_message("File pesan.txt kosong.")
                return "Tidak ada pesan yang tersedia."
    except FileNotFoundError:
        log_message("File pesan.txt tidak ditemukan.")
        return "File pesan.txt tidak ditemukan."

def send_message(channel_id, message_text, reply_to=None):
    headers = {
        'Authorization': f'{discord_token}',
        'Content-Type': 'application/json'
    }

    payload = {'content': message_text}
    if reply_to:
        payload['message_reference'] = {'message_id': reply_to}

    try:
        response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", json=payload, headers=headers)
        response.raise_for_status()

        if response.status_code == 201:
            log_message(f"Sent message: {message_text}")
        else:
            log_message(f"Failed to send message: {response.status_code}")
    except requests.exceptions.RequestException as e:
        log_message(f"Request error: {e}")

def auto_reply(channel_id, read_delay, reply_delay, use_google_ai):
    global last_message_id, bot_user_id

    headers = {'Authorization': f'{discord_token}'}

    try:
        bot_info_response = requests.get('https://discord.com/api/v9/users/@me', headers=headers)
        bot_info_response.raise_for_status()
        bot_user_id = bot_info_response.json().get('id')
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to retrieve bot information: {e}")
        return

    while True:
        try:
            response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)
            response.raise_for_status()

            if response.status_code == 200:
                messages = response.json()
                if len(messages) > 0:
                    most_recent_message = messages[0]
                    message_id = most_recent_message.get('id')
                    author_id = most_recent_message.get('author', {}).get('id')
                    message_type = most_recent_message.get('type', '')

                    if (last_message_id is None or int(message_id) > int(last_message_id)) and author_id != bot_user_id and message_type != 8:
                        user_message = most_recent_message.get('content', '')
                        log_message(f"Received message: {user_message}")

                        result = generate_reply(user_message, google_api_key, use_google_ai)
                        response_text = result['candidates'][0]['content']['parts'][0]['text'] if result else "Maaf, tidak dapat membalas pesan."

                        log_message(f"Waiting for {reply_delay} seconds before replying...")
                        time.sleep(reply_delay)
                        send_message(channel_id, response_text, reply_to=message_id)
                        last_message_id = message_id

            log_message(f"Waiting for {read_delay} seconds before checking for new messages...")
            time.sleep(read_delay)
        except requests.exceptions.RequestException as e:
            log_message(f"Request error: {e}")
            time.sleep(read_delay)

def auto_send_messages(channel_id, send_interval):
    while True:
        message_text = get_random_message()
        send_message(channel_id, message_text)
        log_message(f"Waiting {send_interval} seconds before sending the next message...")
        time.sleep(send_interval)

if __name__ == "__main__":
    use_reply = input("Ingin menggunakan fitur reply? (y/n): ").lower() == 'y'
    
    channel_id = input("Masukkan ID channel: ")
    
    if use_reply:
        use_google_ai = input("Ingin menggunakan Google Gemini AI? (y/n): ").lower() == 'y'
        read_delay = int(input("Set Delay Membaca Pesan Terbaru (dalam detik): "))
        reply_delay = int(input("Set Delay Balas Pesan (dalam detik): "))

        log_message("Mode reply aktif...")
        auto_reply(channel_id, read_delay, reply_delay, use_google_ai)
    else:
        send_interval = int(input("Set Interval Pengiriman Pesan (dalam detik): "))

        log_message("Mode kirim pesan acak aktif...")
        auto_send_messages(channel_id, send_interval)
