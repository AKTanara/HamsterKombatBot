import os
import glob
import time
import uuid
import random
import string
import base64
import asyncio
import hashlib
import datetime

import aiohttp
import aiohttp_proxy
from fake_useragent import UserAgent
from playwright.async_api import async_playwright

from bot.config import settings
from bot.utils.logger import logger
from bot.utils.json_db import JsonDB
from bot.utils.default import DEFAULT_HEADERS, DEFAULT_FINGERPRINT


def get_session_names():
    names = [os.path.splitext(os.path.basename(file))[0] for file in glob.glob('sessions/*.session')]

    return names


def generate_random_visitor_id():
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    visitor_id = hashlib.md5(random_string.encode()).hexdigest()

    return visitor_id


def escape_html(text: str):
    return text.replace('<', '\\<').replace('>', '\\>')


def decode_cipher(cipher: str):
    encoded = cipher[:3] + cipher[4:]
    return base64.b64decode(encoded).decode('utf-8')
    

def get_headers(name: str):
    db = JsonDB("profiles")

    profiles = db.get_data()

    headers = profiles.get(name, {}).get('headers', DEFAULT_HEADERS)

    if settings.USE_RANDOM_USERAGENT:
        android_version = random.randint(24, 33)
        webview_version = random.randint(70, 125)

        headers['Sec-Ch-Ua'] = (
            f'"Android WebView";v="{webview_version}", '
            f'"Chromium";v="{webview_version}", '
            f'"Not?A_Brand";v="{android_version}"'
        )
        headers['User-Agent'] = get_mobile_user_agent()

        if not profiles.get(name):
            profiles[name] = {"proxy": "", "headers": headers}
        else:
            profiles[name]["headers"] = headers

        db.save_data(profiles)

    return headers


def get_fingerprint(name: str):
    db = JsonDB("profiles")

    profiles = db.get_data()
    fingerprint = profiles.get(name, {}).get('fingerprint', DEFAULT_FINGERPRINT)
    fingerprint['visitorId'] = generate_random_visitor_id()

    return fingerprint


def get_mobile_user_agent():
    ua = UserAgent(platforms=['mobile'], os=['android'])
    user_agent = ua.random
    if 'wv' not in user_agent:
        parts = user_agent.split(')')
        parts[0] += '; wv'
        user_agent = ')'.join(parts)
    return user_agent


def generate_client_id():
    time_ms = int(time.time() * 1000)
    rand_num = "34" + str(random.randint(10000000000000000, 99999999999999999))
    return f"{time_ms}-{rand_num}"

def get_or_generate_client_id(name: str, game: str):

    game = game.lower().replace(' ','_')
    db = JsonDB("profiles")
    profiles = db.get_data()
    user_id = profiles.get(name, {}).get(game+'_client_id', '')
    
    if user_id:
        return user_id
    else:
        time_ms = int(time.time() * 1000)
        rand_num = "34" + str(random.randint(10000000000000000, 99999999999999999))
        user_id = f"{time_ms}-{rand_num}"
        profiles[name][game+'_client_id'] = user_id
        db.save_data(profiles)
        return user_id

def get_or_generate_client_id_1(name: str):

    db = JsonDB("profiles")
    profiles = db.get_data()
    user_id = profiles.get(name, {}).get('promo_client_id', '')
    
    if user_id:
        return user_id
    else:
        time_ms = int(time.time() * 1000)
        rand_num = "34" + str(random.randint(10000000000000000, 99999999999999999))
        user_id = f"{time_ms}-{rand_num}"
        profiles[name]['promo_client_id'] = user_id
        db.save_data(profiles)
        return user_id

def get_or_generate_client_id_2(name: str, game: str):

    game = game.lower().replace(' ','_')
    db = JsonDB("profiles")
    profiles = db.get_data()
    user_id = profiles.get(name, {}).get(game+'_client_id', '')
    
    if user_id:
        return user_id
    else:
        new_user_id = str(uuid.uuid4())
        profiles[name][game+'_client_id'] = new_user_id
        db.save_data(profiles)
        return new_user_id


def generate_event_id():
    return str(uuid.uuid4())

