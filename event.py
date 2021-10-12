class Event:
    pass


class MarketEvent(Event):
    def __init__(self):
        self.type = 'MARKET'


class SignalEvent(Event):
    def __init__(self, symbol, datetime, signal_type, quantity, slm_exit=None):
        self.type = 'SIGNAL'
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.quantity = quantity
        self.slm_exit = slm_exit


class OrderEvent(Event):
    def __init__(self, symbol, order_type, quantity, direction, datetime, slm_exit=None):
        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction
        self.datetime = datetime
        self.slm_exit = slm_exit

    def print_order(self):
        print("Order: Symbol={0}, Type={1}, Quantity={2}, Direction={3}").format(
            self.symbol, self.order_type, self.quantity, self.direction)


class FillEvent(Event):
    def __init__(self, timeindex, symbol, exchange, quantity, direction, fill_cost, commission=None):
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost
        self.commission = 20
