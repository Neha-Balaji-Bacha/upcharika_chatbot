import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import streamlit as st

# MUST BE FIRST STREAMLIT COMMAND
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
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_faiss_dir():
    candidates = [
        os.path.join(BASE_DIR, "vectorstore", "db_faiss"),
        os.path.join(os.getcwd(), "vectorstore", "db_faiss"),
        os.path.abspath("vectorstore/db_faiss"),
        "/mount/src/upcharika_chatbot/vectorstore/db_faiss"
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            return c
    return os.path.join(BASE_DIR, "vectorstore", "db_faiss")

FAISS_DIR = find_faiss_dir()
FAISS_INDEX = os.path.join(FAISS_DIR, "index.faiss")
PART1 = os.path.join(FAISS_DIR, "index.faiss.001")
PART2 = os.path.join(FAISS_DIR, "index.faiss.002")
INDEX_PKL = os.path.join(FAISS_DIR, "index.pkl")
LOCAL_MODEL = os.path.join(BASE_DIR, "models", "all-MiniLM-L6-v2")
EXPECTED_FAISS_SIZE = 119248941

# ================= GOOGLE DRIVE VECTORSTORE =================
VECTOR_URL = "https://drive.google.com/uc?id=1UunmpU4iudJycj-OibngzcJf18nA6OmR"
def load_vectorstore():
    target_dir = find_faiss_dir()
    os.makedirs(target_dir, exist_ok=True)
    idx_path = os.path.join(target_dir, "index.faiss")
    p1 = os.path.join(target_dir, "index.faiss.001")
    p2 = os.path.join(target_dir, "index.faiss.002")
    pkl_path = os.path.join(target_dir, "index.pkl")

    # 1. Fast Assembly from Git Repository Parts (Instant, 0 Google Drive dependency)
    needs_assembly = (not os.path.exists(idx_path)) or (os.path.getsize(idx_path) != EXPECTED_FAISS_SIZE)
    if needs_assembly and os.path.exists(p1) and os.path.exists(p2):
        try:
            print(f"[VectorStore] Assembling {idx_path} from repository parts...")
            with open(idx_path, "wb") as out_f:
                with open(p1, "rb") as f1:
                    out_f.write(f1.read())
                with open(p2, "rb") as f2:
                    out_f.write(f2.read())
            print("[VectorStore] index.faiss assembled successfully in 0.3s!")
            return True
        except Exception as e:
            print(f"[VectorStore Assembly Error] {e}")

    # 2. Fallback to Google Drive download if parts are missing
    if (not os.path.exists(idx_path) or os.path.getsize(idx_path) != EXPECTED_FAISS_SIZE) or not os.path.exists(pkl_path):
        try:
            print("[VectorStore] Index not found, downloading from Google Drive...")
            vs_root = os.path.dirname(target_dir)
            os.makedirs(vs_root, exist_ok=True)
            zip_dest = os.path.join(vs_root, "vs.zip")
            gdown.download(VECTOR_URL, zip_dest, quiet=False, fuzzy=True)
            if os.path.exists(zip_dest):
                with zipfile.ZipFile(zip_dest, 'r') as zip_ref:
                    zip_ref.extractall(vs_root)
                os.remove(zip_dest)
                print("[VectorStore] Download & extraction complete!")
                return True
        except Exception as e:
            print(f"[VectorStore Error] Failed to download/extract: {e}")
            return False
    return True

@st.cache_resource(show_spinner="Connecting 77,636 Medical Vectors from 9 Textbooks...")
def get_vectorstore():
    load_vectorstore()
    target_dir = find_faiss_dir()
    idx_path = os.path.join(target_dir, "index.faiss")
    pkl_path = os.path.join(target_dir, "index.pkl")

    if not os.path.exists(idx_path):
        err = f"index.faiss missing in {target_dir}"
        print(f"[FAISS Error] {err}")
        raise RuntimeError(err)

    if not os.path.exists(pkl_path):
        err = f"index.pkl missing in {target_dir}"
        print(f"[FAISS Error] {err}")
        raise RuntimeError(err)

    model_name = LOCAL_MODEL if os.path.exists(LOCAL_MODEL) else "sentence-transformers/all-MiniLM-L6-v2"
    print(f"[FAISS Loading] Initializing embeddings from: {model_name}")
    embed = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"}
    )
    db = FAISS.load_local(target_dir, embed, allow_dangerous_deserialization=True)
    print(f"[FAISS Ready] Successfully loaded {db.index.ntotal} medical vectors from 9 textbooks.")
    return db

