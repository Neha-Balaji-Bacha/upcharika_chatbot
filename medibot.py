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

# Compatibility fix for newer Streamlit versions (Streamlit >= 1.28 removed st.cache)
if not hasattr(st, "cache"):
    st.cache = st.cache_data

from streamlit_cookies_manager import EncryptedCookieManager

# ================= GOOGLE DRIVE VECTORSTORE =================
VECTOR_URL = "https://drive.google.com/uc?id=1UunmpU4iudJycj-OibngzcJf18nA6OmR"
def load_vectorstore():
    if not os.path.exists("vectorstore/db_faiss/index.faiss"):
        with st.spinner("Preparing AI system... please wait"):
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
/* Import Modern Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700&display=swap');

/* Global Reset & Typography */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
}

/* Background & Main Layout */
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 50% 0%, #0f2027 0%, #0b1522 45%, #050811 100%) !important;
    color: #f1f5f9;
}

[data-testid="stHeader"] {
    background: rgba(11, 21, 34, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

[data-testid="stSidebar"] {
    background-color: #080d18 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Auth Card Styles */
.auth-card {
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 24px;
    padding: 36px 30px 20px 30px;
    text-align: center;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 30px rgba(14, 165, 233, 0.15);
    margin-top: 25px;
    margin-bottom: 15px;
}

.auth-icon-wrap {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 68px;
    height: 68px;
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(16, 185, 129, 0.2));
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 20px;
    margin-bottom: 16px;
    box-shadow: 0 0 25px rgba(56, 189, 248, 0.25);
}

.auth-icon {
    font-size: 34px;
}

.auth-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 28px !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #38bdf8 0%, #34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 6px 0 !important;
}

.auth-desc {
    color: #94a3b8;
    font-size: 14px;
    margin: 0 0 10px 0;
    line-height: 1.5;
}

.auth-footer-badges {
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.auth-footer-badges span {
    background: rgba(30, 41, 59, 0.6);
    color: #94a3b8;
    font-size: 12px;
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Tabs Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(15, 23, 42, 0.8);
    padding: 6px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 18px;
    color: #94a3b8;
    font-weight: 600;
    font-size: 14px;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.25), rgba(16, 185, 129, 0.25)) !important;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.4);
}

/* Inputs */
div[data-baseweb="input"] {
    background-color: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
    border-radius: 12px !important;
    color: #f8fafc !important;
    transition: all 0.2s ease;
}

div[data-baseweb="input"]:focus-within {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.25) !important;
    background-color: rgba(15, 23, 42, 0.95) !important;
}

/* Buttons */
div.stButton > button {
    width: 100%;
    border-radius: 12px;
    background: linear-gradient(135deg, #0284c7 0%, #0d9488 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: none !important;
    padding: 12px 24px !important;
    font-size: 15px !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 4px 15px rgba(2, 132, 199, 0.35) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(13, 148, 136, 0.5) !important;
}

/* Chat Header */
.chat-header {
    background: rgba(15, 23, 42, 0.65);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 18px;
    padding: 18px 24px;
    margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.chat-header-main {
    display: flex;
    align-items: center;
    gap: 16px;
}

.chat-header-logo {
    font-size: 34px;
}

.chat-header-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    margin: 0 !important;
    color: #f8fafc;
}

.chat-header-subtitle {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 3px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.live-dot {
    width: 8px;
    height: 8px;
    background-color: #10b981;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 10px #10b981;
}

/* Welcome Card & Suggestions */
.welcome-card {
    background: rgba(15, 23, 42, 0.5);
    border: 1px dashed rgba(56, 189, 248, 0.25);
    border-radius: 18px;
    padding: 24px;
    text-align: center;
    margin-bottom: 20px;
}

.welcome-card h3 {
    margin: 0 0 8px 0;
    color: #e2e8f0;
    font-size: 18px;
}

.welcome-card p {
    margin: 0;
    color: #94a3b8;
    font-size: 14px;
}

.suggestion-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 28px;
}

.suggestion-pill {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 13px;
    color: #cbd5e1;
    transition: all 0.2s ease;
}

/* Chat Messages */
.chat-feed {
    max-width: 900px;
    margin: 0 auto 30px auto;
}

.chat-row {
    display: flex;
    margin-bottom: 20px;
}

.user-row {
    justify-content: flex-end;
}

.bot-row {
    justify-content: flex-start;
}

.user-bubble {
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
    color: #ffffff;
    padding: 14px 20px;
    border-radius: 20px 20px 4px 20px;
    max-width: 78%;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.3);
}

.bubble-header {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 4px;
}

.bubble-body {
    font-size: 15px;
    line-height: 1.5;
}

.bot-card {
    background: rgba(15, 23, 42, 0.85);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 20px 20px 20px 4px;
    padding: 20px 24px;
    max-width: 85%;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}

.bot-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.bot-avatar {
    font-size: 20px;
}

