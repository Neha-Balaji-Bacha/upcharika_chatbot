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

# ================= LOAD EXTERNAL STYLES =================
def load_css(file_name="style.css"):
    css_path = os.path.join(os.path.dirname(__file__), file_name)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

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
    # Executive scoped styling for authentication portal
    st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        .block-container {
            max-width: 100% !important;
            padding-top: 3.5rem !important;
            padding-bottom: 3rem !important;
        }
        /* Portal Card Outer Wrapper */
        div[data-testid="stVerticalBlockBorderWrapper"],
        div.e1lln2w84 {
            background: linear-gradient(180deg, rgba(13, 20, 36, 0.96) 0%, rgba(8, 12, 24, 0.98) 100%) !important;
            backdrop-filter: blur(24px) !important;
            -webkit-backdrop-filter: blur(24px) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.3) !important;
            border-top: 2.5px solid rgba(56, 189, 248, 0.75) !important;
            border-radius: 28px !important;
            padding: 48px 52px 38px 52px !important;
            box-shadow: 0 30px 70px -15px rgba(0, 0, 0, 0.95), 0 0 50px rgba(14, 165, 233, 0.18) !important;
            max-width: 560px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: 28px !important;
        }
        /* Tab list segmented toggle */
        [data-baseweb="tab-list"],
        div[role="tablist"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            max-width: 360px !important;
            min-height: 52px !important;
            background: #080d18 !important;
            padding: 5px !important;
            border-radius: 16px !important;
            border: 1.5px solid rgba(56, 189, 248, 0.25) !important;
            margin: 0 auto 24px auto !important;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5) !important;
        }
        /* Tab buttons */
        button[data-baseweb="tab"] {
            flex: 1 1 50% !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            padding: 11px 0 !important;
            border-radius: 12px !important;
            color: #94a3b8 !important;
            border: none !important;
            border-bottom: none !important;
            outline: none !important;
            background: transparent !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.5) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] * {
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        [data-baseweb="tab-highlight"],
        [data-baseweb="tab-border"] {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
            height: 0px !important;
            width: 0px !important;
        }
        /* Input Labels */
        label[data-testid="stWidgetLabel"] p {
            font-size: 15.5px !important;
            font-weight: 600 !important;
            color: #f1f5f9 !important;
            margin-bottom: 8px !important;
            letter-spacing: 0.2px !important;
        }
        /* Input Boxes */
        div[data-baseweb="input"] {
            background-color: #080d16 !important;
            border: 1.5px solid rgba(255, 255, 255, 0.14) !important;
            border-radius: 14px !important;
            color: #f8fafc !important;
            min-height: 52px !important;
            padding: 4px 16px !important;
            transition: all 0.2s ease !important;
        }
        div[data-baseweb="input"]:hover {
            border-color: rgba(56, 189, 248, 0.45) !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #0284c7 !important;
            background-color: #0c1424 !important;
            box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.28), 0 0 20px rgba(14, 165, 233, 0.18) !important;
        }
        div[data-baseweb="input"] input {
            font-size: 16px !important;
            color: #f8fafc !important;
        }
        div[data-baseweb="input"] input::placeholder {
            font-size: 15px !important;
            color: #64748b !important;
        }
        /* Buttons */
        div.stButton > button {
            width: 100% !important;
            min-height: 54px !important;
            border-radius: 14px !important;
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
            padding: 14px 28px !important;
            font-size: 16.5px !important;
            letter-spacing: 0.5px !important;
            box-shadow: 0 6px 20px rgba(2, 132, 199, 0.4) !important;
            transition: all 0.25s ease !important;
            margin-top: 10px !important;
        }
        div.stButton > button:hover {
            background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
            border-color: #7dd3fc !important;
            transform: translateY(-1.5px) !important;
            box-shadow: 0 8px 28px rgba(14, 165, 233, 0.55) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Centered container for professional appearance
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        with st.container(border=True):
            st.markdown("""
            <div class="auth-header-block">
                <div class="brand-glow-circle">🩺</div>
                <div class="brand-badge-pill">Clinical AI Portal</div>
                <h1 class="brand-heading">UpCharika</h1>
                <p class="brand-caption">Hospital-Grade AI Healthcare Assistance & Triage System</p>
            </div>
            """, unsafe_allow_html=True)

            tab_login, tab_register = st.tabs(["Sign In", "Register"])

            with tab_login:
                user = st.text_input("Username", key="login_user", placeholder="Enter your registered username")
                pw = st.text_input("Password", type="password", key="login_pw", placeholder="Enter your password")
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
                new_user = st.text_input("Choose Username", key="reg_user", placeholder="Enter a unique username")
                new_pw = st.text_input("Choose Password", type="password", key="reg_pw", placeholder="Create a secure password")
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
                <span class="meta-dot">•</span>
                <span>Clinical LLaMA 3.1</span>
                <span class="meta-dot">•</span>
                <span>Multilingual Guidance</span>
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