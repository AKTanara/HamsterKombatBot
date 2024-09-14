from time import time

import aiohttp

from bot.api.http import make_request


async def get_boosts(
        http_client: aiohttp.ClientSession
) -> list[dict]:
    url = 'https://api.hamsterkombatgame.io/clicker/boosts-for-buy'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)

    response_json = await make_request(
        http_client,
        'POST',
        url,
        {},
        'getting Boosts',
    )

    boosts = response_json.get('boostsForBuy', [])

    return boosts


async def apply_boost(
        http_client: aiohttp.ClientSession, boost_id: str
) -> bool:
    url = 'https://api.hamsterkombatgame.io/clicker/buy-boost'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)

    response_json = await make_request(
        http_client,
        'POST',
        url,
        {'timestamp': int(time()), 'boostId': boost_id},
        'Apply Boost',
    )

    return bool(response_json)
