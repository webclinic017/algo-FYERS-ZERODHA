from datetime import datetime

import numpy as np
import pandas as pd
from database import UpdatePositionBook, GetOpenPosition
import pytz


class OrderMng:
    LIVE_FEED = None

    def __init__(self,mode, name,obj):
        self.StrategyFactory_Obj = obj
        self.mode = mode
        self.strategy_name = name
        self.time_zone = pytz.timezone('Asia/kolkata')
        self.date = {}
        self.entry_time = {}
        self.exit_time = {}
        self.nav = {}
        self.Signal = {}
        self.net_qty = {}
        self.CumMtm = 0
        self.Transtype = {}
        self.overnight_variables_update_flag = False

    def Update_OpenPosition(self):
        OpenPos = GetOpenPosition(self.strategy_name) if not self.overnight_variables_update_flag else pd.DataFrame()

        if not OpenPos.empty:
            for index, row in OpenPos.iterrows():
                instrument = row['Instrument']
                self.Initialize_Variables(instrument)
                self.date[instrument] = row['Date']
                self.entry_time[instrument] = row['entrytime']
                self.Transtype[instrument] = row['Transtype']
                self.Signal[instrument] = row['Signal']
                if row['Transtype'] == 'BUY':
                    self.net_qty[instrument] += abs(row['NetQty'])
                    self.nav[instrument] += abs((row['NAV']))
                else:
                    self.net_qty[instrument] -= abs(row['NetQty'])
                    self.nav[instrument] -= abs(row['NAV'])

        self.overnight_variables_update_flag = True

        if self.nav:
            instrument_to_subscribe = [instrument for instrument in self.nav if instrument not in self.LIVE_FEED.token.values()]
            if instrument_to_subscribe:
                self.LIVE_FEED.subscribe_new_symbol(instrument_to_subscribe)

            if all([s in self.LIVE_FEED.ltp.keys() for s in self.nav]):
                for s in self.nav:
                    self.StrategyFactory_Obj.position = self.Signal[s]
                self.StrategyFactory_Obj.scheduler.clear()
            else:
                print(f'Socket is not Opened yet,re-iterating the function')

        else:
            self.StrategyFactory_Obj.overnight_flag = True
            self.StrategyFactory_Obj.scheduler.clear()

    def Live_MTM(self):
        mtm = sum([(self.LIVE_FEED.get_ltp(ins) * self.net_qty[ins]) - self.nav[ins] for ins in self.nav])
        if self.StrategyFactory_Obj.target:
            if mtm >= self.StrategyFactory_Obj.target:
                self.StrategyFactory_Obj.squaring_of_all_position_AT_ONCE()
                self.StrategyFactory_Obj.processed_flag = False

        return self.CumMtm+mtm

    def Add_position(self,Instrument,Transtype, Qty,signal):
        price = 0
        success = False

        if self.mode == 'Simulator':
            price = self.LIVE_FEED.get_ltp(Instrument)
            success = True
        elif self.mode == 'Live':
            # write function for placing order with broker and update the price variable then
            success = True

        # Initialize value with zero if not present
        if success:
            self.Initialize_Variables(Instrument)

        # if success is True i:e order is successfully placed then only taken into consideration
        if Transtype == 'BUY' and success:
            self.net_qty[Instrument] += Qty
            self.nav[Instrument] += (price*Qty)
            self.Transtype[Instrument] = Transtype
            self.Signal[Instrument] = signal

        elif Transtype == 'SELL' and success:
            self.net_qty[Instrument] -= Qty
            self.nav[Instrument] -= (price*Qty)
            self.Transtype[Instrument] = Transtype
            self.Signal[Instrument] = signal

        if success:
            if Instrument not in self.entry_time:
                self.entry_time[Instrument] = datetime.now(self.time_zone).time()
                self.date[Instrument] = datetime.now(self.time_zone).date()

            if self.mode == 'Simulator':
                self.UpdatePosition(Instrument)

        return success

    def close_position(self, Instrument,Qty):
        price = 0
        success = False

        if self.mode == 'Simulator':
            price = self.LIVE_FEED.get_ltp(Instrument)
            success = True
        elif self.mode == 'Live':
            # write function for placing order with broker and update the price variable then
            success = True

        if self.Transtype[Instrument] == 'BUY' and success:
            self.net_qty[Instrument] -= Qty
            self.nav[Instrument] -= (price * Qty)
        elif self.Transtype[Instrument] == 'SELL' and success:
            self.net_qty[Instrument] += Qty
            self.nav[Instrument] += (price * Qty)

        if success and self.mode == 'Simulator':
            self.UpdatePosition(Instrument)

        if success and self.net_qty[Instrument] == 0:
            self.date[Instrument] = datetime.now(self.time_zone).date()
            self.CumMtm += (-self.nav[Instrument])
            self.refresh_variable(Instrument)

        return success

    def UpdatePosition(self, instrument):
        dt = self.date[instrument]
        entry_time = self.entry_time[instrument]
        POSITION = 'OPEN' if self.net_qty[instrument] != 0 else 'CLOSED'
        exit_time = datetime.now(self.time_zone).time() if POSITION == 'CLOSED' else np.nan
        NAV = -1 * self.nav[instrument] if POSITION == 'CLOSED' else self.nav[instrument]
        NetQty = self.net_qty[instrument]
        Signal = self.Signal[instrument]
        Transtype = self.Transtype[instrument]

        UpdatePositionBook(dt, entry_time, exit_time, self.strategy_name,
                           Transtype, instrument, Signal, NetQty, NAV,
                           POSITION)

    def Initialize_Variables(self, instrument):

        if instrument not in self.net_qty:
            self.net_qty[instrument] = 0

        if instrument not in self.nav:
            self.nav[instrument] = 0

    def refresh_variable(self, instrument):
        self.nav.pop(instrument, None)
        self.net_qty.pop(instrument, None)
        self.Transtype.pop(instrument, None)
        self.entry_time.pop(instrument, None)
        self.exit_time.pop(instrument, None)
        self.Signal.pop(instrument, None)
        self.date.pop(instrument, None)


