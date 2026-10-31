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
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ================= GOOGLE DRIVE VECTORSTORE =================
VECTOR_URL = "https://drive.google.com/uc?id=1UunmpU4iudJycj-OibngzcJf18nA6OmR"
def load_vectorstore():
    if not os.path.exists("vectorstore/db_faiss/index.faiss"):
        with st.spinner("Preparing AI system... please wait"):
            gdown.download(VECTOR_URL, "vs.zip", quiet=False)

            with zipfile.ZipFile("vs.zip", 'r') as zip_ref:
                zip_ref.extractall("vectorstore")

            os.remove("vs.zip")

@st.cache_resource(show_spinner=False)
def get_vectorstore():
    try:
        faiss_path = "vectorstore/db_faiss"
        if os.path.exists(os.path.join(faiss_path, "index.faiss")):
            embed = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            return FAISS.load_local(faiss_path, embed, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"Error loading FAISS vectorstore: {e}")
    return None

def retrieve_medical_context(query, k=2):
    db = get_vectorstore()
    if not db:
        return ""
    try:
        docs = db.similarity_search(query, k=k)
        if docs:
            snippets = []
            for d in docs:
                txt = d.page_content.strip()
                if txt:
                    snippets.append(txt)
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
OFFLINE_CLINICAL_KB_EN = {
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

OFFLINE_CLINICAL_KB_MR = {
    "fever": """कारण: व्हायरल इन्फेक्शन (फ्लू, डेंग्यू, साथीचा ताप), जिवाणू संसर्ग किंवा शरीरातील दाहक प्रक्रिया.
उपाय: पूर्ण विश्रांती घ्या, डिहायड्रेशन टाळण्यासाठी भरपूर द्रवपदार्थ (पाणी, ओआरएस, कोमट सूप) प्या, हवेशीर खोलीत राहा आणि कपाळावर कोमट पाण्याच्या घड्या ठेवा.
औषध: डॉक्टरांच्या सल्ल्यानुसार वयोमान व वजनानुसार पॅरासिटामॉल (Paracetamol). मुले व किशोरांमध्ये ॲस्पिरिन टाळा.
डॉक्टरांना कधी भेटावे: ताप १०२°F (३८.९°C) पेक्षा जास्त असल्यास, सलग ३ दिवसांपेक्षा जास्त राहिल्यास किंवा औषध दिल्यावरही कमी न झाल्यास.
तातडीची मदत: तीव्र श्वास लागणे, मान ताठ होणे, अतिसुस्ती, छातीत तीव्र वेदना किंवा झटके (आचके) आल्यास ताबडतोब १०८ / ११२ वर संपर्क साधा.""",

    "headache": """कारण: मानसिक ताण, डिहायड्रेशन, स्क्रीनचा जास्त वापर, झोपेचा अभाव, सायनस किंवा मायग्रेन.
उपाय: शांत आणि अंधाऱ्या खोलीत विश्रांती घ्या, कपाळावर हलकी थंड किंवा कोमट घडी ठेवा, १-२ ग्लास पाणी प्या आणि मोबाईल स्क्रीनपासून दूर राहा.
औषध: डॉक्टरांच्या मार्गदर्शनानुसार सौम्य वेदनाशामक जसे की पॅरासिटामॉल.
डॉक्टरांना कधी भेटावे: डोकेदुखी ४८ तासांपेक्षा जास्त राहिल्यास, सतत वाढत गेल्यास किंवा आठवड्यातून अनेकदा होत असल्यास.
तातडीची मदत: अचानक झालेली अत्यंत तीव्र डोकेदुखी, बोलण्यात अडखळणे, दृष्टी धूसर होणे, चेहऱ्याची किंवा शरीराची एक बाजू कमजोर पडणे.""",

    "cold": """कारण: श्वसनमार्गाचा व्हायरल इन्फेक्शन (रायनोव्हायरस) ज्यामुळे नाकाच्या आतील थराला सूज येते.
उपाय: दिवसातून दोनदा गरम पाण्याची वाफ घ्या, कोमट मिठाच्या पाण्याने गुळण्या करा, आले-तुळशीचा किंवा मध-पाण्याचा काढा प्या आणि विश्रांती घ्या.
औषध: सलाइन नेझल ड्रॉप्स, डॉक्टरांच्या सल्ल्यानुसार ॲलर्जी-विरोधी औषधे (Antihistamines).
डॉक्टरांना कधी भेटावे: लक्षणे १०-१४ दिवसांपेक्षा जास्त राहिल्यास, तीव्र कानदुखी, सायनसचा त्रास किंवा जास्त ताप असल्यास.
तातडीची मदत: श्वास घेण्यास गंभीर अडचण, घरघर येणे, ओठ निळे पडणे किंवा पाणी गिळण्यास असमर्थ असणे.""",

    "cough": """कारण: सर्दीनंतर घशात कफ साचणे, ब्राँकायटिस, हवेतील धूळ/ॲलर्जी किंवा ॲसिड रिफ्लक्स.
उपाय: दिवसभर कोमट पाणी प्या, निलगिरी तेलाची वाफ घ्या, रात्री १ चमचा मध कोमट पाण्यातून घ्या (१ वर्षावरील मुलांसाठी).
औषध: कोमट मिठाच्या पाण्याच्या गुळण्या, कोरड्या अथवा कफयुक्त खोकल्यानुसार डॉक्टरांच्या सल्ल्याने सिरप.
डॉक्टरांना कधी भेटावे: खोकला ३ आठवड्यांपेक्षा जास्त राहिल्यास, थुंकीतून रक्त पडल्यास किंवा विनाकारण वजन कमी झाल्यास.
तातडीची मदत: खोकल्यातून जास्त रक्त येणे, छातीत तीव्र वेदना किंवा श्वास घेण्यास अडथळा निर्माण होणे.""",

    "reflux": """कारण: गॅस्ट्रोएसोफेजल रिफ्लक्स (पोटातील आम्ल अन्ननलिकेत येणे), जे मसालेदार/तळलेले अन्न, उशिरा जेवणे, चहा-कॉफी किंवा ताणामुळे होते.
उपाय: जेवणानंतर २-३ तास झोपू नका, थंड दूध किंवा नारळ पाणी प्या, थोडे-थोडे जेवा आणि सैल कपडे वापरा.
औषध: डॉक्टरांच्या सल्ल्यानुसार ॲन्टासिड जेल किंवा ॲसिडिटी कमी करणाऱ्या गोळ्या (H2 blockers / PPIs).
डॉक्टरांना कधी भेटावे: आठवड्यातून २ पेक्षा जास्त वेळा ॲसिडिटीचा त्रास होणे, गिळताना त्रास होणे किंवा वारंवार उलट्या होणे.
तातडीची मदत: छातीत दाब किंवा तीव्र जळजळ डाव्या हाताकडे अथवा जबड्याकडे पसरणे आणि घाम फुटणे (हृदयाशी संबंधित तातडीची तपासणी आवश्यक).""",

    "diabetes": """कारण: स्वादुपिंडातून इन्सुलिन कमी तयार होणे किंवा पेशींद्वारे त्याचा वापर न होणे ज्यामुळे रक्तातील साखरेचे प्रमाण वाढते.
उपाय: कमी गोड व फायबरयुक्त संतुलित आहार घ्या, दररोज ३० मिनिटे वेगाने चाला आणि नियमितपणे रक्तातील साखर तपासा.
औषध: तज्ज्ञ डॉक्टरांच्या सल्ल्यानुसार मेटफॉर्मिन किंवा इन्सुलिनचे डोस वेळेवर घ्या.
डॉक्टरांना कधी भेटावे: उपाशीपोटी रक्तातील साखर वारंवार १३० mg/dL पेक्षा जास्त असल्यास किंवा शरीरावरील जखम लवकर भरून न आल्यास.
तातडीची मदत: रक्तातील साखर ३०० mg/dL पेक्षा जास्त होणे किंवा ७० mg/dL पेक्षा कमी होऊन चक्कर येणे, थरथर कापणे, बेशुद्ध पडणे.""",

    "emergency": """कारण: गंभीर हृदयविकाराचा झटका, पक्षाघात (स्ट्रोक), तीव्र श्वास अडकणे, ॲनाफिलेक्सिस किंवा गंभीर अपघात.
उपाय: रुग्णाला शांत ठेवा, मोकळ्या हवेत ठेवा, घट्ट कपडे सैल करा आणि तात्काळ १०८ / ११२ रुग्णवाहिका बोलवा.
औषध: वैद्यकीय देखरेखीशिवाय कोणतेही औषध तोंडाने देऊ नका.
डॉक्टरांना कधी भेटावे: विलंब न करता तात्काळ जवळच्या आपत्कालीन रुग्णालयात घेऊन जा.
तातडीची मदत: तात्काळ १०८ किंवा ११२ वर कॉल करून रुग्णाला इमर्जन्सी वॉर्डमध्ये दाखल करा."""
}

OFFLINE_CLINICAL_KB_HI = {
    "fever": """कारण: वायरल संक्रमण (इन्फ्लूएंजा, डेंगू, मौसमी बुखार), जीवाणु संक्रमण या शरीर की सूजन संबंधी प्रतिक्रिया।
उपाय: पूर्ण आराम करें, डिहाइड्रेशन से बचने के लिए खूब तरल पदार्थ (पानी, ओआरएस, गुनगुना सूप) पिएं और माथे पर ताजे पानी की पट्टियां रखें।
दवा: उम्र और वजन के अनुसार डॉक्टर की सलाह से पैरासिटामोल (Paracetamol)। बच्चों में एस्पिरिन का प्रयोग न करें।
डॉक्टर से कब मिलें: यदि बुखार १०२°F (३८.९°C) से अधिक हो, लगातार ३ दिनों से बना रहे या दवा से कम न हो।
आपातकालीन: सांस लेने में भारी तकलीफ, गर्दन में अकड़न, अत्यधिक बेहोशी, सीने में दर्द या दौरे पड़ने पर तुरंत १०८ / ११२ पर कॉल करें।""",

    "headache": """कारण: तनाव, पानी की कमी, अत्यधिक स्क्रीन समय, नींद की कमी, साइनस या माइग्रेन।
उपाय: शांत और अंधेरे कमरे में आराम करें, माथे पर ठंडी या गुनगुनी पट्टी रखें, १-२ गिलास पानी पिएं और मोबाइल स्क्रीन से बचें।
दवा: चिकित्सक के परामर्श अनुसार हल्की दर्द निवारक दवा जैसे पैरासिटामोल।
डॉक्टर से कब मिलें: यदि सिरदर्द ४८ घंटे से अधिक समय तक रहे, लगातार बढ़ता जाए या सप्ताह में कई बार हो।
आपातकालीन: अचानक अत्यधिक तेज सिरदर्द, बोलने में लड़खड़ाहट, दृष्टि में बदलाव, चेहरे या शरीर के एक तरफ कमजोरी होना।""",

    "cold": """कारण: ऊपरी श्वसन तंत्र का वायरल संक्रमण (राइनोवायरस) जिससे नाक की अंदरूनी झिल्ली में सूजन आ जाती है।
उपाय: दिन में दो बार गर्म पानी की भाप लें, गुनगुने नमक के पानी से गरारे करें, अदरक-तुलसी की चाय पिएं और आराम करें।
दवा: सलाइन नेजल ड्रॉप्स, डॉक्टर की सलाह से एंटीहिस्टामाइन (एलर्जी रोधी दवा)।
डॉक्टर से कब मिलें: लक्षण १०-१४ दिनों से अधिक समय तक रहें, कान में तेज दर्द हो या तेज बुखार बना रहे।
आपातकालीन: सांस लेने में अत्यधिक कठिनाई, होंठ नीले पड़ना या तरल पदार्थ निगलने में असमर्थ होना।""",

    "cough": """कारण: सर्दी के बाद बलगम गिरना, ब्रोंकाइटिस, धूल-मिट्टी से एलर्जी या एसिड रिफ्लक्स।
उपाय: दिनभर गुनगुना पानी पिएं, नीलगिरी तेल की भाप लें, रात में गुनगुने पानी में १ चम्मच शहद मिलाकर लें (१ वर्ष से बड़े बच्चों के लिए)।
दवा: नमक के पानी से गरारे करें, सूखी या बलगम वाली खांसी के अनुसार डॉक्टर की सलाह से कफ सिरप लें।
डॉक्टर से कब मिलें: खांसी ३ सप्ताह से अधिक समय तक रहे, बलगम में खून आए या अचानक वजन कम हो।
आपातकालीन: खांसी में अधिक खून आना, सीने में तेज दर्द या सांस लेने में भारी रुकावट।""",

    "reflux": """कारण: पेट का एसिड भोजन नली में वापस आना (एसिड रिफ्लक्स), जो मसालेदार भोजन, देर से खाने, कैफीन या तनाव के कारण होता है।
उपाय: खाने के बाद २-३ घंटे तक न लेटें, ठंडा दूध या नारियल पानी पिएं, थोड़ी-थोड़ी मात्रा में भोजन करें और ढीले कपड़े पहनें।
दवा: डॉक्टर की सलाह से एंटासिड सिरप या एसिडिटी की गोलियां (जैसे Pantoprazole / Omeprazole)।
डॉक्टर से कब मिलें: सप्ताह में २ से अधिक बार एसिडिटी होना, निगलने में दर्द या बार-बार उल्टी होना।
आपातकालीन: सीने में भारी दबाव या दर्द जो बाएं हाथ या जबड़े तक फैले और साथ में पसीना आए (हार्ट अटैक का लक्षण हो सकता है)।""",

    "diabetes": """कारण: अग्न्याशय द्वारा पर्याप्त इंसुलिन न बनना या कोशिकाओं द्वारा इंसुलिन का उपयोग न हो पाना, जिससे ब्लड शुगर बढ़ता है।
उपाय: संतुलित कम ग्लाइसेमिक आहार लें, रोजाना ३० मिनट तेज टहलें और नियमित रूप से फास्टिंग ब्लड शुगर की जांच करें।
दवा: एंडोक्रिनोलॉजिस्ट या डॉक्टर द्वारा निर्धारित दवाइयां (जैसे मेटफॉर्मिन) या इंसुलिन समय पर लें।
डॉक्टर से कब मिलें: खाली पेट ब्लड शुगर लगातार १३० mg/dL से अधिक रहे या चोट/घाव ठीक होने में बहुत समय लगे।
आपातकालीन: ब्लड शुगर ३०० mg/dL से अधिक होना या ७० mg/dL से कम होकर कंपकंपी, अत्यधिक पसीना, चक्कर या बेहोशी आना।""",

    "emergency": """कारण: गंभीर दिल का दौरा, स्ट्रोक, सांस रुकना, तीव्र एलर्जी (एनाफिलेक्सिस) या गंभीर दुर्घटना।
उपाय: मरीज को शांत रखें, आरामदायक स्थिति में लिटाएं, तंग कपड़े ढीले करें और तुरंत एम्बुलेंस बुलाएं।
दवा: डॉक्टरी देखरेख के बिना मुंह से कोई दवा न दें।
डॉक्टर से कब मिलें: बिना किसी देरी के तुरंत नजदीकी आपातकालीन अस्पताल ले जाएं।
आपातकालीन: तुरंत १०८ या ११२ पर कॉल करें और मरीज को इमरजेंसी विभाग में पहुंचाएं।"""
}

OFFLINE_CLINICAL_KB = OFFLINE_CLINICAL_KB_EN

def match_offline_kb(prompt, lang="English"):
    p_lower = prompt.lower()
    matched_key = None

    for key in OFFLINE_CLINICAL_KB_EN.keys():
        if key in p_lower:
            matched_key = key
            break

    if not matched_key:
        if any(w in p_lower for w in ["ताप", "बुखार", "temperature", "chills", "fever"]):
            matched_key = "fever"
        elif any(w in p_lower for w in ["सिरदर्द", "डोकेदुखी", "migraine", "headache"]):
            matched_key = "headache"
        elif any(w in p_lower for w in ["सर्दी", "cold", "flu", "sneeze"]):
            matched_key = "cold"
        elif any(w in p_lower for w in ["खोकला", "खांसी", "cough"]):
            matched_key = "cough"
        elif any(w in p_lower for w in ["acidity", "acid", "heartburn", "gastric", "पित्त", "एसिडिटी", "reflux"]):
            matched_key = "reflux"
        elif any(w in p_lower for w in ["मधुमेह", "शुगर", "sugar", "glucose", "diabetes"]):
            matched_key = "diabetes"
        elif any(w in p_lower for w in ["warning signs", "danger", "critical", "तातडी", "आपात", "emergency"]):
            matched_key = "emergency"

    if matched_key:
        if lang == "Marathi":
            return OFFLINE_CLINICAL_KB_MR.get(matched_key, OFFLINE_CLINICAL_KB_EN[matched_key])
        elif lang == "Hindi":
            return OFFLINE_CLINICAL_KB_HI.get(matched_key, OFFLINE_CLINICAL_KB_EN[matched_key])
        else:
            return OFFLINE_CLINICAL_KB_EN[matched_key]
    return None

# ================= AI =================
AVAILABLE_GROQ_MODELS = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]

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
                    return content.strip()
        except Exception:
            continue
    return None

