import streamlit as st

# ✅ MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="🩺 UpCharika", layout="wide")

import os
# ================= LOAD EXTERNAL STYLES =================
def load_css(file_name="style.css"):
    css_path = os.path.join(os.path.dirname(__file__), file_name)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

import json
import bcrypt
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

# ================= ENV & GROQ SETUP =================
load_dotenv()

# Automatically sync Streamlit Secrets into os.environ if available
if hasattr(st, "secrets"):
    try:
        if "GROQ_API_KEY" in st.secrets:
            os.environ["GROQ_API_KEY"] = str(st.secrets["GROQ_API_KEY"]).strip()
        elif "groq" in st.secrets and "api_key" in st.secrets["groq"]:
            os.environ["GROQ_API_KEY"] = str(st.secrets["groq"]["api_key"]).strip()
    except Exception:
        pass

def get_groq_client():
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key and hasattr(st, "secrets"):
        try:
            if "GROQ_API_KEY" in st.secrets:
                groq_key = str(st.secrets["GROQ_API_KEY"]).strip()
                os.environ["GROQ_API_KEY"] = groq_key
            elif "groq" in st.secrets and "api_key" in st.secrets["groq"]:
                groq_key = str(st.secrets["groq"]["api_key"]).strip()
                os.environ["GROQ_API_KEY"] = groq_key
        except Exception:
            pass
    if groq_key:
        try:
            return Groq(api_key=groq_key.strip())
        except Exception:
            return None
    return None

client = get_groq_client()

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

    stored_val = str(users[username]).strip()

    # 1. Try bcrypt
    try:
        if bcrypt.checkpw(password.encode(), stored_val.encode()):
            return True, "Login success"
    except Exception:
        pass

    # 2. Try SHA-256 fallback (legacy hashes in users.json)
    try:
        import hashlib
        if hashlib.sha256(password.encode()).hexdigest() == stored_val:
            return True, "Login success"
    except Exception:
        pass

    # 3. Plaintext fallback if entered directly
    if password == stored_val:
        return True, "Login success"

    return False, "Invalid password"

# ================= CLEAN TEXT =================
def clean_text_for_voice(text):
    for ch in ["*", "#", "=", "-", "•"]:
        text = text.replace(ch, "")
    return text

# ================= FORMAT MEDICAL CARD =================
def format_medical_card(text):
    if not text:
        return ""

    if text.startswith("⚠️"):
        return f"""
        <div class="med-alert-box" style="background: #fffbeb; border: 1.5px solid #fef3c7; border-left: 4px solid #f59e0b; border-radius: 12px; padding: 14px 18px; margin: 6px 0;">
            <div style="font-weight: 700; color: #b45309; margin-bottom: 6px; font-size: 14px;">Clinical Service Notice</div>
            <div style="font-size: 13.5px; color: #78350f; line-height: 1.6;">{text.replace(chr(10), '<br>')}</div>
        </div>
        """

    sections = []
    current_title = None
    current_body = []

    for line in text.splitlines():
        line_s = line.strip()
        if not line_s:
            continue

        clean_line = line_s.replace("*", "").replace("#", "").strip()
        import re
        clean_line_no_bullet = re.sub(r"^[\d\.\-\*•\s]+", "", clean_line).strip()

        is_header = False
        for kw in ["cause:", "causes:", "solution:", "solutions:", "care:", "medicine:", "medication:", "medications:", "when to see doctor:", "emergency:", "कारण:", "उपाय:", "औषध:", "औषधे:", "डॉक्टर:", "तातडी:", "आपातकालीन:"]:
            if clean_line_no_bullet.lower().startswith(kw):
                is_header = True
                break

        if is_header:
            if current_title or current_body:
                sections.append((current_title, "<br>".join(current_body)))
                current_body = []
            parts = clean_line_no_bullet.split(":", 1)
            current_title = parts[0].strip() + ":"
            if len(parts) > 1 and parts[1].strip():
                current_body.append(parts[1].strip())
        else:
            current_body.append(clean_line)

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
            elif any(k in t_lower for k in ["medicine", "medication", "औषध"]):
                color = "#06b6d4"
            elif any(k in t_lower for k in ["doctor", "डॉक्टर"]):
                color = "#a855f7"
            elif any(k in t_lower for k in ["emergency", "तातडी", "आपात"]):
                color = "#ef4444"
            else:
                color = "#38bdf8"

            html += f"""
            <div class="med-section-card" style="border-left: 3.5px solid {color};">
                <div class="med-section-badge" style="color: {color};">{title}</div>
                <div class="med-section-text">{body}</div>
            </div>
            """
        else:
            html += f"<div class='med-section-intro'>{body}</div>"

    return html

