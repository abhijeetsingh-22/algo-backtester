# %%
# Main file to integrate and run all the components of the system
import calendar
import queue
from strategies.FarOtmStrangle import FarOtmStrangle
from broker import SimulateExecutionHandler
from data import HistoricDBDataHandler
import datetime
from glob import glob
from strategies.bnf_straddle import BnfStraddle
from portfolio import BasicPortfolio
from utils import generate_current_week_option_symbol, get_atm_strike,  get_current_weekly_expiry
from performance import calculate_drawdowns, calculate_sharpe_ratio
from numpy import floor
import math
import pandas as pd
from pandas.io.sql import execute
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import sqlalchemy
from expiries import expiries


def backtest(events, data, portfolio, strategy, broker):
    while True:
        portfolio.update_timeindex()
        data.update_latest_data()
        if data.continue_backtest == False:
            break

        while True:
            try:
                event = events.get(block=False)
            except queue.Empty:
                break
            # print('event is ', event)
            if event is not None:
                if event.type == 'MARKET':
                    strategy.calculate_signals(event)
                    # portfolio.update_timeindex(event)
                elif event.type == 'SIGNAL':
                    portfolio.update_signal(event)
                elif event.type == 'ORDER':
                    broker.execute_order(event)
                elif event.type == 'FILL':
                    portfolio.update_fill(event)

    stats = portfolio.summary_stats()

    for stat in stats:
        print(stat[0] + ": " + stat[1])

    # strategy.plot()
    portfolio.plot_all()


# %%
equity_curve = {}
holdings_curve = {}
trade_details = {}
positions = {}
trades = []
instrument = 'BANKNIFTY'
sl_percent = 50
initial_capital = 150000  # 400000
# total = initial_capital
max_loss_per_day_percent = 1

# start_time = datetime.datetime(2018, 8, 16, 9, 15)  # 2018,8,10
# end_time = datetime.datetime(2019, 1, 5, 15, 30)  # 2020,11,26
start_time = datetime.datetime(2018, 8, 10, 9, 15)  # 2018,8,10
end_time = datetime.datetime(2020, 1, 10, 15, 30)  # 2020,11,26


CONNECTION = 'postgresql://postgres:password@localhost:5432/findata'
engine = sqlalchemy.create_engine(CONNECTION)

expiries = [datetime.datetime.strptime(
            e, '%Y-%m-%d').date() for e in expiries]
# %%
conn = psycopg2.connect(CONNECTION)
cursor = conn.cursor(cursor_factory=RealDictCursor)
# cursor = conn.cursor()
events = queue.Queue()
data = HistoricDBDataHandler(
    events, 'BANKNIFTY', start_time, end_time, cursor)
portfolio = BasicPortfolio(
    data, events, 'Far OTM Sell', initial_capital=initial_capital, )
strategy = FarOtmStrangle(
    data, events, portfolio)
portfolio.strategy_name = strategy.name
broker = SimulateExecutionHandler(events, data, True)
# %%
backtest(events, data, portfolio, strategy, broker)
