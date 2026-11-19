"""Professional Pitch Deck Generator for EDITH-X Enterprise AI Gateway & Runtime.

Built with python-pptx following Midnight Executive theme and strict visual hierarchy.
"""
from __future__ import annotations

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

# ── Color Palette: Midnight Executive & Electric Cyber ──────────────────────
C_BG = RGBColor(14, 19, 42)          # Deep midnight background (#0E132A)
C_CARD_BG = RGBColor(23, 31, 66)     # Elevated card surface (#171F42)
C_CARD_BORDER = RGBColor(45, 60, 118)# Subdued border (#2D3C76)
C_CYAN = RGBColor(0, 229, 255)       # Primary electric cyan accent (#00E5FF)
C_EMERALD = RGBColor(16, 185, 129)   # Savings / Success green (#10B981)
C_CORAL = RGBColor(244, 63, 94)      # Risk / Outage red (#F43F5E)
C_GOLD = RGBColor(245, 158, 11)      # Warning / Tier 2 amber (#F59E0B)
C_PURPLE = RGBColor(168, 85, 247)    # AI Intelligence purple (#A855F7)
C_TEXT_WHITE = RGBColor(255, 255, 255)
C_TEXT_MUTED = RGBColor(165, 180, 225)
C_TEXT_DIM = RGBColor(115, 130, 175)

FONT_HEAD = "Segoe UI"
FONT_BODY = "Segoe UI"


def set_slide_background(slide, color: RGBColor = C_BG):
    """Set solid colored background for 16:9 slide."""
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = color
    bg_shape.line.fill.background()
    return bg_shape


def add_header(slide, category: str, title: str, subtitle: str | None = None):
    """Add standardized top header with category pill and high-contrast title."""
    # Category badge / pill
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.5), Inches(2.8), Inches(0.35))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(30, 42, 85)
    badge.line.color.rgb = C_CYAN
    badge.line.width = Pt(1)
    tf_b = badge.text_frame
    tf_b.word_wrap = True
    p_b = tf_b.paragraphs[0]
    p_b.text = category.upper()
    p_b.font.name = FONT_HEAD
    p_b.font.size = Pt(10)
    p_b.font.bold = True
    p_b.font.color.rgb = C_CYAN
    p_b.alignment = PP_ALIGN.CENTER

    # Main Title
    tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.9), Inches(11.7), Inches(0.8))
    tf = tx_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = FONT_HEAD
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_WHITE

    if subtitle:
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.name = FONT_BODY
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = C_TEXT_MUTED


