from time import time
from typing import Any
from bot.utils.logger import logger
import aiohttp

from bot.api.http import make_request


async def get_version_config(
        http_client: aiohttp.ClientSession, config_version: str
) -> dict[Any, Any] | Any:

    url=f'https://api.hamsterkombatgame.io/clicker/config/{config_version}'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)
    
    response_json = await make_request(
        http_client,
        'GET',
        url,
        {},
        'getting Version Config',
    )
    version_config = response_json.get('config')

    return version_config


async def get_game_config(
        http_client: aiohttp.ClientSession,
) -> dict[Any, Any] | Any:
    
    url='https://api.hamsterkombatgame.io/clicker/config'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)
    
    response_json = await make_request(
        http_client,
        'POST',
        url,
        {},
        'getting Game Config',
    )

    return response_json


async def get_profile_data(http_client: aiohttp.ClientSession) -> dict[str]:
    while True:
    
        url='https://api.hamsterkombatgame.io/clicker/sync'
        response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)
        
        response_json = await make_request(
            http_client,
            'POST',
            url,
            {},
            'getting Profile Data',
            ignore_status=422,
        )

        profile_data = response_json.get('clickerUser') or response_json.get('found', {}).get('clickerUser', {})

        return profile_data


async def get_ip_info(
        http_client: aiohttp.ClientSession
) -> dict:
    url = 'https://api.hamsterkombatgame.io/ip'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)

    response_json = await make_request(
        http_client,
        'POST',
        url,
        {},
        'getting Ip Info',
    )
    return response_json


async def get_account_info(
        http_client: aiohttp.ClientSession
) -> dict:
    url = 'https://api.hamsterkombatgame.io/auth/account-info'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)
    
    response_json = await make_request(
        http_client,
        'POST',
        url,
        {},
        'getting Account Info',
    )
    return response_json


async def get_skins(
        http_client: aiohttp.ClientSession
) -> dict:

    url='https://api.hamsterkombatgame.io/clicker/get-skin'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)
    
    response_json = await make_request(
        http_client,
        'POST',
        url,
        {},
        'getting Skins',
    )
    return response_json


async def send_taps(
        http_client: aiohttp.ClientSession, available_energy: int, taps: int
) -> dict[Any, Any] | Any:

    url='https://api.hamsterkombatgame.io/clicker/tap'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)
    
    response_json = await make_request(
        http_client,
        'POST',
        url,
        {
            'availableTaps': available_energy,
            'count': taps,
            'timestamp': int(time()),
        },
        'Tapping',
        ignore_status=422,
    )

    profile_data = response_json.get('clickerUser') or response_json.get('found', {}).get('clickerUser', {})

    return profile_data
