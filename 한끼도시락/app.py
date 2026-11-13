import streamlit as st
from datetime import date, timedelta

from services import orders as logic
from services.storage import load, save
from llm import get_reply


st.set_page_config(
    page_title="한끼도시락 주문 관리",
    layout="wide",
)

st.title("한끼도시락 — 관리자 주문 관리")
st.caption(
    "단일 로컬 사용자용 수업 초안 · 실제 고객정보를 입력하지 마세요."
)
st.info(
    "신규 주문은 오늘부터 3일 뒤 수령일로 등록할 수 있습니다. "
    "설계 가정: 1주문 1메뉴, 달력 날짜 기준, 발주 완료 이후 변경 제한. "
    "발주 완료 의미는 추가 협의가 필요합니다."
)

try:
    rows = load()
except Exception as exc:
    st.error(f"주문 데이터를 읽을 수 없습니다: {exc}")
    st.stop()

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))


def commit(updated):
    try:
        save(updated)
    except Exception as exc:
        st.error(f"저장 실패. 완료되지 않았습니다: {exc}")
        return

    st.session_state.flash = "저장 완료"
    st.rerun()


menu = st.sidebar.radio(
    "메뉴",
    ["주문 목록", "주문 등록", "준비 수량 조회"],
)

if menu == "주문 등록":
    # 신규 주문은 오늘부터 3일 뒤부터 수령 가능
    earliest_pickup = date.today() + timedelta(days=3)

    st.caption(
        f"가장 빠른 수령일: {earliest_pickup.isoformat()} "
        "(오늘부터 3일 뒤)"
    )

    with st.form("new"):
        group = st.text_input("단체명")
        item = st.text_input("메뉴명")

        qty = st.number_input(
            "수량",
            min_value=1,
            value=1,
            step=1,
        )

        pickup = st.date_input(
            "수령일",
            value=earliest_pickup,
            min_value=earliest_pickup,
            help="접수일로부터 최소 3일 이후의 날짜만 선택할 수 있습니다.",
        )

        submit = st.form_submit_button("등록")

    if submit:
        try:
            new = logic.create(
                group,
                item,
                int(qty),
                str(pickup),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.selected = new["order_id"]
            commit(rows + [new])

else:
    selected_rows = rows

    if menu == "준비 수량 조회":
        a, b = st.columns(2)
        start = a.date_input("시작일")
        end = b.date_input("종료일")

        try:
            totals, selected_rows = logic.aggregate(
                rows,
                str(start),
                str(end),
            )
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

        st.subheader("수령일·메뉴별 준비 수량")

        if totals:
            st.dataframe(
                totals,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("유효 주문 없음 · 준비 수량 0")

    st.subheader("주문 목록")

    if not selected_rows:
        st.info("주문 내역 없음")
        st.stop()

    st.dataframe(
        selected_rows,
        use_container_width=True,
        hide_index=True,
    )

    ids = [o["order_id"] for o in selected_rows]

    if st.session_state.get("selected") in ids:
        idx = ids.index(st.session_state.selected)
    else:
        idx = 0

    oid = st.selectbox(
        "상세 주문 선택",
        ids,
        index=idx,
        format_func=lambda x: next(
            (
                f"{o['group_name']} / {o['pickup_date']} / "
                f"{o['menu_name']} / {o['order_status']}"
            )
            for o in selected_rows
            if o["order_id"] == x
        ),
    )

    st.session_state.selected = oid

    order = next(o for o in rows if o["order_id"] == oid)
    p = logic.permissions(order)

    st.subheader("주문 상세")
    st.json(order)
    st.write("수정·취소 가능 여부", p)

    with st.expander("주문 수정"):
        with st.form("edit_" + oid):
            item = st.text_input(
                "메뉴",
                order["menu_name"],
                disabled=not p["full"],
            )

            pickup = st.date_input(
                "수령일 변경",
                value=date.fromisoformat(order["pickup_date"]),
                disabled=not p["full"],
            )

            qty = st.number_input(
                "수량 변경",
                min_value=1,
                value=int(order["quantity"]),
                step=1,
                disabled=not p["quantity"],
            )

            submit = st.form_submit_button(
                "수정 저장",
                disabled=not p["quantity"],
            )

        if submit:
            try:
                changed = logic.change(
                    order,
                    item,
                    int(qty),
                    str(pickup),
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                commit([
                    changed if r["order_id"] == oid else r
                    for r in rows
                ])

    target = st.selectbox(
        "상태 처리",
        ["취소", "발주 완료", "수령 완료"],
        key="target_" + oid,
    )

    confirmed = st.checkbox(
        "선택한 상태로 처리할 것을 확인합니다",
        key="confirm_" + oid,
    )

    enabled = (
        (target == "취소" and p["cancel"])
        or (
            target == "발주 완료"
            and order["order_status"] == "접수"
        )
        or (
            target == "수령 완료"
            and order["order_status"] == "발주 완료"
        )
    )

    if st.button(
        "상태 변경",
        disabled=not (confirmed and enabled),
    ):
        try:
            changed = logic.transition(order, target)
        except ValueError as exc:
            st.error(str(exc))
        else:
            commit([
                changed if r["order_id"] == oid else r
                for r in rows
            ])

    with st.expander("AI 규칙 안내"):
        if (
            st.session_state.get("chat_order") != oid
            or st.session_state.get("chat_version")
            != order["updated_at"]
        ):
            st.session_state.chat_order = oid
            st.session_state.chat_version = order["updated_at"]
            st.session_state.history = []

        if st.button("대화 초기화"):
            st.session_state.history = []

        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        with st.form("ask"):
            question = st.text_input(
                "질문",
                max_chars=500,
            )
            ask = st.form_submit_button("전송")

        if ask:
            try:
                with st.spinner("답변 생성 중"):
                    answer = get_reply(
                        order,
                        question,
                        st.session_state.history,
                    )
            except Exception as exc:
                st.error(
                    f"AI 안내 실패: {exc}. "
                    "기존 주문 기능은 계속 사용할 수 있습니다."
                )
            else:
                st.session_state.history.extend([
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ])
                st.session_state.history = (
                    st.session_state.history[-6:]
                )
                st.rerun()
