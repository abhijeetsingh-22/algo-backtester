

import datetime
from utils import generate_current_week_option_symbol, get_atm_strike, get_current_weekly_expiry
from expiries import expiries
import math


class BnfStraddle():
    def __init__(self, portfolio) -> None:
        self.name = 'BNF_short_straddle'
        self.portfolio = portfolio
        self.instrument = 'BANKNIFTY'
        self.combined_sl = None
        self.expiries = [datetime.datetime.strptime(
            e, '%Y-%m-%d').date() for e in expiries]
        self.positions = []
        portfolio.register_strategy(self)
    # def add_position(self, trade):
    #     self.positions.append(trade)
    #     # for symbol in position

    def calculate_signal(self, row):
        if(row['datetime'].weekday() != 3):
            if(self.portfolio.can_trade_today):
                if(row['time'].minute == 0):  # trailing the sl after each hour
                    cur_combined_premium = 0
                    for symbol in self.portfolio.positions:
                        cur_combined_premium += row[symbol]
                    cur_sl = 0.1*cur_combined_premium+cur_combined_premium
                    sl = min(cur_sl, self.portfolio.sl_premium)
                    self.portfolio.set_sl_premium(sl)
            if(row['time'] == datetime.time(9, 25)):
                # print('prd is', self.portfolio.get_pdr())
                previous_day_data = self.portfolio.get_pdr()
                cur_time = row['datetime']
                low = float('inf')
                high = float('-inf')
                for d in self.portfolio.history:
                    low = min(d[self.instrument], low)
                    high = max(d[self.instrument], high)

                # Enter only if BNF is trading in previous day's range
                if(high < previous_day_data['high'] and low > previous_day_data['low']):
                    # print(row['datetime'], '@@In range')
                    current_expiry = get_current_weekly_expiry(
                        cur_time, self.expiries)
                    qty = int(math.floor(self.portfolio.total/160000)*25)
                    self.portfolio.qty = qty
                    atm_strike = get_atm_strike(row[self.instrument], 100)
                    self.portfolio.order(row, generate_current_week_option_symbol(
                        atm_strike, 'CE', current_expiry, self.instrument), 'sell', qty, )
                    self.portfolio.order(row, generate_current_week_option_symbol(
                        atm_strike, 'PE', current_expiry, self.instrument), 'sell', qty)
                    combined_premium = row[generate_current_week_option_symbol(
                        atm_strike, 'CE', current_expiry, self.instrument)]+row[generate_current_week_option_symbol(
                            atm_strike, 'PE', current_expiry, self.instrument)]
                    # print(combined_premium)

                    # Set combined premium SL
                    sl = 0.1*combined_premium+combined_premium
                    self.portfolio.set_sl_premium(sl)
                else:
                    print(f"{row['datetime']}: not in range")
            # Exit at intraday Squareoff time
            if(row['time'] == datetime.time(15, 14)):
                self.positions = []
                for symbol in self.portfolio.positions:
                    self.portfolio.order(row, symbol, 'exit')

    def get_name(self):
        return self.name
