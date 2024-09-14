from time import time
from typing import Any

import aiohttp

from bot.api.http import make_request


async def get_upgrades(
        http_client: aiohttp.ClientSession
) -> dict:
    
    url = 'https://api.hamsterkombatgame.io/clicker/upgrades-for-buy'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)
    
    response_json = await make_request(
        http_client,
        'POST',
        url,
        {},
        'getting Upgrades',
    )

    return response_json


async def buy_upgrade(
        http_client: aiohttp.ClientSession, upgrade_id: str
) -> tuple[bool, Any] | tuple[bool, None]:
    
    url = 'https://api.hamsterkombatgame.io/clicker/buy-upgrade'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)

    response_json = await make_request(
        http_client,
        'POST',
        url,
        {'timestamp': int(time()), 'upgradeId': upgrade_id},
        'buying Upgrade',
        ignore_status=422,
    )

    upgrades = response_json.get('upgradesForBuy') or response_json.get('found', {}).get('upgradesForBuy', {})

    return True, upgrades