def store_code(name:str, code:str):
    file = open(f"#_{name}_codes.txt", 'a')
    file.write(f"{code}\n")
    file.close()
    
async def get_promo_code(app_token: str,
                         promo_id: str,
                         promo_title: str,
                         max_attempts: int,
                         event_timeout: int,
                         session_name: str,
                         proxy: str):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Host": "api.gamepromo.io"
    }

    proxy_conn = aiohttp_proxy.ProxyConnector().from_url(proxy) if proxy else None

    async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
        client_id = get_or_generate_client_id(session_name, promo_title)
        #client_id = get_or_generate_client_id_1(session_name)

        json_data = {
            "appToken": app_token,
            "clientId": client_id,
            "clientOrigin": "deviceid"
        }

        response = await http_client.post(url="https://api.gamepromo.io/promo/login-client", json=json_data)

        response_text = await response.text()
        response_json = await response.json()
        access_token = response_json.get("clientToken")

        if not access_token:
            logger.debug(f"{session_name}\t | Can't login to api.gamepromo.io | Try with proxy | "
                         f"Response text: {escape_html(response_text)[:256]}...")
            return

        http_client.headers["Authorization"] = f"Bearer {access_token}"

        await asyncio.sleep(delay=5)

        attempts = 0
        tries = 0
        while attempts < max_attempts:
            tries +=1 
            try:

                event_id = generate_event_id()
                json_data = {
                    "promoId": promo_id,
                    "eventId": event_id,
                    "eventOrigin": "undefined"
                }

                response = await http_client.post(url="https://api.gamepromo.io/promo/register-event", json=json_data)

                await asyncio.sleep(delay=1)
                response_json = await response.json()
                has_code = response_json.get("hasCode", False)
                
                if has_code:
                    json_data = {
                        "promoId": promo_id
                    }

                    response = await http_client.post(url="https://api.gamepromo.io/promo/create-code", json=json_data)
                    response.raise_for_status()

                    response_json = await response.json()
                    promo_code = response_json.get("promoCode")

                    if promo_code:
                        store_code(session_name,promo_code)
                        logger.info(f"{session_name}\t | "
                                    f"Promo code is found for <lm>{promo_title}</lm>: <lc>{promo_code}</lc>")
                        return promo_code
            except Exception as error:
                logger.debug(f"{session_name}\t | Error while getting promo code: {error} <lr>sleeping 10s</lr>")
                if tries>5:
                    logger.debug(f"{session_name}\t | More than 5 tries, RAISING error: {error}")
                    raise
                await asyncio.sleep(20*tries)
                continue

            attempts += 1
            new_event_timeout=event_timeout+random.randint(20, 30)
            logger.debug(
                f"{session_name}\t | Attempt <lr>{attempts}</lr> was successful for <lm>{promo_title}</lm> | "
                f"Sleep <lw>{new_event_timeout}s</lw> before attempt <lr>{attempts + 1}</lr>")
            await asyncio.sleep(delay=new_event_timeout)

    logger.debug(f"{session_name}\t | "
                 f"Promo code not found out of <lw>{max_attempts}</lw> attempts for <lm>{promo_title}</lm> game ")


async def get_game_cipher(start_number: str):
    magic_index = int(start_number % (len(str(start_number)) - 2))
    res = ""
    for i in range(len(str(start_number))):
        res += '0' if i == magic_index else str(int(random.random() * 10))
    return res


async def get_mini_game_cipher(user_id: int,
                               start_date: str,
                               mini_game_id: str,
                               score: int):
    secret1 = "R1cHard_AnA1"
    secret2 = "G1ve_Me_y0u7_Pa55w0rD"

    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%fZ")

    start_number = int(start_dt.replace(tzinfo=datetime.timezone.utc).timestamp())
    cipher_score = (start_number + score) * 2

    combined_string = f'{secret1}{cipher_score}{secret2}'

    sig = hashlib.sha256(combined_string.encode()).digest()
    sig = base64.b64encode(sig).decode()

    game_cipher = await get_game_cipher(start_number=start_number)

    data = f'{game_cipher}|{user_id}|{mini_game_id}|{cipher_score}|{sig}'

    encoded_data = base64.b64encode(data.encode()).decode()

    return encoded_data