def get_ai_response(prompt, lang="English"):
    # 1. RAG Step: Retrieve verified medical textbook context from FAISS
    context = retrieve_medical_context(prompt, k=2)
    has_rag = bool(context and len(context.strip()) > 30)

    active_client = get_groq_client()
    if active_client:
        try:
            lang_instruction = ""
            if lang == "Marathi":
                lang_instruction = """CRITICAL: You MUST write your ENTIRE response in Marathi (मराठी).
Use these exact Marathi medical section headers:
कारण:
उपाय:
औषध:
डॉक्टरांना कधी भेटावे:
तातडीची मदत:"""
            elif lang == "Hindi":
                lang_instruction = """CRITICAL: You MUST write your ENTIRE response in Hindi (हिन्दी).
Use these exact Hindi medical section headers:
कारण:
उपाय:
दवा:
डॉक्टर से कब मिलें:
आपातकालीन:"""
            else:
                lang_instruction = """Format your advice using these clear medical sections:
Cause:
Solution:
Medicine:
When to see doctor:
Emergency:"""

            context_block = ""
            if has_rag:
                context_block = f"""Verified Medical Reference Context (from Clinical Textbook):
\"\"\"
{context}
\"\"\"
Carefully incorporate and ground your clinical advice in the above textbook findings."""

            ans = call_groq_chat(
                active_client,
                [
                    {
                        "role": "system",
                        "content": f"""You are UpCharika, a clinical AI healthcare assistant.
Provide structured, professional medical guidance.

Do NOT use asterisks, markdown symbols (*, **, ==) or bold formatting.
{lang_instruction}

{context_block}

Always conclude by reminding the patient that this is triage support and to consult a licensed physician for definitive medical decisions."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            if ans and len(ans.strip()) > 0:
                source = "rag" if has_rag else "groq"
                return ans, source
        except Exception:
            pass

    # 2. Fallback to offline clinical knowledge base if prompt matches common symptoms
    offline_ans = match_offline_kb(prompt, lang=lang)
    if offline_ans:
        return offline_ans, "offline"

    # 3. If offline but textbook context is available, format from textbook context directly
    if has_rag:
        return f"Cause: Based on clinical textbook findings:\n{context[:400]}...", "rag"

    # 4. If neither Groq nor offline KB answered, show a clear guidance notice in the chosen language
    if lang == "Marathi":
        return (
            "⚠️ सूचना: इतर सर्वसमावेशक प्रश्नांसाठी Groq API Key ची आवश्यकता आहे.\n\n"
            "• Streamlit Community Cloud वर: App Settings ➔ Secrets मध्ये जाऊन नोंदवा:\n"
            'GROQ_API_KEY = "your_groq_api_key"\n\n'
            "• स्थानिक पातळीवर: तुमच्या .env फाईलमध्ये GROQ_API_KEY=your_key जोडा.\n\n"
            "तुम्ही खालील आजारांविषयी विचारू शकता: ताप, डोकेदुखी, सर्दी, खोकला, ॲसिडिटी किंवा मधुमेह."
        ), "notice"
    elif lang == "Hindi":
        return (
            "⚠️ सूचना: अन्य प्रश्नों के लिए Groq API Key कॉन्फ़िगर करना आवश्यक है।\n\n"
            "• Streamlit Community Cloud पर: App Settings ➔ Secrets में दर्ज करें:\n"
            'GROQ_API_KEY = "your_groq_api_key"\n\n'
            "• स्थानीय रूप से: अपनी .env फ़ाइल में GROQ_API_KEY=your_key जोड़ें।\n\n"
            "आप निम्न लक्षणों के बारे में पूछ सकते हैं: बुखार, सिरदर्द, सर्दी, खांसी, एसिडिटी या मधुमेह।"
        ), "notice"
    else:
        return (
            "⚠️ Notice: UpCharika requires a configured Groq API Key for open-ended queries.\n\n"
            "• On Streamlit Community Cloud: Go to App Settings ➔ Secrets and enter:\n"
            'GROQ_API_KEY = "your_groq_api_key"\n\n'
            "• Locally: Add GROQ_API_KEY=your_key in your .env file.\n\n"
            "You can also ask about: Fever, Headache, Cold, Cough, Acid Reflux, or Diabetes."
        ), "notice"

# ================= TRANSLATION =================
def translate_text(text, lang):
    if not text or lang == "English":
        return text

    target_lang_clean = lang.strip().capitalize()

    # 1. Direct offline clinical dictionary match
    for key, en_content in OFFLINE_CLINICAL_KB_EN.items():
        if text.strip() == en_content.strip():
            if target_lang_clean == "Marathi":
                return OFFLINE_CLINICAL_KB_MR[key]
            elif target_lang_clean == "Hindi":
                return OFFLINE_CLINICAL_KB_HI[key]

    for key, mr_content in OFFLINE_CLINICAL_KB_MR.items():
        if text.strip() == mr_content.strip():
            if target_lang_clean == "Marathi":
                return mr_content
            elif target_lang_clean == "Hindi":
                return OFFLINE_CLINICAL_KB_HI[key]
            elif target_lang_clean == "English":
                return OFFLINE_CLINICAL_KB_EN[key]

    for key, hi_content in OFFLINE_CLINICAL_KB_HI.items():
        if text.strip() == hi_content.strip():
            if target_lang_clean == "Hindi":
                return hi_content
            elif target_lang_clean == "Marathi":
                return OFFLINE_CLINICAL_KB_MR[key]
            elif target_lang_clean == "English":
                return OFFLINE_CLINICAL_KB_EN[key]

    # 2. Use Groq AI translation if available (reliable, high accuracy, bypasses scraper blocks)
    active_client = get_groq_client()
    if active_client:
        try:
            t_content = call_groq_chat(
                active_client,
                [
                    {
                        "role": "system",
                        "content": f"""You are a professional medical translator.
Translate the medical text accurately into {target_lang_clean}.
Preserve clear medical section headers (e.g. Cause:, Solution:, Medicine:, When to see doctor:, Emergency: translated into {target_lang_clean}).
Do NOT use asterisks, markdown symbols (*, **, ==) or bold formatting.
Return ONLY the translated text."""
                    },
                    {"role": "user", "content": text}
                ],
                temperature=0.2
            )
            if t_content and len(t_content.strip()) > 0:
                return t_content.strip()
        except Exception:
            pass

    # 3. Use deep_translator with ISO code fallback
    try:
        lang_code = "mr" if target_lang_clean == "Marathi" else ("hi" if target_lang_clean == "Hindi" else lang.lower())
        return GoogleTranslator(source="auto", target=lang_code).translate(text)
    except Exception:
        pass

    try:
        return GoogleTranslator(source="auto", target=lang.lower()).translate(text)
    except Exception:
        pass

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

        # Re-translate existing conversation dynamically if user switches language in sidebar
        if lang != st.session_state.selected_lang:
            st.session_state.selected_lang = lang
            for msg in st.session_state.chat_history:
                if msg.get("role") == "bot":
                    raw_src = msg.get("raw_text", msg.get("text", ""))
                    re_trans = translate_text(raw_src, lang)
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
                            ans, source = get_ai_response(text, lang=lang)
                            trans = translate_text(ans, lang)
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
            source_badge = ""
            msg_source = msg.get("source")
            if msg_source == "rag":
                source_badge = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11px; background:#eff6ff; color:#1d4ed8; padding:3px 10px; border-radius:12px; border:1px solid #bfdbfe; font-weight:600; margin-left:10px;">📖 Medical Textbook Grounded (RAG)</span>'
            elif msg_source == "groq":
                source_badge = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11px; background:#f0fdf4; color:#15803d; padding:3px 10px; border-radius:12px; border:1px solid #bbf7d0; font-weight:600; margin-left:10px;">⚡ Groq AI Engine</span>'
            elif msg_source == "offline":
                source_badge = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11px; background:#fefce8; color:#a16207; padding:3px 10px; border-radius:12px; border:1px solid #fef08a; font-weight:600; margin-left:10px;">📋 Offline Clinical KB</span>'

            st.markdown(f"""
            <div class="chat-row bot-row">
                <div class="bot-card">
                    <div class="bot-header" style="display:flex; align-items:center; flex-wrap:wrap;">
                        <div class="bot-avatar-box">🩺</div>
                        <span class="bot-title">UpCharika Clinical Assistant</span>
                        {source_badge}
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
                answer, source = get_ai_response(user_input, lang=lang)
                translated = translate_text(answer, lang)
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