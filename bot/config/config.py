from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int = 0
    API_HASH: str = ''

    NETWORK_RETRYS: int = 3
    MIN_AVAILABLE_ENERGY: int = 200
    SLEEP_BY_MIN_ENERGY: list[int] = [1800, 3600]

    AUTO_UPGRADE: bool = False
    MAX_LEVEL: int = 20
    MIN_PROFIT: int = 1000
    MAX_PRICE: int = 50000000
    SLEEP_BEFORE_EACH_CARD_UPGRADE: int = 10
    BALANCE_TO_SAVE: int = 1000000
    UPGRADES_COUNT: int = 10
    TARGETING: bool = False
    TARGET_VALUE: int = 0
    TARGET_TIME: int = 0

    MAX_COMBO_PRICE: int = 10000000

    APPLY_PROMO_CODES: bool = True
    PROMO_CODES_PERCENT: int = 50
    PROMO_GAMES_LIST: str = []
    MAX_PROMO_CODES_EACH_ROUND: int = 4
    APPLY_DAILY_CIPHER: bool = True
    APPLY_DAILY_REWARD: bool = True
    APPLY_DAILY_ENERGY: bool = True
    APPLY_DAILY_MINI_GAME: bool = True

    SLEEP_MINI_GAME_TILES: list[int] = [600, 900]
    SCORE_MINI_GAME_TILES: list[int] = [300, 500]
    GAMES_COUNT: list[int] = [1, 10]

    AUTO_COMPLETE_TASKS: bool = True

    USE_RANDOM_DELAY_IN_RUN: bool = False
    RANDOM_DELAY_IN_RUN: list[int] = [0, 15]

    USE_RANDOM_USERAGENT: bool = False


settings = Settings()
