import streamlit as st

# ✅ MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="🩺 UpCharika", layout="wide")

import json
import bcrypt
import os
import gdown
import zipfile
from groq import Groq
from dotenv import load_dotenv
from gtts import gTTS
import tempfile
from deep_translator import GoogleTranslator
from streamlit_cookies_manager import EncryptedCookieManager

# ================= GOOGLE DRIVE VECTORSTORE =================
VECTOR_URL = "https://drive.google.com/uc?id=1UunmpU4iudJycj-OibngzcJf18nA6OmR"
def load_vectorstore():
    if not os.path.exists("vectorstore/db_faiss/index.faiss"):
        with st.spinner("⚡ Preparing AI system... please wait"):
            gdown.download(VECTOR_URL, "vs.zip", quiet=False)

            with zipfile.ZipFile("vs.zip", 'r') as zip_ref:
                zip_ref.extractall("vectorstore")

            os.remove("vs.zip")

# ================= COOKIES =================
cookies = EncryptedCookieManager(
    prefix="upcharika_",
    password="super_secret_key"
)

if not cookies.ready():
    st.stop()

# ================= STYLE =================
st.markdown("""
<style>
.chat-container {
    max-width: 800px;
    margin: auto;
}
.user-msg {
    background: #2563eb;
    color: white;
    padding: 12px;
    border-radius: 12px;
    margin: 8px 0;
    width: fit-content;
    max-width: 70%;
    margin-left: auto;
}
.bot-msg {
    background: #1f2937;
    color: #e5e7eb;
    padding: 12px;
    border-radius: 12px;
    margin: 8px 0;
    width: fit-content;
    max-width: 70%;
}
</style>
""", unsafe_allow_html=True)

# ================= ENV =================
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

USER_DB = "users.json"

# ================= USER DB =================
def load_users():
    try:
        with open(USER_DB, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f)

# ================= AUTH =================
def register_user(username, password):
    users = load_users()
    if username in users:
        return False, "User exists"

    users[username] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    save_users(users)
    return True, "Registered successfully"

def login_user(username, password):
    users = load_users()
    if username not in users:
        return False, "User not found"

    if bcrypt.checkpw(password.encode(), users[username].encode()):
        return True, "Login success"

    return False, "Wrong password"

# ================= CLEAN TEXT =================
def clean_text_for_voice(text):
    for ch in ["*", "#", "=", "-", "•"]:
        text = text.replace(ch, "")
    return text

# ================= AI =================
def get_ai_response(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": """You are a professional medical assistant.

Do NOT use symbols (*, **, ==).
Use simple headings:
Cause:
Solution:
Medicine:
When to see doctor:
Emergency:
"""
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

# ================= TRANSLATION =================
def translate_text(text, lang):
    if lang == "English":
        return text
    return GoogleTranslator(source="auto", target=lang.lower()).translate(text)

# ================= VOICE =================
def generate_voice(text, lang):
    try:
        lang_map = {"English": "en", "Hindi": "hi", "Marathi": "mr"}
        tts = gTTS(text=text, lang=lang_map.get(lang, "en"))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except:
        return None

# ================= AUTH UI =================
def auth_ui():
    st.title("🔐 UpCharika Login")

    menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

    if menu == "Login":
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")

        if st.button("Login"):
            ok, msg = login_user(user, pw)
            if ok:
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.chat_history = []

                cookies["logged_in"] = "true"
                cookies["username"] = user
                cookies.save()

                st.rerun()
            else:
                st.error(msg)

    else:
        user = st.text_input("New Username")
        pw = st.text_input("New Password", type="password")

        if st.button("Register"):
            ok, msg = register_user(user, pw)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

# ================= CHAT =================
def chatbot_ui(username):
    st.title("🩺 UpCharika")
    st.caption("AI-powered medical assistant")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        cookies["logged_in"] = ""
        cookies["username"] = ""
        cookies.save()
        st.rerun()

    lang = st.sidebar.selectbox("🌍 Language", ["English", "Hindi", "Marathi"])

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.chat_input("Ask your medical question...")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "text": user_input})

        answer = get_ai_response(user_input)
        translated = translate_text(answer, lang)

        clean_text = clean_text_for_voice(translated)
        audio = generate_voice(clean_text, lang)

        st.session_state.chat_history.append({
            "role": "bot",
            "text": translated,
            "audio": audio
        })

    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-msg'>{msg['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>{msg['text']}</div>", unsafe_allow_html=True)
            if msg.get("audio"):
                st.audio(msg["audio"])

    st.markdown("</div>", unsafe_allow_html=True)

# ================= MAIN =================
def main():

    # 🔥 PRELOAD VECTORSTORE (BACKGROUND LIKE BEHAVIOR)
    if "vs_loaded" not in st.session_state:
        load_vectorstore()
        st.session_state.vs_loaded = True

    # 🔥 AUTO LOGIN
    if "logged_in" not in st.session_state:
        if cookies.get("logged_in") == "true":
            st.session_state.logged_in = True
            st.session_state.username = cookies.get("username")
        else:
            st.session_state.logged_in = False

    if st.session_state.logged_in:
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        chatbot_ui(st.session_state.username)
    else:
        auth_ui()

if __name__ == "__main__":
    main()