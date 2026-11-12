import unittest, tempfile
from pathlib import Path
from datetime import date
from services.orders import create,permissions,change,transition,aggregate
from services.storage import load,save
class CoreTests(unittest.TestCase):
    def setUp(self): self.o=create('테스트단체','메뉴A',10,'2026-12-10')
    def test_boundary(self):
        self.assertTrue(permissions(self.o,date(2026,12,7))['full'])
        self.assertFalse(permissions(self.o,date(2026,12,8))['full'])
        self.assertTrue(permissions(self.o,date(2026,12,9))['quantity'])
        self.assertFalse(permissions(self.o,date(2026,12,10))['quantity'])
    def test_quantity_only(self):
        self.assertEqual(change(self.o,'메뉴A',11,'2026-12-10',date(2026,12,8))['quantity'],11)
        with self.assertRaises(ValueError): change(self.o,'메뉴B',11,'2026-12-10',date(2026,12,8))
    def test_cancel(self):
        c=transition(self.o,'취소',date(2026,12,7))
        with self.assertRaises(ValueError): transition(c,'취소',date(2026,12,7))
        with self.assertRaises(ValueError): transition(self.o,'취소',date(2026,12,8))
    def test_states(self):
        with self.assertRaises(ValueError):transition(self.o,'수령 완료')
        ready=transition(self.o,'발주 완료');done=transition(ready,'수령 완료')
        self.assertEqual(done['order_status'],'수령 완료')
        self.assertFalse(permissions(ready,date(2026,12,7))['full'])
    def test_totals(self):
        b=create('B','메뉴A',5,'2026-12-10');c=create('C','메뉴A',7,'2026-12-10');c['order_status']='취소'
        totals,selected=aggregate([self.o,b,c],'2026-12-10','2026-12-10')
        self.assertEqual(totals[0]['준비 수량'],15);self.assertEqual(len(selected),3)
    def test_invalid(self):
        for q in [0,-1,1.5,True]:
            with self.assertRaises(ValueError):create('A','B',q,'2026-12-10')
        with self.assertRaises(ValueError):create(' ','B',1,'2026-12-10')
        with self.assertRaises(ValueError):aggregate([],'2026-12-11','2026-12-10')
    def test_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'orders.csv';save([self.o],p);self.assertEqual(load(p),[self.o])
            p.write_text('bad,header\n',encoding='utf-8')
            with self.assertRaises(ValueError):load(p)
if __name__=='__main__':unittest.main()
