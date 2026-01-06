from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    bybit_api_key: str = Field(default="", description="Bybit API Key")
    bybit_api_secret: str = Field(default="", description="Bybit API Secret")
    bybit_testnet: bool = Field(default=True, description="Use Bybit testnet")

    twelve_data_api_key: str = Field(default="", description="Twelve Data API Key for DXY")
    coingecko_api_key: str = Field(default="", description="CoinGecko API Key")
    news_api_key: str = Field(default="", description="News API Key")

    host: str = Field(default="0.0.0.0", description="FastAPI host")
    port: int = Field(default=8000, description="FastAPI port")
    debug: bool = Field(default=True, description="Debug mode")

    max_position_size: float = Field(default=1000.0, description="Max position size in USD")
    base_risk_percent: float = Field(default=1.0, description="Base risk percentage")
    max_daily_loss: float = Field(default=5.0, description="Max daily loss percentage")

    @property
    def bybit_rest_url(self) -> str:
        from .constants import BYBIT_REST_TESTNET_URL, BYBIT_REST_URL
        return BYBIT_REST_TESTNET_URL if self.bybit_testnet else BYBIT_REST_URL

    @property
    def bybit_ws_public_url(self) -> str:
        from .constants import BYBIT_WS_TESTNET_PUBLIC_URL, BYBIT_WS_PUBLIC_URL
        return BYBIT_WS_TESTNET_PUBLIC_URL if self.bybit_testnet else BYBIT_WS_PUBLIC_URL

    @property
    def bybit_ws_private_url(self) -> str:
        from .constants import BYBIT_WS_TESTNET_PRIVATE_URL, BYBIT_WS_PRIVATE_URL
        return BYBIT_WS_TESTNET_PRIVATE_URL if self.bybit_testnet else BYBIT_WS_PRIVATE_URL


settings = Settings()
