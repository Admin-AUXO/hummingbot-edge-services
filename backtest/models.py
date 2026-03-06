from dataclasses import dataclass


@dataclass
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class BacktestConfig:
    initial_capital: float = 100.0
    position_size: float = 0.5
    cash_reserve_ratio: float = 0.15
    min_trade_usd: float = 2.0
    risk_per_trade: float = 0.02
    dex_fee_bps: float = 25.0
    slippage_bps: float = 15.0
    gas_cost: float = 0.05
    stop_loss: float = 0.04
    take_profit: float = 0.06
    time_limit_bars: int = 576
    trailing_activation: float = 0.03
    trailing_delta: float = 0.02
    cooldown_bars: int = 24
    min_hold_bars: int = 48

    @property
    def fee_rate(self):
        return self.dex_fee_bps / 10000.0

    def entry_price(self, market_price):
        return market_price * (1 + self.slippage_bps / 10000.0)

    def exit_price(self, market_price):
        return market_price * (1 - self.slippage_bps / 10000.0)

    def min_required_cash(self):
        return self.min_trade_usd + self.gas_cost + (self.min_trade_usd * self.fee_rate)

    def tradeable_cash(self, cash):
        reserve = cash * max(0.0, min(0.95, self.cash_reserve_ratio))
        return max(0.0, cash - reserve)


@dataclass
class PortfolioConfig(BacktestConfig):
    max_open_trades: int = 5
    max_entries_per_bar: int = 3
    max_rotations_per_bar: int = 0
    rotation_score_threshold: float = 0.05
    past_trade_weight: float = 0.35
    performance_decay: float = 0.2
    workers: int = 2
    batch_size: int = 8