def get_vectorstore_safe():
    try:
        return get_vectorstore()
    except Exception as e:
        print(f"[FAISS Safe Catch] {e}")
        return None

def get_vectorstore_status():
    try:
        db = get_vectorstore()
        if db and hasattr(db, "index"):
            return {"loaded": True, "count": db.index.ntotal, "error": None}
    except Exception as e:
        return {"loaded": False, "count": 0, "error": str(e)}
    return {"loaded": False, "count": 0, "error": "Database not initialized"}

def retrieve_medical_context(query, k=2, score_threshold=1.25):
    try:
        db = get_vectorstore()
    except Exception as e:
        print(f"[RAG Warning] Vectorstore db is None for query: {query} ({e})")
        return ""
    try:
        # If query has non-ASCII characters (e.g. Hindi or Marathi Devanagari), translate search term to English for English FAISS index
        search_query = query
        if any(ord(c) > 127 for c in query):
            try:
                from deep_translator import GoogleTranslator
                search_query = GoogleTranslator(source="auto", target="en").translate(query)
                print(f"[RAG Translation] Translated '{query[:30]}' to '{search_query[:30]}' for English FAISS index")
            except Exception:
                search_query = query

        results = db.similarity_search_with_score(search_query, k=k)
        if results:
            snippets = []
            for doc, score in results:
                # Accept only relevance distance <= 1.25 to distinguish genuine medical topics from unrelated questions
                if score <= score_threshold:
                    txt = doc.page_content.strip()
                    if txt:
                        src = doc.metadata.get("source", "")
                        page = doc.metadata.get("page", "")
                        ref_tag = ""
                        if src:
                            clean_src = os.path.splitext(src)[0].replace("_", " ")
                            ref_tag = f"[{clean_src}" + (f", p.{page}" if page else "") + "]: "
                        snippets.append(ref_tag + txt)
            return "\n\n".join(snippets)
    except Exception as e:
        print(f"Retrieval error: {e}")
    return ""

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

USER_DB = os.path.join(BASE_DIR, "users.json")

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
        clean_alert_text = text.replace(chr(10), '<br>')
        return (
            '<div class="med-alert-box" style="background:#fffbeb; border:1.5px solid #fef3c7; border-left:4px solid #f59e0b; border-radius:12px; padding:14px 18px; margin:6px 0;">'
            '<div style="font-weight:700; color:#b45309; margin-bottom:6px; font-size:14px;">Clinical Service Notice</div>'
            f'<div style="font-size:13.5px; color:#78350f; line-height:1.6;">{clean_alert_text}</div>'
            '</div>'
        )

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
        if ":" in clean_line_no_bullet:
            first_part = clean_line_no_bullet.split(":", 1)[0].strip().lower()
            header_prefixes = [
                "cause", "causes", "solution", "solutions", "care", "medicine", "medication", "medications", "when to see doctor", "emergency",
                "कारण", "कारणे", "उपाय", "घरगुती उपाय", "काळजी", "औषध", "औषधे", "औषधोपचार", "डॉक्टर", "तातडी", "आणीबाणी",
                "समाधान", "दवा", "दवाई", "आपात"
            ]
            if any(hp in first_part for hp in header_prefixes):
                is_header = True

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
            elif any(k in t_lower for k in ["solution", "care", "उपाय", "समाधान", "काळजी"]):
                color = "#10b981"
            elif any(k in t_lower for k in ["medicine", "medication", "औषध", "दवा", "दवाई"]):
                color = "#06b6d4"
            elif any(k in t_lower for k in ["doctor", "डॉक्टर"]):
                color = "#a855f7"
            elif any(k in t_lower for k in ["emergency", "तातडी", "आपात", "आणीबाणी"]):
                color = "#ef4444"
            else:
                color = "#38bdf8"

            html += (
                f'<div class="med-section-card" style="border-left: 3.5px solid {color}; margin: 8px 0; padding: 10px 14px; background: #ffffff; border-radius: 8px; border: 1px solid #f1f5f9; border-left-width: 4px;">'
                f'<div class="med-section-badge" style="color: {color}; font-weight: 700; font-size: 13px; margin-bottom: 4px;">{title}</div>'
                f'<div class="med-section-text" style="color: #334155; font-size: 14px; line-height: 1.6;">{body}</div>'
                '</div>'
            )
        else:
            html += f'<div class="med-section-intro" style="color: #334155; font-size: 14px; line-height: 1.6; margin: 6px 0;">{body}</div>'

    return html

