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
/* Import Professional Typography */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
}

/* Background & Core Theme */
[data-testid="stAppViewContainer"] {
    background: #090e17 !important;
    color: #e2e8f0;
}

[data-testid="stHeader"] {
    background: rgba(9, 14, 23, 0.85) !important;
    backdrop-filter: blur(8px) !important;
    border-bottom: 1px solid #1e293b;
}

[data-testid="stSidebar"] {
    background-color: #0b1120 !important;
    border-right: 1px solid #1e293b !important;
}

/* Auth Portal Container - Wide, Professional, Executive */
.auth-container {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 34px 44px 28px 44px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
    margin-top: 15px;
    margin-bottom: 24px;
}

.auth-stethoscope {
    font-size: 38px;
    margin-bottom: 10px;
    display: inline-block;
}

.auth-main-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    margin: 0 0 6px 0 !important;
    letter-spacing: -0.3px;
}

.auth-sub-title {
    color: #94a3b8;
    font-size: 14px;
    margin: 0 0 4px 0;
    line-height: 1.5;
}

.auth-footer-meta {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid #1e293b;
    color: #64748b;
    font-size: 12px;
    letter-spacing: 0.2px;
}

/* Professional Streamlit Tabs - Centered */
.stTabs {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
}

.stTabs [data-baseweb="tab-list"] {
    display: flex !important;
    justify-content: center !important;
    gap: 12px;
    background-color: #0b1120;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid #1e293b;
    margin: 0 auto 20px auto !important;
    width: fit-content !important;
}

.stTabs [data-baseweb="tab-panel"] {
    width: 100% !important;
}

.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 10px 28px;
    color: #94a3b8;
    font-weight: 600;
    font-size: 14px;
}

.stTabs [aria-selected="true"] {
    background-color: #0284c7 !important;
    color: #ffffff !important;
}

/* Professional Form Inputs */
div[data-baseweb="input"] {
    background-color: #0b1120 !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px !important;
    color: #f8fafc !important;
    transition: border-color 0.15s ease-in-out;
}

div[data-baseweb="input"]:focus-within {
    border-color: #0284c7 !important;
    box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.2) !important;
}

/* Enterprise Primary Button - Centered */
div.stButton {
    display: flex !important;
    justify-content: center !important;
}

div.stButton > button {
    border-radius: 8px;
    background: #0284c7 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: 1px solid #0369a1 !important;
    padding: 12px 28px !important;
    font-size: 14px !important;
    letter-spacing: 0.2px !important;
    transition: background-color 0.15s ease-in-out;
}

div.stButton > button:hover {
    background: #0369a1 !important;
}

/* Chat Header Banner */
.chat-header {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 18px 24px;
    margin-bottom: 22px;
}

.chat-header-main {
    display: flex;
    align-items: center;
    gap: 16px;
}

.chat-header-logo {
    font-size: 30px;
}

.chat-header-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    margin: 0 !important;
    color: #f8fafc;
}

.chat-header-subtitle {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 2px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.status-indicator {
    width: 8px;
    height: 8px;
    background-color: #10b981;
    border-radius: 50%;
    display: inline-block;
}

/* Welcome Overview */
.welcome-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    margin-bottom: 20px;
}

.welcome-card h3 {
    margin: 0 0 6px 0;
    color: #f8fafc;
    font-size: 17px;
}

.welcome-card p {
    margin: 0;
    color: #94a3b8;
    font-size: 14px;
}

.suggestion-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 26px;
}

.suggestion-pill {
    background: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    color: #cbd5e1;
}

/* Chat Messages */
.chat-feed {
    max-width: 900px;
    margin: 0 auto 30px auto;
}

.chat-row {
    display: flex;
    margin-bottom: 18px;
}

.user-row {
    justify-content: flex-end;
}

.bot-row {
    justify-content: flex-start;
}

.user-bubble {
    background: #1e293b;
    color: #ffffff;
    padding: 14px 18px;
    border-radius: 12px 12px 2px 12px;
    max-width: 78%;
    border: 1px solid #334155;
}

.bubble-header {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 4px;
}

.bubble-body {
    font-size: 14px;
    line-height: 1.5;
}

.bot-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px 12px 12px 2px;
    padding: 20px 24px;
    max-width: 86%;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
}

.bot-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e293b;
}

.bot-avatar {
    font-size: 18px;
}

.bot-title {
    font-size: 13px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}

/* Structured Clinical Sections */
.med-section-card {
    background: #0b1120;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
}

.med-section-badge {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: 0.2px;
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
    margin-bottom: 10px;
}

.audio-row {
    margin-top: -8px;
    margin-bottom: 22px;
    padding-left: 20px;
    max-width: 86%;
}

/* Sidebar Components */
.user-profile-card {
    padding: 14px;
    background: #0f172a;
    border-radius: 10px;
    border: 1px solid #1e293b;
}

.user-name {
    font-weight: 700;
    color: #f8fafc;
    font-size: 15px;
}

.user-status {
    font-size: 12px;
    color: #10b981;
    margin-top: 2px;
}

