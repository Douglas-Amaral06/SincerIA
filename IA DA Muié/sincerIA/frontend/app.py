"""Interface Streamlit da SincerIA."""

from __future__ import annotations

import html
import logging
import os
from datetime import datetime

import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
logger = logging.getLogger("sinceria.frontend")
MODES = {
    "normal": "Normal",
    "sincera": "Sincera",
    "acida": "Ácida",
    "nuclear": "Nuclear",
}

st.set_page_config(page_title="SincerIA", page_icon="S", layout="wide", initial_sidebar_state="expanded")


def render_html(content: str, *, allow_javascript: bool = False) -> None:
    """Evita HTML literal em versões recentes e mantém fallback compatível."""
    if hasattr(st, "html"):
        st.html(content, unsafe_allow_javascript=allow_javascript)
    else:
        st.markdown(content, unsafe_allow_html=True)


render_html(
    """
    <style>
    :root { --paper:#f5f2eb; --ink:#201e1a; --muted:#716d65; --line:#d8d2c7; --wine:#8f302d; --soft:#ebe6dc; }
    .stApp { background:var(--paper); color:var(--ink); }
    .block-container { max-width:900px; padding:2.25rem 2.2rem 8rem; }
    section[data-testid="stSidebar"] { background:#eeebe4; border-right:1px solid var(--line); }
    section[data-testid="stSidebar"] .block-container { padding:1.55rem 1rem; }
    .brand-kicker,.section-label { color:var(--wine); font:700 .63rem/1.2 ui-sans-serif,sans-serif; letter-spacing:.16em; text-transform:uppercase; }
    .brand-name { font:700 2.1rem/1 Georgia,serif; letter-spacing:-.06em; margin:.28rem 0 .4rem; }
    .brand-copy { max-width:190px; color:var(--muted); font-size:.82rem; line-height:1.45; margin-bottom:1.5rem; }
    .empty-hero { padding:13vh 0 2rem; text-align:center; }
    .empty-hero h1 { font:400 clamp(2.5rem,7vw,4.7rem)/.95 Georgia,serif; letter-spacing:-.065em; margin:0; }
    .empty-hero p { color:var(--muted); font-size:1.02rem; line-height:1.6; max-width:430px; margin:1.2rem auto; }
    .chat-eyebrow { color:var(--wine); font:700 .67rem ui-sans-serif,sans-serif; text-transform:uppercase; letter-spacing:.13em; margin-bottom:.6rem; }
    .chat-heading { font:400 2rem/1 Georgia,serif; letter-spacing:-.045em; margin-bottom:1.75rem; }
    div[data-testid="stChatMessage"] { padding:1.05rem 0; background:transparent; border-radius:0; }
    div[data-testid="stChatMessageContent"] { color:var(--ink); font-size:1rem; line-height:1.7; }
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) { margin-left:11%; padding:1rem 1.1rem; background:var(--soft); border:1px solid var(--line); border-radius:15px 15px 3px 15px; }
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) { border-left:2px solid var(--wine); padding-left:1.2rem; margin:1.25rem 0; }
    .engine-info { color:#8e887e; font:.67rem ui-monospace,monospace; margin-top:.65rem; }
    .attachment-chip { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:.32rem .62rem; color:var(--muted); font-size:.78rem; margin:.2rem 0 .5rem; }
    div[data-testid="stChatInput"] { background:#fbfaf7; border:1px solid #bdb5a9; border-radius:14px; }
    div[data-testid="stChatInput"] textarea { background:transparent; color:var(--ink); }
    div[data-testid="stChatInput"] button { color:var(--wine); }
    .stButton button { text-align:left; border:0; background:transparent; color:var(--ink); border-radius:6px; padding:.35rem .45rem; }
    .stButton button:hover { background:#e3ddd2; color:var(--ink); }
    div[data-testid="stSidebar"] .stButton button { width:100%; }
    div[data-testid="stSidebar"] .stButton button[kind="secondary"] { font-size:.83rem; }
    [data-testid="stToggle"] label { font-size:.78rem; color:var(--muted); }
    @media(max-width:760px) { .block-container { padding:1.1rem 1rem 5rem; } .empty-hero { padding:8vh 0 1rem; } div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) { margin-left:2%; } }
    </style>
    """
)


