"""
Module 9: Trade Manager
Handles order placement, position tracking, and trade lifecycle management
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from src.execution_engine import ExecutionSignal, SignalType
from src.risk_manager import PositionSize
from src.config import OrderSide

logger = logging.getLogger(__name__)


class PositionStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


@dataclass
class Position:
    """Active or historical position"""
    position_id: str
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    quantity: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: PositionStatus
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    signal_reason: str = ""
    order_ids: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class TradeManager:
    """
    Manages the lifecycle of trades from signal to exit.

    Responsibilities:
    - Place market orders
    - Set stop loss and take profit
    - Track open positions
    - Handle exits (stop hit, TP hit, or manual)
    - Record trade history
    - Error recovery
    """

    def __init__(self, bybit_rest_client=None):
        self.bybit_client = bybit_rest_client
        self.positions: Dict[str, Position] = {}
        self.position_counter = 0
        self.dry_run = True  # Safety: start in dry-run mode

    def enable_live_trading(self):
        """Enable live trading (disable dry-run)"""
        logger.warning("🚨 LIVE TRADING ENABLED - Real orders will be placed!")
        self.dry_run = False

    def disable_live_trading(self):
        """Disable live trading (enable dry-run)"""
        logger.info("Dry-run mode enabled - No real orders will be placed")
        self.dry_run = True

    def _generate_position_id(self) -> str:
        """Generate unique position ID"""
        self.position_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"POS_{timestamp}_{self.position_counter}"

    async def open_position(
        self,
        signal: ExecutionSignal,
        position_size: PositionSize,
        symbol: str = "BTCUSDT"
    ) -> Optional[Position]:
        """
        Open a new position based on signal and position size.

        In dry-run mode: simulates the trade
        In live mode: places actual orders via Bybit API
        """

        if not position_size.approved:
            logger.warning(
                f"Position size not approved: {position_size.rejection_reason}"
            )
            return None

        # Determine side
        if signal.signal_type == SignalType.ENTRY_LONG:
            side = "LONG"
            order_side = OrderSide.BUY
        elif signal.signal_type == SignalType.ENTRY_SHORT:
            side = "SHORT"
            order_side = OrderSide.SELL
        else:
            logger.error(f"Invalid signal type for opening position: {signal.signal_type}")
            return None

        # Create position object
        position = Position(
            position_id=self._generate_position_id(),
            symbol=symbol,
            side=side,
            entry_price=signal.price,
            quantity=position_size.quantity,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            status=PositionStatus.PENDING,
            entry_time=datetime.now(),
            signal_reason=signal.reason
        )

        logger.info(
            f"{'[DRY RUN] ' if self.dry_run else ''}Opening {side} position: "
            f"{position.quantity:.4f} {symbol} @ ${position.entry_price:.2f} | "
            f"SL: ${position.stop_loss:.2f} | TP: ${position.take_profit:.2f}"
        )

        if self.dry_run:
            # Simulate successful order placement
            position.status = PositionStatus.OPEN
            position.order_ids = ["DRY_RUN_ORDER_" + position.position_id]
            self.positions[position.position_id] = position

            logger.info(
                f"[DRY RUN] Position opened: {position.position_id} | "
                f"Risk: ${position_size.risk_amount:.2f} | "
                f"R:R: {position_size.reward_ratio:.2f}"
            )

            return position

        # LIVE TRADING: Place actual orders
        try:
            # Note: Actual Bybit order placement would go here
            # This is a template - actual implementation would use pybit or similar
            logger.warning("Live trading not fully implemented - would place real order here")

            # Placeholder for actual API call:
            # order_result = await self._place_market_order(
            #     symbol=symbol,
            #     side=order_side,
            #     qty=position.quantity
            # )
            #
            # if order_result["success"]:
            #     position.order_ids.append(order_result["orderId"])
            #     position.status = PositionStatus.OPEN
            #
            #     # Place stop loss and take profit orders
            #     if position.stop_loss:
            #         await self._place_stop_loss(position)
            #     if position.take_profit:
            #         await self._place_take_profit(position)
            #
            #     self.positions[position.position_id] = position
            #     return position

            # For now, treat as error in live mode since not fully implemented
            position.status = PositionStatus.ERROR
            position.error_message = "Live trading not fully implemented"
            return None

        except Exception as e:
            logger.error(f"Error opening position: {e}")
            position.status = PositionStatus.ERROR
            position.error_message = str(e)
            return None

    async def close_position(
        self,
        position_id: str,
        exit_price: float,
        reason: str = "Manual close"
    ) -> bool:
        """
        Close an open position.

        In dry-run: simulates close
        In live: places closing market order
        """

        if position_id not in self.positions:
            logger.error(f"Position {position_id} not found")
            return False

        position = self.positions[position_id]

        if position.status != PositionStatus.OPEN:
            logger.warning(f"Position {position_id} is not open (status: {position.status})")
            return False

        logger.info(
            f"{'[DRY RUN] ' if self.dry_run else ''}Closing position {position_id} | "
            f"Reason: {reason} | Exit: ${exit_price:.2f}"
        )

        # Calculate PnL
        if position.side == "LONG":
            pnl = (exit_price - position.entry_price) * position.quantity
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * position.quantity

        pnl_percent = (pnl / (position.entry_price * position.quantity)) * 100

        # Update position
        position.exit_price = exit_price
        position.exit_time = datetime.now()
        position.pnl = pnl
        position.pnl_percent = pnl_percent
        position.status = PositionStatus.CLOSED

        logger.info(
            f"{'[DRY RUN] ' if self.dry_run else ''}Position closed: {position_id} | "
            f"PnL: ${pnl:.2f} ({pnl_percent:.2f}%) | "
            f"Duration: {(position.exit_time - position.entry_time).total_seconds() / 60:.1f}min"
        )

        if not self.dry_run:
            # LIVE TRADING: Place closing market order
            try:
                # Placeholder for actual API call
                logger.warning("Live trading not fully implemented - would close real position here")

                # Actual implementation would be:
                # close_side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
                # order_result = await self._place_market_order(
                #     symbol=position.symbol,
                #     side=close_side,
                #     qty=position.quantity
                # )
                #
                # Cancel any open SL/TP orders
                # await self._cancel_orders(position.order_ids)

                pass

            except Exception as e:
                logger.error(f"Error closing position: {e}")
                position.error_message = str(e)
                position.status = PositionStatus.ERROR
                return False

        return True

    def check_stop_loss(self, current_price: float) -> List[str]:
        """Check if any positions hit stop loss"""
        closed_positions = []

        for pos_id, position in self.positions.items():
            if position.status != PositionStatus.OPEN or not position.stop_loss:
                continue

            hit_stop = False

            if position.side == "LONG" and current_price <= position.stop_loss:
                hit_stop = True
            elif position.side == "SHORT" and current_price >= position.stop_loss:
                hit_stop = True

            if hit_stop:
                logger.warning(
                    f"Stop loss hit for {pos_id} | "
                    f"{position.side} @ ${position.entry_price:.2f} | "
                    f"SL: ${position.stop_loss:.2f} | Current: ${current_price:.2f}"
                )

                asyncio.create_task(
                    self.close_position(pos_id, position.stop_loss, "Stop loss hit")
                )
                closed_positions.append(pos_id)

        return closed_positions

    def check_take_profit(self, current_price: float) -> List[str]:
        """Check if any positions hit take profit"""
        closed_positions = []

        for pos_id, position in self.positions.items():
            if position.status != PositionStatus.OPEN or not position.take_profit:
                continue

            hit_tp = False

            if position.side == "LONG" and current_price >= position.take_profit:
                hit_tp = True
            elif position.side == "SHORT" and current_price <= position.take_profit:
                hit_tp = True

            if hit_tp:
                logger.info(
                    f"Take profit hit for {pos_id} | "
                    f"{position.side} @ ${position.entry_price:.2f} | "
                    f"TP: ${position.take_profit:.2f} | Current: ${current_price:.2f}"
                )

                asyncio.create_task(
                    self.close_position(pos_id, position.take_profit, "Take profit hit")
                )
                closed_positions.append(pos_id)

        return closed_positions

    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        return [p for p in self.positions.values() if p.status == PositionStatus.OPEN]

    def get_closed_positions(self) -> List[Position]:
        """Get all closed positions"""
        return [p for p in self.positions.values() if p.status == PositionStatus.CLOSED]

    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions"""
        open_positions = self.get_open_positions()
        closed_positions = self.get_closed_positions()

        total_pnl = sum(p.pnl for p in closed_positions)
        winning_trades = [p for p in closed_positions if p.pnl > 0]
        losing_trades = [p for p in closed_positions if p.pnl < 0]

        win_rate = (
            len(winning_trades) / len(closed_positions) * 100
            if closed_positions else 0.0
        )

        return {
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "total_trades": len(self.positions),
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "dry_run": self.dry_run
        }

    def get_status(self) -> Dict[str, Any]:
        """Get trade manager status"""
        open_pos = self.get_open_positions()
        summary = self.get_position_summary()

        return {
            "mode": "DRY_RUN" if self.dry_run else "LIVE",
            "summary": summary,
            "open_positions": [
                {
                    "id": p.position_id,
                    "symbol": p.symbol,
                    "side": p.side,
                    "entry_price": p.entry_price,
                    "quantity": p.quantity,
                    "stop_loss": p.stop_loss,
                    "take_profit": p.take_profit,
                    "duration_minutes": (
                        datetime.now() - p.entry_time
                    ).total_seconds() / 60,
                    "reason": p.signal_reason
                }
                for p in open_pos
            ]
        }