.emergency-box {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 10px;
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

.sidebar-info-box {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 12px 14px;
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
            elif any(k in t_lower for k in ["solution", "care", "उपाय", "समाधान"]):
                color = "#10b981"
            elif any(k in t_lower for k in ["medicine", "औषध"]):
                color = "#06b6d4"
            elif any(k in t_lower for k in ["doctor", "डॉक्टर"]):
                color = "#a855f7"
            elif any(k in t_lower for k in ["emergency", "तातडी", "आपात"]):
                color = "#ef4444"
            else:
                color = "#38bdf8"

            html += f"""
            <div class="med-section-card" style="border-left: 3px solid {color};">
                <div class="med-section-badge" style="color: {color};">{title}</div>
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
        <div style="text-align: center; padding: 24px 0 16px 0;">
            <div style="font-size: 38px; margin-bottom: 8px;">🩺</div>
            <h3 style="margin: 0; color: #38bdf8; font-family: 'Outfit', sans-serif; font-size: 20px;">UpCharika</h3>
            <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Clinical Healthcare System</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("""
        <div class="sidebar-info-box">
            <div style="font-weight: 600; font-size: 13px; color: #cbd5e1; margin-bottom: 6px;">Portal Access</div>
            <p style="font-size: 13px; color: #94a3b8; line-height: 1.5; margin: 0;">
                Please authenticate using your registered clinical or patient credentials to access the consultation portal.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Wide, centered container for professional appearance
    col1, col2, col3 = st.columns([0.5, 3.0, 0.5])
    with col2:
        st.markdown("""
        <div class="auth-container">
            <div class="auth-stethoscope">🩺</div>
            <h1 class="auth-main-title">UpCharika Clinical Portal</h1>
            <p class="auth-sub-title">Hospital-Grade AI Healthcare Assistance and Triage System</p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Sign In", "Register"])

        with tab_login:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            user = st.text_input("Username", key="login_user", placeholder="Enter your registered username")
            pw = st.text_input("Password", type="password", key="login_pw", placeholder="Enter your password")
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns([1, 1.4, 1])
            with b2:
                btn_login = st.button("Sign In to Portal", key="btn_login", use_container_width=True)

            if btn_login:
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
            new_user = st.text_input("Choose Username", key="reg_user", placeholder="Enter a unique username")
            new_pw = st.text_input("Choose Password", type="password", key="reg_pw", placeholder="Create a secure password")
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            rb1, rb2, rb3 = st.columns([1, 1.4, 1])
            with rb2:
                btn_reg = st.button("Create Account", key="btn_reg", use_container_width=True)

            if btn_reg:
                if not new_user or not new_pw:
                    st.warning("Please fill in both fields.")
                else:
                    ok, msg = register_user(new_user, new_pw)
                    if ok:
                        st.success(f"{msg}. Please proceed to the Sign In tab.")
                    else:
                        st.error(msg)

        st.markdown("""
        <div class="auth-footer-meta">
            <span>End-to-End Encrypted</span>
            <span>•</span>
            <span>Clinical LLaMA 3.1 Architecture</span>
            <span>•</span>
            <span>Multilingual Healthcare Guidance</span>
        </div>
        """, unsafe_allow_html=True)

# ================= CHAT =================
def chatbot_ui(username):
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div class="user-profile-card">
            <div class="user-name">{username}</div>
            <div class="user-status">Verified User</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        lang = st.selectbox("Consultation Language", ["English", "Hindi", "Marathi"], index=0)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        col_clear, col_logout = st.columns(2)
        with col_clear:
            if st.button("Clear History", help="Reset conversation"):
                st.session_state.chat_history = []
                st.rerun()
        with col_logout:
            if st.button("Sign Out", help="Sign out"):
                st.session_state.logged_in = False
                cookies["logged_in"] = ""
                cookies["username"] = ""
                cookies.save()
                st.rerun()

        st.markdown("---")
        st.markdown("""
        <div class="emergency-box">
            <div class="emergency-badge">EMERGENCY ASSISTANCE</div>
            <p>If you or someone else is experiencing critical or life-threatening symptoms:</p>
            <div class="helpline-num">Ambulance: <b>108 / 112</b></div>
            <div class="helpline-num">National Health Helpline: <b>1800-180-1104</b></div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("UpCharika provides clinical triage and health information only. Always consult a licensed medical practitioner for diagnosis.")

    # Main Chat View
    st.markdown("""
    <div class="chat-header">
        <div class="chat-header-main">
            <span class="chat-header-logo">🩺</span>
            <div>
                <h2 class="chat-header-title">UpCharika Clinical Assistant</h2>
                <div class="chat-header-subtitle"><span class="status-indicator"></span> Active Clinical Engine • LLaMA 3.1 8B</div>
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
            <h3>Welcome to UpCharika Clinical Consultation</h3>
            <p>Describe your symptoms, ask about medications, or request clinical triage guidance.</p>
        </div>
        <div class="suggestion-grid">
            <div class="suggestion-pill">"Fever, persistent headache, and chills for 48 hours"</div>
            <div class="suggestion-pill">"First-aid protocol for acute acid reflux"</div>
            <div class="suggestion-pill">"Clinical criteria for Type 2 diabetes screening"</div>
            <div class="suggestion-pill">"Warning signs requiring immediate emergency evaluation"</div>
        </div>
        """, unsafe_allow_html=True)

    # Chat Feed
    st.markdown("<div class='chat-feed'>", unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-row user-row">
                <div class="user-bubble">
                    <div class="bubble-header">You</div>
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
                        <span class="bot-title">UpCharika Clinical Assistant</span>
                    </div>
                    <div class="bot-body">{formatted_content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if msg.get("audio"):
                st.markdown("<div class='audio-row'>", unsafe_allow_html=True)
                st.caption("Audio Consultation:")
                st.audio(msg["audio"])
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # User Input
    user_input = st.chat_input("Ask a medical question or describe clinical symptoms...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "text": user_input})

        with st.spinner("Evaluating clinical inquiry..."):
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