def api_request(method: str, path: str, **kwargs):
    # Listar histórico não pode congelar a tela inteira quando o backend caiu.
    # Chamadas de chat passam um timeout maior explicitamente.
    timeout = kwargs.pop("timeout", 4)
    response = requests.request(method, f"{BACKEND_URL}{path}", timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else None


def api_error(exc: requests.RequestException) -> str:
    if getattr(exc, "response", None) is not None:
        try:
            detail = exc.response.json().get("detail", {})
            if isinstance(detail, dict):
                return str(detail.get("message", detail))
            return str(detail)
        except ValueError:
            pass
    return "Não consegui falar com o backend agora."


def conversation_groups(items: list[dict]) -> dict[str, list[dict]]:
    groups = {"Hoje": [], "Ontem": [], "Anteriores": []}
    today = datetime.now().date()
    for item in items:
        try:
            date = datetime.fromisoformat(item["updated_at"]).date()
        except (KeyError, ValueError):
            date = today
        label = "Hoje" if date == today else "Ontem" if (today - date).days == 1 else "Anteriores"
        groups[label].append(item)
    return groups


def load_conversation(conversation_id: str) -> None:
    data = api_request("GET", f"/api/conversations/{conversation_id}")
    st.session_state.active_conversation_id = data["id"]
    st.session_state.mode = data["mode"]
    st.session_state.messages = data.get("messages") or []
    st.session_state.pending = None


def create_conversation(*, reset_messages: bool = True) -> None:
    data = api_request("POST", "/api/conversations", json={"mode": st.session_state.mode})
    st.session_state.active_conversation_id = data["id"]
    if reset_messages:
        st.session_state.messages = []
        st.session_state.pending = None
    st.session_state.history_items = None


for key, value in {"messages": [], "mode": "nuclear", "debug": False, "active_conversation_id": None, "pending": None, "history_items": None}.items():
    if key not in st.session_state:
        st.session_state[key] = value


with st.sidebar:
    render_html("<div class='brand-kicker'>conversa privada</div><div class='brand-name'>SincerIA</div><div class='brand-copy'>Opiniões que seus amigos talvez sejam educados demais para dar.</div>")
    if st.button("＋ Nova conversa", key="new-conversation", use_container_width=True):
        try:
            create_conversation()
            st.rerun()
        except requests.RequestException as exc:
            st.error(api_error(exc))
    render_html("<div class='section-label' style='margin:1.6rem 0 .45rem'>Histórico</div>")
    try:
        if st.session_state.history_items is None:
            st.session_state.history_items = api_request("GET", "/api/conversations", timeout=1.5)
        for group, items in conversation_groups(st.session_state.history_items).items():
            if items:
                st.caption(group)
            for item in items:
                marker = "› " if item["id"] == st.session_state.active_conversation_id else ""
                if st.button(f"{marker}{item['title']}", key=f"conversation-{item['id']}", use_container_width=True):
                    load_conversation(item["id"])
                    st.rerun()
    except requests.RequestException:
        st.session_state.history_items = []
        st.caption("Histórico disponível quando o backend iniciar.")
    if st.button("Atualizar histórico", use_container_width=True):
        st.session_state.history_items = None
        st.rerun()
    st.divider()
    st.session_state.debug = st.toggle("Mostrar motor utilizado", value=st.session_state.debug)


if not st.session_state.messages:
    render_html("<section class='empty-hero'><h1>Pode falar.</h1><p>Ela não foi programada para concordar com você. Talvez seja exatamente por isso que você veio.</p><p><strong>Qual foi a má decisão da vez?</strong></p></section>")
else:
    render_html("<div class='chat-eyebrow'>conversa privada</div><div class='chat-heading'>Sem plateia. Sem filtro.</div>")

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        for attachment in item.get("attachments", []):
            mime_type = attachment.get("mime_type", "")
            source = attachment.get("data") or f"{BACKEND_URL}{attachment.get('url', '')}"
            if mime_type.startswith("image/"):
                st.image(source, width=360)
            elif attachment.get("url"):
                st.link_button(f"Arquivo: {attachment['filename']}", f"{BACKEND_URL}{attachment['url']}")
            else:
                render_html(f"<span class='attachment-chip'>{html.escape(attachment.get('name', 'Arquivo'))}</span>")
        if item.get("error"):
            st.error(item["content"])
        else:
            st.markdown(item["content"])
        if item["role"] == "assistant" and st.session_state.debug and item.get("provider"):
            render_html(f"<div class='engine-info'>{html.escape(item['provider'])} / {html.escape(item.get('model') or 'unknown')} · {html.escape(item.get('route') or 'unknown')}</div>")


selected_mode = st.selectbox("Modo de conversa", list(MODES), index=list(MODES).index(st.session_state.mode), format_func=lambda value: MODES[value], disabled=bool(st.session_state.pending))
submitted = st.chat_input("Escreva uma mensagem ou anexe uma foto", accept_file="multiple", file_type=["png", "jpg", "jpeg", "webp", "pdf"], disabled=bool(st.session_state.pending), max_upload_size=15)

if submitted:
    files = [{"name": item.name, "mime_type": item.type, "data": item.getvalue()} for item in submitted.files]
    message_text = submitted.text.strip() or ("Analise o que eu enviei e fale na lata." if files else "")
    if message_text:
        st.session_state.mode = selected_mode
        st.session_state.messages.append({"role": "user", "content": message_text, "attachments": files})
        st.session_state.pending = {"message": message_text, "mode": selected_mode, "files": files}
        with st.chat_message("user"):
            for item in files:
                if item["mime_type"].startswith("image/"):
                    st.image(item["data"], width=360)
                else:
                    st.caption(item["name"])
            st.markdown(message_text)

if st.session_state.pending:
    pending = st.session_state.pending
    with st.chat_message("assistant"):
        progress = st.empty()
        with progress.status("Analisando a imagem..." if pending["files"] else "Pensando...", expanded=False):
            try:
                if not st.session_state.active_conversation_id:
                    create_conversation(reset_messages=False)
                if pending["files"]:
                    multipart_files = [("files", (item["name"], item["data"], item["mime_type"])) for item in pending["files"]]
                    data = api_request("POST", "/api/chat/multimodal", timeout=120, data={"message": pending["message"], "mode": pending["mode"], "history": "[]", "conversation_id": st.session_state.active_conversation_id}, files=multipart_files)
                else:
                    data = api_request("POST", "/api/chat", timeout=120, json={"message": pending["message"], "mode": pending["mode"], "history": [], "conversation_id": st.session_state.active_conversation_id})
                st.session_state.messages.append({"role": "assistant", "content": data["response"], "provider": data["provider"], "model": data["model"], "route": data["route"]})
                st.session_state.history_items = None
            except requests.Timeout:
                st.session_state.messages.append({"role": "assistant", "content": "A resposta demorou demais. Tente enviar de novo.", "error": True})
            except requests.RequestException as exc:
                st.session_state.messages.append({"role": "assistant", "content": api_error(exc), "error": True})
            except Exception:
                logger.exception("Falha ao processar a resposta do chat")
                st.session_state.messages.append({"role": "assistant", "content": "Não consegui processar a resposta. Tente enviar de novo.", "error": True})
            finally:
                st.session_state.pending = None
        progress.empty()
        answer = st.session_state.messages[-1]
        if answer.get("error"):
            st.error(answer["content"])
        else:
            st.markdown(answer["content"])
            if st.session_state.debug:
                render_html(f"<div class='engine-info'>{html.escape(answer['provider'])} / {html.escape(answer['model'])} · {html.escape(answer['route'])}</div>")
