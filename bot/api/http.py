import json
import asyncio

import aiohttp

from bot.utils.logger import logger
from bot.utils.scripts import escape_html
from bot.config import settings

async def make_request(
        http_client: aiohttp.ClientSession,
        method: str,
        url: str,
        json_data: dict,
        error_context: str,
        ignore_status: int | None = None,
) -> dict:

    response_text = ''
    response_stat = ''
    
    async def req(
            http_client: aiohttp.ClientSession,
            method: str,
            url: str,
            json_data: dict,
            error_context: str,
            ignore_status: int | None = None,
    ) -> dict:
        nonlocal response_text, response_stat
        response_text = ''
        response = await http_client.request(method=method, url=url, json=json_data, ssl=False)

        config_version = response.headers.get('Config-Version')
        if config_version and not http_client.headers.get('Config-Version'):
            http_client.headers['Config-Version'] = config_version

        response_text = await response.text()
        response_stat = response.status
        if ignore_status is None or response.status != ignore_status:
            response.raise_for_status()
        response_json = json.loads(response_text)
        return response_json


    for i in range(settings.NETWORK_RETRYS+1):
        try:
            return await req(http_client=http_client, method=method, url=url, json_data=json_data, error_context=error_context, ignore_status=ignore_status)
        except Exception as error:
            if i == settings.NETWORK_RETRYS:
                raise
            await handle_error(i+1, error, response_text, error_context, response_stat)
            await asyncio.sleep(delay=5)


#    try:
#        return await req(http_client=http_client, method=method, url=url, json_data=json_data, error_context=error_context, ignore_status=ignore_status)
#    except Exception as error:
#        print('FIRST TRY ERROR, Trying one more time... in 10s')
#        await handle_error(error, response_text, error_context, response.status)
#        await asyncio.sleep(delay=10)
#        try:
#            return await req(http_client=http_client, method=method, url=url, json_data=json_data, error_context=error_context, ignore_status=ignore_status)
#        except Exception as error:
#            print('SECOND TRY ERROR, raising error...')
#            await handle_error(error, response_text, error_context, response.status)
#            raise


async def handle_error(i: int, error: Exception, response_text: str, context: str, status: str):
    logger.error(
        f'<lr>RETRY {i} of {settings.NETWORK_RETRYS}</lr> | '
        f'Unknown error while {context}: {error} '
#        f'Response text: {escape_html(response_text)[:256]}...'
        f'Response text: {escape_html(response_text)}...'
        f'Response status: {status}'
    )
    await asyncio.sleep(delay=3)
