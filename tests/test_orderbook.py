import pytest
from src.model.exchange import *

class TestPyex:

    def test_order(self):
        o = Order("K00001", Side.sell, 12.3, 100)
        assert(o.filled() == False)

        o.fill(20, 11)
        assert(o.leave_qty == 80)
        assert(o.status == OrderStatus.partial_fill)

        o.fill(80, 11.4)
        assert(o.leave_qty == 0)
        assert(o.status == OrderStatus.filled)

    def test_level_add_exception_px(self):
        lv = Level(12.3, Side.sell)
        order = Order("K00001", Side.sell, 12.4, 100)
        with pytest.raises(Exception) as e_info:
            lv.add(order)
            assert(e_info == 0)

    def test_level_add_exception_side(self):
        lv = Level(12.3, Side.buy)
        order = Order("K00001", Side.sell, 12.3, 100)
        with pytest.raises(Exception) as e_info:
            lv.add(order)
            assert(e_info == 0)


    def test_level_add(self):
        lv = Level(12.3, Side.sell)
        order = Order("K00001", Side.sell, 12.3, 100)
        lv.add(order)
        assert(len(lv.orders) == 1)

    def test_match_buy(self):
        lv = Level(12.3, Side.buy)
        o1 = Order("K00001", Side.buy, 12.3, 40)
        o2 = Order("K00002", Side.sell, 12.2, 100)

        lv.add(o1)
        assert(lv.can_match(o2) == True)

        lv.match(o2)
        assert(len(lv.orders) == 0)
        assert(o2.status == OrderStatus.partial_fill)
        assert(o2.leave_qty == 60)

    def test_match_sell(self):
        lv = Level(12.3, Side.sell)
        o1 = Order("K00001", Side.sell, 12.3, 40)
        o2 = Order("K00002", Side.buy, 12.8, 100)

        lv.add(o1)
        assert(lv.can_match(o2) == True)

        lv.match(o2)
        assert(len(lv.orders) == 0)
        assert(o2.status == OrderStatus.partial_fill)
        assert(o2.leave_qty == 60)

    def test_no_match_buy(self):
        lv = Level(12.3, Side.buy)
        o1 = Order("K00001", Side.buy, 12.3, 40)
        o2 = Order("K00002", Side.sell, 12.5, 100)

        lv.add(o1)
        assert(lv.can_match(o2) == False)

    def test_no_match_sell(self):
        lv = Level(12.3, Side.sell)
        o1 = Order("K00001", Side.sell, 12.3, 40)
        o2 = Order("K00002", Side.buy, 12.2, 100)

        lv.add(o1)
        assert(lv.can_match(o2) == False)


    def test_buy_book(self):
        pass

class TestFull:
    def next_id(self):
        self._id += 1
        return self._id

    def reset_id(self):
        self._id = -1

    def test_cancel(self):
        self.reset_id()
        a = []
        a.append(Order(0, Side.sell, 12.3, 40))
        a.append(Cancel(0))

        engine = Engine()
        for act in a:
            engine.process(act)

        assert(a[0].status == OrderStatus.cancelled)
 
    def test_cancel_partial_fill(self):
        self.reset_id()
        a = []
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))        # 0
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))        # 1
        a.append(Order(self.next_id(), Side.sell, 12.4, 40))        # 2
        a.append(Order(self.next_id(), Side.sell, 12.5, 40))        # 3
        a.append(Order(self.next_id(), Side.buy, 12.3, 20))         # 4, 0 partial filled
        a.append(Cancel(0))                                         # 5, cancel 0
        a.append(Order(self.next_id(), Side.buy, 12.5, 20))         # 6, 1 partial filled

        engine = Engine()
        for action in a:
            engine.process(action)

        assert(a[0].leave_qty == 0)
        assert(a[0].status == OrderStatus.cancelled)
        assert(a[0].avg_fill_price == 12.3)
        assert(a[0].acum_amount == 12.3 * 20)

        assert(a[1].leave_qty == 20)
        assert(a[1].status == OrderStatus.partial_fill)
        assert(a[1].avg_fill_price == 12.3)
        assert(a[1].acum_amount == 12.3 * 20)

        assert(a[4].leave_qty == 0)
        assert(a[4].status == OrderStatus.filled)

        assert(a[6].leave_qty == 0)
        assert(a[6].status == OrderStatus.filled)




        
    def test_trade_buy(self):
        self.reset_id()
        a = []
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))
        a.append(Order(self.next_id(), Side.sell, 12.4, 40))
        a.append(Order(self.next_id(), Side.sell, 12.5, 40))
        a.append(Order(self.next_id(), Side.buy, 12.2, 100))
        a.append(Order(self.next_id(), Side.buy, 12.6, 100))

        engine = Engine()
        for action in a:
            engine.process(action)

        assert(a[2].leave_qty == 20)
        assert(a[4].leave_qty == 100)
        assert(a[5].leave_qty == 0)


    def test_trade_sell_multilevel(self):
        self.reset_id()
        a = []
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))        # 0
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))        # 1
        a.append(Order(self.next_id(), Side.sell, 12.4, 40))        # 2
        a.append(Order(self.next_id(), Side.sell, 12.5, 40))        # 3
        a.append(Order(self.next_id(), Side.buy, 12.0, 100))        # 4
        a.append(Order(self.next_id(), Side.buy, 10.0, 100))        # 5
        a.append(Order(self.next_id(), Side.sell, 10.0, 150))       # 6

        engine = Engine()
        for action in a:
            engine.process(action)

        assert(a[4].leave_qty == 0)
        assert(a[4].status == OrderStatus.filled)
        assert(a[4].avg_fill_price == 12.0)

        assert(a[5].leave_qty == 50)
        assert(a[5].status == OrderStatus.partial_fill)
        assert(a[5].avg_fill_price == 10.0)

        assert(a[6].leave_qty == 0)
        assert(a[6].avg_fill_price == pytest.approx(11.333333))
    
    def test_trade_buy_two(self):
        self.reset_id()
        a = []
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))        # 0
        a.append(Order(self.next_id(), Side.sell, 12.3, 40))        # 1
        a.append(Order(self.next_id(), Side.sell, 12.4, 40))        # 2
        a.append(Order(self.next_id(), Side.sell, 12.5, 40))        # 3
        a.append(Order(self.next_id(), Side.buy, 12.0, 100))        # 4
        a.append(Order(self.next_id(), Side.buy, 10.0, 100))        # 5
        a.append(Order(self.next_id(), Side.buy, 12.4, 80))         # 6

        engine = Engine()
        for action in a:
            engine.process(action)

        assert(a[0].leave_qty == 0)
        assert(a[0].status == OrderStatus.filled)
        assert(a[0].avg_fill_price == 12.3)

        assert(a[1].leave_qty == 0)
        assert(a[1].status == OrderStatus.filled)
        assert(a[1].avg_fill_price == 12.3)

        assert(a[6].leave_qty == 0)
        assert(a[6].status == OrderStatus.filled)
        assert(a[6].avg_fill_price == 12.3)