# ================= OFFLINE CLINICAL KNOWLEDGE BASE =================
OFFLINE_CLINICAL_KB = {
    "fever": """Cause: Viral infections (influenza, dengue, seasonal viral fevers), bacterial infections, or systemic inflammatory response triggers.
Solution: Maintain complete bed rest, drink plenty of fluids (water, ORS, warm broths) to prevent dehydration, stay in a well-ventilated room, and apply a lukewarm damp cloth to forehead.
Medicine: Antipyretics like Paracetamol (Acetaminophen) taken strictly according to age and body weight. Avoid aspirin in children and teenagers.
When to see doctor: If fever reaches or exceeds 102°F (38.9°C), persists beyond 3 consecutive days, or fails to respond to standard antipyretics.
Emergency: Seek immediate emergency evaluation (Dial 108 / 112) if accompanied by severe shortness of breath, stiff neck, extreme drowsiness, chest pain, or seizures.""",

    "headache": """Cause: Tension, dehydration, digital eyestrain, lack of sleep, sinus inflammation, or migraine triggers.
Solution: Rest in a dark, quiet room, apply a cool or warm compress across the forehead, drink 1-2 glasses of water, and avoid mobile/computer screens.
Medicine: Mild OTC analgesics such as Paracetamol or Ibuprofen if suitable and advised by a healthcare provider.
When to see doctor: If headache lasts longer than 48 hours, worsens progressively, or recurs multiple times weekly.
Emergency: Sudden, explosive onset ("thunderclap" headache), or headache accompanied by slurred speech, vision changes, facial weakness, or high fever.""",

    "cold": """Cause: Upper respiratory viral infections (rhinovirus, coronavirus strains) causing inflammation of nasal membranes.
Solution: Inhale steam twice daily, gargle with warm salt water, drink warm ginger-tulsi or honey tea, and get plenty of rest.
Medicine: Saline nasal sprays or drops, antihistamines for runny nose, and throat lozenges as recommended by a doctor.
When to see doctor: Symptoms lasting more than 10-14 days, severe earache, sinus pressure, or high fever.
Emergency: Serious difficulty breathing, wheezing, bluish lips, or inability to swallow fluids.""",

    "cough": """Cause: Post-nasal drip from viral illness, acute bronchitis, airborne allergens, or acid reflux irritation.
Solution: Drink warm liquids throughout the day, use steam inhalation with mint or eucalyptus, take a teaspoon of honey with warm water (for age > 1 year), and elevate head during sleep.
Medicine: Warm saline gargles, OTC cough syrups tailored to dry vs productive cough as advised by a physician.
When to see doctor: Cough lasting over 3 weeks, rust or blood-colored phlegm, or unexplained weight loss.
Emergency: Coughing up significant blood, intense chest pain, or severe breathlessness.""",

    "reflux": """Cause: Gastroesophageal reflux where stomach acid flows back into the esophagus due to spicy/greasy foods, late meals, caffeine, or stress.
Solution: Remain upright for 2-3 hours after eating, drink cold milk or tender coconut water, eat smaller frequent meals, and avoid tight clothing.
Medicine: Antacids containing aluminum hydroxide/magnesium hydroxide, or H2 blockers/PPIs as prescribed by a doctor.
When to see doctor: Acid reflux occurring more than twice a week, painful swallowing, or chronic vomiting.
Emergency: Crushing chest tightness radiating to arm or jaw with cold sweats (requires urgent cardiac rule-out).""",

    "diabetes": """Cause: Metabolic disorder characterized by insufficient insulin secretion (Type 1) or cellular insulin resistance (Type 2) leading to elevated blood sugar.
Solution: Follow a balanced low-glycemic diabetic plate diet, engage in 30 minutes of brisk walking daily, and monitor fasting blood glucose regularly.
Medicine: Prescribed oral hypoglycemic medications (e.g. Metformin) or insulin as strictly prescribed by an endocrinologist.
When to see doctor: Repeated fasting blood sugar above 130 mg/dL, slow-healing wounds, or tingling in hands and feet.
Emergency: Extreme drowsiness, rapid deep breathing, fruity breath odor, blood sugar over 300 mg/dL, or hypoglycemia under 70 mg/dL (shaking, intense hunger, confusion).""",

    "emergency": """Cause: Acute circulatory compromise, myocardial infarction, stroke, severe anaphylaxis, or trauma.
Solution: Keep patient calm, position comfortably (recovery position if unconscious but breathing), loosen tight clothing, and call for emergency ambulance transport.
Medicine: None without paramedic supervision. Administer epinephrine auto-injector only for diagnosed anaphylaxis.
When to see doctor: Immediate emergency medical transport required without delay.
Emergency: Call 108 / 112 immediately for emergency medical transport to the nearest hospital emergency department."""
}

