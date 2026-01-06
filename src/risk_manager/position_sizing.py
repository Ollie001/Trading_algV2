"""
Module 8: Risk Manager
Dynamic position sizing based on regime, account balance, and trade setup
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from src.models import RegimeOutput
from src.execution_engine import ExecutionSignal
from src.config import RISK_THRESHOLDS, settings

logger = logging.getLogger(__name__)


@dataclass
class PositionSize:
    """Calculated position size"""
    quantity: float  # BTC quantity
    notional_value: float  # USD value
    risk_amount: float  # USD at risk (to stop loss)
    risk_percent: float  # % of account at risk
    stop_distance: float  # Distance to stop in USD
    reward_ratio: float  # Reward:Risk ratio
    approved: bool
    rejection_reason: Optional[str] = None


class RiskManager:
    """
    Manages position sizing and risk limits.

    Dynamic sizing based on:
    - Regime state (multiplier from permissions)
    - Signal confidence
    - Account balance
    - Stop loss distance
    - Maximum risk per trade
    - Daily loss limits
    """

    def __init__(self, account_balance: float = None):
        self.account_balance = account_balance or settings.max_position_size
        self.base_risk_percent = settings.base_risk_percent
        self.max_daily_loss_percent = settings.max_daily_loss
        self.max_open_positions = RISK_THRESHOLDS["max_open_positions"]
        self.min_risk_reward = RISK_THRESHOLDS["min_risk_reward_ratio"]

        self.daily_pnl = 0.0
        self.trade_count_today = 0
        self.open_positions = 0

        self.last_reset = datetime.now().date()

    def _reset_daily_stats(self):
        """Reset daily statistics at start of new day"""
        today = datetime.now().date()
        if today > self.last_reset:
            logger.info(f"Resetting daily stats. Previous PnL: ${self.daily_pnl:.2f}")
            self.daily_pnl = 0.0
            self.trade_count_today = 0
            self.last_reset = today

    def update_account_balance(self, new_balance: float):
        """Update account balance"""
        self.account_balance = new_balance
        logger.info(f"Account balance updated: ${new_balance:.2f}")

    def record_trade_result(self, pnl: float):
        """Record trade PnL"""
        self._reset_daily_stats()
        self.daily_pnl += pnl
        self.trade_count_today += 1
        logger.info(
            f"Trade recorded: PnL ${pnl:.2f} | "
            f"Daily PnL: ${self.daily_pnl:.2f} | "
            f"Trades today: {self.trade_count_today}"
        )

    def _check_daily_loss_limit(self) -> tuple[bool, Optional[str]]:
        """Check if daily loss limit has been hit"""
        self._reset_daily_stats()

        max_daily_loss = self.account_balance * (self.max_daily_loss_percent / 100)

        if abs(self.daily_pnl) >= max_daily_loss and self.daily_pnl < 0:
            return False, f"Daily loss limit hit: ${self.daily_pnl:.2f} / ${max_daily_loss:.2f}"

        return True, None

    def _check_open_positions_limit(self) -> tuple[bool, Optional[str]]:
        """Check if max open positions limit reached"""
        if self.open_positions >= self.max_open_positions:
            return False, f"Max open positions reached: {self.open_positions}/{self.max_open_positions}"

        return True, None

    def calculate_position_size(
        self,
        signal: ExecutionSignal,
        regime: Optional[RegimeOutput],
        current_price: float
    ) -> PositionSize:
        """
        Calculate position size for a trade signal.

        Position sizing formula:
        1. Base risk amount = account_balance * base_risk_percent
        2. Regime multiplier applied
        3. Confidence multiplier applied
        4. Position quantity = risk_amount / stop_distance
        """

        # Check daily loss limit
        can_trade, reason = self._check_daily_loss_limit()
        if not can_trade:
            return PositionSize(
                quantity=0.0,
                notional_value=0.0,
                risk_amount=0.0,
                risk_percent=0.0,
                stop_distance=0.0,
                reward_ratio=0.0,
                approved=False,
                rejection_reason=reason
            )

        # Check open positions limit
        can_trade, reason = self._check_open_positions_limit()
        if not can_trade:
            return PositionSize(
                quantity=0.0,
                notional_value=0.0,
                risk_amount=0.0,
                risk_percent=0.0,
                stop_distance=0.0,
                reward_ratio=0.0,
                approved=False,
                rejection_reason=reason
            )

        # Calculate base risk amount
        base_risk_amount = self.account_balance * (self.base_risk_percent / 100)

        # Apply regime multiplier
        regime_multiplier = 1.0
        if regime:
            regime_multiplier = regime.permissions.get("position_size_multiplier", 1.0)

        # Apply confidence multiplier (0.5 to 1.0 based on signal confidence)
        confidence_multiplier = 0.5 + (signal.confidence * 0.5)

        # Total risk amount
        risk_amount = base_risk_amount * regime_multiplier * confidence_multiplier

        # Calculate stop distance
        if not signal.stop_loss:
            return PositionSize(
                quantity=0.0,
                notional_value=0.0,
                risk_amount=0.0,
                risk_percent=0.0,
                stop_distance=0.0,
                reward_ratio=0.0,
                approved=False,
                rejection_reason="No stop loss defined"
            )

        stop_distance = abs(current_price - signal.stop_loss)
        stop_distance_usd = stop_distance

        if stop_distance_usd == 0:
            return PositionSize(
                quantity=0.0,
                notional_value=0.0,
                risk_amount=0.0,
                risk_percent=0.0,
                stop_distance=0.0,
                reward_ratio=0.0,
                approved=False,
                rejection_reason="Stop loss too close to entry"
            )

        # Calculate position quantity
        quantity_btc = risk_amount / stop_distance_usd
        notional_value = quantity_btc * current_price

        # Check if notional value exceeds max
        max_position = RISK_THRESHOLDS["max_position_size_usd"]
        if notional_value > max_position:
            # Scale down
            quantity_btc = max_position / current_price
            notional_value = max_position
            actual_risk = quantity_btc * stop_distance_usd
            risk_amount = actual_risk

        # Calculate risk/reward ratio
        reward_ratio = 0.0
        if signal.take_profit:
            profit_distance = abs(signal.take_profit - current_price)
            reward_ratio = profit_distance / stop_distance if stop_distance > 0 else 0.0

        # Check minimum risk/reward
        if reward_ratio < self.min_risk_reward:
            return PositionSize(
                quantity=quantity_btc,
                notional_value=notional_value,
                risk_amount=risk_amount,
                risk_percent=(risk_amount / self.account_balance) * 100,
                stop_distance=stop_distance_usd,
                reward_ratio=reward_ratio,
                approved=False,
                rejection_reason=f"Risk/reward too low: {reward_ratio:.2f} < {self.min_risk_reward}"
            )

        # Calculate actual risk percent
        risk_percent = (risk_amount / self.account_balance) * 100

        position = PositionSize(
            quantity=quantity_btc,
            notional_value=notional_value,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            stop_distance=stop_distance_usd,
            reward_ratio=reward_ratio,
            approved=True,
            rejection_reason=None
        )

        logger.info(
            f"Position Sizing: {quantity_btc:.4f} BTC (${notional_value:.2f}) | "
            f"Risk: ${risk_amount:.2f} ({risk_percent:.2f}%) | "
            f"R:R {reward_ratio:.2f} | "
            f"Regime multiplier: {regime_multiplier:.2f}"
        )

        return position

    def increment_open_positions(self):
        """Increment open positions counter"""
        self.open_positions += 1
        logger.info(f"Open positions: {self.open_positions}/{self.max_open_positions}")

    def decrement_open_positions(self):
        """Decrement open positions counter"""
        if self.open_positions > 0:
            self.open_positions -= 1
        logger.info(f"Open positions: {self.open_positions}/{self.max_open_positions}")

    def get_status(self) -> Dict[str, Any]:
        """Get risk manager status"""
        self._reset_daily_stats()

        max_daily_loss = self.account_balance * (self.max_daily_loss_percent / 100)
        daily_loss_remaining = max_daily_loss - abs(self.daily_pnl) if self.daily_pnl < 0 else max_daily_loss

        return {
            "account_balance": self.account_balance,
            "base_risk_percent": self.base_risk_percent,
            "daily_stats": {
                "pnl": self.daily_pnl,
                "trades": self.trade_count_today,
                "loss_limit": max_daily_loss,
                "loss_remaining": daily_loss_remaining,
                "limit_hit": daily_loss_remaining <= 0
            },
            "position_limits": {
                "open_positions": self.open_positions,
                "max_positions": self.max_open_positions,
                "limit_reached": self.open_positions >= self.max_open_positions
            },
            "risk_thresholds": {
                "max_position_size_usd": RISK_THRESHOLDS["max_position_size_usd"],
                "min_risk_reward": self.min_risk_reward
            }
        }