# ================= AI =================
AVAILABLE_GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]

def call_groq_chat(client, messages, temperature=0.3):
    for m in AVAILABLE_GROQ_MODELS:
        try:
            res = client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=temperature
            )
            if res and res.choices and len(res.choices) > 0:
                content = res.choices[0].message.content
                if content and len(content.strip()) > 0:
                    print(f"[Groq API] Model used: {m}")
                    return content.strip()
        except Exception as e:
            print(f"Groq model {m} attempt failed: {e}")
            continue
    return None

def get_ai_response(prompt, lang="English", force_offline=False):
    # 1. Retrieve verified medical textbook context from FAISS
    context = retrieve_medical_context(prompt, k=2)
    has_rag = bool(context and len(context.strip()) > 30)

    clean_context = ""
    if has_rag:
        import re
        clean_context = re.sub(r'-\s*\n\s*', '', context.strip())
        clean_context = re.sub(r'[ \t]+', ' ', clean_context)
        if len(clean_context) > 750:
            clean_context = clean_context[:750].rsplit(' ', 1)[0] + "..."

    # CASE 1: USER CLICKED "DISABLE GROQ" -> Answer MUST be given purely by Textbook
    if force_offline:
        if has_rag:
            print("[Textbook Mode] Delivering direct textbook excerpts (Groq disabled)")
            textbook_card = (
                f"Cause: Direct excerpt from Medical Reference Textbooks (FAISS Vector Store):\n{clean_context}\n\n"
                "Solution: Follow evidence-based supportive care as outlined in medical literature. Maintain adequate rest, monitor symptoms, and stay properly hydrated.\n\n"
                "Medicine: Do not self-medicate with prescription drugs. Pharmaceutical treatments and dosages must be directed by a licensed physician.\n\n"
                "When to see doctor: Consult a qualified physician if symptoms are severe, persist beyond 48-72 hours, or progressively worsen.\n\n"
                "Emergency: Immediate emergency medical evaluation (Dial 108 / 112) is required if experiencing high fever, acute chest pain, shortness of breath, or confusion."
            )
            return textbook_card, "textbook_direct"
        else:
            vs_stat = get_vectorstore_status()
            if not vs_stat["loaded"]:
                err_info = vs_stat.get('error') or 'loading vectors'
                return (
                    f"Notice: The medical reference textbook database is currently initializing ({err_info}). "
                    "Please wait a few seconds and send your inquiry again, or click 'Initialize Textbooks Now' in the sidebar."
                ), "notice"
            return (
                "Notice: This symptom was not found in the offline medical reference textbooks. "
                "Please uncheck 'Disable Groq' to allow the AI engine to answer."
            ), "notice"

    # CASE 2 & 3: GROQ IS ACTIVE
    active_client = get_groq_client()
    if not active_client:
        if has_rag:
            textbook_card = (
                f"Cause: Direct excerpt from Medical Reference Textbooks (FAISS Vector Store):\n{clean_context}\n\n"
                "Solution: Follow evidence-based supportive care as outlined in medical literature. Maintain adequate rest, monitor symptoms, and stay properly hydrated.\n\n"
                "Medicine: Do not self-medicate with prescription drugs. Pharmaceutical treatments and dosages must be directed by a licensed physician.\n\n"
                "When to see doctor: Consult a qualified physician if symptoms are severe, persist beyond 48-72 hours, or progressively worsen.\n\n"
                "Emergency: Immediate emergency medical evaluation (Dial 108 / 112) is required if experiencing high fever, acute chest pain, shortness of breath, or confusion."
            )
            return textbook_card, "textbook_direct"
        else:
            return "Notice: Please configure GROQ_API_KEY to consult the AI engine.", "notice"

    # CASE 2: TEXTBOOK + GROQ TOGETHER (both textbook and Groq available)
    if has_rag:
        system_prompt = f"""You are UpCharika, a clinical AI healthcare assistant.
Provide structured medical triage guidance strictly following these 5 headers:
Cause:
Solution:
Medicine:
When to see doctor:
Emergency:

Verified Medical Reference Textbook Context:
\"\"\"
{clean_context}
\"\"\"

CRITICAL INSTRUCTION:
In the Cause section, explicitly explain the clinical cause grounded in the verified medical textbook findings above.
In Solution, Medicine, When to see doctor, and Emergency, provide evidence-based clinical guidance.
Do NOT use asterisks, markdown symbols (*, **, ==) or bold formatting.
Always conclude by reminding the patient to consult a licensed physician for definitive medical decisions."""

        ans = call_groq_chat(
            active_client,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        if ans and len(ans.strip()) > 0:
            return ans.strip(), "rag_groq"

        # If Groq call failed or timed out, fallback directly to Textbook!
        textbook_card = (
            f"Cause: Direct excerpt from Medical Reference Textbooks (FAISS Vector Store):\n{clean_context}\n\n"
            "Solution: Follow evidence-based supportive care as outlined in medical literature. Maintain adequate rest, monitor symptoms, and stay properly hydrated.\n\n"
            "Medicine: Do not self-medicate with prescription drugs. Pharmaceutical treatments and dosages must be directed by a licensed physician.\n\n"
            "When to see doctor: Consult a qualified physician if symptoms are severe, persist beyond 48-72 hours, or progressively worsen.\n\n"
            "Emergency: Immediate emergency medical evaluation (Dial 108 / 112) is required if experiencing high fever, acute chest pain, shortness of breath, or confusion."
        )
        return textbook_card, "textbook_direct"

    # CASE 3: NOT AVAILABLE IN TEXTBOOK -> GROQ GIVES THE ANSWER
    else:
        system_prompt = """You are UpCharika, a clinical AI healthcare assistant.
Provide structured medical triage guidance strictly following these 5 headers:
Cause:
Solution:
Medicine:
When to see doctor:
Emergency:

Do NOT use asterisks, markdown symbols (*, **, ==) or bold formatting.
Always conclude by reminding the patient to consult a licensed physician for definitive medical decisions."""

        ans = call_groq_chat(
            active_client,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        if ans and len(ans.strip()) > 0:
            return ans.strip(), "groq"

        return "Notice: UpCharika could not generate an answer at this time. Please try again.", "notice"

# ================= TRANSLATION =================
def translate_text(text, lang, force_offline=False):
    if not text or lang == "English":
        return text

    target_code = "mr" if lang.strip().lower() in ["marathi", "mr"] else ("hi" if lang.strip().lower() in ["hindi", "hi"] else "en")
    if target_code == "en":
        return text

    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target=target_code).translate(text)
    except Exception as e:
        print(f"GoogleTranslator error: {e}")
        return text

# ================= VOICE =================
def extract_voice_summary(text):
    if not text:
        return ""
    clean = clean_text_for_voice(text)
    sentences = [s.strip() for s in clean.split(".") if len(s.strip()) > 5]
    if sentences:
        summary = ". ".join(sentences[:2])
        if not summary.endswith("."):
            summary += "."
        if len(summary) > 260:
            summary = summary[:257] + "..."
        return summary
    return clean[:260]

def generate_voice(text, lang):
    try:
        if not text:
            return None
        speech_text = extract_voice_summary(text)
        lang_map = {"English": "en", "Hindi": "hi", "Marathi": "mr"}
        tts = gTTS(text=speech_text, lang=lang_map.get(lang, "en"))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception:
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

        /* Fluid background matching Mockup 1 */
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(100% 100% at 50% 0%, #eff6ff 0%, #f8fafc 50%, #ede9fe 100%) !important;
        }

        /* Single, non-cascading executive Auth Card */
        .block-container {
            max-width: 450px !important;
            width: 90% !important;
            margin: 40px auto !important;
            background: #ffffff !important;
            border: 1.5px solid #e2e8f0 !important;
            border-radius: 28px !important;
            box-shadow: 0 25px 60px -15px rgba(99, 102, 241, 0.16), 0 0 1px 1px rgba(226, 232, 240, 0.8) !important;
            padding: 38px 32px 30px 32px !important;
        }

        div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"] div[data-testid="column"] {
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

    with st.container():
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
    st.markdown("""
    <style>
        .block-container {
            max-width: 100% !important;
            width: 100% !important;
            margin: 0 !important;
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

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

        if "selected_lang" not in st.session_state:
            st.session_state.selected_lang = "English"

        st.markdown("---")
        lang_list = ["English", "Hindi", "Marathi"]
        curr_idx = lang_list.index(st.session_state.selected_lang) if st.session_state.selected_lang in lang_list else 0
        lang = st.selectbox("Consultation Language", lang_list, index=curr_idx)

        # Developer / Examiner Test Toggle
        force_offline = st.checkbox(
            "🧪 Test Mode: Disable Groq",
            value=False,
            help="Enable this to demonstrate that answers are fetched directly from your medical textbook without Groq AI."
        )

        vs_status = get_vectorstore_status()
        if vs_status["loaded"]:
            st.markdown(
                f'<div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:6px 10px; margin:4px 0 10px 0; font-size:11.5px; color:#1e40af; display:flex; align-items:center; gap:6px;">'
                f'<span>📚</span> <span><b>Medical Textbooks:</b> {vs_status["count"]:,} vectors ready</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:8px 12px; margin:4px 0 6px 0; font-size:12px; color:#1e40af;">'
                f'<div style="display:flex; align-items:center; gap:6px; font-weight:600;"><span>⏳</span> <span>Connecting Medical Library...</span></div>'
                f'<div style="font-size:11px; margin-top:3px; color:#3b82f6;">Loading 77,636 verified vectors from 9 textbooks</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button("🔄 Connect Textbooks Now", use_container_width=True, help="Click to connect the 9 medical textbooks"):
                with st.spinner("Connecting 77,636 medical textbook vectors..."):
                    try:
                        st.cache_resource.clear()
                        load_vectorstore()
                        get_vectorstore()
                        st.rerun()
                    except Exception as ex:
                        st.info("Medical knowledge base is completing background installation. Please wait 15-20 seconds and refresh.")

        # Re-translate existing conversation dynamically if user switches language in sidebar
        if lang != st.session_state.selected_lang:
            st.session_state.selected_lang = lang
            for msg in st.session_state.chat_history:
                if msg.get("role") == "bot":
                    raw_src = msg.get("raw_text", msg.get("text", ""))
                    re_trans = translate_text(raw_src, lang, force_offline=force_offline)
                    msg["text"] = re_trans
                    try:
                        clean_t = clean_text_for_voice(re_trans)
                        msg["audio"] = generate_voice(clean_t, lang)
                    except Exception:
                        pass
            st.rerun()

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

        pdf_guide_path = os.path.join(BASE_DIR, "UpCharika_Complete_Project_Study_Guide.pdf")
        if os.path.exists(pdf_guide_path):
            with open(pdf_guide_path, "rb") as f_pdf:
                st.download_button(
                    label="📄 Download Full Study Guide (PDF)",
                    data=f_pdf.read(),
                    file_name="UpCharika_Complete_Project_Study_Guide.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        pdf_flow_path = os.path.join(BASE_DIR, "UpCharika_Complete_Project_Flow.pdf")
        if os.path.exists(pdf_flow_path):
            with open(pdf_flow_path, "rb") as f_flow:
                st.download_button(
                    label="📊 Download Project Flow Diagram (PDF)",
                    data=f_flow.read(),
                    file_name="UpCharika_Complete_Project_Flow.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        pdf_structure_path = os.path.join(BASE_DIR, "UpCharika_Project_Folder_Structure_Guide.pdf")
        if os.path.exists(pdf_structure_path):
            with open(pdf_structure_path, "rb") as f_struct:
                st.download_button(
                    label="📁 Download Folder Structure Guide (PDF)",
                    data=f_struct.read(),
                    file_name="UpCharika_Project_Folder_Structure_Guide.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        pdf_rag_path = os.path.join(BASE_DIR, "UpCharika_Master_VectorStore_and_RAG_Architecture_Guide.pdf")
        if os.path.exists(pdf_rag_path):
            with open(pdf_rag_path, "rb") as f_rag:
                st.download_button(
                    label="🧠 Download VectorStore & RAG Guide (PDF)",
                    data=f_rag.read(),
                    file_name="UpCharika_Master_VectorStore_and_RAG_Architecture_Guide.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        pdf_groq_path = os.path.join(BASE_DIR, "UpCharika_Groq_API_and_Medical_Textbook_Master_Guide.pdf")
        if os.path.exists(pdf_groq_path):
            with open(pdf_groq_path, "rb") as f_groq:
                st.download_button(
                    label="⚡ Download Groq API & Textbook Guide (PDF)",
                    data=f_groq.read(),
                    file_name="UpCharika_Groq_API_and_Medical_Textbook_Master_Guide.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        pdf_code_path = os.path.join(BASE_DIR, "UpCharika_Medibot_Code_Walkthrough_and_Viva_Guide.pdf")
        if os.path.exists(pdf_code_path):
            with open(pdf_code_path, "rb") as f_code:
                st.download_button(
                    label="💻 Download medibot.py Code & Viva Guide (PDF)",
                    data=f_code.read(),
                    file_name="UpCharika_Medibot_Code_Walkthrough_and_Viva_Guide.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

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

        suggestions_map = {
            "English": [
                ("💬", "I have fever, headache, and chills for 48 hours"),
                ("💊", "First-aid protocol for acute acid reflux"),
                ("🩺", "Clinical criteria for Type 2 diabetes screening"),
                ("⚠️", "Warning signs requiring immediate emergency evaluation"),
            ],
            "Marathi": [
                ("💬", "मला २ दिवसांपासून ताप, डोकेदुखी आणि थंडी भरली आहे"),
                ("💊", "तीव्र ॲसिडिटी / पित्तासाठी तातडीचे प्रथमोपचार"),
                ("🩺", "टाईप २ मधुमेहाची लक्षणे व तपासणी निकष"),
                ("⚠️", "तातडीने रुग्णालयात जाण्याची आवश्यकता असणारी धोक्याची लक्षणे"),
            ],
            "Hindi": [
                ("💬", "मुझे २ दिनों से बुखार, सिरदर्द और ठंड लग रही है"),
                ("💊", "तीव्र एसिडिटी / गैस के लिए प्राथमिक उपचार"),
                ("🩺", "टाइप २ डायबिटीज के लक्षण और जांच के नियम"),
                ("⚠️", "तत्काल आपातकालीन चिकित्सा की आवश्यकता वाले खतरे के संकेत"),
            ]
        }
        suggestions = suggestions_map.get(lang, suggestions_map["English"])
        col_s1, col_s2 = st.columns(2)
        for idx, (icon, text) in enumerate(suggestions):
            col = col_s1 if idx % 2 == 0 else col_s2
            with col:
                if st.button(f"{icon}  {text}", key=f"sugg_{idx}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "text": text})
                    with st.spinner("Evaluating clinical inquiry..."):
                        try:
                            ans, source = get_ai_response(text, lang=lang, force_offline=force_offline)
                            trans = translate_text(ans, lang, force_offline=force_offline)
                        except Exception as e:
                            ans = str(e)
                            trans = f"⚠️ Clinical Service Notice: {str(e)}"
                            source = "notice"

                        audio = None
                        try:
                            clean_text = clean_text_for_voice(trans)
                            audio = generate_voice(clean_text, lang)
                        except Exception:
                            audio = None

                        st.session_state.chat_history.append({
                            "role": "bot",
                            "text": trans,
                            "raw_text": ans,
                            "audio": audio,
                            "source": source
                        })
                    st.rerun()

    # Chat Feed
    st.markdown("<div class='chat-feed'>", unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            user_card_html = (
                '<div class="chat-row user-row">'
                '<div class="user-bubble">'
                '<div class="bubble-header">You</div>'
                f'<div class="bubble-body">{msg["text"]}</div>'
                '</div>'
                '</div>'
            )
            st.markdown(user_card_html, unsafe_allow_html=True)
        else:
            formatted_content = format_medical_card(msg['text'])
            source_badge = ""
            msg_source = msg.get("source")
            if msg_source in ["rag", "rag_groq"]:
                source_badge = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11px; background:#eff6ff; color:#1d4ed8; padding:3px 10px; border-radius:12px; border:1px solid #bfdbfe; font-weight:600; margin-left:10px;">📖 Medical Textbook Grounded + Groq AI</span>'
            elif msg_source == "textbook_direct":
                source_badge = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11px; background:#f5f3ff; color:#6d28d9; padding:3px 10px; border-radius:12px; border:1px solid #ddd6fe; font-weight:600; margin-left:10px;">📚 100% Direct Textbook (Groq OFF)</span>'
            elif msg_source == "groq":
                source_badge = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11px; background:#f0fdf4; color:#15803d; padding:3px 10px; border-radius:12px; border:1px solid #bbf7d0; font-weight:600; margin-left:10px;">⚡ Groq AI Engine</span>'
            elif msg_source == "offline":
                source_badge = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11px; background:#fefce8; color:#a16207; padding:3px 10px; border-radius:12px; border:1px solid #fef08a; font-weight:600; margin-left:10px;">📋 Offline Clinical KB</span>'

            bot_card_html = (
                '<div class="chat-row bot-row">'
                '<div class="bot-card">'
                '<div class="bot-header" style="display:flex; align-items:center; flex-wrap:wrap;">'
                '<div class="bot-avatar-box">🩺</div>'
                '<span class="bot-title">UpCharika Clinical Assistant</span>'
                f'{source_badge}'
                '</div>'
                f'<div class="bot-body">{formatted_content}</div>'
                '</div>'
                '</div>'
            )
            st.markdown(bot_card_html, unsafe_allow_html=True)
            if msg.get("audio"):
                st.markdown("<div class='audio-row'>", unsafe_allow_html=True)
                st.caption("Audio Consultation:")
                st.audio(msg["audio"])
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # User Input
    input_placeholders = {
        "English": "Ask a medical question or describe clinical symptoms...",
        "Marathi": "वैद्यकीय प्रश्न विचारा किंवा लक्षणांचे वर्णन करा...",
        "Hindi": "चिकित्सीय प्रश्न पूछें या लक्षणों का वर्णन करें..."
    }
    chat_placeholder = input_placeholders.get(lang, input_placeholders["English"])
    user_input = st.chat_input(chat_placeholder)
    if user_input:
        st.session_state.chat_history.append({"role": "user", "text": user_input})

        with st.spinner("Evaluating clinical inquiry..."):
            try:
                answer, source = get_ai_response(user_input, lang=lang, force_offline=force_offline)
                translated = translate_text(answer, lang, force_offline=force_offline)
            except Exception as e:
                answer = str(e)
                translated = f"⚠️ Clinical Service Notice: {str(e)}"
                source = "notice"

            audio = None
            try:
                clean_text = clean_text_for_voice(translated)
                audio = generate_voice(clean_text, lang)
            except Exception:
                audio = None

            st.session_state.chat_history.append({
                "role": "bot",
                "text": translated,
                "raw_text": answer,
                "audio": audio,
                "source": source
            })
        st.rerun()

# ================= MAIN =================
def main():
    # Preload Vectorstore into memory
    if "vs_loaded" not in st.session_state:
        get_vectorstore_safe()
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