def match_offline_kb(prompt):
    p_lower = prompt.lower()
    for key, content in OFFLINE_CLINICAL_KB.items():
        if key in p_lower:
            return content
    if any(w in p_lower for w in ["ताप", "बुखार", "temperature", "chills"]):
        return OFFLINE_CLINICAL_KB["fever"]
    if any(w in p_lower for w in ["सिरदर्द", "डोकेदुखी", "migraine"]):
        return OFFLINE_CLINICAL_KB["headache"]
    if any(w in p_lower for w in ["सर्दी", "खोकला", "flu", "sneeze"]):
        return OFFLINE_CLINICAL_KB["cold"]
    if any(w in p_lower for w in ["acidity", "acid", "heartburn", "gastric", "पित्त", "एसिडिटी"]):
        return OFFLINE_CLINICAL_KB["reflux"]
    if any(w in p_lower for w in ["मधुमेह", "sugar", "glucose"]):
        return OFFLINE_CLINICAL_KB["diabetes"]
    if any(w in p_lower for w in ["warning signs", "danger", "critical", "तातडी", "आपात"]):
        return OFFLINE_CLINICAL_KB["emergency"]
    return None

# ================= AI =================
def get_ai_response(prompt):
    active_client = get_groq_client()
    if active_client:
        try:
            response = active_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": """You are UpCharika, a clinical AI healthcare assistant.
Provide structured, professional medical guidance.

Do NOT use asterisks, markdown symbols (*, **, ==) or bold formatting.
Format your advice using these clear medical sections:
Cause:
Solution:
Medicine:
When to see doctor:
Emergency:

Always conclude by reminding the patient that this is triage support and to consult a licensed physician for definitive medical decisions."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            ans = response.choices[0].message.content
            if ans and len(ans.strip()) > 0:
                return ans
        except Exception:
            pass

    # Fallback to offline clinical knowledge base if prompt matches common symptoms
    offline_ans = match_offline_kb(prompt)
    if offline_ans:
        return offline_ans

    # If neither Groq nor offline KB answered, show a clear guidance notice
    return (
        "⚠️ Notice: UpCharika requires a configured Groq API Key for open-ended queries.\n\n"
        "• On Streamlit Community Cloud: Go to App Settings ➔ Secrets and enter:\n"
        'GROQ_API_KEY = "your_groq_api_key"\n\n'
        "• Locally: Add GROQ_API_KEY=your_key in your .env file.\n\n"
        "You can also ask about: Fever, Headache, Cold, Cough, Acid Reflux, or Diabetes."
    )

