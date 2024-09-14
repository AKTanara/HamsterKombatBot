import aiohttp

from bot.api.http import make_request


async def select_exchange(
        http_client: aiohttp.ClientSession, exchange_id: str
) -> bool:
    url = 'https://api.hamsterkombatgame.io/clicker/select-exchange'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)

    response_json = await make_request(
        http_client,
        'POST',
        url,
        {'exchangeId': exchange_id},
        'Select Exchange',
    )
    return bool(response_json)
