from datetime import time, timedelta
import math
import pandas as pd
import matplotlib.pyplot as plt
import queue

from abc import ABCMeta, abstractmethod
from math import floor, pi
from matplotlib import style
from event import FillEvent, OrderEvent
from performance import calculate_sharpe_ratio, calculate_drawdowns


class Portfolio(metaclass=ABCMeta):
    @abstractmethod
    def update_signal(self, event):
        raise NotImplementedError

    @abstractmethod
    def update_fill(self, event):
        raise NotImplementedError


class BasicPortfolio(Portfolio):
    def __init__(self, data, events, strategy_name, initial_capital=1.0):
        self.data = data
        self.events = events
        # self.symbol_list = self.data.symbol_list
        self.initial_capital = initial_capital
        self.strategy_name = strategy_name
        self.total = initial_capital
        self.all_positions = []
        self.current_positions = {}
        self.all_positions = {}

        self.all_holdings = []
        # self.current_holdings = self.construct_current_holdings()
        self.current_holdings = {}
        self.trades = []
        self.trade_details = {
            (self.data.start_time-timedelta(days=1)).date(): {'total': self.initial_capital, 'pl': 0}}

    def register_strategy(self, strategyInstance):
        self.strategy = strategyInstance

    def update_pl(self):
        for symbol in self.current_positions:
            cur_pos = self.current_positions[symbol]
            ltp = float(self.data.get_latest_data(symbol)[0]['ltp'])
            cur_pos['pl'] = (cur_pos['sell_avg']*cur_pos['sell_qty'])-(cur_pos['buy_avg'] * cur_pos['buy_qty'])\
                + (cur_pos['buy_qty']-cur_pos['sell_qty'])*ltp
            self.positions[symbol] = cur_pos

    def get_current_pl(self):
        total_pl = 0
        for symbol in self.current_positions:
            cur_pos = self.current_positions[symbol]
            ltp = float(self.data.get_latest_data(symbol)[0]['ltp'])
            cur_pos['pl'] = (cur_pos['sell_avg']*cur_pos['sell_qty'])-(cur_pos['buy_avg'] * cur_pos['buy_qty'])\
                + (cur_pos['buy_qty']-cur_pos['sell_qty'])*ltp
            self.current_positions[symbol] = cur_pos
            total_pl += self.current_positions[symbol]['pl']
        return total_pl

    def update_timeindex(self):
        current_time = self.data.current_time.time()
        current_date = self.data.current_time.date()
        if(current_time == time(9, 18)):
            self.data.update_weekly_expiry()
        if(current_time >= time(15, 25) and len(self.trades) > 0):

            pl = self.get_current_pl()
            if(not math.isnan(pl)):
                self.trade_details[current_date] = {
                    'pl': pl, 'trades': self.trades, 'total': self.total+pl}
                self.all_positions[current_date] = self.current_positions
                self.total += pl
                if(pl > 0):
                    print(
                        f'{current_time} -,total: {self.total} \x1b[1;32m PL: {pl} \x1b[0m')
                else:
                    print(
                        f'{current_time} -,total: {self.total} \x1b[1;31m PL: {pl} \x1b[0m')
                print('x=====================================x')
            self.trades = []
            self.current_positions = {}

        # data = {symbol: self.data.get_latest_data(
        #     symbol) for symbol in self.symbol_list}
        # datetime = data[self.symbol_list[0]][0][self.data.time_col]

        # positions = {
        #     symbol: self.current_positions[symbol] for symbol in self.symbol_list}
        # positions['datetime'] = datetime
        # self.all_positions.append(positions)

        # holdings = {symbol: 0.0 for symbol in self.symbol_list}
        # # holdings['datetime'] = datetime
        # holdings['cash'] = self.current_holdings['cash']
        # holdings['commission'] = self.current_holdings['commission']
        # holdings['total'] = self.current_holdings['cash']

        # for symbol in self.symbol_list:
        #     market_value = self.current_positions[symbol] * \
        #         data[symbol][0][self.data.price_col]
        #     holdings[symbol] = market_value
        #     holdings['total'] += market_value
        pass
        # self.all_holdings.append(holdings)

    def update_positions_from_fill(self, fill):
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        elif fill.direction == 'SELL':
            fill_dir = -1

        self.current_positions[fill.symbol] += fill_dir * fill.quantity

    def update_holdings_from_fill(self, fill):
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        elif fill.direction == 'SELL':
            fill_dir = -1

        fill_cost = self.data.get_latest_data(
            fill.symbol)[0]['ltp']
        cost = fill_cost * fill_dir * fill.quantity
        if fill.symbol not in self.current_holdings:
            self.current_holdings[fill.symbol] = 0
        self.current_holdings[fill.symbol] += cost
        self.current_holdings['commission'] += fill.commission
        self.current_holdings['cash'] -= (cost + fill.commission)
        self.current_holdings['total'] -= (cost + fill.commission)

    def update_trades_from_fill(self, fill):
        cur_trade = {'symbol': fill.symbol, 'datetime': fill.timeindex,
                     'direction': fill.direction, 'qty': fill.quantity, 'fill_avg': fill.fill_cost}
        self.trades.append(cur_trade)

    def update_current_positions(self, fill):
        ltp = float(fill.fill_cost)
        direction = fill.direction
        symbol = fill.symbol
        qty = fill.quantity
        if(symbol not in self.current_positions):
            cur_pos = {'buy_avg': 0, 'buy_qty': 0,
                       'sell_avg': 0, 'sell_qty': 0}
        else:
            cur_pos = self.current_positions[symbol]

        # print(cur_pos)
        if(direction == 'BUY'):
            # ltp += ltp*0.01  # slippage
            cur_pos['buy_avg'] = (
                cur_pos['buy_avg']*cur_pos['buy_qty']+ltp*qty)/(cur_pos['buy_qty']+qty)
            cur_pos['buy_qty'] += qty
        elif(direction == 'SELL'):
            # ltp -= ltp*0.01  # slippage
            # cur_pos['sl'] =
            cur_pos['sell_avg'] = (
                cur_pos['sell_avg']*cur_pos['sell_qty']+ltp*qty)/(cur_pos['sell_qty']+qty)
            cur_pos['sell_qty'] += qty
        cur_pos['pl'] = (cur_pos['sell_avg']*cur_pos['sell_qty'])-(cur_pos['buy_avg'] * cur_pos['buy_qty'])\
            + (cur_pos['buy_qty']-cur_pos['sell_qty'])*ltp
        # if(cur_pos['buy_qty'] > cur_pos['sell_qty']):
        #     cur_pos['sl'] = cur_pos['buy_avg'] - \
        #         cur_pos['buy_avg']*self.sl_percent/100
        # elif(cur_pos['buy_qty'] < cur_pos['sell_qty']):
        #     cur_pos['sl'] = cur_pos['sell_avg'] + \
        #         cur_pos['sell_avg']*self.sl_percent/100

        self.current_positions[symbol] = cur_pos
        self.strategy.update_position_from_fill(symbol, cur_pos)

    def update_fill(self, event):
        if event.type == 'FILL':
            # self.update_positions_from_fill(event)
            # self.update_holdings_from_fill(event)
            self.update_trades_from_fill(event)
            self.update_current_positions(event)

    def generate_naive_order(self, signal):
        order = None

        symbol = signal.symbol
        direction = signal.signal_type
        quantity = signal.quantity
        current_time = self.data.current_time
        market_quantity = quantity
        if symbol not in self.current_positions:
            self.current_positions[symbol] = {
                'buy_qty': 0, 'sell_qty': 0, 'buy_avg': 0, 'sell_avg': 0}
        # print('generating order', symbol, direction, quantity)
        current_quantity = self.current_positions[symbol]['buy_qty'] - \
            self.current_positions[symbol]['sell_qty']
        order_type = 'MKT'

        if direction == 'LONG':
            order = OrderEvent(symbol, order_type,
                               market_quantity, 'BUY', current_time)
        if direction == 'SHORT':
            order = OrderEvent(symbol, order_type,
                               market_quantity, 'SELL', current_time)

        if direction == 'EXIT' and current_quantity > 0:
            order = OrderEvent(symbol, order_type,
                               market_quantity, 'SELL', current_time)
        if direction == 'EXIT' and current_quantity < 0:
            order = OrderEvent(symbol, order_type,
                               market_quantity, 'BUY', current_time)
        if direction == 'SL' and current_quantity > 0:
            order = OrderEvent(symbol, 'SLM',
                               market_quantity, 'SELL', current_time, signal.slm_exit)
        if direction == 'SL' and current_quantity < 0:
            order = OrderEvent(symbol, 'SLM',
                               market_quantity, 'BUY', current_time, signal.slm_exit)

        return order

    def update_signal(self, event):
        if event.type == 'SIGNAL':
            order_event = self.generate_naive_order(event)
            self.events.put(order_event)

    def create_equity_curve_dataframe(self):
        # curve = pd.DataFrame(self.all_holdings)
        curve = pd.DataFrame.from_dict(
            self.trade_details, orient='index', columns=['pl', 'total'],)
        # curve.set_index('date', inplace=True)
        curve.index = pd.to_datetime(curve.index)
        curve['returns'] = curve['total'].pct_change()
        curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
        # self.curve = curve
        self.equity_curve = curve
        self.holdings_curve = curve['total']

    def summary_stats(self):
        self.create_equity_curve_dataframe()
        total_return = self.equity_curve['equity_curve'][-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['equity_curve']

        sharpe_ratio = calculate_sharpe_ratio(returns)
        max_dd, dd_duration = calculate_drawdowns(pnl)
        winning_days=len(self.equity_curve[self.equity_curve['pl']>0])
        losing_days=len(self.equity_curve[self.equity_curve['pl']<0])
        winning_percent=(winning_days/(winning_days+losing_days))*100
        stats = [("Total Return", "%0.2f%%" % ((total_return - 1.0) * 100.0)),
                 ("Sharpe Ratio", "%0.2f" % sharpe_ratio),
                 ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
                 ("Drawdown Duration", "%d" % dd_duration),
                  ("Winning Days", f'{winning_days}'),
                 ("Losing Days", f'{losing_days}'),
                 ("Winning percentage (Days)", f'{winning_percent}'),
                 ("Max Profit", "%0.2f" %
                 self.equity_curve[self.equity_curve['pl'] > 0]['pl'].max()),
                 ("Avg Profit", "%0.2f" %
                 self.equity_curve[self.equity_curve['pl'] > 0]['pl'].mean()),
                 ("Max Loss", "%0.2f" %
                 self.equity_curve[self.equity_curve['pl'] < 0]['pl'].min()),
                 ("Avg Loss", "%0.2f" %
                 self.equity_curve[self.equity_curve['pl'] < 0]['pl'].mean()),
                 #  ("RRR", "%0.2f" % int(self.equity_curve[self.equity_curve['pl'] > 0]['pl'].mean(
                 #  ))/int(self.equity_curve[self.equity_curve['pl'] < 0]['pl'].mean())),
                 ("Total P/L", "%0.2f" % self.equity_curve['pl'].sum())]

        return stats

    def plot_holdings(self):
        holdings_fig, holdings_ax = plt.subplots()
        self.holdings_curve.plot(ax=holdings_ax)
        holdings_ax.set_title('Holdings')
        holdings_ax.set_xlabel('Time')
        holdings_ax.set_ylabel('Total')

    def plot_performance(self):
        performance_df = self.data.create_baseline_dataframe()
        performance_df[self.strategy_name] = self.equity_curve['equity_curve']
        performance_df = (performance_df * 100) - 100
        performance_fig, performance_ax = plt.subplots()
        performance_df.plot(ax=performance_ax)
        performance_ax.set_title('Performance')
        performance_ax.set_xlabel('Time')
        performance_ax.set_ylabel('Return (%)')

    def plot_all(self):
        style.use('ggplot')
        self.create_equity_curve_dataframe()
        self.plot_performance()
        self.plot_holdings()
        plt.show()