.bot-title {
    font-size: 13px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* Medical Card Sections */
.med-section-card {
    background: rgba(30, 41, 59, 0.45);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 12px;
}

.med-section-badge {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
}

.med-section-text {
    font-size: 14px;
    line-height: 1.6;
    color: #e2e8f0;
}

.med-section-intro {
    font-size: 14px;
    line-height: 1.6;
    color: #cbd5e1;
    margin-bottom: 12px;
}

.audio-row {
    margin-top: -10px;
    margin-bottom: 24px;
    padding-left: 20px;
    max-width: 85%;
}

/* Sidebar Components */
.user-profile-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px;
    background: rgba(30, 41, 59, 0.5);
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.user-avatar {
    font-size: 24px;
}

.user-name {
    font-weight: 700;
    color: #f8fafc;
    font-size: 15px;
}

.user-status {
    font-size: 11px;
    color: #34d399;
}

.emergency-box {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 14px;
    padding: 14px;
    margin-top: 16px;
}

.emergency-badge {
    font-size: 11px;
    font-weight: 800;
    color: #f87171;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}

.emergency-box p {
    font-size: 12px;
    color: #fca5a5;
    margin: 0 0 8px 0;
    line-height: 1.4;
}

.helpline-num {
    font-size: 13px;
    color: #ffffff;
    margin-bottom: 4px;
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
        return False, "Username already exists"

    users[username] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    save_users(users)
    return True, "Account created successfully"

def login_user(username, password):
    users = load_users()
    if username not in users:
        return False, "User not found"

    if bcrypt.checkpw(password.encode(), users[username].encode()):
        return True, "Login success"

    return False, "Invalid password"

# ================= CLEAN TEXT =================
def clean_text_for_voice(text):
    for ch in ["*", "#", "=", "-", "•"]:
        text = text.replace(ch, "")
    return text

# ================= FORMAT MEDICAL CARD =================
def format_medical_card(text):
    sections = []
    current_title = None
    current_body = []

    for line in text.splitlines():
        line_s = line.strip()
        if not line_s:
            continue

        is_header = False
        for kw in ["cause:", "solution:", "medicine:", "when to see doctor:", "emergency:", "कारण:", "उपाय:", "औषध:", "औषधे:", "डॉक्टर:", "तातडी:", "आपातकालीन:"]:
            if line_s.lower().startswith(kw):
                is_header = True
                break

        if is_header:
            if current_title or current_body:
                sections.append((current_title, "<br>".join(current_body)))
                current_body = []
            parts = line_s.split(":", 1)
            current_title = parts[0].strip() + ":"
            if len(parts) > 1 and parts[1].strip():
                current_body.append(parts[1].strip())
        else:
            current_body.append(line_s)

    if current_title or current_body:
        sections.append((current_title, "<br>".join(current_body)))

    if not sections or (len(sections) == 1 and not sections[0][0]):
        return f"<div class='med-section-intro'>{text.replace(chr(10), '<br>')}</div>"

    html = ""
    for title, body in sections:
        if title:
            t_lower = title.lower()
            if any(k in t_lower for k in ["cause", "कारण"]):
                color = "#f59e0b"
                icon = "🔍"
            elif any(k in t_lower for k in ["solution", "care", "उपाय", "समाधान"]):
                color = "#10b981"
                icon = "💡"
            elif any(k in t_lower for k in ["medicine", "औषध"]):
                color = "#06b6d4"
                icon = "💊"
            elif any(k in t_lower for k in ["doctor", "डॉक्टर"]):
                color = "#a855f7"
                icon = "👨‍⚕️"
            elif any(k in t_lower for k in ["emergency", "तातडी", "आपात"]):
                color = "#f43f5e"
                icon = "🚨"
            else:
                color = "#38bdf8"
                icon = "📋"

            html += f"""
            <div class="med-section-card" style="border-left: 3px solid {color};">
                <div class="med-section-badge" style="color: {color};">{icon} {title}</div>
                <div class="med-section-text">{body}</div>
            </div>
            """
        else:
            html += f"<div class='med-section-intro'>{body}</div>"

    return html

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
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-size: 40px; margin-bottom: 10px;">🩺</div>
            <h3 style="margin: 0; color: #38bdf8; font-family: 'Outfit', sans-serif;">UpCharika</h3>
            <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Smart Healthcare Portal</p>
        </div>
        """, unsafe_allow_html=True)
        st.info("💡 **Welcome to UpCharika!**\nPlease sign in or register to consult with the AI medical specialist.")

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div class="auth-card">
            <div class="auth-icon-wrap">
                <span class="auth-icon">🩺</span>
            </div>
            <h1 class="auth-title">UpCharika Health</h1>
            <p class="auth-desc">AI-Powered Clinical Guidance & Triage Assistant</p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 Sign In", "✨ Create Account"])

        with tab_login:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            user = st.text_input("Username", key="login_user", placeholder="Enter your username")
            pw = st.text_input("Password", type="password", key="login_pw", placeholder="Enter your password")
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            if st.button("Sign In to Portal", key="btn_login"):
                if not user or not pw:
                    st.warning("Please fill in both fields.")
                else:
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

        with tab_register:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            new_user = st.text_input("New Username", key="reg_user", placeholder="Choose a username")
            new_pw = st.text_input("New Password", type="password", key="reg_pw", placeholder="Create a secure password")
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            if st.button("Create Account", key="btn_reg"):
                if not new_user or not new_pw:
                    st.warning("Please fill in both fields.")
                else:
                    ok, msg = register_user(new_user, new_pw)
                    if ok:
                        st.success(f"{msg}! Please switch to the Sign In tab.")
                    else:
                        st.error(msg)

        st.markdown("""
        <div class="auth-footer-badges">
            <span>🔒 End-to-End Encrypted</span>
            <span>⚡ LLaMA 3.1 8B Engine</span>
            <span>🌐 3 Languages</span>
        </div>
        """, unsafe_allow_html=True)

# ================= CHAT =================
def chatbot_ui(username):
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div class="user-profile-card">
            <div class="user-avatar">👤</div>
            <div>
                <div class="user-name">{username}</div>
                <div class="user-status">🟢 Verified Patient / User</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        lang = st.selectbox("🌍 Consultation Language", ["English", "Hindi", "Marathi"], index=0)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        col_clear, col_logout = st.columns(2)
        with col_clear:
            if st.button("🗑️ Clear", help="Reset conversation"):
                st.session_state.chat_history = []
                st.rerun()
        with col_logout:
            if st.button("🚪 Logout", help="Sign out"):
                st.session_state.logged_in = False
                cookies["logged_in"] = ""
                cookies["username"] = ""
                cookies.save()
                st.rerun()

        st.markdown("---")
        st.markdown("""
        <div class="emergency-box">
            <div class="emergency-badge">🚨 EMERGENCY HELPLINE</div>
            <p>If you or someone else is experiencing critical or life-threatening symptoms:</p>
            <div class="helpline-num">🚑 Ambulance: <b>108 / 112</b></div>
            <div class="helpline-num">🏥 National Health: <b>1800-180-1104</b></div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("⚠️ UpCharika provides triage & health info only. Always seek a doctor's advice.")

    # Main Chat View
    st.markdown("""
    <div class="chat-header">
        <div class="chat-header-main">
            <span class="chat-header-logo">🩺</span>
            <div>
                <h2 class="chat-header-title">UpCharika Clinical Assistant</h2>
                <div class="chat-header-subtitle"><span class="live-dot"></span> Clinical Engine Active • LLaMA 3.1 8B</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Welcome card if no messages
    if len(st.session_state.chat_history) == 0:
        st.markdown("""
        <div class="welcome-card">
            <h3>Hello! How can I assist you with your health today?</h3>
            <p>Describe your symptoms, ask about medications, first-aid measures, or preventive health tips.</p>
        </div>
        <div class="suggestion-grid">
            <div class="suggestion-pill">🤒 "I have a high fever, headache, and chills"</div>
            <div class="suggestion-pill">💊 "First-aid and home remedies for severe acid reflux"</div>
            <div class="suggestion-pill">🩺 "What are the common early symptoms of Type 2 diabetes?"</div>
            <div class="suggestion-pill">🚨 "What warning signs require immediate emergency care?"</div>
        </div>
        """, unsafe_allow_html=True)

    # Chat Feed
    st.markdown("<div class='chat-feed'>", unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-row user-row">
                <div class="user-bubble">
                    <div class="bubble-header">👤 You</div>
                    <div class="bubble-body">{msg['text']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            formatted_content = format_medical_card(msg['text'])
            st.markdown(f"""
            <div class="chat-row bot-row">
                <div class="bot-card">
                    <div class="bot-header">
                        <span class="bot-avatar">🩺</span>
                        <span class="bot-title">UpCharika AI Medical Consultant</span>
                    </div>
                    <div class="bot-body">{formatted_content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if msg.get("audio"):
                st.markdown("<div class='audio-row'>", unsafe_allow_html=True)
                st.caption("🎙️ Audio Consultation:")
                st.audio(msg["audio"])
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # User Input
    user_input = st.chat_input("Ask your medical question or describe symptoms...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "text": user_input})

        with st.spinner("Analyzing symptoms & consulting medical knowledge base..."):
            answer = get_ai_response(user_input)
            translated = translate_text(answer, lang)

            clean_text = clean_text_for_voice(translated)
            audio = generate_voice(clean_text, lang)

            st.session_state.chat_history.append({
                "role": "bot",
                "text": translated,
                "audio": audio
            })
        st.rerun()

# ================= MAIN =================
def main():
    # Preload Vectorstore
    if "vs_loaded" not in st.session_state:
        load_vectorstore()
        st.session_state.vs_loaded = True

    # Auto Login from Cookies
    if "logged_in" not in st.session_state:
        if cookies.get("logged_in") == "true":
            st.session_state.logged_in = True
            st.session_state.username = cookies.get("username")
        else:
            st.session_state.logged_in = False

    if st.session_state.logged_in:
        chatbot_ui(st.session_state.username)
    else:
        auth_ui()

if __name__ == "__main__":
    main()