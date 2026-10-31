import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
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
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "UpCharika - Multilingual Clinical AI Assistant | Project Study Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)

        # Footer
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 36, text)
        self.drawString(54, 36, "Confidential - Final Year Engineering Project Defense")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * 72 - 54, 48)
        self.restoreState()

def build_pdf(filename="UpCharika_Complete_Project_Study_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#1e3a8a")     # Deep Blue
    c_secondary = colors.HexColor("#0284c7")   # Sky Blue
    c_dark = colors.HexColor("#0f172a")        # Slate 900
    c_text = colors.HexColor("#334155")        # Slate 700
    c_bg_light = colors.HexColor("#f8fafc")    # Light background
    c_accent = colors.HexColor("#7c3aed")      # Purple
    c_border = colors.HexColor("#e2e8f0")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        alignment=0,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_secondary,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_secondary,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=c_text,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )

    q_style = ParagraphStyle(
        'Q_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=c_primary,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    a_style = ParagraphStyle(
        'A_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_dark,
        leftIndent=10,
        spaceAfter=8
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=c_primary
    )

    story = []

    # Title Banner
    story.append(Paragraph("UpCharika: Multilingual Clinical AI Assistant", title_style))
    story.append(Paragraph("Final Year Engineering Project Study Guide & Comprehensive Technical Manual", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=0, spaceAfter=12))

    # Meta Table
    meta_data = [
        [Paragraph("<b>Domain:</b> Healthcare AI / NLP / RAG", body_style), Paragraph("<b>Target Languages:</b> English, Marathi, Hindi", body_style)],
        [Paragraph("<b>Core Framework:</b> LangChain + FAISS + Groq LPUs", body_style), Paragraph("<b>UI Engine:</b> Streamlit + Custom CSS SaaS", body_style)],
        [Paragraph("<b>Vector Index:</b> 119 MB FAISS (Medical Textbooks)", body_style), Paragraph("<b>Voice Synthesis:</b> Latency-Optimized gTTS", body_style)],
    ]
    t_meta = Table(meta_data, colWidths=[250, 254])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # SECTION 1
    story.append(Paragraph("1. Executive Summary & Problem Statement", h1_style))
    story.append(Paragraph(
        "Modern Large Language Models (LLMs) such as ChatGPT or Claude demonstrate remarkable conversational fluency, yet they pose critical hazards when applied directly to clinical triage. Standard models frequently exhibit <b>hallucination</b>—the fabrication of plausible-sounding but medically inaccurate diagnoses and dosages. Furthermore, over 70% of semi-urban and rural patients across Maharashtra communicate primarily in regional dialects (Marathi and Hindi) and encounter steep language barriers when seeking medical guidance online.",
        body_style
    ))
    story.append(Paragraph(
        "<b>UpCharika</b> addresses these clinical and accessibility gaps by implementing a <b>True Retrieval-Augmented Generation (RAG)</b> architecture. Rather than permitting the AI to guess, UpCharika enforces mathematical similarity search across a 119 MB vectorized library of peer-reviewed clinical textbooks (FAISS), grounds the AI prompt with verifiable textbook excerpts, and produces structured 5-part triage guidance with low-latency spoken voice consultation in English, Marathi, and Hindi.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # SECTION 2
    story.append(Paragraph("2. What Makes UpCharika Unique (The 5 Key Differentiators)", h1_style))
    story.append(Paragraph("The table below contrasts standard chatbots against UpCharika across essential clinical evaluation metrics:", body_style))
    story.append(Spacer(1, 4))

    diff_data = [
        [
            Paragraph("<b>Evaluation Dimension</b>", body_style),
            Paragraph("<b>Generic Chatbots (ChatGPT / Basic Clones)</b>", body_style),
            Paragraph("<b>UpCharika (Your Project)</b>", body_style)
        ],
        [
            Paragraph("<b>Medical Accuracy</b>", body_style),
            Paragraph("Generates advice purely from internal probabilistic weights; susceptible to hallucination.", body_style),
            Paragraph("<b>Strict RAG Grounding:</b> Extracts verified paragraphs from a 119 MB textbook vectorstore before generating advice.", body_style)
        ],
        [
            Paragraph("<b>Language Accessibility</b>", body_style),
            Paragraph("Literal machine translation; frequently mistranslates clinical terms in Devanagari script.", body_style),
            Paragraph("<b>Native Devanagari Triage:</b> Dedicated Marathi (मराठी) and Hindi (हिन्दी) triage cards and multi-tier translation fallback.", body_style)
        ],
        [
            Paragraph("<b>Spoken Voice Latency</b>", body_style),
            Paragraph("Text only, or synthesizes entire documents causing an unacceptable 60–90s freeze.", body_style),
            Paragraph("<b>Optimized Clinical Voice (2.5s):</b> <code>extract_voice_summary</code> extracts the primary 2 actionable sentences for instant audio.", body_style)
        ],
        [
            Paragraph("<b>Clinical Structure</b>", body_style),
            Paragraph("Unstructured wall of text; patient struggles to locate urgent emergency warnings.", body_style),
            Paragraph("<b>Standardized 5-Section Protocol:</b> Cause, Solution, Medicine, When to See Doctor, and Emergency Red Flags.", body_style)
        ],
        [
            Paragraph("<b>Offline Resilience & Viva Proof</b>", body_style),
            Paragraph("Fails completely if cloud API expires or network connection drops.", body_style),
            Paragraph("<b>Test Mode & Direct FAISS Extraction:</b> Functions even without Groq, verifiable via the purple 'Direct Textbook' badge.", body_style)
        ]
    ]
    t_diff = Table(diff_data, colWidths=[110, 194, 200])
    t_diff.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e0e7ff")),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_diff)
    story.append(Spacer(1, 14))

    # SECTION 3
    story.append(Paragraph("3. End-to-End System Architecture & Data Flow", h1_style))
    story.append(Paragraph("When an authenticated patient inputs an inquiry (e.g. <i>'What is jaundice and what diet should I eat?'</i>), the system executes the following 6 sequential steps:", body_style))
    
    steps = [
        "<b>Step 1: Session & Authentication Gate:</b> <code>medibot.py</code> verifies user session authenticity using salted <code>bcrypt</code> hashes and <code>EncryptedCookieManager</code>.",
        "<b>Step 2: Dense Semantic Embedding (384-D):</b> The user query is converted into a 384-dimensional dense numerical vector using <code>sentence-transformers/all-MiniLM-L6-v2</code>.",
        "<b>Step 3: FAISS Similarity Search (Top-K):</b> The query vector searches through <code>vectorstore/db_faiss/index.faiss</code> (119 MB) in under 20ms using Cosine/Euclidean distance, extracting the top 2 textbook passages.",
        "<b>Step 4: Augmented Prompt Construction:</b> The retrieved context is enclosed inside a strict system prompt instructing the LLM to ground all findings exclusively in the verified textbook literature.",
        "<b>Step 5: High-Speed LLM Inference (Groq LPUs):</b> Groq's Language Processing Units execute model inference (<code>qwen/qwen3.8-27b</code> / <code>gpt-oss-20b</code>) with <code>temperature=0.3</code>, outputting clean triage text.",
        "<b>Step 6: Voice Synthesis & UI Rendering:</b> <code>extract_voice_summary</code> creates a 2-sentence summary synthesized by <code>gTTS</code> into MP3 audio in 2.5s, while the card displays the verified source badge."
    ]
    for s in steps:
        story.append(Paragraph(f"• {s}", bullet_style))

    story.append(Spacer(1, 14))

    # SECTION 4
    story.append(Paragraph("4. Complete File & Folder Anatomy", h1_style))
    file_data = [
        [Paragraph("<b>File / Directory</b>", body_style), Paragraph("<b>Architectural Responsibility</b>", body_style)],
        [Paragraph("<code>medibot.py</code>", body_style), Paragraph("Core runtime application. Orchestrates Streamlit UI, cookie session persistence, FAISS retrieval hooks, Groq LPU API calls, translation engine, and message rendering.", body_style)],
        [Paragraph("<code>create_memory_for_llm.py</code>", body_style), Paragraph("Offline data pipeline. Uses PyMuPDF (<code>fitz</code>) to parse medical textbook PDFs, divides text with <code>RecursiveCharacterTextSplitter</code> (chunk=1000, overlap=100), and exports FAISS index.", body_style)],
        [Paragraph("<code>vectorstore/db_faiss/</code>", body_style), Paragraph("Pre-computed 119 MB knowledge store: <code>index.faiss</code> holds the high-dimensional index tree; <code>index.pkl</code> holds chunk text strings and page metadata.", body_style)],
        [Paragraph("<code>style.css</code>", body_style), Paragraph("Custom clinical styling. Eliminates default Streamlit UI styling in favor of modern hospital SaaS components: rounded cards, color-coded borders, responsive flexboxes.", body_style)],
        [Paragraph("<code>users.json</code>", body_style), Paragraph("Credential database. Stores registered usernames mapped to cryptographically salted <code>bcrypt</code> password hashes with 12 salt rounds.", body_style)],
        [Paragraph("<code>requirements.txt</code>", body_style), Paragraph("Declares dependencies: <code>streamlit</code>, <code>groq</code>, <code>faiss-cpu</code>, <code>sentence-transformers</code>, <code>deep-translator</code>, <code>bcrypt</code>, <code>gtts</code>, <code>pypdf</code>.", body_style)],
        [Paragraph("<code>.env</code> / <code>secrets.toml</code>", body_style), Paragraph("Secure storage for private <code>GROQ_API_KEY</code>. Excluded from version control via <code>.gitignore</code>.", body_style)]
    ]
    t_file = Table(file_data, colWidths=[150, 354])
    t_file.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_file)
    story.append(Spacer(1, 14))

    # SECTION 5
    story.append(Paragraph("5. Deep Dive into Core Technical Concepts", h1_style))
    
    concepts = [
        ("Concept 1: The 'Open-Book' RAG Model",
         "A standard LLM behaves like a student writing an examination purely from memory; when unsure, it fabricates plausible answers. UpCharika's RAG architecture converts this into an open-book examination: it queries the FAISS index for relevant textbook passages, injects them into the context window, and forces the model to synthesize answers strictly from verified medical literature."),
        
        ("Concept 2: Semantic Vector Embeddings (384 Dimensions)",
         "Computers cannot parse semantic intent from raw ASCII characters. The <code>all-MiniLM-L6-v2</code> model maps sentences into a continuous 384-dimensional vector space. Phrases sharing clinical concepts (such as 'elevated body heat' and 'acute pyrexia / fever') occupy proximal coordinates, enabling accurate conceptual matching even when keywords differ."),
        
        ("Concept 3: Text Chunking & Chunk Overlap",
         "Clinical textbooks contain extensive narrative chapters that exceed transformer context windows. <code>RecursiveCharacterTextSplitter</code> partitions text into 1,000-character segments. A 100-character overlap is preserved between successive segments to guarantee that clinical directives spanning chunk boundaries (e.g., compound drug dosages) are not severed."),
        
        ("Concept 4: FAISS Vector Database vs Relational SQL",
         "Traditional relational databases (MySQL) perform exact string or index filtering (e.g. <code>WHERE symptom='fever'</code>) and cannot compute contextual proximity. FAISS constructs an inverted file index tree enabling nearest-neighbor distance computation across thousands of vectors in sub-20ms latency."),
        
        ("Concept 5: Groq LPUs vs Conventional GPUs",
         "Standard generative AI relies on GPUs (Nvidia A100/H100) which suffer from memory bandwidth bottlenecks during auto-regressive token generation. Groq's Language Processing Units (LPUs) feature high-bandwidth on-chip SRAM, yielding 250–400 tokens/sec and reducing clinical query turnaround to ~1.5 seconds."),
        
        ("Concept 6: Low-Latency Voice Optimization (gTTS)",
         "Google Text-to-Speech synthesis latency scales linearly with character volume. Transcribing full 1,500-character clinical guidance initially required 82 seconds. The <code>extract_voice_summary</code> routine extracts the first two primary clinical triage sentences (<= 250 chars), dropping generation latency to under 3 seconds."),
        
        ("Concept 7: Password Security via Salted Bcrypt",
         "User credentials stored in <code>users.json</code> utilize <code>bcrypt</code> key derivation with 12 algorithmic cost rounds. The algorithm generates a unique cryptographic salt for each entry, neutralizing rainbow-table attacks and precomputed dictionary cracking.")
    ]

    for title, desc in concepts:
        story.append(Paragraph(title, h2_style))
        story.append(Paragraph(desc, body_style))

    story.append(Spacer(1, 14))

    # SECTION 6
    story.append(Paragraph("6. Top 10 Viva Voce & Defense Questions with Model Answers", h1_style))
    story.append(Paragraph("Memorize and understand these high-frequency examiner questions for your final defense:", body_style))
    story.append(Spacer(1, 4))

    viva_qa = [
        ("Q1: Why did you choose RAG over Fine-Tuning an LLM?",
         "Fine-tuning adjusts internal neural weights, which requires extensive GPU resources, takes hours or days, risks catastrophic forgetting, and can still hallucinate. With RAG, the LLM remains frozen. We simply update the textbook PDF in our FAISS vectorstore with zero GPU re-training cost and 100% source verifiability."),

        ("Q2: What is the specific difference between your Embedding Model and the LLM?",
         "The Embedding Model (sentence-transformers/all-MiniLM-L6-v2) is a mathematical encoder: it converts text into 384 numbers for similarity search. It cannot generate text. The LLM (Groq / Qwen / LLaMA) is a generative language model: it ingests the retrieved textbook context and writes structured clinical answers."),

        ("Q3: What mathematical metric does FAISS use to identify relevant textbook passages?",
         "FAISS computes Cosine Similarity (the cosine of the angle between two normalized vectors) or L2 Euclidean Distance in 384-dimensional space. Smaller geometric distance signifies higher medical topic relevance."),

        ("Q4: Why is temperature set to 0.3 in your Groq inference parameters?",
         "Temperature controls output randomness. High values (0.8–1.0) promote creative, divergent language suited for storytelling. In medical triage, hallucinations are hazardous; a low temperature of 0.3 enforces strict, deterministic, and factual responses."),

        ("Q5: How did you solve the audio lag problem in voice consultation?",
         "By default, gTTS attempted to synthesize the entire 1,500-character diagnosis, taking 82 seconds. I engineered extract_voice_summary to isolate the first 2 primary clinical sentences (under 250 characters), reducing synthesis time down to ~2.5 seconds."),

        ("Q6: How can you prove to an examiner that an answer originated from your textbook rather than Groq's general training?",
         "We built a Test Mode toggle in the sidebar ('Test Mode: Disable Groq'). When enabled, it bypasses Groq completely and extracts the raw textbook excerpt directly from FAISS with a distinct purple badge: '100% Direct Textbook (Groq OFF)'. When turned off, Groq refines that same excerpt with the blue badge: 'Medical Textbook Grounded + Groq AI'."),

        ("Q7: What happens if internet connectivity fails or API rate limits are exceeded?",
         "UpCharika features a 3-tier fault tolerance fallback: Tier 1 executes True RAG (FAISS + Groq). Tier 2 falls back to Direct Textbook Extraction if Groq is unreachable. Tier 3 activates an offline Devanagari triage knowledge base for common emergencies."),

        ("Q8: How does your multilingual translation engine function?",
         "It uses a hybrid pipeline: common emergencies trigger native Devanagari clinical triage dictionaries (zero latency); open inquiries prompt Groq to generate native Marathi/Hindi; and deep-translator (GoogleTranslator engine) dynamically re-translates conversation history upon language switching."),

        ("Q9: Why chunk overlap is set to 100 characters instead of 0?",
         "Zero overlap can bisect critical medical guidance right down the middle across adjacent chunks (e.g. splitting a drug dosage from its contraindication). A 100-character overlap ensures contextual continuity across boundaries."),

        ("Q10: What are three immediate future directions for the UpCharika project?",
         "1. Integration with hospital Electronic Health Record (EHR) systems via HL7/FHIR standards. 2. Speech-to-Text input for voice-driven patient queries. 3. Computer Vision / OCR to read and interpret physical prescription slips and lab diagnostic reports.")
    ]

    for q, a in viva_qa:
        story.append(Paragraph(q, q_style))
        story.append(Paragraph(f"<b>Answer:</b> {a}", a_style))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generated successfully: {filename}")

if __name__ == "__main__":
    build_pdf()
