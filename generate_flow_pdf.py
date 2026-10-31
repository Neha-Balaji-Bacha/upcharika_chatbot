import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Nirmala', r'C:\Windows\Fonts\Nirmala.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', r'C:\Windows\Fonts\arialbd.ttf'))

class FlowNumberedCanvas(canvas.Canvas):
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
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "UpCharika - Complete End-to-End Project Flow | Executive Summary")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)

        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 34, text)
        self.drawString(54, 34, "UpCharika Project Flow Diagram & Technical Lifecycle")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * 72 - 54, 46)
        self.restoreState()

def build_flow_pdf(filename="UpCharika_Complete_Project_Flow.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=50,
        rightMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    c_primary = colors.HexColor("#1e3a8a")     # Deep Blue
    c_secondary = colors.HexColor("#0284c7")   # Sky Blue
    c_dark = colors.HexColor("#0f172a")        # Slate 900
    c_text = colors.HexColor("#1e293b")        # Slate 800
    c_bg_light = colors.HexColor("#f8fafc")    # Light gray
    c_border = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
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
        fontSize=13.5,
        leading=17.5,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=10.5,
        leading=14.5,
        textColor=c_secondary,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Nirmala',
        fontSize=8.5,
        leading=12.5,
        textColor=c_text,
        spaceAfter=4
    )

    pre_style = ParagraphStyle(
        'PreformattedCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=4,
        spaceAfter=6
    )

    story = []

    # Title Banner
    story.append(Paragraph("<b>UpCharika: Complete Project Flow & Lifecycle</b>", title_style))
    story.append(Paragraph("<b>Executive Summary: How Every Part of the System Works from Start to Finish</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=0, spaceAfter=8))

    # Flowchart ASCII
    flowchart_text = (
        "┌─────────────────────────────────────────────────────────────────────────────────────────────────┐\n"
        "│                          STAGE 1: OFFLINE KNOWLEDGE PREPARATION (ONE-TIME)                      │\n"
        "│  Medical PDF Books ──> PyMuPDF Extractor ──> Text Splitter (Chunk: 1000, Overlap: 100)          │\n"
        "│                      ──> sentence-transformers (384-D) ──> FAISS Vector Store (119 MB)           │\n"
        "└────────────────────────────────────────────────┬────────────────────────────────────────────────┘\n"
        "                                                 │ Pre-loaded into RAM\n"
        "                                                 ▼\n"
        "┌─────────────────────────────────────────────────────────────────────────────────────────────────┐\n"
        "│                          STAGE 2: PATIENT ONBOARDING & AUTHENTICATION                           │\n"
        "│  Patient visits App ──> Login / Register ──> bcrypt Salting & Hashing ──> users.json            │\n"
        "│                                         ──> Encrypted Cookie Session Established                │\n"
        "└────────────────────────────────────────────────┬────────────────────────────────────────────────┘\n"
        "                                                 │ Authenticated User\n"
        "                                                 ▼\n"
        "┌─────────────────────────────────────────────────────────────────────────────────────────────────┐\n"
        "│                          STAGE 3: THE LIVE CLINICAL INQUIRY & RAG PIPELINE                      │\n"
        "│  1. Patient types inquiry: 'What is jaundice and what diet should I eat?' (EN/MR/HI)            │\n"
        "│  2. Query converted to 384-D vector via all-MiniLM-L6-v2                                        │\n"
        "│  3. FAISS performs Similarity Search ──> Pulls Top 2 Verified Medical Textbook Passages         │\n"
        "│  4. System builds Augmented Prompt: 'You are UpCharika. Ground advice in this textbook: [text]' │\n"
        "│  5. Groq LPU executes fast inference (qwen/qwen3.8-27b) in 1.2s                                 │\n"
        "│     [Fallback: If Groq disabled/offline, direct textbook excerpts delivered with purple badge]   │\n"
        "└────────────────────────────────────────────────┬────────────────────────────────────────────────┘\n"
        "                                                 │ Raw Medical Answer\n"
        "                                                 ▼\n"
        "┌─────────────────────────────────────────────────────────────────────────────────────────────────┐\n"
        "│                          STAGE 4: MULTILINGUAL TRANSLATION, VOICE & UI DELIVERY                 │\n"
        "│  1. Text Translation: deep-translator converts response to Marathi/Hindi if selected             │\n"
        "│  2. Voice Summarizer: extract_voice_summary isolates first 2 sentences (<= 250 chars)           │\n"
        "│  3. Audio Synthesis: gTTS converts summary to MP3 in 2.5s (slashing legacy 82s freeze)          │\n"
        "│  4. UI Presentation: Displayed in 5 clinical cards (Cause, Solution, Medicine, Doctor, Emergency│\n"
        "│     with visual badge: [📖 Medical Textbook Grounded + Groq AI]                                 │\n"
        "└─────────────────────────────────────────────────────────────────────────────────────────────────┘"
    )
    story.append(Preformatted(flowchart_text, pre_style))
    story.append(Spacer(1, 6))

    # Stage 1 Deep Dive
    story.append(Paragraph("<b>Stage 1: Offline Knowledge Preparation (The Foundation)</b>", h1_style))
    story.append(Paragraph("Before the chatbot ever starts, the medical knowledge must be transformed into a searchable mathematical matrix. This is handled by <code>create_memory_for_llm.py</code>:", body_style))
    s1_points = [
        "<b>1. Document Extraction:</b> Uses <code>fitz</code> (PyMuPDF) to read clinical textbook PDFs page-by-page.",
        "<b>2. Intelligent Chunking:</b> Splits long text into 1,000-character segments using <code>RecursiveCharacterTextSplitter</code>. It maintains a 100-character overlap between adjacent segments so sentences are never cut in half.",
        "<b>3. Vector Embeddings:</b> Passes each chunk through <code>sentence-transformers/all-MiniLM-L6-v2</code>, converting textual meaning into 384 decimal numbers.",
        "<b>4. FAISS Indexing:</b> Saves all vectors into <code>vectorstore/db_faiss/index.faiss</code> (119 MB), enabling sub-20ms nearest-neighbor semantic search."
    ]
    for p in s1_points:
        story.append(Paragraph(f"• {p}", body_style))

    story.append(Spacer(1, 6))

    # Stage 2 Deep Dive
    story.append(Paragraph("<b>Stage 2: User Access & Clinical Security (The Gatekeeper)</b>", h1_style))
    story.append(Paragraph("Healthcare applications require secure, tamper-proof user sessions:", body_style))
    s2_points = [
        "<b>1. Salted Bcrypt Hashing:</b> When a user signs up, their password is encrypted using <code>bcrypt</code> with 12 algorithmic salt rounds. Passwords cannot be reverse-engineered even if <code>users.json</code> is accessed.",
        "<b>2. Persistent Sessions:</b> Uses <code>streamlit-cookies-manager</code> with AES encryption to store login credentials in browser cookies, keeping the patient logged in even across page reloads.",
        "<b>3. Seamless Sign Out:</b> Clicking 'Sign Out' flushes session state and clears encrypted cookies instantly."
    ]
    for p in s2_points:
        story.append(Paragraph(f"• {p}", body_style))

    story.append(Spacer(1, 6))

    # Stage 3 Deep Dive
    story.append(Paragraph("<b>Stage 3: The Live Clinical Inquiry & True RAG Pipeline (The Core Brain)</b>", h1_style))
    story.append(Paragraph("When a patient submits a question (e.g. <i>'What is jaundice and what diet should I eat?'</i>), <code>medibot.py</code> processes it through True RAG:", body_style))
    s3_points = [
        "<b>1. Vectorization:</b> The patient's query is converted into a 384-dimensional vector using the exact same MiniLM embedding model.",
        "<b>2. FAISS Similarity Search:</b> FAISS calculates Cosine Similarity across the 119 MB index and extracts the Top 2 verified textbook passages.",
        "<b>3. Prompt Augmentation:</b> The retrieved textbook paragraphs are injected into a strict system prompt instructing the LLM: <i>'Base your clinical guidance exclusively on this textbook evidence.'</i>",
        "<b>4. Ultra-Fast Groq Inference:</b> Groq LPUs run <code>qwen/qwen3.8-27b</code> (with fallback to <code>openai/gpt-oss-20b</code>) with <code>temperature=0.3</code>, delivering answers in 1.2s.",
        "<b>5. Fault Tolerance & Test Mode:</b> If Groq is disabled or offline, the system delivers direct textbook excerpts with the purple badge: <b>📚 100% Direct Textbook (Groq OFF)</b>."
    ]
    for p in s3_points:
        story.append(Paragraph(f"• {p}", body_style))

    story.append(Spacer(1, 6))

    # Stage 4 Deep Dive
    story.append(Paragraph("<b>Stage 4: Multilingual Translation, Voice & Clinical Delivery (The Output)</b>", h1_style))
    story.append(Paragraph("The generated clinical answer is converted into accessible patient triage:", body_style))
    s4_points = [
        "<b>1. Regional Translation:</b> If the patient selected Marathi or Hindi, the response is translated using native Devanagari templates or <code>deep-translator</code> (Google Engine).",
        "<b>2. Voice Synthesis Latency Optimization:</b> <code>extract_voice_summary</code> extracts the first 2 actionable sentences (<= 250 chars). <code>gTTS</code> synthesizes audio in <b>2.5 seconds</b> (eliminating the legacy 82s document freeze).",
        "<b>3. Standardized 5-Section Cards:</b> The answer is displayed in clean, color-coded clinical cards: <b>Cause</b> (Orange), <b>Solution / Diet</b> (Green), <b>Medicine</b> (Teal), <b>Doctor</b> (Purple), and <b>Emergency</b> (Red).",
        "<b>4. Visual Grounding Badges:</b> Every message displays a badge showing its exact origin: <code>📖 Medical Textbook Grounded + Groq AI</code>, <code>📚 100% Direct Textbook (Groq OFF)</code>, or <code>📋 Offline Clinical KB</code>."
    ]
    for p in s4_points:
        story.append(Paragraph(f"• {p}", body_style))

    story.append(Spacer(1, 8))

    # Summary Table
    story.append(Paragraph("<b>Summary Matrix of Project Technologies Across All 4 Stages</b>", h2_style))
    tech_matrix = [
        [Paragraph("<b>Lifecycle Stage</b>", body_style), Paragraph("<b>Components & Libraries</b>", body_style), Paragraph("<b>Exact Function in UpCharika</b>", body_style)],
        [Paragraph("<b>Stage 1: Prep</b>", body_style), Paragraph("PyMuPDF (fitz), LangChain TextSplitter, sentence-transformers, FAISS", body_style), Paragraph("Extracts PDFs, splits into 1000-char chunks (overlap 100), builds 119 MB vector index.", body_style)],
        [Paragraph("<b>Stage 2: Auth</b>", body_style), Paragraph("bcrypt, EncryptedCookieManager, users.json", body_style), Paragraph("Encrypts passwords with 12 salt rounds; maintains persistent client cookies.", body_style)],
        [Paragraph("<b>Stage 3: RAG</b>", body_style), Paragraph("FAISS search, Groq LPUs, qwen/qwen3.8-27b", body_style), Paragraph("Finds top 2 textbook paragraphs, augments prompt, generates factual clinical triage in 1.2s.", body_style)],
        [Paragraph("<b>Stage 4: Output</b>", body_style), Paragraph("deep-translator, extract_voice_summary, gTTS, Streamlit, style.css", body_style), Paragraph("Translates to Marathi/Hindi, generates 2.5s audio, renders 5-tier clinical triage cards.", body_style)]
    ]
    t_tech = Table(tech_matrix, colWidths=[90, 180, 240])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e0e7ff")),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_tech)

    doc.build(story, canvasmaker=FlowNumberedCanvas)
    print(f"Generated Project Flow PDF: {filename}")

if __name__ == "__main__":
    build_flow_pdf()
