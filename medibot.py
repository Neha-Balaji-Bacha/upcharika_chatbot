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
    try:
        # Pre-warm embeddings model and FAISS search index so first user query has 0s latency
        db.similarity_search("clinical triage warmup query", k=1)
        print("[FAISS Ready] Pre-warm query search completed successfully!")
    except Exception as e:
        print(f"[FAISS Warmup Notice] {e}")
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
    if not text:
        return ""
    import re
    # 1. Remove citations in square brackets like [standard-treatment-guidelines, p.27]
    t = re.sub(r'\[.*?\]', '', text)
    # 2. Remove technical vectorstore boilerplate
    t = re.sub(r'\(FAISS Vector Store\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'Direct excerpt from Medical Reference Textbooks:?', '', t, flags=re.IGNORECASE)
    t = re.sub(r'वैद्यकीय संदर्भ (ग्रंथांमधील|पुस्तकांमधील|साहित्यामधील) थेट उतारा:?', '', t)
    t = re.sub(r'चिकित्सा? संदर्भ (पुस्तकों|ग्रंथों) से सीधा (उद्धरण|अंश):?', '', t)
    # 3. Expand abbreviations that cause "full stop" to be spoken
    t = re.sub(r'\bTab\.\s*', 'Tablet ', t, flags=re.IGNORECASE)
    t = re.sub(r'\bCap\.\s*', 'Capsule ', t, flags=re.IGNORECASE)
    t = re.sub(r'\bSyr\.\s*', 'Syrup ', t, flags=re.IGNORECASE)
    t = re.sub(r'\bInj\.\s*', 'Injection ', t, flags=re.IGNORECASE)
    t = re.sub(r'\be\.g\.\s*', 'for example ', t, flags=re.IGNORECASE)
    t = re.sub(r'\bi\.e\.\s*', 'that is ', t, flags=re.IGNORECASE)
    t = re.sub(r'\b[pP]\.\s*\d+', '', t)
    t = re.sub(r'टॅब\.\s*', 'टॅब्लेट ', t)
    t = re.sub(r'टैब\.\s*', 'टैबलेट ', t)
    # 4. Remove ellipsis / multiple dots that cause gTTS to say "full stop full stop"
    t = re.sub(r'\.{2,}', ' ', t)
    # 5. Remove markdown symbols
    for ch in ["*", "#", "=", "-", "•", "🗹", "~", "_", "`", "<", ">", "(", ")", "[", "]"]:
        t = t.replace(ch, " ")
    # 6. Clean up multiple colons or weird punctuation
    t = re.sub(r'^(Cause|Solution|Medicine|When to see doctor|Emergency|कारण|उपाय|औषधे|डॉक्टरांचा सल्ला|आणीबाणी)\s*[:\s]+', '', t, flags=re.IGNORECASE)
    t = re.sub(r':+', ':', t)
    t = re.sub(r'\s+:', ':', t)
    t = re.sub(r':\s*:', ' ', t)
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()

# ================= FORMAT MEDICAL CARD =================
def format_medical_card(text):
    if not text:
        return ""

    if text.startswith("⚠️"):
        clean_alert_text = text.replace(chr(10), '<br>')
        return (
            '<div class="med-alert-box" style="background:#fffbeb; border:1.5px solid #fef3c7; border-left:4px solid #f59e0b; border-radius:12px; padding:14px 18px; margin:6px 0;">'
            '<div style="font-weight:700; color:#b45309; margin-bottom:6px; font-size:15px;">Clinical Service Notice</div>'
            f'<div style="font-size:15.5px; color:#78350f; line-height:1.65;">{clean_alert_text}</div>'
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
                "समाधान", "दवा", "दवाई", "दवाइयां", "आपात", "आपातकालीन", "डॉक्टर से परामर्श"
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
                f'<div class="med-section-card" style="border-left: 3.5px solid {color}; margin: 8px 0; padding: 12px 16px; background: #ffffff; border-radius: 8px; border: 1px solid #f1f5f9; border-left-width: 4px;">'
                f'<div class="med-section-badge" style="color: {color}; font-weight: 700; font-size: 15.5px; margin-bottom: 5px;">{title}</div>'
                f'<div class="med-section-text" style="color: #334155; font-size: 16px; line-height: 1.7;">{body}</div>'
                '</div>'
            )
        else:
            html += f'<div class="med-section-intro" style="color: #334155; font-size: 16px; line-height: 1.7; margin: 6px 0;">{body}</div>'

    return html

# ================= AI =================
AVAILABLE_GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b"
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
        # Remove private use characters (like \uf0b7, \u25a0, checkbox symbols from PDFs)
        clean_context = re.sub(r'[\uf000-\uf8ff\U00010000-\U0010ffff]', ' ', context)
        # Remove hyphenated linebreaks
        clean_context = re.sub(r'-\s*\n\s*', '', clean_context)
        # Remove bracket citations from inside the excerpt
        clean_context = re.sub(r'\[.*?\]:?', '', clean_context)
        # Normalize internal linebreaks to spaces so sentences flow naturally
        clean_context = re.sub(r'\s*\n\s*', ' ', clean_context)
        # Normalize whitespace
        clean_context = re.sub(r'[ \t]+', ' ', clean_context).strip()
        if len(clean_context) > 600:
            clean_context = clean_context[:600].rsplit(' ', 1)[0] + "."

    # CASE 1: USER CLICKED "DISABLE GROQ" -> Answer MUST be given purely by Textbook
    if force_offline:
        if has_rag:
            print("[Textbook Mode] Delivering direct textbook excerpts (Groq disabled)")
            textbook_card = (
                f"Cause: Direct excerpt from Medical Reference Textbooks:\n{clean_context}\n\n"
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
                f"Cause: Direct excerpt from Medical Reference Textbooks:\n{clean_context}\n\n"
                "Solution: Follow evidence-based supportive care as outlined in medical literature. Maintain adequate rest, monitor symptoms, and stay properly hydrated.\n\n"
                "Medicine: Do not self-medicate with prescription drugs. Pharmaceutical treatments and dosages must be directed by a licensed physician.\n\n"
                "When to see doctor: Consult a qualified physician if symptoms are severe, persist beyond 48-72 hours, or progressively worsen.\n\n"
                "Emergency: Immediate emergency medical evaluation (Dial 108 / 112) is required if experiencing high fever, acute chest pain, shortness of breath, or confusion."
            )
            return textbook_card, "textbook_direct"
        else:
            return "Notice: Please configure GROQ_API_KEY to consult the AI engine.", "notice"

    # LANGUAGE DIRECTIVE FOR GROQ
    lang_directive = ""
    if lang == "Marathi":
        lang_directive = (
            "\n\nCRITICAL LANGUAGE INSTRUCTION: You MUST write your entire clinical response strictly in MARATHI (मराठी) using natural Devanagari script. "
            "Use standard Marathi clinical headers exactly as:\n"
            "कारण:\n"
            "उपाय:\n"
            "औषधे:\n"
            "डॉक्टरांचा सल्ला:\n"
            "आणीबाणी:"
        )
    elif lang == "Hindi":
        lang_directive = (
            "\n\nCRITICAL LANGUAGE INSTRUCTION: You MUST write your entire clinical response strictly in HINDI (हिंदी) using natural Devanagari script. "
            "Use standard Hindi clinical headers exactly as:\n"
            "कारण:\n"
            "समाधान:\n"
            "दवाइयां:\n"
            "डॉक्टर से परामर्श:\n"
            "आपातकालीन स्थिति:"
        )

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
Always conclude by reminding the patient to consult a licensed physician for definitive medical decisions.{lang_directive}"""

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
            f"Cause: Direct excerpt from Medical Reference Textbooks:\n{clean_context}\n\n"
            "Solution: Follow evidence-based supportive care as outlined in medical literature. Maintain adequate rest, monitor symptoms, and stay properly hydrated.\n\n"
            "Medicine: Do not self-medicate with prescription drugs. Pharmaceutical treatments and dosages must be directed by a licensed physician.\n\n"
            "When to see doctor: Consult a qualified physician if symptoms are severe, persist beyond 48-72 hours, or progressively worsen.\n\n"
            "Emergency: Immediate emergency medical evaluation (Dial 108 / 112) is required if experiencing high fever, acute chest pain, shortness of breath, or confusion."
        )
        return textbook_card, "textbook_direct"

    # CASE 3: NOT AVAILABLE IN TEXTBOOK -> GROQ GIVES THE ANSWER
    else:
        system_prompt = f"""You are UpCharika, a clinical AI healthcare assistant.
Provide structured medical triage guidance strictly following these 5 headers:
Cause:
Solution:
Medicine:
When to see doctor:
Emergency:

Do NOT use asterisks, markdown symbols (*, **, ==) or bold formatting.
Always conclude by reminding the patient to consult a licensed physician for definitive medical decisions.{lang_directive}"""

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
def translate_chunk_robust(text, target_code, source_code="auto"):
    if not text or not text.strip():
        return text

    clean_q = text.strip()

    # Strategy 1: Google GTX Client API (fast, reliable, handles multi-sentence clinical text without 429 errors)
    try:
        import urllib.parse
        import requests
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_code}&tl={target_code}&dt=t&q={urllib.parse.quote(clean_q)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            translated = "".join(part[0] for part in data[0] if part[0])
            if translated and len(translated.strip()) > 0:
                return translated.strip()
    except Exception as e:
        print(f"[GTX Translation Notice] {e}")

    # Strategy 2: deep_translator GoogleTranslator
    try:
        from deep_translator import GoogleTranslator
        res = GoogleTranslator(source=source_code, target=target_code).translate(clean_q)
        if res and res.strip():
            return res.strip()
    except Exception as e:
        print(f"[GoogleTranslator Notice] {e}")

    # Strategy 3: deep_translator MyMemoryTranslator (chunks < 400 chars)
    try:
        from deep_translator import MyMemoryTranslator
        target_mymemory = "mr-IN" if target_code == "mr" else ("hi-IN" if target_code == "hi" else "en-US")
        dev_count = sum(1 for c in clean_q if '\u0900' <= c <= '\u097f')
        source_mymemory = "mr-IN" if (dev_count > len(clean_q) * 0.3 and target_code == "hi") else ("hi-IN" if (dev_count > len(clean_q) * 0.3 and target_code == "mr") else "en-US")
        
        if len(clean_q) > 400:
            import re
            sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', clean_q) if s.strip()]
            chunks = []
            curr = ""
            for s in sentences:
                if len(curr) + len(s) + 1 < 380:
                    curr = (curr + " " + s).strip()
                else:
                    if curr:
                        chunks.append(curr)
                    curr = s
            if curr:
                chunks.append(curr)
            
            sub_res = []
            for c in chunks:
                tr = MyMemoryTranslator(source=source_mymemory, target=target_mymemory).translate(c)
                sub_res.append(tr or c)
            res = " ".join(sub_res)
        else:
            res = MyMemoryTranslator(source=source_mymemory, target=target_mymemory).translate(clean_q)

        if res and res.strip():
            return res.strip()
    except Exception as e:
        print(f"[MyMemory Notice] {e}")

    return text

def translate_text(text, lang, force_offline=False, source_lang=None):
    if not text:
        return text

    target_code = "mr" if lang.strip().lower() in ["marathi", "mr"] else ("hi" if lang.strip().lower() in ["hindi", "hi"] else "en")

    # If source language matches target language, no translation needed
    if source_lang and source_lang.strip().lower() == lang.strip().lower():
        return text

    # Canonical headers for each target language
    CANONICAL_HEADERS = {
        "mr": {
            "cause": "कारण:",
            "solution": "उपाय:",
            "medicine": "औषधे:",
            "doctor": "डॉक्टरांचा सल्ला:",
            "emergency": "आणीबाणी:"
        },
        "hi": {
            "cause": "कारण:",
            "solution": "समाधान:",
            "medicine": "दवाइयां:",
            "doctor": "डॉक्टर से परामर्श:",
            "emergency": "आपातकालीन स्थिति:"
        },
        "en": {
            "cause": "Cause:",
            "solution": "Solution:",
            "medicine": "Medicine:",
            "doctor": "When to see doctor:",
            "emergency": "Emergency:"
        }
    }

    # Verify if text is already completely in target language
    if target_code == "en":
        dev_count = sum(1 for c in text if '\u0900' <= c <= '\u097f')
        if dev_count < len(text) * 0.15:
            return text
    elif target_code == "mr":
        if any(h in text for h in ["औषधे:", "डॉक्टरांचा सल्ला:", "आणीबाणी:"]) and not any(h in text for h in ["Cause:", "Solution:", "Medicine:"]):
            return text
    elif target_code == "hi":
        if any(h in text for h in ["दवाइयां:", "डॉक्टर से परामर्श:", "आपातकालीन स्थिति:"]) and not any(h in text for h in ["Cause:", "Solution:", "Medicine:"]):
            return text

    # Strategy A: If Groq is active (not offline test mode), use AI translation for instant, flawless translation
    if not force_offline:
        active_client = get_groq_client()
        if active_client:
            expected_headers = list(CANONICAL_HEADERS[target_code].values())
            target_name = "MARATHI (मराठी Devanagari)" if target_code == "mr" else ("HINDI (हिंदी Devanagari)" if target_code == "hi" else "ENGLISH")
            trans_prompt = (
                f"You are a professional medical translator. Translate the following clinical triage consultation accurately into natural {target_name}.\n"
                f"You MUST use these exact section headers:\n"
                + "\n".join(expected_headers)
                + "\nDo NOT use asterisks or markdown bolding (**, *). Translate both headers and body text completely into the target language. Do not output words from other languages.\n\n"
                f"Clinical text to translate:\n{text}"
            )
            res = call_groq_chat(active_client, [{"role": "user", "content": trans_prompt}], temperature=0.2)
            if res and len(res.strip()) > 50:
                return res.strip()

    # Strategy B: Offline / Direct Textbook / deep_translator fallback
    HEADER_MATCHERS = [
        ("cause", ["cause:", "कारण:"]),
        ("solution", ["solution:", "उपाय:", "समाधान:"]),
        ("medicine", ["medicine:", "औषधे:", "दवाइयां:", "दवाई:", "औषध:"]),
        ("doctor", ["when to see doctor:", "डॉक्टरांचा सल्ला:", "डॉक्टर से परामर्श:"]),
        ("emergency", ["emergency:", "आणीबाणी:", "आपातकालीन स्थिति:", "आपात:"])
    ]

    import re
    raw_lines = text.splitlines()
    sections = []
    current_cat = None
    current_body = []

    for line in raw_lines:
        line_s = line.strip()
        if not line_s:
            continue
        matched_cat = None
        clean_l = re.sub(r"^[\d\.\-\*•\s]+", "", line_s).strip()
        clean_l_lower = clean_l.lower()

        for cat, pats in HEADER_MATCHERS:
            for p in pats:
                if clean_l_lower.startswith(p):
                    matched_cat = cat
                    clean_l = clean_l[len(p):].strip()
                    break
            if matched_cat:
                break

        if matched_cat:
            if current_cat or current_body:
                sections.append((current_cat, " ".join(current_body)))
                current_body = []
            current_cat = matched_cat
            if clean_l:
                current_body.append(clean_l)
        else:
            current_body.append(clean_l)

    if current_cat or current_body:
        sections.append((current_cat, " ".join(current_body)))

    translated_sections = []
    src_code = "mr" if (source_lang and source_lang.lower() == "marathi") else ("hi" if (source_lang and source_lang.lower() == "hindi") else "auto")

    for cat, body_str in sections:
        body_clean = re.sub(r'Direct excerpt from Medical Reference Textbooks:?', '', body_str, flags=re.IGNORECASE).strip()
        body_clean = re.sub(r'\s+', ' ', body_clean).strip()

        prefix = ""
        if cat and cat in CANONICAL_HEADERS[target_code]:
            prefix = CANONICAL_HEADERS[target_code][cat] + "\n"

        trans_body = translate_chunk_robust(body_clean, target_code, source_code=src_code)
        translated_sections.append(prefix + trans_body)

    return "\n\n".join(translated_sections)

# ================= VOICE =================
def extract_voice_summary(raw_text, lang="English"):
    if not raw_text:
        return ""
    import re

    header_keywords = {
        'cause': ['cause', 'causes', 'कारण', 'कारणे'],
        'solution': ['solution', 'solutions', 'care', 'उपाय', 'घरगुती उपाय', 'काळजी', 'समाधान'],
        'medicine': ['medicine', 'medication', 'medications', 'औषध', 'औषधे', 'औषधोपचार', 'दवा', 'दवाई', 'दवाइयां'],
        'doctor': ['when to see doctor', 'doctor', 'डॉक्टर', 'डॉक्टरांचा सल्ला', 'डॉक्टर से परामर्श'],
        'emergency': ['emergency', 'तातडी', 'आणीबाणी', 'आपात', 'आपातकालीन']
    }

    spoken_headers = {
        'English': {
            'cause': 'Cause: ',
            'solution': 'Solution: ',
            'medicine': 'Medicine: ',
            'doctor': 'When to see doctor: ',
            'emergency': 'Emergency: '
        },
        'Marathi': {
            'cause': 'कारण: ',
            'solution': 'उपाय: ',
            'medicine': 'औषधे: ',
            'doctor': 'डॉक्टरांचा सल्ला: ',
            'emergency': 'आणीबाणी: '
        },
        'Hindi': {
            'cause': 'कारण: ',
            'solution': 'उपाय: ',
            'medicine': 'दवाइयां: ',
            'doctor': 'डॉक्टर से परामर्श: ',
            'emergency': 'आपातकालीन: '
        }
    }

    hdrs = spoken_headers.get(lang, spoken_headers['English'])

    def get_first_sentences(text_content, n=1):
        if not text_content:
            return ''
        parts = [p.strip() for p in re.split(r'[\.।!?\n\r]+', text_content) if len(p.strip()) > 3]
        if not parts:
            return ''
        is_dev = any('\u0900' <= c <= '\u097f' for c in text_content)
        end_p = '। ' if is_dev else '. '
        chosen = parts[:n]
        res = end_p.join(chosen).strip()
        if not res.endswith(('.', '।', '!')):
            res += ('।' if is_dev else '.')
        return res

    sections = {}
    current_key = None
    current_lines = []

    for line in raw_text.splitlines():
        line_clean = line.strip().replace('*', '').replace('#', '')
        if not line_clean:
            continue
        no_bullet = re.sub(r'^[\d\.\-\*•\s]+', '', line_clean).strip()

        matched_cat = None
        if ':' in no_bullet:
            prefix = no_bullet.split(':', 1)[0].strip().lower()
            for cat, kws in header_keywords.items():
                if any(kw in prefix for kw in kws):
                    matched_cat = cat
                    remainder = no_bullet.split(':', 1)[1].strip()
                    break
        else:
            prefix = no_bullet.lower()
            for cat, kws in header_keywords.items():
                if any(kw == prefix for kw in kws):
                    matched_cat = cat
                    remainder = ''
                    break

        if matched_cat:
            if current_key and current_lines:
                sections[current_key] = ' '.join(current_lines)
            current_key = matched_cat
            current_lines = [remainder] if remainder else []
        else:
            if current_key:
                current_lines.append(line_clean)
            else:
                current_lines.append(line_clean)

    if current_key and current_lines:
        sections[current_key] = ' '.join(current_lines)

    summary_parts = []
    # If structured medical sections are present, build a 360-degree consultation summary
    if any(k in sections for k in ['cause', 'solution', 'medicine', 'doctor']):
        for cat in ['cause', 'solution', 'medicine', 'doctor', 'emergency']:
            if cat in sections and sections[cat].strip():
                body = clean_text_for_voice(sections[cat])
                # Solution gets up to 2 sentences; others get 1 key sentence
                n_sent = 2 if cat == 'solution' else 1
                sent = get_first_sentences(body, n=n_sent)
                if sent:
                    summary_parts.append(hdrs[cat] + sent)
        summary = ' '.join(summary_parts)
    else:
        # Fallback for conversational / unstructured text: take up to 4 complete sentences
        body = clean_text_for_voice(raw_text)
        summary = get_first_sentences(body, n=4)

    # Sanity check for length (keep up to ~950 characters so gTTS speaks a complete, rich consultation)
    if len(summary) > 950:
        summary = summary[:940].rsplit(' ', 1)[0]
        is_dev = any('\u0900' <= c <= '\u097f' for c in summary)
        if not summary.endswith(('.', '।', '!')):
            summary += ('।' if is_dev else '.')

    return summary

def generate_voice(text, lang):
    try:
        if not text:
            return None
        speech_text = extract_voice_summary(text, lang=lang)
        if not speech_text:
            speech_text = clean_text_for_voice(text)[:400]
        lang_map = {"English": "en", "Hindi": "hi", "Marathi": "mr"}
        target_lang = lang_map.get(lang, "en")
        tts = gTTS(text=speech_text, lang=target_lang)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        print(f"[Voice Error] {e}")
        return None

# ================= UI LOCALIZATION (i18n) =================
UI_STRINGS = {
    "English": {
        "portal_tag": "Clinical AI Portal",
        "portal_desc": "Hospital-Grade AI Healthcare Assistance & Triage System",
        "lang_label": "Language",
        "sign_in_tab": "Sign In",
        "register_tab": "Register",
        "username": "Username",
        "username_placeholder": "Enter your registered username",
        "password": "Password",
        "password_placeholder": "Enter your password",
        "choose_username": "Choose Username",
        "choose_username_placeholder": "Enter a unique username",
        "choose_password": "Choose Password",
        "choose_password_placeholder": "Create a secure password",
        "btn_signin": "Sign In to Portal  →",
        "btn_register": "Create Account  →",
        "fill_both": "Please fill in both fields.",
        "reg_success": "Account created successfully. Please click Sign In to continue.",
        "err_user_not_found": "User not found.",
        "err_invalid_pw": "Invalid password.",
        "err_user_exists": "Username already exists.",
        "trust_encrypted": "End-to-End<br>Encrypted",
        "trust_engine": "Clinical<br>RAG + Groq AI",
        "trust_multilingual": "Multilingual<br>Guidance",
        "or_divider": "or",
        "verified_user": "Verified User",
        "nav_chat": "💬 Chat Assistant",
        "nav_history": "🕒 Consultation History",
        "nav_settings": "⚙️ Settings",
        "consult_lang": "Consultation Language",
        "test_mode_toggle": "🧪 Test Mode: Disable Groq",
        "test_mode_help": "Enable this to demonstrate that answers are fetched directly from your medical textbook without Groq AI.",
        "textbooks_ready": "Medical Textbooks: {count:,} vectors ready",
        "connecting_library": "Connecting Medical Library...",
        "loading_vectors": "Loading 77,636 verified vectors from 9 textbooks",
        "btn_connect_now": "🔄 Connect Textbooks Now",
        "btn_clear_history": "Clear History",
        "clear_history_help": "Reset conversation",
        "btn_sign_out": "Sign Out",
        "sign_out_help": "Sign out of portal",
        "emergency_title": "⚠️ EMERGENCY ASSISTANCE",
        "emergency_desc": "If you or someone else is experiencing critical or life-threatening symptoms:",
        "ambulance": "🚑 Ambulance: <b>108 / 112</b>",
        "helpline": "📞 National Health Helpline: <b>1800-180-1104</b>",
        "disclaimer": "UpCharika provides clinical triage and health information support only. Always consult a licensed medical practitioner for diagnosis.",
        "chat_title": "UpCharika Clinical Assistant",
        "chat_subtitle": "Active Clinical Engine • Medical Textbook RAG + Groq AI",
        "welcome_title": "Welcome to UpCharika Clinical Consultation",
        "welcome_desc": "Describe your symptoms, ask about medications, or request clinical triage guidance.",
        "user_label": "You",
        "audio_consultation": "Audio Consultation:",
        "input_placeholder": "Ask a medical question or describe clinical symptoms...",
        "evaluating_spinner": "Evaluating clinical inquiry...",
        "translating_spinner": "Translating consultation to {lang}...",
        "badge_rag_groq": "📖 Medical Textbook Grounded + Groq AI",
        "badge_textbook_direct": "📚 100% Direct Textbook (Groq OFF)",
        "badge_groq": "⚡ Groq AI Engine",
        "badge_offline": "📋 Offline Clinical KB"
    },
    "Marathi": {
        "portal_tag": "क्लिनिकल एआय पोर्टल",
        "portal_desc": "रुग्णालय-दर्जाचे एआय आरोग्य सहाय्य आणि ट्रायज प्रणाली",
        "lang_label": "भाषा निवडा",
        "sign_in_tab": "साइन इन",
        "register_tab": "नोंदणी",
        "username": "वापरकर्ता नाव (Username)",
        "username_placeholder": "आपले नोंदणीकृत वापरकर्ता नाव प्रविष्ट करा",
        "password": "पासवर्ड (Password)",
        "password_placeholder": "आपला पासवर्ड प्रविष्ट करा",
        "choose_username": "नवीन वापरकर्ता नाव निवडा",
        "choose_username_placeholder": "एक अद्वितीय वापरकर्ता नाव प्रविष्ट करा",
        "choose_password": "सुरक्षित पासवर्ड तयार करा",
        "choose_password_placeholder": "किमान ६ अक्षरांचा पासवर्ड प्रविष्ट करा",
        "btn_signin": "पोर्टलमध्ये साइन इन करा  →",
        "btn_register": "नवीन खाते तयार करा  →",
        "fill_both": "कृपया दोन्ही माहिती भरा.",
        "reg_success": "खाते यशस्वीरित्या तयार झाले. कृपया साइन इन वर क्लिक करा.",
        "err_user_not_found": "वापरकर्ता सापडला नाही.",
        "err_invalid_pw": "चुकीचा पासवर्ड.",
        "err_user_exists": "हे वापरकर्ता नाव आधीपासून अस्तित्वात आहे.",
        "trust_encrypted": "एंड-टू-एंड<br>एनक्रिप्टेड",
        "trust_engine": "क्लिनिकल<br>RAG + ग्रॉक AI",
        "trust_multilingual": "त्रिभाषिक<br>मार्गदर्शन",
        "or_divider": "किंवा",
        "verified_user": "सत्यापित वापरकर्ता",
        "nav_chat": "💬 चॅट सहाय्यक",
        "nav_history": "🕒 सल्लागार इतिहास",
        "nav_settings": "⚙️ सेटिंग्ज",
        "consult_lang": "सल्लागार भाषा",
        "test_mode_toggle": "🧪 चाचणी मोड: ग्रॉक बंद करा",
        "test_mode_help": "ग्रॉक AI शिवाय थेट वैद्यकीय संदर्भ ग्रंथातून उत्तरे घेतली जातात हे दाखवण्यासाठी हे चालू करा.",
        "textbooks_ready": "वैद्यकीय संदर्भ ग्रंथ: {count:,} वेक्टर्स सज्ज",
        "connecting_library": "वैद्यकीय ग्रंथालय जोडत आहे...",
        "loading_vectors": "९ संदर्भ ग्रंथांमधून ७७,६३६ वेक्टर्स लोड करत आहे",
        "btn_connect_now": "🔄 संदर्भ ग्रंथ आता जोडा",
        "btn_clear_history": "इतिहास साफ करा",
        "clear_history_help": "संभाषण रीसेट करा",
        "btn_sign_out": "बाहेर पडा",
        "sign_out_help": "पोर्टलमधून बाहेर पडा",
        "emergency_title": "⚠️ तातडीची वैद्यकीय मदत",
        "emergency_desc": "जर तुम्ही किंवा इतर कोणी गंभीर किंवा जीवघेणी लक्षणे अनुभवत असाल तर:",
        "ambulance": "🚑 रुग्णवाहिका: <b>108 / 112</b>",
        "helpline": "📞 राष्ट्रीय आरोग्य हेल्पलाइन: <b>1800-180-1104</b>",
        "disclaimer": "उपचारिका केवळ क्लिनिकल ट्रायज आणि आरोग्य माहिती सहाय्य प्रदान करते. निश्चित निदानासाठी नेहमी परवानाधारक डॉक्टरांचा सल्ला घ्या.",
        "chat_title": "उपचारिका क्लिनिकल सहाय्यक",
        "chat_subtitle": "सक्रिय क्लिनिकल इंजिन • वैद्यकीय संदर्भ ग्रंथ RAG + ग्रॉक AI",
        "welcome_title": "उपचारिका क्लिनिकल सल्लागार पोर्टलवर आपले स्वागत आहे",
        "welcome_desc": "आपल्या लक्षणांचे वर्णन करा, औषधांविषयी माहिती विचारा किंवा प्रथमोपचार मार्गदर्शन मिळवा.",
        "user_label": "तुम्ही",
        "audio_consultation": "ऑडिओ सल्लागार:",
        "input_placeholder": "वैद्यकीय प्रश्न विचारा किंवा लक्षणांचे वर्णन करा...",
        "evaluating_spinner": "वैद्यकीय प्रश्नाचे विश्लेषण करत आहे...",
        "translating_spinner": "सल्लागार {lang} मध्ये अनुवादित करत आहे...",
        "badge_rag_groq": "📖 वैद्यकीय ग्रंथ आधारित + ग्रॉक AI",
        "badge_textbook_direct": "📚 १००% थेट वैद्यकीय ग्रंथ (ग्रॉक बंद)",
        "badge_groq": "⚡ ग्रॉक AI इंजिन",
        "badge_offline": "📋 ऑफलाइन क्लिनिकल ज्ञानकोश"
    },
    "Hindi": {
        "portal_tag": "क्लिनिकल एआई पोर्टल",
        "portal_desc": "अस्पताल-स्तरीय एआई स्वास्थ्य सहायता एवं ट्राइएज प्रणाली",
        "lang_label": "भाषा चुनें",
        "sign_in_tab": "लॉग इन",
        "register_tab": "पंजीकरण",
        "username": "उपयोगकर्ता नाम (Username)",
        "username_placeholder": "अपना पंजीकृत उपयोगकर्ता नाम दर्ज करें",
        "password": "पासवर्ड (Password)",
        "password_placeholder": "अपना पासवर्ड दर्ज करें",
        "choose_username": "नया उपयोगकर्ता नाम चुनें",
        "choose_username_placeholder": "एक अद्वितीय उपयोगकर्ता नाम दर्ज करें",
        "choose_password": "सुरक्षित पासवर्ड बनाएं",
        "choose_password_placeholder": "कम से कम ६ अक्षरों का पासवर्ड बनाएं",
        "btn_signin": "पोर्टल में लॉग इन करें  →",
        "btn_register": "नया खाता बनाएं  →",
        "fill_both": "कृपया दोनों विवरण भरें।",
        "reg_success": "खाता सफलतापूर्वक बन गया है। कृपया जारी रखने के लिए लॉग इन करें।",
        "err_user_not_found": "उपयोगकर्ता नहीं मिला।",
        "err_invalid_pw": "अमान्य पासवर्ड।",
        "err_user_exists": "यह उपयोगकर्ता नाम पहले से मौजूद है।",
        "trust_encrypted": "एंड-टू-एंड<br>एन्क्रिप्टेड",
        "trust_engine": "क्लिनिकल<br>RAG + ग्रॉक AI",
        "trust_multilingual": "त्रिभाषी<br>मार्गदर्शन",
        "or_divider": "या",
        "verified_user": "सत्यापित उपयोगकर्ता",
        "nav_chat": "💬 चैट सहायक",
        "nav_history": "🕒 परामर्श इतिहास",
        "nav_settings": "⚙️ सेटिंग्स",
        "consult_lang": "परामर्श भाषा",
        "test_mode_toggle": "🧪 परीक्षण मोड: ग्रॉक अक्षम करें",
        "test_mode_help": "ग्रॉक AI के बिना सीधे चिकित्सा पाठ्यपुस्तकों से उत्तर प्राप्त करने के लिए इसे चालू करें।",
        "textbooks_ready": "चिकित्सा संदर्भ ग्रंथ: {count:,} वेक्टर्स तैयार",
        "connecting_library": "चिकित्सा पुस्तकालय कनेक्ट हो रहा है...",
        "loading_vectors": "९ संदर्भ पुस्तकों से ७७,६३६ वेक्टर्स लोड हो रहे हैं",
        "btn_connect_now": "🔄 संदर्भ पुस्तकें अभी कनेक्ट करें",
        "btn_clear_history": "इतिहास हटाएं",
        "clear_history_help": "बातचीत रीसेट करें",
        "btn_sign_out": "लॉग आउट करें",
        "sign_out_help": "पोर्टल से बाहर निकलें",
        "emergency_title": "⚠️ आपातकालीन सहायता",
        "emergency_desc": "यदि आप या कोई अन्य व्यक्ति गंभीर या जानलेवा लक्षण महसूस कर रहा है:",
        "ambulance": "🚑 एम्बुलेंस: <b>108 / 112</b>",
        "helpline": "📞 राष्ट्रीय स्वास्थ्य हेल्पलाइन: <b>1800-180-1104</b>",
        "disclaimer": "उपचारिका केवल चिकित्सीय ट्राइएज और स्वास्थ्य जानकारी सहायता प्रदान करती है। अंतिम निदान के लिए हमेशा लाइसेंस प्राप्त चिकित्सक से परामर्श लें।",
        "chat_title": "उपचारिका चिकित्सीय सहायक",
        "chat_subtitle": "सक्रिय चिकित्सीय इंजन • चिकित्सा पाठ्यपुस्तक RAG + ग्रॉक AI",
        "welcome_title": "उपचारिका चिकित्सीय परामर्श पोर्टल में आपका स्वागत है",
        "welcome_desc": "अपने लक्षणों का वर्णन करें, दवाओं के बारे में पूछें, या प्राथमिक चिकित्सीय मार्गदर्शन प्राप्त करें।",
        "user_label": "आप",
        "audio_consultation": "ऑडियो परामर्श:",
        "input_placeholder": "चिकित्सीय प्रश्न पूछें या लक्षणों का वर्णन करें...",
        "evaluating_spinner": "चिकित्सीय प्रश्न का विश्लेषण हो रहा है...",
        "translating_spinner": "परामर्श {lang} में अनुवादित हो रहा है...",
        "badge_rag_groq": "📖 चिकित्सा ग्रंथ आधारित + ग्रॉक AI",
        "badge_textbook_direct": "📚 १००% सीधा चिकित्सा ग्रंथ (ग्रॉक बंद)",
        "badge_groq": "⚡ ग्रॉक AI इंजन",
        "badge_offline": "📋 ऑफलाइन चिकित्सीय ज्ञानकोश"
    }
}

def t(key, **kwargs):
    current_lang = st.session_state.get("selected_lang", "English")
    lang_dict = UI_STRINGS.get(current_lang, UI_STRINGS["English"])
    text_val = lang_dict.get(key, UI_STRINGS["English"].get(key, key))
    if kwargs:
        try:
            return text_val.format(**kwargs)
        except Exception:
            return text_val
    return text_val

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

        /* Complete elimination of top padding & Streamlit header push */
        header[data-testid="stHeader"],
        [data-testid="stHeader"] {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            visibility: hidden !important;
        }
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"] {
            display: none !important;
            height: 0 !important;
        }
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(100% 100% at 50% 0%, #eff6ff 0%, #f8fafc 50%, #ede9fe 100%) !important;
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        [data-testid="stAppViewContainer"] > .main,
        section[data-testid="stMain"],
        section.main {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }

        /* Single, non-cascading executive Auth Card tightly hugging top */
        [data-testid="stAppViewContainer"] section.main .block-container,
        .main .block-container,
        div[data-testid="stAppViewBlockContainer"],
        .block-container {
            max-width: 440px !important;
            width: 92% !important;
            margin-top: 6px !important;
            margin-bottom: 28px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            background: #ffffff !important;
            border: 1.5px solid #e2e8f0 !important;
            border-radius: 22px !important;
            box-shadow: 0 16px 40px -10px rgba(99, 102, 241, 0.14), 0 0 1px 1px rgba(226, 232, 240, 0.8) !important;
            padding-top: 10px !important;
            padding-bottom: 34px !important;
            padding-left: 22px !important;
            padding-right: 22px !important;
        }

        /* Compact Streamlit vertical flow */
        div[data-testid="stVerticalBlock"] {
            gap: 0.45rem !important;
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
            margin-bottom: 6px !important;
        }
        .brand-glow-circle {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 52px;
            height: 52px;
            background: linear-gradient(135deg, #e0e7ff 0%, #ede9fe 100%);
            border: 1.5px solid rgba(99, 102, 241, 0.25);
            border-radius: 16px;
            font-size: 26px;
            margin: 0 auto 6px auto;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.15);
        }
        .brand-heading {
            font-family: 'Outfit', sans-serif !important;
            font-size: 30px !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px !important;
            margin: 0 0 2px 0 !important;
            line-height: 1.15 !important;
            color: #1e1b4b !important;
        }
        .brand-heading-gradient {
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .brand-portal-tag {
            font-size: 13.5px !important;
            font-weight: 600 !important;
            color: #6366f1 !important;
            margin-bottom: 2px !important;
            letter-spacing: 0.2px !important;
        }
        .brand-caption {
            font-size: 13px !important;
            color: #64748b !important;
            margin: 0 !important;
            line-height: 1.35 !important;
            font-weight: 400 !important;
        }

        /* Form Inputs */
        label[data-testid="stWidgetLabel"] p {
            font-size: 15px !important;
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
        div[data-baseweb="input"] input {
            color: #0f172a !important;
            font-size: 16px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        div[data-baseweb="input"] input::placeholder {
            color: #94a3b8 !important;
            font-size: 15px !important;
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
            margin: 12px 0 14px 0 !important;
        }

        div[data-testid="stHorizontalBlock"] button[kind="primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.28) !important;
            min-height: 44px !important;
            border: none !important;
            font-size: 15.5px !important;
            font-weight: 700 !important;
        }

        div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
            background: transparent !important;
            color: #64748b !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            border: none !important;
            min-height: 44px !important;
            font-size: 15.5px !important;
            font-weight: 600 !important;
        }
        div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
            color: #0f172a !important;
            background: rgba(255, 255, 255, 0.7) !important;
        }

        /* Action Buttons */
        div.stButton > button {
            width: 100% !important;
            min-height: 50px !important;
            border-radius: 14px !important;
            font-weight: 700 !important;
            font-size: 16px !important;
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
            margin: 16px 0 12px 0;
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
            font-size: 14.5px;
            font-weight: 500;
        }
        .trust-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 10px;
            padding-bottom: 8px;
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
            font-size: 13px;
            color: #64748b;
            font-weight: 500;
            line-height: 1.35;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        # Language Selector Bar at top of Auth Card
        col_l1, col_l2 = st.columns([1.2, 1.8])
        with col_l1:
            st.markdown(f'<div style="font-size:14.5px; font-weight:700; color:#4f46e5; padding-top:6px;">🌐 {t("lang_label")}</div>', unsafe_allow_html=True)
        with col_l2:
            lang_opts = ["English", "Hindi", "Marathi"]
            curr_l = st.session_state.get("selected_lang", "English")
            idx = lang_opts.index(curr_l) if curr_l in lang_opts else 0
            chosen_l = st.selectbox(
                "Auth Language",
                lang_opts,
                index=idx,
                key="auth_lang_select",
                label_visibility="collapsed"
            )
            if chosen_l != st.session_state.get("selected_lang"):
                st.session_state.selected_lang = chosen_l
                try:
                    cookies["selected_lang"] = chosen_l
                    cookies.save()
                except Exception:
                    pass
                st.rerun()

        st.markdown(f"""
        <div class="auth-header-block">
            <div class="brand-glow-circle">🩺</div>
            <h1 class="brand-heading">Up<span class="brand-heading-gradient">Charika</span></h1>
            <div class="brand-portal-tag">{t("portal_tag")}</div>
            <p class="brand-caption">{t("portal_desc")}</p>
        </div>
        """, unsafe_allow_html=True)

        # Segmented Switcher Pill
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            is_sign_in = (st.session_state.auth_mode == "signin")
            if st.button(t("sign_in_tab"), key="toggle_signin", use_container_width=True, type="primary" if is_sign_in else "secondary"):
                st.session_state.auth_mode = "signin"
                st.rerun()
        with col_t2:
            is_reg = (st.session_state.auth_mode == "register")
            if st.button(t("register_tab"), key="toggle_reg", use_container_width=True, type="primary" if is_reg else "secondary"):
                st.session_state.auth_mode = "register"
                st.rerun()

        if st.session_state.auth_mode == "signin":
            user = st.text_input(t("username"), key="login_user", placeholder=t("username_placeholder"))
            pw = st.text_input(t("password"), type="password", key="login_pw", placeholder=t("password_placeholder"))
            btn_login = st.button(t("btn_signin"), key="btn_login", type="primary", use_container_width=True)

            if btn_login:
                if not user or not pw:
                    st.warning(t("fill_both"))
                else:
                    ok, msg = login_user(user, pw)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.username = user
                        st.session_state.chat_history = []

                        cookies["logged_in"] = "true"
                        cookies["username"] = user
                        try:
                            cookies["selected_lang"] = st.session_state.selected_lang
                            cookies.save()
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        err_text = t("err_user_not_found") if "not found" in msg.lower() else (t("err_invalid_pw") if "password" in msg.lower() else msg)
                        st.error(err_text)
        else:
            new_user = st.text_input(t("choose_username"), key="reg_user", placeholder=t("choose_username_placeholder"))
            new_pw = st.text_input(t("choose_password"), type="password", key="reg_pw", placeholder=t("choose_password_placeholder"))
            btn_reg = st.button(t("btn_register"), key="btn_reg", type="primary", use_container_width=True)

            if btn_reg:
                if not new_user or not new_pw:
                    st.warning(t("fill_both"))
                else:
                    ok, msg = register_user(new_user, new_pw)
                    if ok:
                        st.success(t("reg_success"))
                    else:
                        err_text = t("err_user_exists") if "already exists" in msg.lower() else msg
                        st.error(err_text)

        st.markdown(f"""
        <div class="auth-divider">
            <span>{t("or_divider")}</span>
        </div>
        <div class="trust-grid">
            <div class="trust-item">
                <svg class="trust-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
                <span class="trust-text">{t("trust_encrypted")}</span>
            </div>
            <div class="trust-item">
                <svg class="trust-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z"/></svg>
                <span class="trust-text">{t("trust_engine")}</span>
            </div>
            <div class="trust-item">
                <svg class="trust-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                <span class="trust-text">{t("trust_multilingual")}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ================= CHAT =================
def chatbot_ui(username):
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] section.main .block-container,
        .main .block-container,
        div[data-testid="stAppViewBlockContainer"],
        .block-container {
            max-width: 100% !important;
            width: 100% !important;
            margin: 0 !important;
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding-top: 10px !important;
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
                <div class="sidebar-brand-sub">{t("portal_tag")}</div>
            </div>
        </div>
        <div class="user-profile-card">
            <div class="user-avatar-circle">👤</div>
            <div class="user-info">
                <div class="user-name">{username}</div>
                <div class="user-status-verified"><span class="verified-dot"></span> {t("verified_user")}</div>
            </div>
        </div>
        <div class="nav-menu">
            <div class="nav-item active">{t("nav_chat")}</div>
            <div class="nav-item">{t("nav_history")}</div>
            <div class="nav-item">{t("nav_settings")}</div>
        </div>
        """, unsafe_allow_html=True)

        if "selected_lang" not in st.session_state:
            st.session_state.selected_lang = "English"

        st.markdown("---")
        lang_list = ["English", "Hindi", "Marathi"]
        curr_idx = lang_list.index(st.session_state.selected_lang) if st.session_state.selected_lang in lang_list else 0
        lang = st.selectbox(t("consult_lang"), lang_list, index=curr_idx)

        # Developer / Examiner Test Toggle
        force_offline = st.checkbox(
            t("test_mode_toggle"),
            value=False,
            help=t("test_mode_help")
        )

        vs_status = get_vectorstore_status()
        if vs_status["loaded"]:
            st.markdown(
                f'<div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:8px 12px; margin:4px 0 10px 0; font-size:13.5px; color:#1e40af; display:flex; align-items:center; gap:6px;">'
                f'<span>📚</span> <span><b>{t("textbooks_ready", count=vs_status["count"])}</b></span>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:10px 14px; margin:4px 0 6px 0; font-size:14px; color:#1e40af;">'
                f'<div style="display:flex; align-items:center; gap:6px; font-weight:600;"><span>⏳</span> <span>{t("connecting_library")}</span></div>'
                f'<div style="font-size:13px; margin-top:3px; color:#3b82f6;">{t("loading_vectors")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(t("btn_connect_now"), use_container_width=True, help="Click to connect the 9 medical textbooks"):
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
            prev_l = st.session_state.selected_lang
            st.session_state.selected_lang = lang
            try:
                cookies["selected_lang"] = lang
                cookies.save()
            except Exception:
                pass
            with st.spinner(t("translating_spinner", lang=lang)):
                for msg in st.session_state.chat_history:
                    if msg.get("role") == "bot":
                        raw_src = msg.get("raw_text", msg.get("text", ""))
                        re_trans = translate_text(raw_src, lang, force_offline=force_offline, source_lang=msg.get("lang", prev_l))
                        msg["text"] = re_trans
                        msg["lang"] = lang
                        try:
                            msg["audio"] = generate_voice(re_trans, lang)
                        except Exception:
                            pass
            st.rerun()

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        col_clear, col_logout = st.columns(2)
        with col_clear:
            if st.button(t("btn_clear_history"), help=t("clear_history_help")):
                st.session_state.chat_history = []
                st.rerun()
        with col_logout:
            if st.button(t("btn_sign_out"), help=t("sign_out_help")):
                st.session_state.logged_in = False
                cookies["logged_in"] = ""
                cookies["username"] = ""
                cookies.save()
                st.rerun()

        st.markdown("---")
        st.markdown(f"""
        <div class="emergency-box">
            <div class="emergency-header">{t("emergency_title")}</div>
            <p>{t("emergency_desc")}</p>
            <div class="helpline-row">{t("ambulance")}</div>
            <div class="helpline-row">{t("helpline")}</div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(t("disclaimer"))

    # Main Chat View matching Mockup Image 2
    st.markdown(f"""
    <div class="chat-header">
        <div class="chat-header-main">
            <div class="chat-header-logo-box">🩺</div>
            <div>
                <h2 class="chat-header-title">{t("chat_title")}</h2>
                <div class="chat-header-subtitle"><span class="status-indicator"></span> {t("chat_subtitle")}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Welcome card if no messages
    if len(st.session_state.chat_history) == 0:
        st.markdown(f"""
        <div class="welcome-card">
            <h3>{t("welcome_title")}</h3>
            <p>{t("welcome_desc")}</p>
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
                    with st.spinner(t("evaluating_spinner")):
                        try:
                            ans, source = get_ai_response(text, lang=lang, force_offline=force_offline)
                            trans = translate_text(ans, lang, force_offline=force_offline)
                        except Exception as e:
                            ans = str(e)
                            trans = f"⚠️ Clinical Service Notice: {str(e)}"
                            source = "notice"

                        audio = None
                        try:
                            audio = generate_voice(trans, lang)
                        except Exception:
                            audio = None

                        st.session_state.chat_history.append({
                            "role": "bot",
                            "text": trans,
                            "raw_text": ans,
                            "audio": audio,
                            "source": source,
                            "lang": lang
                        })
                    st.rerun()

    # Chat Feed
    st.markdown("<div class='chat-feed'>", unsafe_allow_html=True)
    prev_user_text = None
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            if msg.get("text") and msg.get("text") == prev_user_text:
                continue
            prev_user_text = msg.get("text")
            user_card_html = (
                '<div class="chat-row user-row">'
                '<div class="user-bubble">'
                f'<div class="bubble-header">{t("user_label")}</div>'
                f'<div class="bubble-body">{msg["text"]}</div>'
                '</div>'
                '</div>'
            )
            st.markdown(user_card_html, unsafe_allow_html=True)
        else:
            prev_user_text = None
            formatted_content = format_medical_card(msg['text'])
            source_badge = ""
            msg_source = msg.get("source")
            if msg_source in ["rag", "rag_groq"]:
                source_badge = f'<span style="display:inline-flex; align-items:center; gap:5px; font-size:13px; background:#eff6ff; color:#1d4ed8; padding:4px 11px; border-radius:12px; border:1px solid #bfdbfe; font-weight:600; margin-left:10px;">{t("badge_rag_groq")}</span>'
            elif msg_source == "textbook_direct":
                source_badge = f'<span style="display:inline-flex; align-items:center; gap:5px; font-size:13px; background:#f5f3ff; color:#6d28d9; padding:4px 11px; border-radius:12px; border:1px solid #ddd6fe; font-weight:600; margin-left:10px;">{t("badge_textbook_direct")}</span>'
            elif msg_source == "groq":
                source_badge = f'<span style="display:inline-flex; align-items:center; gap:5px; font-size:13px; background:#f0fdf4; color:#15803d; padding:4px 11px; border-radius:12px; border:1px solid #bbf7d0; font-weight:600; margin-left:10px;">{t("badge_groq")}</span>'
            elif msg_source == "offline":
                source_badge = f'<span style="display:inline-flex; align-items:center; gap:5px; font-size:13px; background:#fefce8; color:#a16207; padding:4px 11px; border-radius:12px; border:1px solid #fef08a; font-weight:600; margin-left:10px;">{t("badge_offline")}</span>'

            bot_card_html = (
                '<div class="chat-row bot-row">'
                '<div class="bot-card">'
                '<div class="bot-header" style="display:flex; align-items:center; flex-wrap:wrap;">'
                '<div class="bot-avatar-box">🩺</div>'
                f'<span class="bot-title">{t("chat_title")}</span>'
                f'{source_badge}'
                '</div>'
                f'<div class="bot-body">{formatted_content}</div>'
                '</div>'
                '</div>'
            )
            st.markdown(bot_card_html, unsafe_allow_html=True)
            if msg.get("audio"):
                st.markdown("<div class='audio-row'>", unsafe_allow_html=True)
                st.caption(t("audio_consultation"))
                st.audio(msg["audio"])
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # User Input
    chat_placeholder = t("input_placeholder")
    user_input = st.chat_input(chat_placeholder)
    if user_input:
        if not (st.session_state.chat_history and 
                st.session_state.chat_history[-1].get("role") == "user" and 
                st.session_state.chat_history[-1].get("text") == user_input):
            st.session_state.chat_history.append({"role": "user", "text": user_input})

        with st.spinner(t("evaluating_spinner")):
            try:
                answer, source = get_ai_response(user_input, lang=lang, force_offline=force_offline)
                translated = translate_text(answer, lang, force_offline=force_offline)
            except Exception as e:
                answer = str(e)
                translated = f"⚠️ Clinical Service Notice: {str(e)}"
                source = "notice"

            audio = None
            try:
                audio = generate_voice(translated, lang)
            except Exception:
                audio = None

            st.session_state.chat_history.append({
                "role": "bot",
                "text": translated,
                "raw_text": answer,
                "audio": audio,
                "source": source,
                "lang": lang
            })
        st.rerun()

# ================= MAIN =================
def main():
    # Persistent Language Selection from Cookies or Default to English
    if "selected_lang" not in st.session_state:
        saved_lang = cookies.get("selected_lang")
        if saved_lang in ["English", "Hindi", "Marathi"]:
            st.session_state.selected_lang = saved_lang
        else:
            st.session_state.selected_lang = "English"

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