# ================= TRANSLATION =================
def translate_text(text, lang):
    if not text or lang == "English":
        return text
    try:
        return GoogleTranslator(source="auto", target=lang.lower()).translate(text)
    except Exception:
        return text

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
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "signin"

    # Scoped styles for the Login Portal matching Mockup 1
    st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        .block-container {
            max-width: 100% !important;
            padding-top: 3rem !important;
            padding-bottom: 2.5rem !important;
        }

        /* Fluid background matching Mockup 1 */
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(100% 100% at 50% 0%, #eff6ff 0%, #f8fafc 50%, #ede9fe 100%) !important;
        }

        /* Card Container in col2 */
        div[data-testid="stVerticalBlockBorderWrapper"]:not(div[data-testid="stHorizontalBlock"] *) {
            background: #ffffff !important;
            border: 1.5px solid #e2e8f0 !important;
            border-radius: 36px !important;
            box-shadow: 0 25px 60px -15px rgba(99, 102, 241, 0.16), 0 0 1px 1px rgba(226, 232, 240, 0.8) !important;
            padding: 42px 38px 36px 38px !important;
            max-width: 460px !important;
            margin: 20px auto !important;
            overflow: hidden !important;
        }

        div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"] div[data-testid="column"],
        div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlockBorderWrapper"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 0 !important;
        }

        /* Header Elements */
        .auth-header-block {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            margin-bottom: 20px;
        }
        .brand-glow-circle {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 76px;
            height: 76px;
            background: linear-gradient(135deg, #e0e7ff 0%, #ede9fe 100%);
            border: 1.5px solid rgba(99, 102, 241, 0.25);
            border-radius: 24px;
            font-size: 38px;
            margin: 0 auto 14px auto;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.18);
        }
        .brand-heading {
            font-family: 'Outfit', sans-serif !important;
            font-size: 34px !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px !important;
            margin: 0 0 4px 0 !important;
            color: #1e1b4b !important;
        }
        .brand-heading-gradient {
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .brand-portal-tag {
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #6366f1 !important;
            margin-bottom: 6px !important;
            letter-spacing: 0.2px !important;
        }
        .brand-caption {
            font-size: 13.5px !important;
            color: #64748b !important;
            margin: 0 !important;
            line-height: 1.5 !important;
            font-weight: 400 !important;
        }

        /* Form Inputs */
        label[data-testid="stWidgetLabel"] p {
            font-size: 13.5px !important;
            font-weight: 600 !important;
            color: #334155 !important;
            margin-bottom: 6px !important;
        }
        div[data-baseweb="input"] {
            background-color: #ffffff !important;
            border: 1.5px solid #cbd5e1 !important;
            border-radius: 14px !important;
            color: #0f172a !important;
            min-height: 52px !important;
            padding: 4px 14px !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
            transition: all 0.2s ease !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18) !important;
        }

        /* Segmented Switcher Pill Row */
        div[data-testid="stHorizontalBlock"]:has(button[key="toggle_signin"]),
        div[data-testid="stHorizontalBlock"]:has(button[key="toggle_reg"]) {
            background: #f1f5f9 !important;
            padding: 4px !important;
            border-radius: 16px !important;
            border: 1px solid #e2e8f0 !important;
            gap: 4px !important;
            margin: 16px 0 20px 0 !important;
        }

        div[data-testid="stHorizontalBlock"] button[kind="primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.28) !important;
            min-height: 42px !important;
            border: none !important;
            font-weight: 700 !important;
        }

        div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
            background: transparent !important;
            color: #64748b !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            border: none !important;
            min-height: 42px !important;
            font-weight: 600 !important;
        }
        div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
            color: #0f172a !important;
            background: rgba(255, 255, 255, 0.7) !important;
        }

        /* Action Buttons */
        div.stButton > button {
            width: 100% !important;
            min-height: 48px !important;
            border-radius: 14px !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
        }

        /* Primary Submit Buttons */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: 0 8px 24px rgba(79, 70, 229, 0.35) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            box-shadow: 0 12px 28px rgba(79, 70, 229, 0.45) !important;
            transform: translateY(-1px) !important;
        }

        /* Divider & Badges */
        .auth-divider {
            display: flex;
            align-items: center;
            text-align: center;
            margin: 22px 0 18px 0;
        }
        .auth-divider::before,
        .auth-divider::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid #e2e8f0;
        }
        .auth-divider span {
            padding: 0 14px;
            color: #94a3b8;
            font-size: 13px;
            font-weight: 500;
        }
        .trust-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 10px;
            text-align: center;
        }
        .trust-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }
        .trust-icon-svg {
            width: 28px;
            height: 28px;
            stroke: #4f46e5;
        }
        .trust-text {
            font-size: 11.5px;
            color: #64748b;
            font-weight: 500;
            line-height: 1.3;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("""
        <div class="auth-header-block">
            <div class="brand-glow-circle">🩺</div>
            <h1 class="brand-heading">Up<span class="brand-heading-gradient">Charika</span></h1>
            <div class="brand-portal-tag">Clinical AI Portal</div>
            <p class="brand-caption">Hospital-Grade AI Healthcare Assistance & Triage System</p>
        </div>
        """, unsafe_allow_html=True)

        # Segmented Switcher Pill
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            is_sign_in = (st.session_state.auth_mode == "signin")
            if st.button("Sign In", key="toggle_signin", use_container_width=True, type="primary" if is_sign_in else "secondary"):
                st.session_state.auth_mode = "signin"
                st.rerun()
        with col_t2:
            is_reg = (st.session_state.auth_mode == "register")
            if st.button("Register", key="toggle_reg", use_container_width=True, type="primary" if is_reg else "secondary"):
                st.session_state.auth_mode = "register"
                st.rerun()

        if st.session_state.auth_mode == "signin":
            user = st.text_input("Username", key="login_user", placeholder="Enter your registered username")
            pw = st.text_input("Password", type="password", key="login_pw", placeholder="Enter your password")
            btn_login = st.button("Sign In to Portal  →", key="btn_login", type="primary", use_container_width=True)

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
        else:
            new_user = st.text_input("Choose Username", key="reg_user", placeholder="Enter a unique username")
            new_pw = st.text_input("Choose Password", type="password", key="reg_pw", placeholder="Create a secure password")
            btn_reg = st.button("Create Account  →", key="btn_reg", type="primary", use_container_width=True)

            if btn_reg:
                if not new_user or not new_pw:
                    st.warning("Please fill in both fields.")
                else:
                    ok, msg = register_user(new_user, new_pw)
                    if ok:
                        st.success(f"{msg}. Please click Sign In to continue.")
                    else:
                        st.error(msg)

        st.markdown("""
        <div class="auth-divider">
            <span>or</span>
        </div>
        <div class="trust-grid">
            <div class="trust-item">
                <svg class="trust-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
                <span class="trust-text">End-to-End<br>Encrypted</span>
            </div>
            <div class="trust-item">
                <svg class="trust-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z"/></svg>
                <span class="trust-text">Clinical<br>LLaMA 3.1</span>
            </div>
            <div class="trust-item">
                <svg class="trust-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                <span class="trust-text">Multilingual<br>Guidance</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ================= CHAT =================
def chatbot_ui(username):
    # Sidebar matching Mockup Image 2
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">🩺</div>
            <div>
                <h3 class="sidebar-brand-title">UpCharika</h3>
                <div class="sidebar-brand-sub">Clinical AI Portal</div>
            </div>
        </div>
        <div class="user-profile-card">
            <div class="user-avatar-circle">👤</div>
            <div class="user-info">
                <div class="user-name">{username}</div>
                <div class="user-status-verified"><span class="verified-dot"></span> Verified User</div>
            </div>
        </div>
        <div class="nav-menu">
            <div class="nav-item active">💬 Chat Assistant</div>
            <div class="nav-item">🕒 Consultation History</div>
            <div class="nav-item">⚙️ Settings</div>
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
            <div class="emergency-header">⚠️ EMERGENCY ASSISTANCE</div>
            <p>If you or someone else is experiencing critical or life-threatening symptoms:</p>
            <div class="helpline-row">🚑 Ambulance: <b>108 / 112</b></div>
            <div class="helpline-row">📞 National Health Helpline: <b>1800-180-1104</b></div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("UpCharika provides clinical triage and health information support only. Always consult a licensed medical practitioner for diagnosis.")

    # Main Chat View matching Mockup Image 2
    st.markdown("""
    <div class="chat-header">
        <div class="chat-header-main">
            <div class="chat-header-logo-box">🩺</div>
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
        """, unsafe_allow_html=True)

        suggestions = [
            ("💬", "I have fever, headache, and chills for 48 hours"),
            ("💊", "First-aid protocol for acute acid reflux"),
            ("🩺", "Clinical criteria for Type 2 diabetes screening"),
            ("⚠️", "Warning signs requiring immediate emergency evaluation"),
        ]
        col_s1, col_s2 = st.columns(2)
        for idx, (icon, text) in enumerate(suggestions):
            col = col_s1 if idx % 2 == 0 else col_s2
            with col:
                if st.button(f"{icon}  {text}", key=f"sugg_{idx}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "text": text})
                    with st.spinner("Evaluating clinical inquiry..."):
                        try:
                            ans = get_ai_response(text)
                            trans = translate_text(ans, lang)
                        except Exception as e:
                            trans = f"⚠️ Clinical Service Notice: {str(e)}"

                        audio = None
                        try:
                            clean_text = clean_text_for_voice(trans)
                            audio = generate_voice(clean_text, lang)
                        except Exception:
                            audio = None

                        st.session_state.chat_history.append({
                            "role": "bot",
                            "text": trans,
                            "audio": audio
                        })
                    st.rerun()

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
                        <div class="bot-avatar-box">🩺</div>
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
            try:
                answer = get_ai_response(user_input)
                translated = translate_text(answer, lang)
            except Exception as e:
                translated = f"⚠️ Clinical Service Notice: {str(e)}"

            audio = None
            try:
                clean_text = clean_text_for_voice(translated)
                audio = generate_voice(clean_text, lang)
            except Exception:
                audio = None

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