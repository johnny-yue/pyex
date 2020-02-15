from sortedcontainers import SortedDict
from enum import Enum

epsilon = 0.000001

class Side(Enum):
    buy = 1
    sell = -1

    def opposite(self):
        return Side(self.value * -1)

class OrderStatus(Enum):
    open = 0
    partial_fill = 1
    filled = 2
    cancelled = 3


class MatchResult(Enum):
    error = -1
    complete = 0
    continuation = 1

class Order:
    def __init__(self, order_id, side, price, quantity, timestamp=None):
        self.order_id = order_id
        self.side = side
        self.price = price
        self.quantity = quantity
        self.leave_qty = quantity
        self.status = OrderStatus.open
        self.acum_amount = 0
        self.timestamp = timestamp
        self.avg_fill_price = 0

    def fill(self, quantity, price):
        self.acum_amount += quantity * price
        self.leave_qty = self.leave_qty - quantity
        acum_qty = self.quantity - self.leave_qty
        self.avg_fill_price = self.acum_amount / acum_qty

        if abs(self.leave_qty) < epsilon:
            self.status = OrderStatus.filled
            self.leave_qty = 0
        else:
            self.status = OrderStatus.partial_fill

    def filled(self):
        return self.status == OrderStatus.filled

    def final(self):
        return self.status == OrderStatus.cancelled or self.status == OrderStatus.filled

class Cancel:
    def __init__(self, order_id):
        self.order_id = order_id

class Level:
    def __init__(self, price, side):
        self.orders = []
        self.price = price
        self.side = side
    
    def can_match(self, order : Order):
        # Try to match with the best price of the opposite orderbook
        assert(self.side.value*order.side.value == -1) # must be different side
        return order.price * order.side.value >= self.price * order.side.value

    def match(self, o_taker : Order):
        while (len(self.orders) > 0):
            o_maker = self.orders[0]
            
            matched_qty = min(o_taker.leave_qty, o_maker.leave_qty)
            o_taker.fill(matched_qty, self.price)
            o_maker.fill(matched_qty, self.price)

            if o_maker.filled():
                # remote from the order queue
                self.orders.pop(0)

            if o_taker.filled():
                # matching completed
                return MatchResult.complete
        return MatchResult.continuation

    def add(self, order : Order):
        assert(order.price == self.price)
        assert(order.side == self.side)
        self.orders.append(order)

    def cancel(self, order : Order):
        self.orders.remove(order)
        order.status = OrderStatus.cancelled
        order.leave_qty = 0

    def empty(self):
        return len(self.orders) == 0

class OrderBook:
    def __init__(self, side : Side):
        if side == Side.buy:
            self.book = SortedDict(lambda x: -x)
        elif side == Side.sell:
            self.book = SortedDict()
        self.side = side

    def add(self, order : Order):
        assert(order.filled() == False)
        if order.price not in self.book:
            self.book[order.price] = Level(order.price, self.side)
        self.book[order.price].add(order)

    def match(self, order : Order):
        removed_px = []
        for px, lv in self.book.items():
            if not lv.can_match(order):
                break
            result = lv.match(order)
            if lv.empty():
                removed_px.append(lv.price)
            if result == MatchResult.complete:
                break

        for px in removed_px:
            del self.book[px]

    def cancel(self, order : Order):
        lv = self.book.get(order.price)
        lv.cancel(order)

class Engine:
    def __init__(self):
        self.books = {}
        self.books[Side.buy] = OrderBook(Side.buy)
        self.books[Side.sell] = OrderBook(Side.sell)
        self.orders = {}

    def process_order(self, order : Order):
        if order.order_id in self.orders:
            return {'code':'500', 'msg':'duplicated order_id'}
        self.orders[order.order_id] = order

        my_book = self.books[order.side]
        op_book = self.books[order.side.opposite()]

        op_book.match(order)

        if not order.filled():
            my_book.add(order)
        
        return {'code':'200', 'msg':'order accepted'}

    def process_cancel(self, cancel : Cancel):
        if cancel.order_id in self.orders:
            order = self.orders[cancel.order_id]
            if order.final():
                # error, cannot cancel
                return {'code':500, 'msg':'order is done, cannot cancel'}
            return self.books[order.side].cancel(order)
            
        else:
            # error, order_id not found
            return {'code':500, 'msg':'cannot cancel order that does not exist'}


    def process(self, request):
        try:
            if isinstance(request, Order):
                return self.process_order(request)
            elif isinstance(request, Cancel):
                return self.process_cancel(request)
        except Exception as err:
            print(err)
            return {'code':'500', 'msg':str(err)}



