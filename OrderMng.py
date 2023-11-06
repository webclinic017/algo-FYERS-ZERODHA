from datetime import datetime
from database import append_position,post_position
import pytz


class OrderMng():
    LIVE_FEED = None
    def __init__(self , mode , name):
        self.mode = mode
        self.strategy_name = name
        self.time_zone = pytz.timezone('Asia/kolkata')
        self.nav = {}
        self.net_qty = {}
        self.BuyValue = {}
        self.SellValue = {}
        self.BuyQty = {}
        self.SellQty = {}
        self.MTM = {}
        self.CumMtm = 0
        self.Transtype = {}
        self.entry_time ={}
        self.exit_time = {}


    def Live_MTM(self):
        for instrument in self.nav.keys():
            if self.net_qty[instrument]:
                self.MTM[instrument] = self.LIVE_FEED.get_ltp(instrument)*self.net_qty[instrument]-self.nav[instrument]

        return self.CumMtm+sum(self.MTM.values())

    def Add_position(self,Instrument,Transtype,Qty):
         price = 0
         success = False
         if self.mode == 'Simulator':
            price = self.LIVE_FEED.get_ltp(Instrument)
            success =True
         elif self.mode == 'Live':
              # write function for placining order with broker and update the price variable then
                success = True

         # initialize value with zero if not present
         if Instrument not in self.BuyValue:
             self.BuyValue[Instrument] = 0

         if Instrument not in self.BuyQty:
             self.BuyQty[Instrument] = 0

         if Instrument not in self.SellValue:
             self.SellValue[Instrument] = 0

         if Instrument not in self.SellQty:
             self.SellQty[Instrument] = 0

         if Instrument not in self.net_qty:
             self.net_qty[Instrument] = 0

         if Instrument not in self.nav:
             self.nav[Instrument] = 0


         # if success is True i:e order is succssfully placed then only taken into consideration
         if Transtype=='BUY' and success:
            self.BuyValue[Instrument]+=price*Qty
            self.BuyQty[Instrument]+=Qty
            self.net_qty[Instrument]+=Qty
            self.nav[Instrument]+=(price*Qty)
            self.Transtype[Instrument] = Transtype

         elif Transtype == 'SELL' and success:
            self.SellValue[Instrument] += price*Qty
            self.SellQty[Instrument] += Qty
            self.net_qty[Instrument] -= Qty
            self.nav[Instrument] -= (price*Qty)
            self.Transtype[Instrument] = Transtype

         if success:
            self.entry_time[Instrument] = datetime.now(self.time_zone).time()


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
        if self.Transtype[Instrument]=='BUY' and success:
            self.SellValue[Instrument]+=price * Qty
            self.SellQty[Instrument]+=Qty
            self.net_qty[Instrument]-=Qty
            self.nav[Instrument]-=(price * Qty)
        elif self.Transtype[Instrument]=='SELL' and success:
            self.BuyValue[Instrument]+= price * Qty
            self.BuyQty[Instrument]+= Qty
            self.net_qty[Instrument]+= Qty
            self.nav[Instrument]+=(price * Qty)


        if success:
            self.exit_time[Instrument] = datetime.now(self.time_zone).time()
            self.CumMtm+=(-self.nav[Instrument])
            self.MTM.pop(Instrument, None)

            if self.mode=='Simulator':
                self.update_server(Instrument , Qty)

        return success

    def update_server(self,Instrument,Qty):
        ABP = round(self.BuyValue[Instrument]/self.BuyQty[Instrument],2)
        ASP = round(self.SellValue[Instrument] / self.SellQty[Instrument], 2)
        MTM = round((ASP-ABP)*Qty)
        BuyValue = ABP*Qty
        SellValue = ASP*Qty


        append_position(datetime.today().date(),
                        self.entry_time[Instrument],
                        self.exit_time[Instrument],
                        self.strategy_name,
                        self.Transtype[Instrument],
                        Instrument,
                        ABP,
                        ASP,
                        Qty,
                        BuyValue,
                        SellValue,
                        MTM
                        )
        # position information to database server at pythonanywhere
        post_position()


    def refresh_variable(self):
        self.nav = {}
        self.net_qty = {}
        self.BuyValue = {}
        self.SellValue = {}
        self.BuyQty = {}
        self.SellQty = {}
        self.Transtype = {}
        self.entry_time = {}
        self.exit_time = {}
        self.MTM = {}


