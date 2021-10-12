# from expiries import expiries


def get_current_weekly_expiry(cur_time, expiries):
    dt = cur_time.date()
    for e in expiries:
        if e >= dt:
            return e
    return None


def generate_current_week_option_symbol(strike, type, current_expiry, symbol):
    # expiry_date: date = _get_current_expiry()
    dt_component = current_expiry.strftime('%y%#m%d')
    option_symbol = f'{symbol}{dt_component}{strike}{type}'
    return option_symbol


def get_atm_strike(ltp, step):
    return step*round(ltp/step)
