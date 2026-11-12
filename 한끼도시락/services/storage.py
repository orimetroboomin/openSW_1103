import csv, os, tempfile
from pathlib import Path
from services.orders import validate, STATES
PATH = Path(__file__).resolve().parents[1] / 'data' / 'orders.csv'
FIELDS = ['order_id','group_name','menu_name','quantity','pickup_date','order_status','created_at','updated_at']
def load(path=PATH):
    path=Path(path)
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames != FIELDS: raise ValueError('CSV 헤더가 올바르지 않습니다. 기존 파일을 확인하세요.')
        rows=list(reader)
    ids=set()
    for r in rows:
        r['quantity']=int(r['quantity'])
        validate(r['group_name'],r['menu_name'],r['quantity'],r['pickup_date'])
        if r['order_status'] not in STATES or not r['order_id'] or r['order_id'] in ids: raise ValueError('CSV 상태 또는 주문 ID 오류')
        ids.add(r['order_id'])
    return rows
def save(rows,path=PATH):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
