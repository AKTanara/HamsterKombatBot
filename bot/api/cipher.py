import aiohttp

from bot.api.http import make_request


async def claim_daily_cipher(
        http_client: aiohttp.ClientSession, cipher: str
) -> bool:
    url = 'https://api.hamsterkombatgame.io/clicker/claim-daily-cipher'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)

    response_json = await make_request(
        http_client,
        'POST',
        url,
        {'cipher': cipher},
        'Claim Daily Cipher',
    )

    return bool(response_json)
