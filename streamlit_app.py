"""Streamlit operations console for the AI customer-support API."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st


def setting(name: str, default: str) -> str:
    """Read a Streamlit secret, falling back to an environment variable."""

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return str(value or os.getenv(name, default))


API_URL = setting("API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
CUSTOMER_ID = setting("CUSTOMER_ID", "C001")
KNOWLEDGE_ADMIN_TOKEN = setting("KNOWLEDGE_ADMIN_TOKEN", "")


@st.cache_resource
def api_client() -> httpx.Client:
    return httpx.Client(base_url=API_URL, timeout=30.0)


def api_request(path: str, method: str = "GET", **kwargs: Any) -> Any:
    response = api_client().request(method, path, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"API error ({response.status_code}): {detail}")
    return response.json() if response.content else None


def badge(value: str, kind: str = "") -> None:
    st.markdown(f'<span class="badge {kind}">{value.replace("_", " ")}</span>', unsafe_allow_html=True)


def render_workspace() -> None:
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "decision" not in st.session_state:
        st.session_state.decision = None

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.subheader("Customer chat")
        st.caption(f"Demo customer · {CUSTOMER_ID}")
        chat_box = st.container(height=430, border=True)
        with chat_box:
            if not st.session_state.messages:
                st.info("Ask about shipping, returns, warranty, account access, or an order.")
            for item in st.session_state.messages:
                with st.chat_message(item["sender"]):
                    st.write(item["content"])
        prompt = st.chat_input("Type a support question…")
        if prompt:
            st.session_state.messages.append({"sender": "user", "content": prompt})
            try:
                result = api_request(
                    "/chat",
                    "POST",
                    json={
                        "customer_id": CUSTOMER_ID,
                        "message": prompt,
                        "conversation_id": st.session_state.conversation_id,
                    },
                )
                st.session_state.conversation_id = result["conversation_id"]
                st.session_state.messages.append({"sender": "assistant", "content": result["response"]})
                st.session_state.decision = result
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

    with right:
        st.subheader("Agent decision")
        decision = st.session_state.decision
        if not decision:
            st.info("Send a message to inspect classification, safety, and sources.")
        else:
            status = "Human review" if decision["escalated"] else "Automated"
            badge(status, "red" if decision["escalated"] else "green")
            fields = {
                "Intent": decision["intent"],
                "Priority": decision["priority"],
                "Sentiment": decision["sentiment"],
                "Confidence": f'{decision["confidence"]:.0%}',
                "Suggested action": decision["suggested_action"],
            }
            for label, value in fields.items():
                st.metric(label, str(value).replace("_", " ").title())
            if decision["escalation_reasons"]:
                st.warning("Escalation: " + ", ".join(decision["escalation_reasons"]))
            st.markdown("**Retrieved sources**")
            if decision["sources"]:
                for source in decision["sources"]:
                    with st.expander(f'{source["title"]} · {source["source"]}'):
                        st.write(source["excerpt"])
            else:
                st.caption("No source evidence was retrieved.")

    st.divider()
    render_history()


def render_history() -> None:
    st.subheader("Conversation history")
    try:
        conversations = api_request(f"/conversations?customer_id={CUSTOMER_ID}")
    except RuntimeError as exc:
        st.error(str(exc))
        return
    if not conversations:
        st.caption("Completed conversations will appear here.")
        return
    options = {f'{item.get("subject") or "Support conversation"} · {item["id"][:8]}': item["id"] for item in conversations}
    selected = st.selectbox("Select a conversation", ["Choose a conversation"] + list(options))
    if selected != "Choose a conversation":
        transcript = api_request(f"/conversations/{options[selected]}?customer_id={CUSTOMER_ID}")
        for message in transcript["messages"]:
            with st.chat_message(message["sender"]):
                st.write(message["content"])


def render_queue() -> None:
    st.subheader("Human review queue")
    try:
        tickets = api_request("/dashboard/tickets")
    except RuntimeError as exc:
        st.error(str(exc))
        return
    open_count = sum(ticket["status"] != "resolved" for ticket in tickets)
    st.caption(f"{open_count} open ticket(s)")
    if not tickets:
        st.info("No tickets need review.")
        return
    for ticket in tickets:
        with st.container(border=True):
            badge(ticket["priority"], "red" if ticket["priority"] == "urgent" else "amber")
            st.write(ticket["summary"])
            st.caption(f'Assigned to: {ticket.get("assignee") or "Unassigned"} · Status: {ticket["status"]}')
            if ticket["status"] != "resolved":
                assignee = st.text_input("Assignee", value=ticket.get("assignee") or "", key=f"assignee-{ticket['id']}")
                note = st.text_area("Human note or suggested response", key=f"note-{ticket['id']}")
                save, resolve = st.columns(2)
                with save:
                    if st.button("Save note", key=f"save-{ticket['id']}"):
                        api_request(f'/dashboard/tickets/{ticket["id"]}', "PATCH", json={"status": "pending", "assignee": assignee or None, "note": note or None})
                        st.rerun()
                with resolve:
                    if st.button("Resolve", key=f"resolve-{ticket['id']}"):
                        api_request(f'/dashboard/tickets/{ticket["id"]}', "PATCH", json={"status": "resolved", "assignee": assignee or None, "note": note or None})
                        st.rerun()


def render_analytics() -> None:
    st.subheader("Support analytics")
    try:
        metrics = api_request("/dashboard/metrics")
    except RuntimeError as exc:
        st.error(str(exc))
        return
    columns = st.columns(4)
    for column, label, value in zip(
        columns,
        ["Conversations", "Messages", "Open tickets", "Automation rate"],
        [metrics["conversations"], metrics["messages"], metrics["open_tickets"], f'{metrics["automation_rate"]:.0%}'],
        strict=True,
    ):
        column.metric(label, value)
    st.markdown("#### Top intents")
    intents = metrics.get("top_intents", {})
    if intents:
        st.bar_chart(intents)
    else:
        st.caption("No decision events yet.")


def main() -> None:
    st.set_page_config(page_title="Northstar Support", page_icon="✦", layout="wide")
    st.markdown("""
    <style>
    .badge { border-radius: 999px; padding: .25rem .55rem; font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; border: 1px solid #777; }
    .green { color: #267a43; background: #e2f4e5; border-color: #85c894; }
    .red { color: #9c3026; background: #fbe4e2; border-color: #e5a09a; }
    .amber { color: #8b5b08; background: #fff1cf; border-color: #e6c979; }
    </style>
    """, unsafe_allow_html=True)
    st.title("Northstar support operations")
    st.caption("AI customer support with grounded answers and human oversight")
    page = st.sidebar.radio("Navigate", ["Workspace", "Review queue", "Analytics"])
    st.sidebar.caption(f"API: {API_URL}")
    st.sidebar.caption(f"Customer: {CUSTOMER_ID}")
    if page == "Workspace":
        render_workspace()
    elif page == "Review queue":
        render_queue()
    else:
        render_analytics()


if __name__ == "__main__":
    main()
