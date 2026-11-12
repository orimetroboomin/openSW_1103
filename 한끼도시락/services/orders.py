from datetime import date, datetime
import uuid
STATES = ['접수', '발주 완료', '수령 완료', '취소']
def permissions(order, today=None):
    today = today or date.today()
    days = (date.fromisoformat(order['pickup_date']) - today).days
    active = order['order_status'] == '접수'
    return {'full': active and days >= 3, 'quantity': active and days >= 1, 'cancel': active and days >= 3}
def validate(group, menu, quantity, pickup):
    if not group.strip() or not menu.strip(): raise ValueError('단체명과 메뉴를 입력하세요.')
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1: raise ValueError('수량은 1 이상의 정수여야 합니다.')
    date.fromisoformat(pickup)
def create(group, menu, quantity, pickup):
    validate(group, menu, quantity, pickup)
    now = datetime.now().isoformat(timespec='seconds')
    return dict(order_id=uuid.uuid4().hex, group_name=group.strip(), menu_name=menu.strip(), quantity=quantity, pickup_date=pickup, order_status='접수', created_at=now, updated_at=now)
def change(order, menu, quantity, pickup, today=None):
    p = permissions(order, today)
    if not p['quantity']: raise ValueError('수정할 수 없는 상태 또는 날짜입니다.')
    if not p['full'] and (menu != order['menu_name'] or pickup != order['pickup_date']): raise ValueError('현재는 수량만 수정할 수 있습니다.')
    validate(order['group_name'], menu, quantity, pickup)
    result = dict(order, menu_name=menu.strip(), quantity=quantity, pickup_date=pickup)
    result['updated_at'] = datetime.now().isoformat(timespec='seconds')
    return result
def transition(order, target, today=None):
    allowed = (target == '취소' and permissions(order,today)['cancel']) or (target == '발주 완료' and order['order_status'] == '접수') or (target == '수령 완료' and order['order_status'] == '발주 완료')
    if not allowed: raise ValueError('허용되지 않는 상태 변경입니다.')
    return dict(order, order_status=target, updated_at=datetime.now().isoformat(timespec='seconds'))
def aggregate(orders, start, end):
    if start > end: raise ValueError('시작일이 종료일보다 늦습니다.')
    totals = {}; selected = []
    for o in orders:
        if start <= o['pickup_date'] <= end:
            selected.append(o)
            if o['order_status'] != '취소':
                key = (o['pickup_date'],o['menu_name'])
                totals[key] = totals.get(key,0) + int(o['quantity'])
    return [{'수령일': k[0], '메뉴': k[1], '준비 수량': v} for k,v in sorted(totals.items())], sorted(selected,key=lambda o:(o['pickup_date'],o['created_at']))