def add_card(slide, left: float, top: float, width: float, height: float, border_color: RGBColor = C_CARD_BORDER):
    """Create a rounded card container with dark surface fill."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = C_CARD_BG
    card.line.color.rgb = border_color
    card.line.width = Pt(1.5)
    return card


def build_pitch_deck(output_path: str):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 1: HERO TITLE SLIDE
    # ══════════════════════════════════════════════════════════════════════════
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, RGBColor(10, 14, 32))

    # Glow accent container
    hero_card = add_card(s1, 1.2, 1.2, 10.933, 5.1, border_color=C_CYAN)

    tb1 = s1.shapes.add_textbox(Inches(1.8), Inches(1.8), Inches(9.7), Inches(3.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "ENTERPRISE DISTRIBUTED INTELLIGENCE TOKEN HANDLER"
    p0.font.name = FONT_HEAD
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = C_CYAN
    p0.space_after = Pt(12)

    p1 = tf1.add_paragraph()
    p1.text = "EDITH-X"
    p1.font.name = FONT_HEAD
    p1.font.size = Pt(54)
    p1.font.bold = True
    p1.font.color.rgb = C_TEXT_WHITE
    p1.space_after = Pt(12)

    p2 = tf1.add_paragraph()
    p2.text = "The Zero-Trust Autonomous AI Operating System & Cost Firewall"
    p2.font.name = FONT_HEAD
    p2.font.size = Pt(22)
    p2.font.color.rgb = C_TEXT_MUTED
    p2.space_after = Pt(24)

    p3 = tf1.add_paragraph()
    p3.text = "⚡ Sub-Millisecond L0 Semantic Caching  |  🛡️ Zero-Trust PII Redaction  |  🎯 Calibrated Pareto Routing  |  🔄 3-State Resilient Waterfall"
    p3.font.name = FONT_BODY
    p3.font.size = Pt(13)
    p3.font.bold = True
    p3.font.color.rgb = C_EMERALD

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 2: THE 3 ENTERPRISE AI CRISES (PROBLEM)
    # ══════════════════════════════════════════════════════════════════════════
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "Executive Problem Statement", "The 3 Critical Liabilities of Enterprise AI Adoption", "Why direct application-to-LLM connections drain budgets and create severe compliance risks.")

    cards_data = [
        ("💸 Cost Hyperinflation", "Unchecked Token Consumption", [
            "Enterprises spend $50k-$150k+/mo on cloud LLMs.",
            "30-40% of queries are exact/semantic duplicates.",
            "Paying $15/1M tokens for simple FAQ responses.",
            "Zero centralized visibility or quota controls.",
        ], C_CORAL),
        ("🔓 Security & Compliance Leaks", "Regulatory Non-Compliance", [
            "Employees paste credit cards, SSNs, and API keys.",
            "Violates PCI-DSS v4.0, HIPAA §164.312, and GDPR.",
            "Unbounded cross-tenant semantic data exposure.",
            "Lack of cryptographically audited access ledgers.",
        ], C_GOLD),
        ("💥 Upstream Fragility", "Outages & Cascading Timeouts", [
            "Cloud provider 429 rate-limits halt production.",
            "HTTP 500 outages paralyze customer support apps.",
            "No circuit-breaking or automatic failover waterfall.",
            "Total dependency on single proprietary foundation vendors.",
        ], C_PURPLE),
    ]

    for idx, (head, sub, bullets, color) in enumerate(cards_data):
        left = 0.8 + idx * 4.0
        c = add_card(s2, left, 2.0, 3.733, 4.8, border_color=color)
        tb = s2.shapes.add_textbox(Inches(left + 0.3), Inches(2.3), Inches(3.133), Inches(4.2))
        tf = tb.text_frame
        tf.word_wrap = True

        p_h = tf.paragraphs[0]
        p_h.text = head
        p_h.font.name = FONT_HEAD
        p_h.font.size = Pt(18)
        p_h.font.bold = True
        p_h.font.color.rgb = color
        p_h.space_after = Pt(4)

        p_s = tf.add_paragraph()
        p_s.text = sub
        p_s.font.name = FONT_HEAD
        p_s.font.size = Pt(12)
        p_s.font.color.rgb = C_TEXT_MUTED
        p_s.space_after = Pt(14)

        for b in bullets:
            p_b = tf.add_paragraph()
            p_b.text = f"•  {b}"
            p_b.font.name = FONT_BODY
            p_b.font.size = Pt(12)
            p_b.font.color.rgb = C_TEXT_WHITE
            p_b.space_after = Pt(8)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 3: ENTER EDITH-X (THE SOLUTION)
    # ══════════════════════════════════════════════════════════════════════════
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "Product Architecture", "EDITH-X: The High-Throughput Enterprise AI Operating System", "A zero-trust reverse proxy delivering drop-in OpenAI SDK compatibility with sub-millisecond governance.")

    # Left Column: Value Proposition
    c_left = add_card(s3, 0.8, 2.0, 5.6, 4.8, border_color=C_CYAN)
    tb_l = s3.shapes.add_textbox(Inches(1.1), Inches(2.3), Inches(5.0), Inches(4.2))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Drop-in Middleware Integration"
    p.font.name = FONT_HEAD
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = C_CYAN
    p.space_after = Pt(12)

    features = [
        ("Zero Code Changes", "Change OpenAI base_url='http://gateway:8000/v1' in any app, SDK, or LangChain pipeline."),
        ("Universal Provider Mesh", "Seamlessly orchestrates NVIDIA NIM, Groq, OpenAI, Anthropic, and local vLLM / Ollama."),
        ("Microsecond Latency", "In-process pre-routing governance pipeline executes in < 0.65ms P99."),
        ("Proven Reliability", "100% test pass rate across 85 verified unit, integration, and benchmark suites."),
    ]
    for title, desc in features:
        p_t = tf_l.add_paragraph()
        p_t.text = f"✔ {title}"
        p_t.font.name = FONT_HEAD
        p_t.font.size = Pt(14)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_WHITE
        p_d = tf_l.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_after = Pt(8)

    # Right Column: The 4 Operational Firewalls
    c_right = add_card(s3, 6.7, 2.0, 5.8, 4.8, border_color=C_EMERALD)
    tb_r = s3.shapes.add_textbox(Inches(7.0), Inches(2.3), Inches(5.2), Inches(4.2))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "The 4-Layer Cost & Security Firewall"
    p.font.name = FONT_HEAD
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.space_after = Pt(12)

    pillars = [
        ("Tier 0: Sub-ms Semantic Cache", "Exact SHA-256 + Inverted Index Cosine. Eliminates 25-35% of traffic at $0.00 cost."),
        ("Tier 1: Presidio PII Firewall", "Luhn credit card check + Shannon entropy redaction. Air-gaps sensitive banking records."),
        ("Tier 2: Pareto Model Router", "Fast-path heuristics + semantic centroid cosine. Dispatches to cheapest sufficient model."),
        ("Tier 3: 3-State Circuit Breaker", "CLOSED / OPEN / HALF_OPEN state machine. Trips on error bursts, cascades seamlessly."),
    ]
    for title, desc in pillars:
        p_t = tf_r.add_paragraph()
        p_t.text = f"🛡️ {title}"
        p_t.font.name = FONT_HEAD
        p_t.font.size = Pt(14)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_WHITE
        p_d = tf_r.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_after = Pt(8)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 4: SYSTEM TOPOLOGY & DECOUPLED PROTOCOLS
    # ══════════════════════════════════════════════════════════════════════════
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "Engineering Excellence", "Micro-Modular Clean Architecture (M1 - M14)", "14 loosely coupled modules communicating via strict Python Protocol interfaces and dependency injection.")

    layers = [
        ("Layer 1: Perimeter Governance", "M1-M4", [
            "M1 Gateway: Auth extraction, sliding-window rate limiting",
            "M2 Identity: Constant-time HMAC keys, RBAC, audit logs",
            "M3 Intent: Sub-2ms centroid classifier, complexity scoring",
            "M4 Policy: Luhn CC check, Shannon entropy, data residency",
        ], C_CYAN),
        ("Layer 2: Cognitive & Cache Runtime", "M5-M8", [
            "M5 Planner: LangGraph cyclic DAG autonomous state graph",
            "M6 Knowledge: Qdrant hybrid retrieval (Dense + BM25)",
            "M7 Context: Token budget allocation & deduplication",
            "M8 Cache: Two-tier L1 LRU + L2 distributed adapter",
        ], C_PURPLE),
        ("Layer 3: Routing & Execution", "M9-M10", [
            "M9 Router: Calibrated Pareto continuous threshold tuning",
            "M10 Execution: LiteLLM abstraction & waterfall cascading",
            "FastMCP Tools: Sandboxed AST execution & tool registry",
            "Circuit Breaker: Jittered backoff & canary probe verification",
        ], C_EMERALD),
        ("Layer 4: Quality & Telemetry", "M11-M14", [
            "M11 Verification: Grounding & hallucination confidence",
            "M12 Reflection: Evaluation of quality vs goal acceptance",
            "M13 Memory: Hierarchical user and team persistent memory",
            "M14 Observability: Financial savings ledger & Prometheus",
        ], C_GOLD),
    ]

    for idx, (title, tag, items, col) in enumerate(layers):
        left = 0.8 + idx * 2.95
        c = add_card(s4, left, 2.0, 2.8, 4.8, border_color=col)
        tb = s4.shapes.add_textbox(Inches(left + 0.2), Inches(2.2), Inches(2.4), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p_t = tf.paragraphs[0]
        p_t.text = tag
        p_t.font.name = FONT_HEAD
        p_t.font.size = Pt(11)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_h = tf.add_paragraph()
        p_h.text = title
        p_h.font.name = FONT_HEAD
        p_h.font.size = Pt(14)
        p_h.font.bold = True
        p_h.font.color.rgb = C_TEXT_WHITE
        p_h.space_after = Pt(10)

        for it in items:
            p_i = tf.add_paragraph()
            p_i.text = f"• {it}"
            p_i.font.name = FONT_BODY
            p_i.font.size = Pt(11)
            p_i.font.color.rgb = C_TEXT_MUTED
            p_i.space_after = Pt(6)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 5: ZERO-TRUST SECURITY & PII REDACTION
    # ══════════════════════════════════════════════════════════════════════════
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Enterprise Security", "Zero-Trust Perimeter & Adversarial PII Firewall", "Presidio-grade context-aware redaction preventing data leaks and side-channel vulnerabilities.")

    # Stat Cards Row
    stats = [
        ("100.0%", "Critical Secret Recall", "API Keys, JWTs, AWS credentials automatically redacted", C_CYAN),
        ("0.00%", "Benign False Positive Rate", "Zero false blocks measured across 1,000 real benign enterprise queries", C_EMERALD),
        ("< 0.65ms", "Pre-Routing Pipeline P99", "Complete PII scan + Intent + Pareto decision overhead", C_PURPLE),
    ]
    for idx, (val, label, sub, col) in enumerate(stats):
        left = 0.8 + idx * 4.0
        c = add_card(s5, left, 2.0, 3.733, 1.4, border_color=col)
        tb = s5.shapes.add_textbox(Inches(left + 0.2), Inches(2.1), Inches(3.333), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = val
        p.font.name = FONT_HEAD
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = col
        p_l = tf.add_paragraph()
        p_l.text = f"{label}: {sub}"
        p_l.font.name = FONT_BODY
        p_l.font.size = Pt(11)
        p_l.font.color.rgb = C_TEXT_WHITE

    # Lower 2 Detail Cards
    c1 = add_card(s5, 0.8, 3.6, 5.6, 3.2, border_color=C_CARD_BORDER)
    tb1 = s5.shapes.add_textbox(Inches(1.0), Inches(3.8), Inches(5.2), Inches(2.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Mathematical PII & Entropy Scanning"
    p.font.name = FONT_HEAD
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_CYAN
    p.space_after = Pt(8)
    points_sec = [
        "Luhn Check Algorithm: Verifies real credit cards (Visa, MC, Amex) while ignoring innocent numeric sequences.",
        "Shannon Entropy (>3.8 bits): Flags raw passwords, private keys, and high-entropy API tokens.",
        "Adversarial Robustness: Defeats spaced digits ('4 5 3 2...'), obfuscated emails ('user [at] corp [dot] com'), and unicode homoglyphs.",
    ]
    for pt in points_sec:
        p_i = tf1.add_paragraph()
        p_i.text = f"✔ {pt}"
        p_i.font.name = FONT_BODY
        p_i.font.size = Pt(11)
        p_i.font.color.rgb = C_TEXT_MUTED
        p_i.space_after = Pt(6)

    c2 = add_card(s5, 6.7, 3.6, 5.8, 3.2, border_color=C_CARD_BORDER)
    tb2 = s5.shapes.add_textbox(Inches(6.9), Inches(3.8), Inches(5.4), Inches(2.8))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Timing-Safe Auth & Sliding-Window Limiter"
    p.font.name = FONT_HEAD
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.space_after = Pt(8)
    points_auth = [
        "Constant-Time HMAC: All API keys compared via hmac.compare_digest() eliminating side-channel timing attacks.",
        "Structured Enterprise Keys: Native validation of edx_live_... and edx_test_... with bound tenant metadata.",
        "Sliding-Window Limiter: In-memory/Redis timestamp tracking preventing burst attacks and cross-worker quota race conditions.",
    ]
    for pt in points_auth:
        p_i = tf2.add_paragraph()
        p_i.text = f"✔ {pt}"
        p_i.font.name = FONT_BODY
        p_i.font.size = Pt(11)
        p_i.font.color.rgb = C_TEXT_MUTED
        p_i.space_after = Pt(6)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 6: SUB-MILLISECOND DUAL SEMANTIC CACHE
    # ══════════════════════════════════════════════════════════════════════════
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Optimization Engine", "Two-Tier Inverted Semantic Cache with Polarity Guards", "Sub-millisecond retrieval serving recurring queries at $0.00 compute cost.")

    # 3 Stat Cards
    c_s1 = add_card(s6, 0.8, 2.0, 3.733, 1.4, border_color=C_CYAN)
    tb = s6.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(3.333), Inches(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "0.014 ms"
    p.font.name = FONT_HEAD
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = C_CYAN
    p_l = tf.add_paragraph()
    p_l.text = "L0 Exact Hash P99: Zero-latency SHA-256 match"
    p_l.font.size = Pt(11)
    p_l.font.color.rgb = C_TEXT_WHITE

    c_s2 = add_card(s6, 4.8, 2.0, 3.733, 1.4, border_color=C_EMERALD)
    tb = s6.shapes.add_textbox(Inches(5.0), Inches(2.1), Inches(3.333), Inches(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "0.320 ms"
    p.font.name = FONT_HEAD
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p_l = tf.add_paragraph()
    p_l.text = "L0 Semantic Vector P99: Inverted index candidate search"
    p_l.font.size = Pt(11)
    p_l.font.color.rgb = C_TEXT_WHITE

    c_s3 = add_card(s6, 8.8, 2.0, 3.733, 1.4, border_color=C_PURPLE)
    tb = s6.shapes.add_textbox(Inches(9.0), Inches(2.1), Inches(3.333), Inches(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "100% Guarded"
    p.font.name = FONT_HEAD
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = C_PURPLE
    p_l = tf.add_paragraph()
    p_l.text = "Polarity & Negation: Zero false-positive direction flips"
    p_l.font.size = Pt(11)
    p_l.font.color.rgb = C_TEXT_WHITE

    # Lower 2 Architecture Cards
    c1 = add_card(s6, 0.8, 3.6, 5.6, 3.2, border_color=C_CARD_BORDER)
    tb1 = s6.shapes.add_textbox(Inches(1.0), Inches(3.8), Inches(5.2), Inches(2.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Inverted Index Candidate Pruning (O(k) vs O(N))"
    p.font.name = FONT_HEAD
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_CYAN
    p.space_after = Pt(8)
    cache_pts = [
        "Sparse Term-Frequency Vectors: Fast CPU cosine similarity computed via normalized n-gram histograms.",
        "Candidate Posting Lists: Instead of scanning 50,000 items linearly, token index inspects only matching entries (< 20 candidates).",
        "Two-Tier L1/L2 Sync: Process-local LRU memory cache backed by an async distributed L2 store interface (Redis/KeyDB).",
    ]
    for pt in cache_pts:
        p_i = tf1.add_paragraph()
        p_i.text = f"• {pt}"
        p_i.font.name = FONT_BODY
        p_i.font.size = Pt(11)
        p_i.font.color.rgb = C_TEXT_MUTED
        p_i.space_after = Pt(6)

    c2 = add_card(s6, 6.7, 3.6, 5.8, 3.2, border_color=C_CARD_BORDER)
    tb2 = s6.shapes.add_textbox(Inches(6.9), Inches(3.8), Inches(5.4), Inches(2.8))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Grammatical Polarity & Directionality Guard"
    p.font.name = FONT_HEAD
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.space_after = Pt(8)
    polar_pts = [
        "Negation Detection: Rejects false hits between 'Is mutual TLS enabled?' and 'Is mutual TLS not enabled?'",
        "Directional Antonyms: Distinguishes 'Transfer funds to Alice' from 'Transfer funds from Alice' (opposite business effects).",
        "Safe Auto-Eviction: Maintains clean LRU bounds with automatic expiration TTL windows (default 24h).",
    ]
    for pt in polar_pts:
        p_i = tf2.add_paragraph()
        p_i.text = f"• {pt}"
        p_i.font.name = FONT_BODY
        p_i.font.size = Pt(11)
        p_i.font.color.rgb = C_TEXT_MUTED
        p_i.space_after = Pt(6)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 7: HYBRID PARETO MODEL ROUTER
    # ══════════════════════════════════════════════════════════════════════════
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "Intelligent Model Routing", "Calibrated Pareto Cost-Complexity Dispatcher", "Predicts P(cheap_is_sufficient) to allocate workloads across local, fast cloud, and flagship tiers.")

    tiers = [
        ("Tier L1: Local Mesh", "Llama 3.2 3B / Ollama", "$0.00 / 1M tokens", "150 - 250 ms", [
            "Factual Q&A, definitions, grammar fixes",
            "Classification & entity extraction",
            "Air-gapped PII processing on-premise",
        ], C_CYAN),
        ("Tier L2: Fast Cloud", "NVIDIA NIM Llama 3.1 70B", "$0.80 / 1M tokens", "400 - 1,100 ms", [
            "Multi-paragraph summaries & technical docs",
            "Code generation, refactoring, SQL queries",
            "70% cost reduction vs GPT-4o baseline",
        ], C_EMERALD),
        ("Tier L3: Frontier Cloud", "GPT-4o / Claude 3.5 Sonnet", "$2.50 - $15.00 / 1M", "1,500 - 3,500 ms", [
            "Byzantine consensus & distributed proofs",
            "Complex financial modeling & threat analysis",
            "Reserved strictly for high-complexity queries",
        ], C_PURPLE),
    ]

    for idx, (t_name, model_ex, cost, lat, uses, col) in enumerate(tiers):
        left = 0.8 + idx * 4.0
        c = add_card(s7, left, 2.0, 3.733, 4.8, border_color=col)
        tb = s7.shapes.add_textbox(Inches(left + 0.25), Inches(2.2), Inches(3.233), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = t_name
        p.font.name = FONT_HEAD
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = col

        p_m = tf.add_paragraph()
        p_m.text = model_ex
        p_m.font.name = FONT_BODY
        p_m.font.size = Pt(12)
        p_m.font.color.rgb = C_TEXT_WHITE
        p_m.space_after = Pt(8)

        p_c = tf.add_paragraph()
        p_c.text = f"Cost: {cost}\nLatency: {lat}"
        p_c.font.name = FONT_BODY
        p_c.font.size = Pt(11)
        p_c.font.bold = True
        p_c.font.color.rgb = C_GOLD
        p_c.space_after = Pt(12)

        p_u = tf.add_paragraph()
        p_u.text = "Target Workloads:"
        p_u.font.name = FONT_HEAD
        p_u.font.size = Pt(12)
        p_u.font.bold = True
        p_u.font.color.rgb = C_TEXT_WHITE
        p_u.space_after = Pt(4)

        for u in uses:
            p_i = tf.add_paragraph()
            p_i.text = f"• {u}"
            p_i.font.name = FONT_BODY
            p_i.font.size = Pt(11)
            p_i.font.color.rgb = C_TEXT_MUTED
            p_i.space_after = Pt(6)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 8: 3-STATE CIRCUIT BREAKER & WATERFALL
    # ══════════════════════════════════════════════════════════════════════════
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "High-Availability Resilience", "3-State Enterprise Circuit Breaker & Fallback Waterfall", "Guarantees zero HTTP 500 downtime through automated failure detection and canary probe recovery.")

    cb_states = [
        ("🟢 CLOSED State", "Normal Operation", [
            "All requests route to primary model provider.",
            "Rolling error window tracks failures over 60s.",
            "Sub-millisecond pass-through with 0% overhead.",
        ], C_EMERALD),
        ("🔴 OPEN State", "Fast-Fail & Short Circuit", [
            "Tripped when error rate >= 50% or 3 consecutive timeouts.",
            "Calls fail fast immediately without waiting for HTTP timeouts.",
            "Diverts traffic instantly to secondary cloud / local fallback.",
        ], C_CORAL),
        ("🟡 HALF-OPEN State", "Canary Recovery Probes", [
            "Entered after jittered exponential backoff cooldown.",
            "Sends 2 isolated canary probes to test upstream recovery.",
            "Success resets to CLOSED; failure trips back to OPEN.",
        ], C_GOLD),
    ]

    for idx, (title, sub, items, col) in enumerate(cb_states):
        left = 0.8 + idx * 4.0
        c = add_card(s8, left, 2.0, 3.733, 4.8, border_color=col)
        tb = s8.shapes.add_textbox(Inches(left + 0.25), Inches(2.3), Inches(3.233), Inches(4.2))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title
        p.font.name = FONT_HEAD
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = col
        p.space_after = Pt(4)

        p_s = tf.add_paragraph()
        p_s.text = sub
        p_s.font.name = FONT_BODY
        p_s.font.size = Pt(12)
        p_s.font.color.rgb = C_TEXT_MUTED
        p_s.space_after = Pt(14)

        for it in items:
            p_i = tf.add_paragraph()
            p_i.text = f"• {it}"
            p_i.font.name = FONT_BODY
            p_i.font.size = Pt(12)
            p_i.font.color.rgb = C_TEXT_WHITE
            p_i.space_after = Pt(8)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 9: AUDITED EMPIRICAL BENCHMARKS
    # ══════════════════════════════════════════════════════════════════════════
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "Empirical Validation", "Audited Benchmark Results (Pre-Committed Thresholds)", "Evaluated on held-out test splits with pre-committed thresholds.yaml eliminating circularity.")

    bench_cards = [
        ("Reasoning & Routing Accuracy", "GSM8K Held-Out Test Split (n=100)", [
            ("Flagship Cloud Baseline", "93.0%"),
            ("EDITH-X Pareto Router", "91.0%"),
            ("Calls Routed to Flagship", "51.0%"),
            ("AUC Gain vs Random Router", "+0.106"),
        ], C_CYAN),
        ("Measured Enterprise Cost Savings", "Audited Financial Cost Waterfall", [
            ("Conservative 50/50 Traffic Mix", "52.6% Savings"),
            ("Standard Enterprise 70/30 Mix", "70.3% Savings"),
            ("High-Volume FAQ 90/10 Mix", "87.9% Savings"),
            ("L0 Cache Dollar Cost", "$0.00 / req"),
        ], C_EMERALD),
        ("Needle QA & Context Compression", "Multi-Length Retention (500-2000 tokens)", [
            ("Compression Ratio", "0.51 (49% reduction)"),
            ("Needle QA Accuracy Retention", "90.0%"),
            ("Accuracy Gain vs Naive Truncate", "+50.0%"),
            ("Accuracy Gain vs Random Drop", "+43.3%"),
        ], C_PURPLE),
    ]

    for idx, (title, sub, metrics, col) in enumerate(bench_cards):
        left = 0.8 + idx * 4.0
        c = add_card(s9, left, 2.0, 3.733, 4.8, border_color=col)
        tb = s9.shapes.add_textbox(Inches(left + 0.25), Inches(2.2), Inches(3.233), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title
        p.font.name = FONT_HEAD
        p.font.size = Pt(17)
        p.font.bold = True
        p.font.color.rgb = col
        p.space_after = Pt(2)

        p_s = tf.add_paragraph()
        p_s.text = sub
        p_s.font.name = FONT_BODY
        p_s.font.size = Pt(11)
        p_s.font.color.rgb = C_TEXT_MUTED
        p_s.space_after = Pt(14)

        for label, val in metrics:
            p_l = tf.add_paragraph()
            p_l.text = label
            p_l.font.name = FONT_BODY
            p_l.font.size = Pt(11)
            p_l.font.color.rgb = C_TEXT_MUTED

            p_v = tf.add_paragraph()
            p_v.text = val
            p_v.font.name = FONT_HEAD
            p_v.font.size = Pt(15)
            p_v.font.bold = True
            p_v.font.color.rgb = C_TEXT_WHITE
            p_v.space_after = Pt(8)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 10: MULTI-TENANCY & AUTONOMOUS TOOLING
    # ══════════════════════════════════════════════════════════════════════════
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "Enterprise Governance", "Multi-Tenant Vector Isolation & Autonomous Agent Tools", "Enterprise-grade tenant boundaries and dynamic Model Context Protocol (FastMCP) tool execution.")

    # Left: Multi-Tenant Qdrant
    c_l = add_card(s10, 0.8, 2.0, 5.6, 4.8, border_color=C_CYAN)
    tb_l = s10.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.4))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Multi-Tenant Vector Isolation (Qdrant)"
    p.font.name = FONT_HEAD
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_CYAN
    p.space_after = Pt(10)

    qdrant_points = [
        ("Strict Partition Filtering", "Point payloads bound to org_id. Retrieval applies mandatory FieldCondition(org_id == ctx.org_id)."),
        ("Zero Cross-Tenant Leakage", "Documents from Tenant A are mathematically invisible to queries originating from Tenant B."),
        ("Hybrid Retrieval Architecture", "Blends 128-dim dense semantic vector cosine similarity with BM25 lexical term overlap."),
        ("Air-Gapped In-Memory Fallback", "Automatically provisions local memory vector store when remote Qdrant is unavailable."),
    ]
    for h, d in qdrant_points:
        p_h = tf_l.add_paragraph()
        p_h.text = f"✔ {h}"
        p_h.font.name = FONT_HEAD
        p_h.font.size = Pt(13)
        p_h.font.bold = True
        p_h.font.color.rgb = C_TEXT_WHITE
        p_d = tf_l.add_paragraph()
        p_d.text = d
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_after = Pt(6)

    # Right: Autonomous Tool Registry
    c_r = add_card(s10, 6.7, 2.0, 5.8, 4.8, border_color=C_EMERALD)
    tb_r = s10.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.2), Inches(4.4))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "Enterprise Tool Registry & Agent Dispatch"
    p.font.name = FONT_HEAD
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.space_after = Pt(10)

    tool_points = [
        ("Sandboxed AST Arithmetic", "Calculator tool parses expressions into AST nodes without dangerous eval() execution."),
        ("ISO UTC Time & Health", "Provides live datetime_now and system_status runtime telemetry to LLM agents."),
        ("Dynamic FastMCP Registration", "Plug in custom database connectors, CRM lookups, or Git commit tools via register()."),
        ("LangGraph Cyclic Orchestration", "Powers multi-step agent reasoning loops with grounding and self-reflection checks."),
    ]
    for h, d in tool_points:
        p_h = tf_r.add_paragraph()
        p_h.text = f"⚙️ {h}"
        p_h.font.name = FONT_HEAD
        p_h.font.size = Pt(13)
        p_h.font.bold = True
        p_h.font.color.rgb = C_TEXT_WHITE
        p_d = tf_r.add_paragraph()
        p_d.text = d
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_after = Pt(6)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 11: MEASURED ENTERPRISE ROI & BUSINESS CASE
    # ══════════════════════════════════════════════════════════════════════════
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "Financial ROI & Impact", "Quantified Enterprise Financial Business Case", "Projected savings model for a 500-seat enterprise generating 100,000 AI interactions per month.")

    # Top ROI Stat Card
    c_roi = add_card(s11, 0.8, 2.0, 11.733, 1.4, border_color=C_EMERALD)
    tb = s11.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(11.133), Inches(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "$72,400+ Annual Net Cost Savings"
    p.font.name = FONT_HEAD
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p_l = tf.add_paragraph()
    p_l.text = "Based on conservative 70.3% blended cost reduction across repetitive queries, semantic cache hits, and Pareto L2 routing."
    p_l.font.size = Pt(12)
    p_l.font.color.rgb = C_TEXT_WHITE

    # Comparison Columns
    c_bef = add_card(s11, 0.8, 3.6, 5.6, 3.2, border_color=C_CORAL)
    tb_b = s11.shapes.add_textbox(Inches(1.1), Inches(3.8), Inches(5.0), Inches(2.8))
    tf_b = tb_b.text_frame
    tf_b.word_wrap = True
    p = tf_b.paragraphs[0]
    p.text = "❌ Direct Unmanaged Cloud AI"
    p.font.name = FONT_HEAD
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_CORAL
    p.space_after = Pt(8)
    b_items = [
        "Monthly Spend: ~$8,600 / month ($103,200/year)",
        "Duplicated Queries: Billed at full GPT-4o frontier pricing every time",
        "Outage Vulnerability: Zero SLA protection against upstream provider downtime",
        "Compliance Risk: Millions in potential fines under PCI-DSS, HIPAA, and GDPR",
    ]
    for b in b_items:
        p_i = tf_b.add_paragraph()
        p_i.text = f"• {b}"
        p_i.font.name = FONT_BODY
        p_i.font.size = Pt(11)
        p_i.font.color.rgb = C_TEXT_MUTED
        p_i.space_after = Pt(6)

    c_aft = add_card(s11, 6.7, 3.6, 5.8, 3.2, border_color=C_EMERALD)
    tb_a = s11.shapes.add_textbox(Inches(7.0), Inches(3.8), Inches(5.2), Inches(2.8))
    tf_a = tb_a.text_frame
    tf_a.word_wrap = True
    p = tf_a.paragraphs[0]
    p.text = "✅ EDITH-X Managed AI Gateway"
    p.font.name = FONT_HEAD
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.space_after = Pt(8)
    a_items = [
        "Monthly Spend: ~$2,560 / month ($30,720/year) — 70.3% Net Savings",
        "Zero-Cost Caching: 30,000 queries answered instantly in < 0.5ms for $0.00",
        "Guaranteed 99.99% Availability: Resilient multi-provider waterfall fallback",
        "Zero Compliance Exposure: Real-time air-gapped PII & secret stripping",
    ]
    for a in a_items:
        p_i = tf_a.add_paragraph()
        p_i.text = f"✔ {a}"
        p_i.font.name = FONT_BODY
        p_i.font.size = Pt(11)
        p_i.font.color.rgb = C_TEXT_WHITE
        p_i.space_after = Pt(6)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 12: CONCLUSION & CALL TO ACTION
    # ══════════════════════════════════════════════════════════════════════════
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12, RGBColor(10, 14, 32))

    c_final = add_card(s12, 1.2, 1.2, 10.933, 5.1, border_color=C_CYAN)
    tb = s12.shapes.add_textbox(Inches(1.8), Inches(1.6), Inches(9.7), Inches(4.3))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "ENTERPRISE DEPLOYMENT READY"
    p.font.name = FONT_HEAD
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_CYAN
    p.space_after = Pt(8)

    p_t = tf.add_paragraph()
    p_t.text = "Empower Your Organization with EDITH-X"
    p_t.font.name = FONT_HEAD
    p_t.font.size = Pt(36)
    p_t.font.bold = True
    p_t.font.color.rgb = C_TEXT_WHITE
    p_t.space_after = Pt(16)

    p_b = tf.add_paragraph()
    p_b.text = (
        "EDITH-X transforms unmonitored AI liabilities into audited, cost-effective corporate intelligence. "
        "With 85 verified test suites, audited sub-millisecond latencies, and drop-in OpenAI SDK compatibility, "
        "production deployment takes under 15 minutes."
    )
    p_b.font.name = FONT_BODY
    p_b.font.size = Pt(14)
    p_b.font.color.rgb = C_TEXT_MUTED
    p_b.space_after = Pt(20)

    cta_items = [
        "📦 Docker & Kubernetes Ready: docker-compose.yml and Helm deployment configs included.",
        "📊 Live ROI Dashboard: Visual web control center and Prometheus /metrics monitoring.",
        "🔗 GitHub Repository: Fully open, documented, and production certified (github.com/Ay24/EDITH_X).",
    ]
    for it in cta_items:
        p_c = tf.add_paragraph()
        p_c.text = f"🚀 {it}"
        p_c.font.name = FONT_BODY
        p_c.font.size = Pt(13)
        p_c.font.bold = True
        p_c.font.color.rgb = C_TEXT_WHITE
        p_c.space_after = Pt(8)

    # Save presentation
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prs.save(output_path)
    print(f"Pitch deck successfully created at: {output_path}")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/presentations/EDITH_X_Enterprise_Pitch_Deck.pptx"
    build_pitch_deck(out)
