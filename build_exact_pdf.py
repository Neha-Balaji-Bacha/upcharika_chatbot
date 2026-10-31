import os
import sys
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Nirmala for flawless Devanagari (Marathi/Hindi) + English rendering
pdfmetrics.registerFont(TTFont('Nirmala', r'C:\Windows\Fonts\Nirmala.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Nirmala-Bold', r'C:\Windows\Fonts\Nirmala.ttc', subfontIndex=1 if os.path.exists(r'C:\Windows\Fonts\Nirmala.ttc') else 0))
pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', r'C:\Windows\Fonts\arialbd.ttf'))

class CustomNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Arial", 8.5)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "UpCharika - Multilingual Clinical AI Assistant | Complete Study Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)

        # Footer
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 34, text)
        self.drawString(54, 34, "UpCharika Project Defense & Comprehensive Viva Guide")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * 72 - 54, 46)
        self.restoreState()

def build_pdf():
    pdf_filename = "UpCharika_Complete_Project_Study_Guide.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Palette
    c_primary = colors.HexColor("#1e3a8a")     # Deep Blue
    c_secondary = colors.HexColor("#0284c7")   # Medical Cyan/Blue
    c_dark = colors.HexColor("#0f172a")        # Slate 900
    c_text = colors.HexColor("#1e293b")        # Slate 800
    c_bg_light = colors.HexColor("#f8fafc")    # Light gray
    c_code_bg = colors.HexColor("#f1f5f9")     # Code background
    c_border = colors.HexColor("#cbd5e1")
    c_accent = colors.HexColor("#7c3aed")      # Purple
    c_green = colors.HexColor("#059669")

    # Typography
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=22,
        leading=26,
        textColor=c_primary,
        spaceAfter=4
    )

    doc_subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=11,
        leading=15,
        textColor=c_secondary,
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=15,
        leading=19,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=12,
        leading=16,
        textColor=c_secondary,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'H3',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=10.5,
        leading=14.5,
        textColor=c_dark,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=9,
        leading=13.5,
        textColor=c_text,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=9,
        leading=13.5,
        textColor=c_text,
        leftIndent=12,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=9,
        leading=13.5,
        textColor=c_primary,
        leftIndent=8,
        spaceBefore=2,
        spaceAfter=4
    )

    pre_style = ParagraphStyle(
        'PreformattedCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=4,
        spaceAfter=6
    )

    story = []

    # Title Banner
    story.append(Paragraph("<b>UpCharika: Multilingual Clinical AI Assistant</b>", doc_title_style))
    story.append(Paragraph("<b>Comprehensive Step-by-Step Project Study Guide & Complete Viva Voce Defense</b>", doc_subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=0, spaceAfter=10))

    # Meta Info Box
    meta_data = [
        [Paragraph("<b>Project:</b> UpCharika Clinical Healthcare AI", body_style), Paragraph("<b>Target Languages:</b> English, Marathi (मराठी), Hindi (हिन्दी)", body_style)],
        [Paragraph("<b>Architecture:</b> True RAG (Retrieval-Augmented Generation)", body_style), Paragraph("<b>Vector Index:</b> 119 MB FAISS Index (Textbook PDFs)", body_style)],
        [Paragraph("<b>Inference Engine:</b> Groq LPUs (qwen/qwen3.8-27b)", body_style), Paragraph("<b>Voice Synthesis:</b> Latency-Optimized gTTS (2.5s)", body_style)],
    ]
    t_meta = Table(meta_data, colWidths=[250, 254])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # ================= PART 1 =================
    story.append(Paragraph("<b>Part 1: What Makes UpCharika Unique? (Compared to Other Chatbots)</b>", h1_style))
    story.append(Paragraph("Most college chatbots or generic AI tools (like ChatGPT) are not designed for real-world healthcare in India. Here is a direct comparison showing why <b>UpCharika</b> stands out:", body_style))
    story.append(Spacer(1, 4))

    table_p1 = [
        [
            Paragraph("<b>Feature</b>", body_style),
            Paragraph("<b>Generic Chatbots (ChatGPT / Standard College Projects)</b>", body_style),
            Paragraph("<b>UpCharika (Your Project)</b>", body_style),
            Paragraph("<b>Why It Matters</b>", body_style)
        ],
        [
            Paragraph("<b>1. Source of Medical Knowledge</b>", body_style),
            Paragraph("Hallucinates or guesses from generic internet data. Can invent dangerous dosages.", body_style),
            Paragraph("<b>Grounded in Verified Medical Literature (RAG):</b> Searches your <b>119 MB FAISS Textbook Index</b> first before answering.", body_style),
            Paragraph("Prevents medical misinformation; answers cite verified clinical books.", body_style)
        ],
        [
            Paragraph("<b>2. Regional Indian Languages</b>", body_style),
            Paragraph("Clunky machine translation that often distorts medical terms in Marathi or Hindi.", body_style),
            Paragraph("<b>Native Devanagari Medical Triage:</b> Pre-built native clinical dictionaries in Marathi (मराठी) and Hindi (हिन्दी) + multilingual LLM synthesis.", body_style),
            Paragraph("In Maharashtra, over 70% of rural/semi-urban patients only understand health advice in Marathi or Hindi.", body_style)
        ],
        [
            Paragraph("<b>3. Accessibility for Elderly / Ill Patients</b>", body_style),
            Paragraph("Only text on a screen. Hard for ill or illiterate patients to read long paragraphs.", body_style),
            Paragraph("<b>Instant Spoken Voice Consultation (gTTS):</b> Speaks the critical clinical advice in English, Hindi, or Marathi in under 3 seconds.", body_style),
            Paragraph("Elderly patients or those with poor vision can simply listen to the doctor's advice.", body_style)
        ],
        [
            Paragraph("<b>4. Safety & Structure</b>", body_style),
            Paragraph("Wall of unstructured paragraphs. Hard to find what medicine to take or when to rush to the hospital.", body_style),
            Paragraph("<b>Strict 5-Tier Clinical Protocol:</b> Every response is split into: Cause (कारणे), Solution / Diet (उपाय / आहार), Medicine (औषध), When to see Doctor (डॉक्टरांना कधी भेटावे), and Emergency Red Flags (तातडीची मदत).", body_style),
            Paragraph("Patients can immediately spot life-threatening red flags vs home remedies.", body_style)
        ],
        [
            Paragraph("<b>5. Offline Resilience & Examiner Proof</b>", body_style),
            Paragraph("Dies completely if internet drops or API quota ends.", body_style),
            Paragraph("<b>Dual-Engine Architecture:</b> If Groq is offline or disabled, it falls back to <b>Direct Textbook Search</b> + <b>Offline Clinical KB</b>. Includes a <b>Test Mode Switch</b> to prove this to examiners.", body_style),
            Paragraph("Reliability during hospital power cuts or network blackouts.", body_style)
        ]
    ]

    t_p1 = Table(table_p1, colWidths=[90, 138, 148, 128])
    t_p1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e0e7ff")),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_p1)
    story.append(Spacer(1, 10))

    # ================= PART 2 =================
    story.append(Paragraph("<b>Part 2: Project Structure — How the Files Work Together</b>", h1_style))
    story.append(Paragraph("Here is the entire anatomy of your project, explained simply:", body_style))

    folder_diagram = (
        "Medical_chatbot/\n"
        "│\n"
        "├── create_memory_for_llm.py   <-- [Phase 1: The Builder] Converts Medical Books to Math Vectors\n"
        "├── vectorstore/\n"
        "│   └── db_faiss/             <-- [The Knowledge Vault] 119 MB Searchable Medical Textbook\n"
        "│       ├── index.faiss\n"
        "│       └── index.pkl\n"
        "│\n"
        "├── medibot.py                 <-- [Phase 2: The Main Application] Web Server, AI, RAG & Voice\n"
        "├── style.css                  <-- [The Presentation] Clean, modern hospital-grade theme\n"
        "├── users.json                 <-- [Security] User database with encrypted passwords\n"
        "├── requirements.txt           <-- [Dependencies] List of all Python packages needed\n"
        "├── .env / secrets.toml        <-- [Credentials] Secure API keys (Groq)\n"
        "└── venv/                      <-- [Python Virtual Environment] Isolated dependencies"
    )
    story.append(Preformatted(folder_diagram, pre_style))
    story.append(Spacer(1, 6))

    files_info = [
        ("File 1: create_memory_for_llm.py (The Builder)",
         "<b>What it does:</b> You run this script <b>once</b> before launching the chatbot. It converts raw medical textbook PDFs into a high-speed search database.<br/>"
         "<b>How it works inside (3 steps):</b><br/>"
         "1. <b>Reads PDFs (fitz / PyMuPDF):</b> Opens medical books page-by-page and extracts raw text.<br/>"
         "2. <b>Text Chunking (RecursiveCharacterTextSplitter):</b> A whole textbook is too big to search at once. It splits the book into small pieces of <b>1,000 characters each</b> (with a 100-character overlap so sentences aren't cut mid-thought).<br/>"
         "3. <b>Embeddings & FAISS Indexing (sentence-transformers/all-MiniLM-L6-v2):</b> It converts each 1,000-character chunk into a <b>384-dimensional mathematical vector</b> (a list of 384 numbers representing its clinical meaning) and saves them into <code>vectorstore/db_faiss/index.faiss</code>."),
        
        ("File 2: vectorstore/db_faiss/ (The Medical Knowledge Vault)",
         "• <b>index.faiss (119 MB):</b> The raw mathematical vector matrix created by Facebook AI Research (FAISS). It allows finding the most relevant medical book passage in <b>less than 20 milliseconds</b>.<br/>"
         "• <b>index.pkl:</b> The dictionary that maps vector IDs back to the actual English sentences and page numbers in your book."),

        ("File 3: medibot.py (The Core Engine)",
         "This is the master file that runs your entire web platform. It handles:<br/>"
         "1. <b>User Authentication:</b> Login and Sign Up using <code>bcrypt</code> (passwords are salted and hashed so they can never be stolen).<br/>"
         "2. <b>Session Cookies (EncryptedCookieManager):</b> Keeps you logged in even if you refresh your browser.<br/>"
         "3. <b>RAG Pipeline (retrieve_medical_context):</b> Embeds the user query and searches <code>db_faiss</code> for top 2 relevant paragraphs.<br/>"
         "4. <b>Groq AI Integration (call_groq_chat):</b> Sends the user's question <b>along with textbook paragraphs</b> to Groq LPUs (<code>qwen/qwen3.8-27b</code>).<br/>"
         "5. <b>Multilingual Translation (translate_text):</b> Translates responses into Marathi or Hindi dynamically.<br/>"
         "6. <b>Optimized Voice Synthesis (generate_voice):</b> Extracts first 2 actionable sentences (<code>extract_voice_summary</code>) and generates audio in 2.5s.<br/>"
         "7. <b>Offline / Test Mode Fallback:</b> Bypasses Groq when toggled and delivers direct textbook excerpts with the purple badge <b>📚 100% Direct Textbook (Groq OFF)</b>."),

        ("File 4: style.css (The Clinical Design System)",
         "Instead of looking like a generic default Streamlit hobby project, <code>style.css</code> transforms it into a <b>professional Medical SaaS Portal</b> with clean cards, responsive layout, blue/purple/green source badges, rounded input boxes, and smooth buttons."),

        ("File 5: users.json (Security)",
         "Holds user records in secure salted hash format: <code>{\"nikita\": \"$2b$12$yv.7Xoamu...\"}</code>. Even if someone opens <code>users.json</code>, they cannot see the password because <code>bcrypt</code> uses one-way mathematical encryption with 12 salt rounds.")
    ]

    for fname, fdesc in files_info:
        story.append(Paragraph(f"<b>{fname}</b>", h3_style))
        story.append(Paragraph(fdesc, body_style))

    story.append(Spacer(1, 8))

    # ================= PART 3 =================
    story.append(Paragraph("<b>Part 3: Deep Walkthrough of a Single Question</b>", h1_style))
    story.append(Paragraph("Let's trace exactly what happens inside the computer when a user types: <i>'What is jaundice and what diet should I eat?'</i>", body_style))

    walkthrough = (
        "Step 1: Patient hits Enter in medibot.py\n"
        "   │\n"
        "   ▼\n"
        "Step 2: Vector Search (RAG Step)\n"
        "   • The sentence is converted into 384 numbers by `all-MiniLM-L6-v2`.\n"
        "   • FAISS searches through 119 MB of vectors in 15 milliseconds.\n"
        "   • It finds Textbook Page 42:\n"
        "     'Exposure to people with jaundice; contaminated foods; alcohol; duration;\n"
        "      anorexia, abdominal pain... evaluation of nutritional status...'\n"
        "   │\n"
        "   ▼\n"
        "Step 3: Augmenting the AI Prompt\n"
        "   • medibot.py constructs a prompt:\n"
        "     'You are UpCharika. Here is verified medical textbook context:\n"
        "      [Textbook Paragraphs on Jaundice and Nutrition].\n"
        "      Formulate a clinical triage answer for the user's query.'\n"
        "   │\n"
        "   ▼\n"
        "Step 4: Groq AI Inference\n"
        "   • Groq LPU processes this in 1.2 seconds.\n"
        "   • Generates the structured 5-part clinical response.\n"
        "   │\n"
        "   ▼\n"
        "Step 5: Voice Summary & Audio Generation\n"
        "   • `extract_voice_summary` extracts:\n"
        "     'Jaundice occurs due to elevated bilirubin levels and liver inflammation.\n"
        "      Adhere to a light, easily digestible diet with plenty of fluids and boiled vegetables.'\n"
        "   • `gTTS` converts these 2 concise sentences to MP3 in 2.2 seconds.\n"
        "   │\n"
        "   ▼\n"
        "Step 6: Display on Screen\n"
        "   • Card rendered with badge: 📖 Medical Textbook Grounded + Groq AI\n"
        "   • 5 color-coded sections: Cause, Solution, Medicine, Doctor, Emergency.\n"
        "   • Audio player ready for instant playback."
    )
    story.append(Preformatted(walkthrough, pre_style))
    story.append(Spacer(1, 10))

    # ================= LESSON 1 =================
    story.append(Paragraph("<b>Lesson 1: How the Medical Memory was Created (create_memory_for_llm.py)</b>", h1_style))
    story.append(Paragraph("This file is an <b>offline pipeline</b>. You run it once to convert medical PDF textbooks into the 119 MB FAISS vector database. It has <b>3 core functions</b>:", body_style))

    l1_flow = (
        "[Raw PDFs in data/]\n"
        "        │\n"
        "        ▼ (Function 1: load_pdf_files)\n"
        "[Extracted Text Pages + Metadata]\n"
        "        │\n"
        "        ▼ (Function 2: create_chunks)\n"
        "[1,000-character Text Chunks with 100 overlap]\n"
        "        │\n"
        "        ▼ (Function 3: store_in_faiss)\n"
        "[384-dimensional Vectors stored in vectorstore/db_faiss]"
    )
    story.append(Preformatted(l1_flow, pre_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Step 1: Loading the PDFs (load_pdf_files, Lines 17–51)</b>", h2_style))
    code_step1 = (
        "import fitz  # PyMuPDF library\n\n"
        "for pdf_path in pdf_files:\n"
        "    with fitz.open(pdf_path) as doc:\n"
        "        for page_num, page in enumerate(doc):\n"
        "            text = page.get_text('text').strip()\n"
        "            if text:\n"
        "                metadata = {\n"
        "                    'source': os.path.basename(pdf_path),\n"
        "                    'page': page_num + 1\n"
        "                }\n"
        "                documents.append({'text': text, 'metadata': metadata})"
    )
    story.append(Preformatted(code_step1, pre_style))
    story.append(Paragraph("• <b>What fitz (PyMuPDF) does:</b> PyMuPDF is one of the fastest PDF extractors in Python. It opens the medical textbook, iterates through every single page, and extracts clean text.<br/>• <b>Why metadata is saved:</b> Every page records <b>which book it came from</b> and the <b>exact page number</b>. When someone asks a question, the system knows not just the answer, but the textbook page where it was found!", body_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Step 2: Chunking the Text (create_chunks, Lines 53–69)</b>", h2_style))
    code_step2 = (
        "text_splitter = RecursiveCharacterTextSplitter(\n"
        "    chunk_size=1000,\n"
        "    chunk_overlap=100\n"
        ")\n"
        "chunks = text_splitter.create_documents(texts, metadatas=metadatas)"
    )
    story.append(Preformatted(code_step2, pre_style))
    story.append(Paragraph("<b>Why do we need chunking? (Crucial Viva Question)</b><br/>"
                           "<i>Examiner Question:</i> 'Why not just embed the entire textbook or whole chapters at once?'<br/>"
                           "<i>Your Answer:</i> 'Because embedding models have a maximum token limit (typically 256–512 tokens). If you put an entire 50-page chapter in, the model forgets specific details. By splitting into 1,000-character chunks, each chunk represents a single focused medical concept (like symptoms of Jaundice or fever management).'", body_style))
    story.append(Paragraph("<b>What is chunk_overlap=100?</b><br/>"
                           "Imagine a critical sentence spans across the boundary: Chunk 1 ends at: <i>'For severe dehydration, oral rehydration'</i> ... and Chunk 2 starts at: <i>'salts (ORS) should be given immediately.'</i> If there were <b>zero overlap</b>, that medical advice would be cut in half and lost! The <b>100-character overlap</b> ensures that the end of Chunk 1 and the start of Chunk 2 share the same words, preserving full sentence meaning.", body_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Step 3: Vector Embeddings & FAISS (store_in_faiss, Lines 71–85)</b>", h2_style))
    code_step3 = (
        "embedding_model = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')\n\n"
        "db = FAISS.from_documents(\n"
        "    documents=text_chunks,\n"
        "    embedding=embedding_model\n"
        ")\n"
        "db.save_local('vectorstore/db_faiss')"
    )
    story.append(Preformatted(code_step3, pre_style))
    story.append(Paragraph("<b>What are Embeddings? (The Core Math)</b><br/>"
                           "• An embedding model is a neural network that translates human text into <b>numbers</b>.<br/>"
                           "• <code>all-MiniLM-L6-v2</code> converts every chunk into an array of <b>384 decimal numbers</b> (a 384-dimensional vector).<br/>"
                           "• Words with similar clinical meanings have high mathematical similarity (calculated via <b>Cosine Similarity</b> or <b>Euclidean Distance</b>):<br/>"
                           "  Similarity('high fever', 'elevated body temperature') ≈ 0.92<br/>"
                           "  Similarity('high fever', 'stock market crash') ≈ 0.05", body_style))
    story.append(Paragraph("<b>What is FAISS?</b><br/>"
                           "• <b>FAISS</b> stands for <b>Facebook AI Similarity Search</b>.<br/>"
                           "• Instead of comparing a question to all 100,000 sentences one by one (which would take 10 seconds), FAISS uses an indexed tree structure to find the closest vectors in <b>under 20 milliseconds</b>.", body_style))

    story.append(Spacer(1, 10))

    # ================= LESSON 2 =================
    story.append(Paragraph("<b>Lesson 2: How the Live Chatbot Runs (medibot.py)</b>", h1_style))
    story.append(Paragraph("Now let's examine the 4 most important functions inside <code>medibot.py</code>:", body_style))

    story.append(Paragraph("<b>1. Retrieving Textbook Context (retrieve_medical_context, Lines 60–75)</b>", h2_style))
    code_m1 = (
        "@st.cache_resource(show_spinner=False)\n"
        "def get_vectorstore():\n"
        "    embed = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')\n"
        "    return FAISS.load_local('vectorstore/db_faiss', embed, allow_dangerous_deserialization=True)\n\n"
        "def retrieve_medical_context(query, k=2):\n"
        "    db = get_vectorstore()\n"
        "    docs = db.similarity_search(query, k=k)\n"
        "    return '\\n\\n'.join([d.page_content.strip() for d in docs])"
    )
    story.append(Preformatted(code_m1, pre_style))
    story.append(Paragraph("• <code>@st.cache_resource</code>: Ensures the 119 MB vector database is loaded into RAM <b>only once</b>. Every user query reuses the database in memory without reloading.<br/>• <code>k=2</code>: Retrieves the <b>Top 2</b> most relevant paragraphs matching the patient's question.", body_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>2. The AI Generation & Prompt Injection (get_ai_response, Lines 455–550)</b>", h2_style))
    code_m2 = (
        "context = retrieve_medical_context(prompt, k=2)\n\n"
        "prompt_to_groq = f'''\n"
        "You are UpCharika, a clinical AI healthcare assistant.\n"
        "Provide structured, professional medical guidance using:\n"
        "Cause:\n"
        "Solution:\n"
        "Medicine:\n"
        "When to see doctor:\n"
        "Emergency:\n\n"
        "Verified Medical Reference Context (from Clinical Textbook):\n"
        "\\\"\\\"\\\"\n"
        "{context}\n"
        "\\\"\\\"\\\"\n"
        "Carefully incorporate and ground your clinical advice in the above textbook findings.\n"
        "'''"
    )
    story.append(Preformatted(code_m2, pre_style))
    story.append(Paragraph("• This is <b>True RAG</b>: We don't ask the AI model to guess. We feed it the <b>exact textbook paragraphs</b> inside <code>{context}</code> and tell it: <i>'Ground your answer in this textbook.'</i><br/>• Groq processes this prompt and generates the final response in ~1.2 seconds.", body_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>3. Low-Latency Voice Optimization (extract_voice_summary, Lines 355–375)</b>", h2_style))
    code_m3 = (
        "def extract_voice_summary(text):\n"
        "    sentences = re.split(r'(?<=[.!?।])\\s+', text.strip())\n"
        "    summary = ' '.join(sentences[:2])\n"
        "    return summary[:250]"
    )
    story.append(Preformatted(code_m3, pre_style))
    story.append(Paragraph("<b>Why was this needed?</b><br/>"
                           "• In earlier versions, <code>gTTS</code> tried to convert the entire 1,500-character document into voice. It took <b>82 seconds</b> and froze the screen!<br/>"
                           "• By isolating the <b>first 2 actionable sentences</b> (under 250 characters), synthesis time dropped from <b>82 seconds to 2.5 seconds</b>!", body_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>4. Direct Textbook Mode (Groq Offline / Test Mode)</b>", h2_style))
    code_m4 = (
        "if force_offline:\n"
        "    # Bypasses Groq completely!\n"
        "    # Returns the direct excerpt from the FAISS vector database\n"
        "    return direct_textbook_body, 'textbook_direct'"
    )
    story.append(Preformatted(code_m4, pre_style))
    story.append(Paragraph("• When you check <code>[✔] Test Mode: Disable Groq</code>, the system bypasses the LLM and delivers the textbook excerpt directly with the purple badge <b>📚 100% Direct Textbook (Groq OFF)</b>.", body_style))

    story.append(Spacer(1, 10))

    # ================= SECTION 1 =================
    story.append(Paragraph("<b>SECTION 1: The 6 Core Concepts Explained Deeply</b>", h1_style))

    core_concepts = [
        ("1. What is RAG (Retrieval-Augmented Generation)?",
         "• <b>The Problem:</b> If you ask a standard AI (like ChatGPT) about a disease, it answers from memory. If it forgets or doesn't know, it <b>hallucinates</b> (invents believable but fake medical advice).<br/>"
         "• <b>The Solution (The 'Open-Book Exam' Analogy):</b><br/>"
         "  - Standard AI without RAG = A student writing a closed-book exam from memory. They might misremember a dosage or symptom.<br/>"
         "  - UpCharika with RAG = An open-book exam. When the patient asks a question, UpCharika first opens the medical textbook, finds the exact 2 paragraphs, and then writes the answer based <i>only</i> on those textbook pages."),

        ("2. What are Vector Embeddings?",
         "• <b>In Simple Words:</b> Computers do not understand words; they only understand numbers.<br/>"
         "• <b>The Concept:</b> An embedding model (<code>sentence-transformers/all-MiniLM-L6-v2</code>) converts a sentence into <b>384 decimal numbers</b>. These 384 numbers represent the <b>conceptual meaning</b> of the sentence.<br/>"
         "• <b>Why this is powerful (Semantic Search vs Keyword Search):</b><br/>"
         "  - Old search (Google in 1998): If you search <i>'high body temperature'</i>, it only looks for pages with the exact words 'high', 'body', 'temperature'. If the book says 'fever', it misses it!<br/>"
         "  - Embedding search (UpCharika): The model knows that <i>'high body temperature'</i> and <i>'acute fever'</i> have nearly identical numbers in 384-dimensional space. It finds the right page even if different words are used!"),

        ("3. What is Chunking & Chunk Overlap?",
         "• <b>Chunking (chunk_size=1000):</b> A 500-page medical textbook has over 1,000,000 words. You cannot feed the whole book into an embedding model at once. So, we split the book into bite-sized pieces of <b>1,000 characters each</b> (about 150 words — roughly one medical paragraph).<br/>"
         "• <b>Chunk Overlap (chunk_overlap=100):</b> What if a crucial sentence is split right down the middle across two chunks? Example: Chunk 1 ends with: <i>'For severe dehydration, oral rehydration'</i> ... and Chunk 2 starts with: <i>'salts (ORS) should be given.'</i> Without overlap, the meaning is cut in half. The 100-character overlap ensures that the end of Chunk 1 repeats at the start of Chunk 2, so no medical advice is ever severed."),

        ("4. What is FAISS and How is it Different from SQL?",
         "• <b>FAISS</b> stands for <b>Facebook AI Similarity Search</b>.<br/>"
         "• <b>Traditional Database (MySQL / PostgreSQL):</b> Searches for exact matches: <code>WHERE disease = 'jaundice'</code>. Cannot understand similarity or context.<br/>"
         "• <b>Vector Database (FAISS):</b> Searches for geometric proximity between vectors. Given a question vector Q, FAISS calculates the mathematical distance (Cosine Similarity) between Q and all textbook vectors, returning the closest matches in <b>under 20 milliseconds</b>."),

        ("5. Why Groq and What is an LPU?",
         "• Traditional AI runs on <b>GPUs</b> (Graphics Processing Units made by Nvidia). GPUs are powerful, but they take 5 to 15 seconds to generate an answer.<br/>"
         "• <b>Groq</b> invented the <b>LPU (Language Processing Unit)</b>: A chip designed specifically for sequential language generation. It generates text at <b>250–400 tokens per second</b> (sub-second response time). That is why UpCharika responds in <b>1.5 seconds</b>!"),

        ("6. Why bcrypt Password Hashing?",
         "• If a hacker steals your <code>users.json</code>, storing plain passwords (e.g. <code>password123</code>) is a critical security flaw.<br/>"
         "• Even standard SHA-256 is vulnerable to 'rainbow table' brute-force attacks.<br/>"
         "• <b>bcrypt adds a random 'Salt'</b> (random garbage characters) to every password before hashing and applies <b>12 rounds of mathematical stretching</b>. It is mathematically impossible to reverse a <code>bcrypt</code> hash back into the password.")
    ]

    for title, desc in core_concepts:
        story.append(Paragraph(f"<b>{title}</b>", h2_style))
        story.append(Paragraph(desc, body_style))

    story.append(Spacer(1, 10))

    # ================= SECTION 2 =================
    story.append(Paragraph("<b>SECTION 2: Top Most Asked Questions & Answers (Viva Prep)</b>", h1_style))

    qa_list = [
        ("Q1: 'Why did you use RAG instead of Fine-Tuning the model on medical data?'",
         "Fine-tuning changes the internal weights of a model, which requires expensive GPU training, takes days, and can still hallucinate. Moreover, if medical guidelines change, you must re-train the whole model. With RAG, the LLM stays untouched. We simply update the PDF in our vector database without any re-training. It is faster, free, zero-GPU, and 100% verifiable because we can see the exact textbook source."),

        ("Q2: 'What is the difference between an Embedding Model and an LLM?'",
         "They have two completely different jobs: 1. The <b>Embedding Model</b> (all-MiniLM-L6-v2) is a <b>Search Engine</b>. It converts text into 384 numbers so we can find relevant textbook paragraphs. It cannot write or speak. 2. The <b>LLM</b> (Groq / Qwen / LLaMA) is a <b>Writer / Brain</b>. It reads the retrieved textbook paragraphs and writes a fluent, conversational clinical answer in English, Marathi, or Hindi."),

        ("Q3: 'What mathematical metric does FAISS use to find similar vectors?'",
         "FAISS measures similarity using either <b>Cosine Similarity</b> (the angle between two vectors) or <b>L2 Euclidean Distance</b> (the straight-line distance between two points in 384-dimensional space). The smaller the distance or the closer the cosine angle is to 1, the more medically relevant that textbook passage is."),

        ("Q4: 'What is temperature=0.3 in your Groq API call?'",
         "Temperature controls the creativity vs. determinism of the AI: • A high temperature (0.8 to 1.0) makes the AI creative and unpredictable (good for poetry or story writing). • A low temperature (0.1 to 0.3) makes the AI strict, factual, and cautious. In medical healthcare, we set temperature=0.3 so the model stays strictly grounded in verified facts and does not take creative risks."),

        ("Q5: 'How did you solve the voice generation delay (gTTS lag)?'",
         "Initially, Google Text-to-Speech was trying to synthesize the entire 1,500-character clinical diagnosis into audio, which caused an 82-second freeze. I created an intelligent extraction algorithm (extract_voice_summary) that extracts only the first 2 primary clinical sentences (under 250 characters). This reduced voice synthesis time from <b>82 seconds down to 2.5 seconds</b>."),

        ("Q6: 'How do you prove that an answer came from your textbook and not from Groq's general training?'",
         "We implemented a <b>Test Mode Switch</b> in the sidebar (Test Mode: Disable Groq). When enabled, it turns off Groq completely. The system executes the FAISS vector search alone and displays the raw medical textbook excerpt with a purple badge: <b>📚 100% Direct Textbook (Groq OFF)</b>. When Test Mode is turned off, Groq refines that exact text with the blue badge: <b>📖 Medical Textbook Grounded + Groq AI</b>."),

        ("Q7: 'What happens if the internet goes down or Groq API is unavailable?'",
         "UpCharika has a <b>3-tier fault tolerance system</b>: 1. If Groq is active -> True RAG (Textbook + LLM). 2. If Groq fails but textbook has the topic -> Direct Textbook Retrieval. 3. If offline and asking about common symptoms (fever, headache, diabetes, acidity) -> Instant Offline Knowledge Base in English, Marathi, and Hindi."),

        ("Q8: 'How does the Multilingual Translation work?'",
         "UpCharika uses a hybrid approach: • For common clinical conditions, we have pre-translated native Devanagari clinical triage cards in Marathi and Hindi (zero latency). • For open-ended questions, Groq generates the response directly in native Marathi/Hindi using specialized Devanagari system prompts. • As a fallback, deep-translator (Google Translator engine) re-translates dynamically if the user toggles the sidebar language.")
    ]

    for q, a in qa_list:
        story.append(Paragraph(f"<b>{q}</b>", h3_style))
        story.append(Paragraph(f"<b>Your Answer:</b><br/><i>\"{a}\"</i>", body_style))
        story.append(Spacer(1, 3))

    # Build the PDF
    doc.build(story, canvasmaker=CustomNumberedCanvas)
    print(f"Generated PDF successfully: {pdf_filename}")

if __name__ == "__main__":
    build_pdf()
