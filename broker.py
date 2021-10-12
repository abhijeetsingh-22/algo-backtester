import queue

from datetime import datetime
from abc import ABCMeta, abstractmethod
from event import FillEvent, OrderEvent


class ExecutionHandler(metaclass=ABCMeta):
    @abstractmethod
    def execute_order(self, event):
        raise NotImplementedError


class SimulateExecutionHandler(ExecutionHandler):
    def __init__(self, events, data, verbose=True):
        self.events = events
        self.verbose = verbose
        self.data = data

    def execute_order(self, event):
        if event.type == 'ORDER':
            # if self.verbose:
            fill_price = 0
            if(event.order_type == 'SLM'):
                fill_price = event.slm_exit
                fill_event = FillEvent(
                    datetime.utcnow(), event.symbol, 'ARCA', event.quantity, event.direction, event.slm_exit)
                self.events.put(fill_event)
            else:
                ltp = float(self.data.get_latest_data(event.symbol,)[0]['ltp'])
                fill_price = ltp
                fill_event = FillEvent(
                    datetime.utcnow(), event.symbol, 'ARCA', event.quantity, event.direction, ltp)
                self.events.put(fill_event)
            print(f"{event.datetime} - Order Executed:", event.symbol,
                  event.quantity, event.direction, '@', fill_price)
