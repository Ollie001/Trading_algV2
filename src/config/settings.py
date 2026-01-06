from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized environment-driven configuration.

    Notes:
    - All fields are loaded from `.env` (if present) and environment variables.
    - Field names map to env vars via Pydantic (e.g. `bybit_api_key` -> `BYBIT_API_KEY`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Exchange / Trading ---
    bybit_api_key: str = Field(default="", description="Bybit API Key")
    bybit_api_secret: str = Field(default="", description="Bybit API Secret")
    bybit_testnet: bool = Field(default=True, description="Use Bybit testnet")

    # --- Optional data providers ---
    twelve_data_api_key: str = Field(default="", description="Twelve Data API Key for DXY")
    alpha_vantage_api_key: str = Field(default="", description="Alpha Vantage API Key for DXY and Forex")
    coingecko_api_key: str = Field(default="", description="CoinGecko API Key")
    news_api_key: str = Field(default="", description="News API Key")

    # --- App server ---
    host: str = Field(default="0.0.0.0", description="FastAPI host")
    port: int = Field(default=8000, description="FastAPI port")
    debug: bool = Field(default=True, description="Debug mode")

    # --- Risk ---
    max_position_size: float = Field(default=1000.0, description="Max position size in USD")
    base_risk_percent: float = Field(default=1.0, description="Base risk percentage")
    max_daily_loss: float = Field(default=5.0, description="Max daily loss percentage")

    # --- Bybit WebSocket tuning (backpressure + throttling) ---
    bybit_ws_ping_interval_sec: int = Field(default=20, description="WS ping interval seconds")
    bybit_ws_connect_timeout_sec: int = Field(default=10, description="WS connect timeout seconds")
    bybit_ws_reconnect_base_delay_sec: float = Field(default=2.0, description="Reconnect base delay seconds")
    bybit_ws_reconnect_max_delay_sec: float = Field(default=60.0, description="Reconnect max delay seconds")
    bybit_ws_reconnect_jitter_sec: float = Field(default=0.5, description="Reconnect jitter seconds (+/-)")

    bybit_ws_orderbook_depth: int = Field(default=50, description="Top-N levels kept for bids/asks")
    bybit_ws_orderbook_publish_hz: float = Field(default=2.0, description="Orderbook callback rate (Hz)")
    bybit_ws_trade_publish_interval_sec: float = Field(default=0.5, description="Trade callback batching window seconds")
    bybit_ws_max_queue: int = Field(default=2000, description="Max queued items (trades/klines). Oldest dropped when full.")

    # --- Derived URLs ---
    @property
    def bybit_rest_url(self) -> str:
        from .constants import BYBIT_REST_TESTNET_URL, BYBIT_REST_URL

        return BYBIT_REST_TESTNET_URL if self.bybit_testnet else BYBIT_REST_URL

    @property
    def bybit_ws_public_url(self) -> str:
        from .constants import BYBIT_WS_PUBLIC_URL, BYBIT_WS_TESTNET_PUBLIC_URL

        return BYBIT_WS_TESTNET_PUBLIC_URL if self.bybit_testnet else BYBIT_WS_PUBLIC_URL

    @property
    def bybit_ws_private_url(self) -> str:
        from .constants import BYBIT_WS_PRIVATE_URL, BYBIT_WS_TESTNET_PRIVATE_URL

        return BYBIT_WS_TESTNET_PRIVATE_URL if self.bybit_testnet else BYBIT_WS_PRIVATE_URL


settings = Settings()
