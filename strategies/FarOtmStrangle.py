import pandas as pd
import matplotlib.pyplot as plt
import math
from datetime import datetime, time
from matplotlib import style
from event import SignalEvent
from strategies.strategy import Strategy
from utils import generate_current_week_option_symbol, get_atm_strike, get_current_weekly_expiry


class FarOtmStrangle(Strategy):
    def __init__(self, data, events, portfolio, verbose=True, ):
        self.data = data
        self.events = events
        self.portfolio = portfolio

        self.name = 'Far OTM Sell'
        self.verbose = verbose
        self.symbol = self.data.symbol
        self.sl_multiplier = 2.5

        self.positions = {}
        self.portfolio.register_strategy(self)

    def update_position_from_fill(self, symbol, position):
        self.positions[symbol] = position
        self.positions[symbol]['sl'] = self.sl_multiplier*position['sell_avg']

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            events = []
            res = self.data.get_latest_data('BANKNIFTY', N=1)
            ltp = res[0]['ltp']
            current_datetime = self.data.current_time
            current_time = current_datetime.time()
            if(current_time >= time(9, 15) and current_time <= time(9, 20)):
                self.positions = {}

            if(current_time > time(9, 25) and current_time < time(15, 20)):
                sl_symbol = None
                for symbol in self.positions:
                    position = self.positions[symbol]
                    if(position['sell_qty'] - position['buy_qty'] > 0):
                        symbol_ltp = self.data.get_latest_data(symbol)[
                            0]['ltp']

                        if(symbol_ltp >= position['sl']):
                            sl_symbol = symbol
                            print(
                                f"{current_datetime} - SL hit for {symbol} at {position['sl']}")
                            signal = SignalEvent(
                                symbol, current_datetime, 'SL', 25, position['sl'])
                            self.events.put(signal)

                for symbol in self.positions:
                    if(sl_symbol and symbol != sl_symbol):
                        position = self.positions[symbol]
                        if(position['sell_qty'] - position['buy_qty'] > 0):
                            symbol_ltp = self.data.get_latest_data(symbol)[
                                0]['ltp']

                            # if(symbol_ltp < position['sell_avg']):
                            sl = self.sl_multiplier*symbol_ltp
                            if(sl < self.positions[symbol]['sl']):
                                self.positions[symbol]['sl'] = sl
                                print(
                                    f"{current_datetime} - Trailed SL for {symbol} to {sl}")

            if(current_time >= time(9, 45) and len(self.positions) == 0):
                try:
                    self.positions = {}

                    pe_strike = self.data.find_strike(30, 'PE',)
                    pe_symbol = generate_current_week_option_symbol(
                        pe_strike, 'PE', self.data.current_weekly_expiry, 'BANKNIFTY')
                    signal = SignalEvent(
                        pe_symbol, current_datetime, 'SHORT', 25)
                    # self.positions[pe_symbol] = {'qty': 25}
                    self.events.put(signal)

                    ce_strike = self.data.find_strike(30, 'CE',)
                    # print(ce_strike)
                    ce_symbol = generate_current_week_option_symbol(
                        ce_strike, 'CE', self.data.current_weekly_expiry, 'BANKNIFTY')
                    signal = SignalEvent(
                        ce_symbol, current_datetime, 'SHORT', 25)
                    # self.positions[ce_symbol] = {'qty': 25, }
                    self.events.put(signal)
                except Exception:
                    pass
            if(current_time == time(13, 30) or current_time == time(14, 30)):
                for symbol in self.positions:
                    position = self.positions[symbol]
                    if(position['sell_qty'] - position['buy_qty'] > 0):
                        symbol_ltp = self.data.get_latest_data(symbol)[
                            0]['ltp']

                        # if(symbol_ltp < position['sell_avg']):
                        sl = self.sl_multiplier*symbol_ltp
                        if(sl < self.positions[symbol]['sl']):
                            self.positions[symbol]['sl'] = sl
                            print(
                                f"{current_datetime} - Trailed SL for {symbol} to {sl}")

            if(current_time == time(15, 20)):
                for symbol in self.positions:
                    if(self.positions[symbol]['sell_qty'] != 0):
                        signal = SignalEvent(
                            symbol, current_datetime, 'EXIT', 25)
                        self.events.put(signal)
                print(f"{current_datetime} - {self.positions}")

    def plot(self):
        style.use('ggplot')

        for symbol in self.symbol_list:
            self.strategy[symbol].set_index('Date', inplace=True)
            self.signals[symbol].set_index('Date', inplace=True)
            signals = self.signals[symbol]
            strategy_fig, strategy_ax = plt.subplots()
            df = self.data.all_data[symbol].copy()
            df.columns = ['OMXS30']
            # df['Short'] = df['OMXS30'].ewm(span=self.short_period, min_periods=self.short_period, adjust=False).mean()
            # df['Long'] = df['OMXS30'].ewm(span=self.long_period, min_periods=self.long_period, adjust=False).mean()

            df.plot(ax=strategy_ax, color='dodgerblue', linewidth=1.0)

            short_index = signals[signals['Signal'] < 0].index
            long_index = signals[signals['Signal'] > 0].index

            strategy_ax.plot(
                self.strategy[symbol]['Short'], label='Short EMA', color='grey')
            strategy_ax.plot(self.strategy[symbol]
                             ['Long'], label='Long EMA', color='k')
            strategy_ax.plot(
                short_index, df['OMXS30'].loc[short_index], 'v', markersize=10, color='r', label='Exit')
            strategy_ax.plot(
                long_index, df['OMXS30'].loc[long_index], '^', markersize=10, color='g', label='Long')

            strategy_ax.set_title(self.name)
            strategy_ax.set_xlabel('Time')
            strategy_ax.set_ylabel('Value')
            strategy_ax.legend()

        plt.show()
