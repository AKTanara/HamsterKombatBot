import heapq
import asyncio
import warnings
import calendar
import time
from random import randint
from datetime import datetime, timedelta

import uuid
import aiohttp
import aiohttp_proxy
from pyrogram import Client

from bot.config import settings
from bot.utils.logger import logger
from bot.utils.proxy import check_proxy
from bot.utils.tg_web_data import get_tg_web_data
from bot.utils.scripts import decode_cipher, get_headers, get_mini_game_cipher, get_promo_code, get_or_generate_client_id_1, get_or_generate_client_id_2
from bot.exceptions import InvalidSession

from bot.api.auth import login
from bot.api.clicker import (
    get_version_config,
    get_game_config,
    get_profile_data,
    get_ip_info,
    get_account_info,
    get_skins,
    send_taps)
from bot.api.boosts import get_boosts, apply_boost
from bot.api.upgrades import get_upgrades, buy_upgrade
from bot.api.combo import claim_daily_combo, get_combo_cards
from bot.api.cipher import claim_daily_cipher
from bot.api.promo import get_apps_info, get_promos, apply_promo
from bot.api.minigame import start_daily_mini_game, claim_daily_mini_game
from bot.api.tasks import get_tasks, get_airdrop_tasks, check_task
from bot.api.exchange import select_exchange
from bot.api.nuxt import get_nuxt_builds


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def run(self, proxy: str | None) -> None:
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        
        access_token_created_time = 0
        daily_reward_exe_day = 0
        sorted_waiting_list = None
        target_card = None
        target_time = time.time()+1000000
        target_reason = ''
        
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
            logger.info(f"{self.tg_client.name} | Run for <lw>{random_delay} s</lw>")

            await asyncio.sleep(delay=random_delay)

        headers = get_headers(name=self.tg_client.name)
        proxy_conn = aiohttp_proxy.ProxyConnector().from_url(proxy) if proxy else None
        http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)
        if proxy : await check_proxy(http_client=http_client, proxy=proxy, session_name=self.session_name)
        tg_web_data = await get_tg_web_data(tg_client=self.tg_client, proxy=proxy, session_name=self.session_name)

        if not tg_web_data:
            if not http_client.closed:
                await http_client.close()
            if proxy_conn:
                if not proxy_conn.closed:
                    proxy_conn.close()
            return


        async def daily_reward():
            try:                    
                tasks = await get_tasks(http_client=http_client)
                daily_task = tasks[-1]
                is_completed = daily_task['isCompleted']
                weeks = daily_task['weeks']
                days = daily_task['days']
                nonlocal daily_reward_exe_day
                tasks_config = version_config['tasks']

                for task in tasks_config:
                    if task.get("id") == "streak_days_special":
                        for week_data in task["rewardsByWeeksAndDays"]:
                            if week_data["week"] == weeks:
                                for day_data in week_data["days"]:
                                    if day_data["day"] == days:
                                        if "coins" in day_data:
                                            reward = f"{day_data['coins']} coins"
                                        elif "keys" in day_data:
                                            reward = f"{day_data['keys']} keys"
                                        elif "skinId" in day_data:
                                            reward = f"Skin: {day_data['skinId']}"

                await asyncio.sleep(delay=2)
                if not is_completed:
                    task, profile_data = await check_task(http_client=http_client,
                                                          task_id="streak_days_special")
                    is_completed = task.get('isCompleted')

                    if is_completed:
                        daily_reward_exe_day = datetime.utcnow().day
                        logger.success(f"{self.session_name}\t | <g>Successfully get daily reward</g> | "
                                       f"Week: <lm>{weeks}</lm> Day: <lm>{days}</lm> | "
                                       f"Reward: <lg>+{reward}</lg>")
                else:
                    daily_reward_exe_day = datetime.utcnow().day
                    logger.info(f"{self.session_name}\t | Daily Reward already claimed today")
            except Exception as error:
                logger.error(f"{self.session_name}\t | Daily reward execution error: <lr>{error}</lr>")

        async def daily_reward_loop():
            while True:
                await asyncio.sleep(10)
                if (daily_reward_exe_day != datetime.utcnow().day
                    and access_token_created_time != 0):
                    await daily_reward()
                    
        async def promo_check():
                    promo_remain_local = False
                    keys_per_day_total = 0
                    keys_today_total = 0
                    promos_data = await get_promos(http_client=http_client)
                    promos = promos_data.get('promos', [])
                    promo_states = promos_data.get('states', [])
                    promo_activates = {prom['promoId']: prom['receiveKeysToday']
                                       for prom in promo_states}
                    
                    for promo in promos:
                        if promo['title']['en'] in settings.PROMO_GAMES_LIST:
                            keys_per_day_total += promo['keysPerDay'] * settings.PROMO_CODES_PERCENT // 100
                            keys_today_total += promo_activates.get(promo['promoId'], 0)
                    if (keys_per_day_total > keys_today_total):
                        promo_remain_local = True
                    logger.info(f"{self.session_name}\t | Promos <lr>{keys_today_total} of {keys_per_day_total}</lr> taken")
                    return promo_remain_local
        
        while True:
            try:
                if http_client.closed:
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()

                    proxy_conn = aiohttp_proxy.ProxyConnector().from_url(proxy) if proxy else None
                    http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)

                if time.time() - access_token_created_time >= 3600:
            
                    http_client.headers.pop('Authorization', None)
                    await get_nuxt_builds(http_client=http_client)

                    access_token = await login(
                        http_client=http_client,
                        tg_web_data=tg_web_data,
                        session_name=self.session_name)
                    
                    if not access_token:
                        return

                    http_client.headers['Authorization'] = f"Bearer {access_token}"

                    access_token_created_time = time.time()            
                    account_info = await get_account_info(http_client=http_client)
                    user_id = account_info.get('accountInfo', {}).get('id', 1)
                    profile_data = await get_profile_data(http_client=http_client)

                    config_version = http_client.headers.get('Config-Version')
                    http_client.headers.pop('Config-Version', None)
                    if config_version:
                        version_config = await get_version_config(http_client=http_client,
                                                                  config_version=config_version)

                    game_config = await get_game_config(http_client=http_client)
                    upgrades_data = await get_upgrades(http_client=http_client)
                    upgrades = upgrades_data['upgradesForBuy']
                        
                    for upgrade in upgrades:
                        upgrade['cooldownTime'] = time.time() + upgrade.get('cooldownSeconds', 0)
                    tasks = await get_tasks(http_client=http_client)
                    await get_airdrop_tasks(http_client=http_client)
                    ip_info = await get_ip_info(http_client=http_client)
                    await get_skins(http_client=http_client)

                    ip = ip_info.get('ip', 'NO')
                    country_code = ip_info.get('country_code', 'NO')
                    city_name = ip_info.get('city_name', 'NO')
                    asn_org = ip_info.get('asn_org', 'NO')

                    logger.info(f"{self.session_name}\t | IP: <lw>{ip}</lw> | Country: <le>{country_code}</le> | "
                                f"City: <lc>{city_name}</lc> | Network Provider: <lg>{asn_org}</lg>")

                    last_passive_earn = int(profile_data.get('lastPassiveEarn', 0))
                    earn_on_hour = int(profile_data.get('earnPassivePerHour', 0))
                    total_keys = profile_data.get('totalKeys', 0)

                    logger.info(f"{self.session_name}\t | Last passive earn: <lg>+{last_passive_earn:,}</lg> | "
                                f"PPH: <ly>{earn_on_hour:,}</ly> | "
                                f"TOTAL KEYS: <le>{total_keys}</le> | "
                                f"<lm>BALANCE: {int(profile_data.get('balanceCoins', 0)):,}</lm> | "
                                f"<r>TOTAL INCOME: {int(profile_data.get('totalCoins', 0)):,}</r>" )

                    availableTaps = profile_data.get('availableTaps', 0)
                    balance = int(profile_data.get('balanceCoins', 0))  
                    await daily_reward()
                    promo_remain = await promo_check()
                    
                    background_tasks_list = set()
                    refresh_upgrade_task = asyncio.create_task(daily_reward_loop())                            
                    background_tasks_list.add(refresh_upgrade_task)
                    refresh_upgrade_task.add_done_callback(background_tasks_list.discard)

                    await asyncio.sleep(delay=randint(2, 4))
                    
                    daily_cipher = game_config.get('dailyCipher')
                    if daily_cipher and settings.APPLY_DAILY_CIPHER:
                        cipher = daily_cipher['cipher']
                        bonus = daily_cipher['bonusCoins']
                        is_claimed = daily_cipher['isClaimed']

                        if not is_claimed and cipher:
                            decoded_cipher = decode_cipher(cipher=cipher)

                            status = await claim_daily_cipher(http_client=http_client, cipher=decoded_cipher)
                            if status is True:
                                logger.success(f"{self.session_name}\t | "
                                               f"Successfully claim daily cipher: <ly>{decoded_cipher}</ly> | "
                                               f"Bonus: <lg>+{bonus:,}</lg>")

                        await asyncio.sleep(delay=2)

                    await asyncio.sleep(delay=randint(2, 4))

                    daily_mini_game = game_config.get('dailyKeysMiniGames')
                    if daily_mini_game and settings.APPLY_DAILY_MINI_GAME:
                        candles_mini_game = daily_mini_game.get('Candles')
                        if candles_mini_game:
                            is_claimed = candles_mini_game['isClaimed']
                            seconds_to_next_attempt = candles_mini_game['remainSecondsToNextAttempt']
                            start_date = candles_mini_game['startDate']
                            mini_game_id = candles_mini_game['id']

                        if not is_claimed and seconds_to_next_attempt <= 0:
                            game_sleep_time = randint(12, 26)

                            encoded_body = await get_mini_game_cipher(
                                user_id=user_id,
                                start_date=start_date,
                                mini_game_id=mini_game_id,
                                score=0
                            )

                            if encoded_body:
                                await start_daily_mini_game(http_client=http_client,
                                                            mini_game_id=mini_game_id)

                                logger.info(f"{self.session_name}\t | "
                                            f"Sleep <lw>{game_sleep_time:,} s</lw> in Mini Game <lm>{mini_game_id}</lm>")
                                await asyncio.sleep(delay=game_sleep_time)

                                profile_data, daily_mini_game, bonus = await claim_daily_mini_game(
                                    http_client=http_client, cipher=encoded_body, mini_game_id=mini_game_id)

                                await asyncio.sleep(delay=2)

                                if daily_mini_game:
                                    is_claimed = daily_mini_game['isClaimed']

                                    if is_claimed:
                                        new_total_keys = profile_data.get('totalKeys', total_keys)

                                        logger.success(f"{self.session_name}\t | "
                                                       f"Successfully claimed Mini Game <lm>{mini_game_id}</lm> | "
                                                       f"Total keys: <le>{new_total_keys}</le> (<lg>+{bonus}</lg>)")
                        else:
                            if is_claimed:
                                logger.info(
                                    f"{self.session_name}\t | Daily Mini Game <lm>{mini_game_id}</lm> already claimed today")
                            elif seconds_to_next_attempt > 0:
                                logger.info(f"{self.session_name}\t | "
                                            f"Need <lw>{seconds_to_next_attempt} s</lw> to next attempt in Mini Game <lm>{mini_game_id}</lm>")
                            elif not encoded_body:
                                logger.info(
                                    f"{self.session_name}\t | Key for Mini Game <lm>{mini_game_id}</lm> is not found")

                    await asyncio.sleep(delay=randint(2, 4))

                    for _ in range(randint(a=settings.GAMES_COUNT[0], b=settings.GAMES_COUNT[1])):
                        game_config = await get_game_config(http_client=http_client)
                        daily_mini_game = game_config.get('dailyKeysMiniGames')
                        if daily_mini_game and settings.APPLY_DAILY_MINI_GAME:
                            tiles_mini_game = daily_mini_game.get('Tiles')
                            if tiles_mini_game:
                                is_claimed = tiles_mini_game['isClaimed']
                                seconds_to_next_attempt = tiles_mini_game['remainSecondsToNextAttempt']
                                start_date = tiles_mini_game['startDate']
                                mini_game_id = tiles_mini_game['id']
                                remain_points = tiles_mini_game['remainPoints']
                                max_points = tiles_mini_game['maxPoints']

                            if not is_claimed and remain_points > 0:
                                game_sleep_time = randint(a=settings.SLEEP_MINI_GAME_TILES[0],
                                                          b=settings.SLEEP_MINI_GAME_TILES[1])
                                game_score = randint(a=settings.SCORE_MINI_GAME_TILES[0],
                                                     b=settings.SCORE_MINI_GAME_TILES[1])

                                if game_score > remain_points:
                                    game_score = remain_points

                                logger.info(f"{self.session_name}\t | "
                                            f"Remain points <lg>{remain_points}/{max_points}</lg> in <lm>{mini_game_id}</lm> | "
                                            f"Sending score <lg>{game_score}</lg>")

                                encoded_body = await get_mini_game_cipher(
                                    user_id=user_id,
                                    start_date=start_date,
                                    mini_game_id=mini_game_id,
                                    score=game_score
                                )

                                if encoded_body:
                                    await start_daily_mini_game(http_client=http_client, mini_game_id=mini_game_id)

                                    logger.info(f"{self.session_name}\t | "
                                                f"Sleep <lw>{game_sleep_time} s</lw> in Mini Game <lm>{mini_game_id}</lm>")
                                    await asyncio.sleep(delay=game_sleep_time)

                                    profile_data, daily_mini_game, bonus = await claim_daily_mini_game(
                                        http_client=http_client, cipher=encoded_body, mini_game_id=mini_game_id)

                                    await asyncio.sleep(delay=2)

                                    if bonus:
                                        new_balance = int(profile_data.get('balanceCoins', 0))
                                        balance = new_balance

                                        logger.success(f"{self.session_name}\t | "
                                                       f"Successfully claimed Mini Game <lm>{mini_game_id}</lm> | "
                                                       f"Balance <le>{balance:,}</le> (<lg>+{bonus:,}</lg>)")
                            else:
                                if is_claimed or remain_points == 0:
                                    logger.info(f"{self.session_name}\t | "
                                                f"Daily Mini Game <lm>{mini_game_id}</lm> already claimed today")
                                    break
                                elif seconds_to_next_attempt > 0:
                                    logger.info(f"{self.session_name}\t | "
                                                f"Need <lw>{seconds_to_next_attempt} s</lw> to next attempt in Mini Game <lm>{mini_game_id}</lm>")
                                    break
                                elif not encoded_body:
                                    logger.info(f"{self.session_name}\t | "
                                                f"Key for Mini Game <lm>{mini_game_id}</lm> is not found")
                                    break

                    await asyncio.sleep(delay=randint(2, 4))

                    
                    if settings.AUTO_COMPLETE_TASKS:
                        tasks = await get_tasks(http_client=http_client)
                        for task in tasks:
                            task_id = task['id']
                            is_completed = task['isCompleted']
                            
                            tasks_config = version_config['tasks']
                            for task_config in tasks_config:
                                if task_config['id'] == task_id:
                                    amount_reward = int(task_config.get('rewardCoins', 0))

                            if not task_id.startswith('hamster_youtube'):
                                continue

                            if not is_completed and amount_reward > 0:
                                logger.info(f"{self.session_name}\t | "
                                            f"Sleep <lw>3s</lw> before complete <ly>{task_id}</ly> task")
                                await asyncio.sleep(delay=3)

                                task, profile_data = await check_task(http_client=http_client, task_id=task_id)
                                is_completed = task.get('isCompleted')

                                if is_completed:
                                    balance = int(profile_data.get('balanceCoins', 0))
                                    logger.success(f"{self.session_name}\t | "
                                                   f"Successfully completed <ly>{task_id}</ly> task | "
                                                   f"Balance: <lc>{balance:,}</lc> (<lg>+{amount_reward:,}</lg>)")

                                    tasks = await get_tasks(http_client=http_client)
                                else:
                                    logger.info(f"{self.session_name}\t | Task <ly>{task_id}</ly> is not complete")

                        #await get_upgrades(http_client=http_client)

                    await asyncio.sleep(delay=randint(2, 4))

                    exchange_id = profile_data.get('exchangeId')
                    if not exchange_id:
                        status = await select_exchange(http_client=http_client, exchange_id='bybit')
                        if status is True:
                            logger.success(f"{self.session_name}\t | Successfully selected exchange <ly>Bybit</ly>")

                    await asyncio.sleep(delay=randint(2, 4))

                
                            
                            
                async def promo_func(count):
                    nonlocal balance, total_keys, promo_remain
                    promo_remain_local = False
                    promos_data = await get_promos(http_client=http_client)
                    promo_states = promos_data.get('states', [])

                    promo_activates = {promo['promoId']: promo['receiveKeysToday']
                                       for promo in promo_states}

                    count_in_round = 0
                    
                    apps_info = await get_apps_info(http_client=http_client)
                    apps = {
                        app['promoId']: {
                            'appToken': app['appToken'],
                            'event_timeout': app['minWaitAfterLogin']
                        } for app in apps_info
                    }

                    promos = promos_data.get('promos', [])
                    
                    for promo in promos:
                        if promo['title']['en'] in settings.PROMO_GAMES_LIST and count_in_round < count:
                            
                            promo_id = promo['promoId']

                            app = apps.get(promo_id)

                            if not app:
                                continue

                            app_token = app.get('appToken')
                            event_timeout = app.get('event_timeout')

                            if not app_token:
                                continue

                            title = promo['title']['en']

                            today_promo_activates_count = promo_activates.get(promo_id, 0)
                            keys_per_day = promo['keysPerDay'] * settings.PROMO_CODES_PERCENT // 100
                            if (keys_per_day > today_promo_activates_count):
                                promo_remain_local = True


                            if today_promo_activates_count >= keys_per_day:
                                logger.info(f"{self.session_name}\t | "
                                            f"Promo Codes already claimed for <lm>{title}</lm> | <le>{today_promo_activates_count} of {keys_per_day}</le> <lr>(Max:{promo['keysPerDay']})</lr>")
                            else:
                                logger.info(f"{self.session_name}\t | "
                                            f"Getting Promo Codes for <lm>{title}</lm> | <le>{keys_per_day}</le> <lr>(Max:{promo['keysPerDay']})</lr> | <y>{today_promo_activates_count}</y> already taken")
                                while today_promo_activates_count < keys_per_day and count_in_round < count:
                                    
                                    promo_code = await get_promo_code(app_token=app_token,
                                                                      promo_id=promo_id,
                                                                      promo_title=title,
                                                                      max_attempts=30,
                                                                      event_timeout=event_timeout,
                                                                      session_name=self.session_name,
                                                                      proxy=proxy)

                                    if not promo_code:
                                        break

                                    temp_delay = randint(20,30)
                                    logger.info(f"{self.session_name}\t | Waiting <le>{temp_delay} s</le> before applying promo code")
                                    await asyncio.sleep(temp_delay)
                                    profile_data, promo_state, reward_promo = await apply_promo(http_client=http_client,
                                                                                                promo_code=promo_code)

                                    if profile_data and promo_state:
                                        balance = int(profile_data.get('balanceCoins', balance))
                                        total_keys = profile_data.get('totalKeys', total_keys)
                                        today_promo_activates_count = promo_state.get('receiveKeysToday',
                                                                                      today_promo_activates_count)

                                        type_reward = reward_promo.get('type', 'None')
                                        amount_reward = reward_promo.get('amount', 0)

                                        logger.success(f"{self.session_name}\t | "
                                                       f"Successfully activated promo code in <lm>{title}</lm> | "
                                                       f"<ly>{today_promo_activates_count}</ly><lw>/</lw><ly>{keys_per_day}</ly> keys | "
                                                       f"<lg>+{amount_reward:,} {type_reward}</lg> | "
                                                       f"Total keys: <le>{total_keys}</le> Balance: <lc>{balance:,}</lc>")
                                        count_in_round+=1
                                        
                                    else:
                                        logger.info(f"{self.session_name}\t | "
                                                    f"Promo code <lc>{promo_code}</lc> was wrong in <lm>{title}</lm> game | "
                                                    f"Trying again...")

                                    await asyncio.sleep(delay=1)   #Pause before next code
                            await asyncio.sleep(delay=1)     #Pause before next game
                    await asyncio.sleep(delay=randint(2, 4))
                    return promo_remain_local


                if settings.AUTO_UPGRADE:
                    if (settings.TARGETING 
                        and settings.TARGET_VALUE > earn_on_hour * (45/24) * (settings.TARGET_TIME - time.time()) / 3600):
                        logger.info(f"{self.session_name}\t | <r>---- TO REACH TARGET, CARD UPGRADES DISABLED except fast returning cards!!! ----</r>")    
                        min_ratio = (24/45) * (settings.TARGET_TIME - time.time()) / 3600
                    else:
                        min_ratio = 1000000
                    while True:
                        
                        #for data in upgrades:
                            #logger.success(f"<le>{data['name']}</le> <lc>{data['price']}</lc> <lg>{data['profitPerHourDelta']}</lg> <ly>{data['price']//max(1,data['profitPerHourDelta'])}</ly>   {data.get('cooldownSeconds', 0)}")
                            #logger.success(f"{data}")

                        available_upgrades = [
                            data for data in upgrades
                            if data['isAvailable'] is True
                               and data['isExpired'] is False
                               and data.get('maxLevel', data['level']) >= data['level']
                        ]

                        #for data in available_upgrades:
                        #    logger.success(f"<le>{data['name']}</le> <le>{data['id']}</le> <lc>{data['price']:,}</lc> <lg>{data['profitPerHourDelta']:,}</lg> <ly>{data['price']//max(1,data['profitPerHourDelta']):,}</ly>")

                        queue_sig = []
                        queue_exp = []
                        
                        for upgrade in available_upgrades:
                            upgrade_id = upgrade['id']
                            level = upgrade['level']
                            price = upgrade['price']
                            profit = upgrade['profitPerHourDelta']                            
                            coot_time = upgrade['cooldownTime']
                            exp_time = calendar.timegm(time.strptime(upgrade.get('expiresAt',"2025-12-01T00:00:00.000Z"), "%Y-%m-%dT%H:%M:%S.%fZ"))

                            significance = price / max(profit, 1)
                            
                            heapq.heappush(queue_exp, (exp_time, upgrade_id, upgrade))
                            if (profit > settings.MIN_PROFIT
                                and level <= settings.MAX_LEVEL
                                and price <= settings.MAX_PRICE
                                and (price/profit) < min_ratio):
                                heapq.heappush(queue_sig, (significance, upgrade_id, upgrade))

                        if not queue_sig:
                            break

                        sorted_sig = heapq.nsmallest(10, queue_sig)
                        sorted_exp = heapq.nsmallest(len(queue_exp), queue_exp)
                        
                        #for mData in sorted_sig:
                        #    data=mData[2]
                        #    logger.info(f"{self.session_name}\t | "
                        #                   f"  >>>  <lr>{data['name']}</lr> "
                                           #f"<le>{data['id']}</le> "
                        #                   f"<lc>Price:{data['price']:,}</lc> "
                        #                   f"<lg>Profit:{data['profitPerHourDelta']:,}</lg> "
                        #                   f"<ly>Ratio:{data['price'] / max(1,data['profitPerHourDelta']):,.3f}</ly> "
                        #                   f"<lr>Cool:{int(data['cooldownTime']-time.time()):,}</lr>")

                        profile_data = await send_taps(
                            http_client=http_client,
                            available_energy=availableTaps,
                            taps=1,
                        )
                        earn_on_hour = int(profile_data.get('earnPassivePerHour', 0))
                        balance = int(profile_data.get('balanceCoins', 0))
                        free_money = balance - settings.BALANCE_TO_SAVE
                        
                        cool_down = 0
                        price_acc = 0
                        upgrade_id = ''
                        waiting_list = []
                        inspect_list = []
                        for card in sorted_sig:
                            if card[2]['cooldownTime'] > time.time() :
                                cool_down = max (cool_down, card[2]['cooldownTime'] - time.time())
                                price_acc += card[2]['price']
                                heapq.heappush(waiting_list, (card[2]['cooldownTime'], card[1], card[2], 'TIMER'))
                                #heapq.heappush(inspect_list, (card[2]['cooldownTime'], card[1], card[2]))
                            else:
                                if (card[2]['price'] > free_money):
                                    #logger.info(f"{self.session_name}\t | Not enough balance to buy <m>{card[2]['name']}</m>")
                                    
                                    #print('')
                                    #print(f'name: {card[2]["name"]}')
                                    #print(f'card price: {card[2]["price"]}')
                                    #print(f'free money: {free_money}')
                                    #print(f'difference: {card[2]["price"]-free_money}')
                                    #print(f'PPH: {earn_on_hour}')
                                    #print(f'seconds: {(card[2]["price"] - free_money) * 3600 / earn_on_hour}')
                                    time_mark = ((card[2]['price'] - free_money) * 3600 / earn_on_hour ) + time.time() + 1
                                    heapq.heappush(waiting_list, (time_mark, card[1], card[2], 'MINING'))
                                elif (card[2]['price'] + price_acc - free_money > cool_down * earn_on_hour / 3600):
                                    a=2
                                    #logger.info(f"{self.session_name}\t | First available card is not good enought to buy")
                                else:
                                    upgrade_id = card[2]['id']
                                    upgrade_name = card[2]['name']
                                    upgrade_level = card[2]['level']
                                    upgrade_price = card[2]['price']
                                    upgrade_profit = card[2]['profitPerHourDelta']
                                break
                        
                                
                        if (upgrade_id):
                            logger.info(f"{self.session_name}\t | "
                                        f"In <lw>{settings.SLEEP_BEFORE_EACH_CARD_UPGRADE}s</lw> "
                                        f"upgrade <le>{upgrade_name}</le> "
                                        f"<ly>lvl:{upgrade_level}</ly> "
                                        f"<lr>Price: {upgrade_price:,}</lr> <lg>Profit: {upgrade_profit:,}</lg> "
                                        f"<ly>Ratio: {upgrade_price//max(1,upgrade_profit):,}</ly>")
                            await asyncio.sleep(settings.SLEEP_BEFORE_EACH_CARD_UPGRADE)
                            status, upgrades = await buy_upgrade(http_client=http_client, upgrade_id=upgrade_id)
                            
                            for upgrade in upgrades:
                                upgrade['cooldownTime'] = time.time() + upgrade.get('cooldownSeconds', 0)
                            if status:
                                earn_on_hour += upgrade_profit
                                balance -= upgrade_price
                                logger.success(f"{self.session_name}\t | "
                                        f"Successfully upgraded <le>{upgrade_name}</le> "
                                        f"Money left: <lr>{balance:,}</lr>")
                                await asyncio.sleep(delay=1)
                            else:
                                logger.error(f"{self.session_name}\t | ISSUE upgrading <le>{upgrade_name}</le>")
                        
                        else:
                            sorted_waiting_list = heapq.nsmallest(len(waiting_list), waiting_list)
                            target_reason = None
                            target_time = time.time()+1000000
                            target_card = None
                            target_reason = ''
                            #print('')
                            #print('waiting list:')
                            #for tData in sorted_waiting_list:
                            #    print(f'{tData[2]["name"]:<30} {int(tData[0]-time.time()):<10} {time.strftime("%H:%M:%S", time.localtime(tData[0]))}')
                            #print('')
                            
                            for future in sorted_waiting_list:
                                assum_time = future[0]
                                assum_free_money = free_money + (assum_time - time.time()) * earn_on_hour / 3600
                                for card in sorted_sig:
                                    if (card[2]['cooldownTime'] <= assum_time 
                                        and card[2]['price'] <= assum_free_money):
                                        target_card = card[2]
                                        target_time = assum_time
                                        target_reason = future[3]
                                        #logger.info(f'<r>FOUND NEXT TARGET:</r> <m>{target_card["name"]}</m> '
                                        #            f'<lr>in: {time.strftime("%H:%M:%S", time.localtime(target_time))}</lr> '
                                        #            f'<ly>Ratio: {card[2]["price"]//max(1,card[2]["profitPerHourDelta"])}</ly>')
                                        break
                                if target_card: break
                                
                            break
                
                random_sleep = randint(settings.SLEEP_BY_MIN_ENERGY[0], settings.SLEEP_BY_MIN_ENERGY[1])

                if (target_time < random_sleep+time.time()):
                    random_sleep = max(10, int(target_time - time.time() + 10))
                    logger.info(f"{self.session_name}\t | \t Sleep <e>{random_sleep//60}m {random_sleep%60}s</e> "
                                f"till <e>{time.strftime('%H:%M:%S', time.localtime(time.time()+random_sleep))}</e> "
                                f"for <m>{target_card['name']}</m> "
                                f"<lc>lvl: {target_card['level']}</lc> "
                                f"<ly>Ratio: {target_card['price'] // max(1,target_card['profitPerHourDelta']):,}</ly> "
                                f"({target_reason})")
                else:
                    logger.info(f"{self.session_name}\t | \t Sleep <e>{random_sleep//60}m {random_sleep%60}s</e> "
                                f"till <e>{time.strftime('%H:%M:%S', time.localtime(time.time()+random_sleep))}</e>")
                
                if (random_sleep > 500 and settings.APPLY_PROMO_CODES and promo_remain):
                    random_sleep_time = random_sleep + time.time()
                    rounds = min(settings.MAX_PROMO_CODES_EACH_ROUND, random_sleep//500)
                    logger.info(f"{self.session_name}\t | Getting <lm>{rounds}</lm> Promo Codes in between!")
                    await promo_func(rounds)
                    random_sleep = int(max(1, random_sleep_time - time.time()))
                    logger.info(f"{self.session_name}\t | \t Continuing Sleep <e>{random_sleep//60}m {random_sleep%60}s</e> "
                                f"till <e>{time.strftime('%H:%M:%S', time.localtime(time.time()+random_sleep))}</e> "
                                f"for <m>{target_card['name']}</m> "
                                f"<lc>lvl: {target_card['level']}</lc> "
                                f"<ly>Ratio: {target_card['price'] // max(1,target_card['profitPerHourDelta']):,}</ly> "
                                f"({target_reason})")
                    
                if random_sleep > 1000:
                    access_token_created_time = 0
                    await http_client.close()
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()
                                       

                await asyncio.sleep(delay=random_sleep)


#            except InvalidSession as error:
#                raise error

            except Exception as error:
                logger.error(f"{self.session_name}\t | Unknown error: {error}")
                access_token_created_time = 0
                await http_client.close()
                if proxy_conn:
                    if not proxy_conn.closed:
                        proxy_conn.close()
                await asyncio.sleep(delay=60)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
