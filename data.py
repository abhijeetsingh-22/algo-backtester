from typing import List
from numpy import log
import pandas as pd
import os.path
import queue
# import quandl

from abc import ABCMeta, abstractmethod
from event import MarketEvent
from datetime import datetime, time, timedelta
from enum import Enum
from expiries import expiries
from utils import generate_current_week_option_symbol, get_atm_strike, get_current_weekly_expiry


class DataHandler(metaclass=ABCMeta):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_latest_data(self, symbol, N=1):
        raise NotImplementedError

    @abstractmethod
    def update_latest_data(self):
        raise NotImplementedError


class HistoricDBDataHandler(DataHandler):
    def __init__(self, events, symbol, start_time: datetime, end_time: datetime, cursor):
        self.events = events
        self.symbol = symbol

        self.symbol_data = {}
        # self.symbol_dataframe = {}
        self.latest_symbol_data = {}
        # self.spot_data = {}
        # self.option_data = {}
        # self.all_data = {}
        self.continue_backtest = True
        self.start_time = start_time
        self.end_time = end_time
        self.cursor = cursor
        self.time_col = 1
        self.price_col = 2
        self.expiries = [datetime.strptime(
            e, '%Y-%m-%d').date() for e in expiries]
        self.cursor.execute(
            """
                select datetime from price_data where instrument_type='SPOT' and datetime>=%s and datetime<=%s order by datetime asc
            """, [start_time, end_time]
        )
        self.time_list = []
        t_list = self.cursor.fetchall()
        # t_list = filter(
        #     lambda t: self.start_time <= t['time'] <= self.end_time, t_list)
        for t in t_list:
            # if(t['datetime'].date() in self.expiries):
            self.time_list.append(t['datetime'])
            if t['datetime'].time() == time(15, 29):
                self.time_list.append(t['datetime'].replace(minute=30))

        self.current_time = start_time
        self.update_time = self._update_current_time()
        self.update_weekly_expiry()
        # self.current_time = datetime.fromisoformat(self.time_list[0])
        # self.latest_spot_data=[]
        # self.latest_option_data=[]

        # self._open_convert_csv_files(source)

    # def _get_new_data(self, symbol):
    #     for row in self.symbol_data[symbol]:
    #         yield tuple([symbol, row[0], row[1][0]])
    def update_weekly_expiry(self):
        self.current_weekly_expiry = get_current_weekly_expiry(
            self.current_time, self.expiries)

    def get_latest_data(self, symbol, N=1):
        try:
            return self.latest_symbol_data[symbol][-N:]
        except KeyError:
            print("{symbol} is not a valid symbol.".format(symbol=symbol))
            raise LookupError()

    def _update_current_time(self):
        for time in self.time_list:
            yield time

    # def _is_time_in_range(self):
    #     print('time is ', self.start_time, self.current_time)
    #     return self.current_time <= self.end_time

    def update_latest_data(self):
        # if time is in less than end time fetch symbol data and add to the list
        try:
            cur_time = next(self.update_time)
            self.current_time = cur_time

        except StopIteration:

            self.continue_backtest = False
            # return

        timestamp_to_fetch = self.current_time
        is_first_tick = self.current_time.time() == time(9, 15)
        if(not is_first_tick):
            timestamp_to_fetch = self.current_time-timedelta(minutes=1)
        # print('fetching ', timestamp_to_fetch)
        self.cursor.execute(""" 
        SELECT * FROM price_data
        WHERE datetime=%s
        """, [timestamp_to_fetch])
        price_data = self.cursor.fetchall()
        if len(price_data) <= 0:
            self.update_latest_data()
        # print(price_data)
        for d in price_data:
            symbol = d['symbol']
            ltp = d['close']
            if(is_first_tick):
                ltp = d['open']
            # time = self.current_time
            expiry = d['expiry']
            strike = d['strike']
            if symbol not in self.latest_symbol_data:
                self.latest_symbol_data[symbol] = []
            self.latest_symbol_data[symbol].append(
                {'symbol': symbol, 'time': self.current_time, 'ltp': float(ltp), 'expiry': expiry, 'strike': strike})
        self.events.put(MarketEvent())

    def find_strike(self, price, type):
        strike = get_atm_strike(
            self.get_latest_data('BANKNIFTY')[0]['ltp'], 100)
        strike_ltp = float(self.get_latest_data(generate_current_week_option_symbol(
            strike, type, self.current_weekly_expiry, 'BANKNIFTY'))[0]['ltp'])
        # print(type(strike_ltp))
        # print(type(price))
        if(strike_ltp > price):

            while(True):
                if(type == 'PE'):
                    strike -= 100
                else:
                    strike += 100
                prev_ltp = strike_ltp
                strike_ltp = float(self.get_latest_data(generate_current_week_option_symbol(
                    strike, type, self.current_weekly_expiry, 'BANKNIFTY'))[0]['ltp'])
                if(strike_ltp < price):
                    if(abs(price-strike_ltp) < abs(price-prev_ltp)):
                        return strike
                    else:
                        if(type == 'PE'):
                            return strike+100
                        else:
                            return strike-100
            # STATICTICS CALCULATIONS

    def create_baseline_dataframe(self):
        dataframe = None
        self.cursor.execute("""
            select time_bucket(INTERVAL '1 day', time) as day,
            last(close,time) as close
            from spot_price
            where time>= %s and time<=%s
            group by day
            order by day asc
        """, [self.start_time, self.end_time])
        data = self.cursor.fetchall()
        symbol = 'BANKNIFTY'
        df = pd.DataFrame.from_records(data)
        df.index = pd.to_datetime(df['day'])
        df['close'] = [float(d) for d in df['close']]
        # if dataframe == None:
        dataframe = pd.DataFrame(df['close'])
        dataframe.columns = [symbol]
        # else:
        #     dataframe[symbol] = pd.DataFrame(df['close'])
        dataframe[symbol] = dataframe[symbol].pct_change()
        dataframe[symbol] = (1.0 + dataframe[symbol]).cumprod()

        return dataframe
