import aiohttp

from bot.api.http import make_request


async def get_combo_cards(http_client: aiohttp.ClientSession) -> dict:
    return await make_request(
        http_client,
        'POST',
        'https://api21.datavibe.top/api/GetCombo',
        {},
        'getting Combo Cards',
    )


async def claim_daily_combo(
        http_client: aiohttp.ClientSession
) -> bool:
    url = 'https://api.hamsterkombatgame.io/clicker/claim-daily-combo'
    response = await http_client.request(method='OPTIONS', url=url, json={}, ssl=False)

    response_json = await make_request(
        http_client,
        'POST',
        url,
        {},
        'Claim Daily Combo',
    )
    return bool(response_json)
