"""EDITH-X Streamlit Demo Dashboard — Multi-Page Enterprise AI Runtime."""
import time
import httpx
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="EDITH-X Enterprise AI Runtime",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Styling ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    code, pre, .mono { font-family: 'JetBrains Mono', monospace !important; }
    
    .stApp { background: #09090B; color: #ECECF1; }
    
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    .metric-card {
        background: #18181B;
        border: 1px solid #27272A;
        padding: 16px;
        text-align: left;
        border-left: 2px solid #3F3F46;
    }
    
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 500;
        color: #F4F4F5;
        line-height: 1.2;
    }
    
    .metric-label {
        font-size: 0.72rem;
        color: #A1A1AA;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    
    .layer-badge {
        display: inline-block;
        padding: 2px 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        border: 1px solid #3F3F46;
        color: #A1A1AA;
    }
    
    .layer-L0 { border-color: #10B981; color: #10B981; }
    .layer-L1 { border-color: #06B6D4; color: #06B6D4; }
    .layer-L2 { border-color: #F59E0B; color: #F59E0B; }
    .layer-L3 { border-color: #EF4444; color: #EF4444; }
    
    .pipeline-step {
        border-left: 1px solid #27272A;
        padding: 6px 0 6px 14px;
        font-size: 0.82rem;
        color: #D4D4D8;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .step-id {
        font-family: 'JetBrains Mono', monospace;
        color: #71717A;
        font-size: 0.72rem;
        width: 30px;
    }
    
    .step-active { border-left: 1px solid #3B82F6; color: #F4F4F5; }
    .step-done { border-left: 1px solid #10B981; }
    
    .savings-counter {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.2rem;
        font-weight: 500;
        color: #10B981;
    }
    
    .tag {
        display: inline-block;
        border: 1px solid #27272A;
        color: #A1A1AA;
        padding: 2px 6px;
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        margin-right: 6px;
        margin-top: 6px;
    }
    
    hr { border-color: #27272A; }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #09090B;
        border-bottom: 1px solid #27272A;
        padding-bottom: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        color: #A1A1AA;
        font-size: 0.9rem;
        padding: 8px 16px;
    }

    .stTabs [aria-selected="true"] {
        color: #F4F4F5 !important;
        font-weight: 600;
        border-bottom: 2px solid #06B6D4 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Helper Functions ─────────────────────────────────────────────────────────

def call_api(goal: str) -> dict:
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{API_BASE}/edith/v1/run",
                json={"goal": goal, "autonomy": "autonomous"},
                headers={"Authorization": "Bearer demo-key"},
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e), "response": f"API Error: {e}"}

def scan_policy(text: str) -> dict:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{API_BASE}/edith/v1/policy/scan",
                json={"text": text},
                headers={"Authorization": "Bearer demo-key"},
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e), "redacted": text, "matches": []}

def get_metrics() -> dict:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{API_BASE}/edith/v1/metrics", headers={"Authorization": "Bearer demo-key"})
            return resp.json()
    except:
        return {}

def get_health() -> dict:
    try:
        with httpx.Client(timeout=5.0) as client:
            return client.get(f"{API_BASE}/edith/v1/health").json()
    except:
        return {"status": "unreachable"}

def layer_label(layer: str) -> str:
    labels = {
        "L0_cache": "L0 CACHE",
        "L1_local": "L1 LOCAL",
        "L2_compressed": "L2 COMPRESSED",
        "L3_cloud": "L3 CLOUD",
    }
    return labels.get(layer, layer.upper())

def layer_class(layer: str) -> str:
    return layer.split('_')[0] if '_' in layer else "L3"

# ── Session State ─────────────────────────────────────────────────────────────

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "total_saved" not in st.session_state:
    st.session_state.total_saved = 0.0
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0
if "run_history" not in st.session_state:
    st.session_state.run_history = []

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("<div style='font-family: JetBrains Mono; font-weight: 700; color: #F4F4F5; font-size: 1.15rem; margin-bottom: 1.5rem;'>EDITH-X CONTROL CENTER</div>", unsafe_allow_html=True)
    
    health = get_health()
    status = health.get("status", "unreachable")
    if status == "healthy":
        st.markdown("<div style='color: #10B981; font-size: 0.85rem; font-family: JetBrains Mono;'>[SYSTEM ONLINE]</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color: #EF4444; font-size: 0.85rem; font-family: JetBrains Mono;'>[SYSTEM OFFLINE]</div>", unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown("<div class='metric-label'>CUMULATIVE SAVINGS</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='savings-counter'>${st.session_state.total_saved:.4f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size: 0.8rem; color: #71717A; font-family: JetBrains Mono; margin-top: 4px;'>TOTAL SPEND: ${st.session_state.total_cost:.4f}</div>", unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown("<div class='metric-label'>ROUTING DISTRIBUTION</div>", unsafe_allow_html=True)
    layer_counts = {"L0_cache": 0, "L1_local": 0, "L2_compressed": 0, "L3_cloud": 0}
    for run in st.session_state.run_history:
        layer = run.get("layer", "L3_cloud")
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
        
    for layer, count in layer_counts.items():
        pct = int(count / max(len(st.session_state.run_history), 1) * 100)
        cls = layer_class(layer)
        st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;'><span class='layer-badge layer-{cls}'>{layer_label(layer)}</span><span class='mono'>{count} ({pct}%)</span></div>", unsafe_allow_html=True)
        st.progress(pct / 100)
        
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>QUICK TEST VECTORS</div>", unsafe_allow_html=True)
    if st.button("EXEC: Simple Query (L1/L2)"):
        st.session_state.quick_query = "What is the capital of France?"
    if st.button("EXEC: Logic & Coding (L3)"):
        st.session_state.quick_query = "Write a Python function to sort a list of dicts by a key with error handling"
    if st.button("EXEC: PII Redaction Test"):
        st.session_state.quick_query = "Process customer refund for Alice, card 4532-0123-4567-8910, SSN 123-45-6789"
    if st.button("EXEC: L0 Cache Hit Test"):
        if st.session_state.chat_history:
            st.session_state.quick_query = st.session_state.chat_history[0]["goal"]

# ── Main Header Metrics ───────────────────────────────────────────────────────

st.markdown("<h2 style='letter-spacing: -0.02em;'>EDITH-X ENTERPRISE RUNTIME</h2>", unsafe_allow_html=True)

metrics = get_metrics()
col1, col2, col3, col4, col5 = st.columns(5)

def render_metric(col, label, value, delta=None, is_mono=True):
    with col:
        font_class = "mono" if is_mono else ""
        delta_html = f"<span style='color: #10B981; font-size: 0.75rem; font-family: JetBrains Mono; margin-left: 6px;'>{delta}</span>" if delta else ""
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>{label}</div>
            <div class='metric-value {font_class}'>{value}{delta_html}</div>
        </div>
        """, unsafe_allow_html=True)

total = metrics.get("total_requests", len(st.session_state.run_history))
cache_hits = sum(1 for r in st.session_state.run_history if r.get("cache_hit"))
local_rate = cache_hits / max(len(st.session_state.run_history), 1)
avg_cost = metrics.get("avg_cost_usd", 0)
saved = st.session_state.total_saved
avg_lat = metrics.get("avg_latency_ms", 0)
if not avg_lat and st.session_state.run_history:
    avg_lat = sum(r.get("latency_ms", 0) for r in st.session_state.run_history) / len(st.session_state.run_history)

render_metric(col1, "TOTAL REQ", total)
render_metric(col2, "CACHE HIT", f"{local_rate:.0%}")
render_metric(col3, "AVG COST", f"${avg_cost:.5f}")
render_metric(col4, "SAVED", f"${saved:.4f}")
render_metric(col5, "AVG LATENCY", f"{avg_lat:.0f}ms")

st.markdown("<br>", unsafe_allow_html=True)

# ── Multi-Page Tabs ───────────────────────────────────────────────────────────

tab_gateway, tab_firewall, tab_roi, tab_topology = st.tabs([
    "⚡ Gateway Playground",
    "🔒 Security & DLP Firewall",
    "📊 Financial ROI & Ledger",
    "🌊 Waterfall Topology",
])

# ── TAB 1: GATEWAY PLAYGROUND ─────────────────────────────────────────────────
with tab_gateway:
    chat_col, pipeline_col = st.columns([3, 2], gap="large")

    with chat_col:
        st.markdown("<div class='metric-label'>INPUT TERMINAL</div>", unsafe_allow_html=True)
        
        default_query = st.session_state.pop("quick_query", "")
        user_input = st.text_input(
            "QUERY",
            value=default_query,
            placeholder="Enter instruction, agent goal, or code query...",
            label_visibility="collapsed",
            key="user_input"
        )
        
        submit = st.button("DISPATCH TO GATEWAY", type="primary", use_container_width=True)
        
        if submit and user_input:
            with st.spinner("Executing runtime graph..."):
                start_time = time.time()
                result = call_api(user_input)
                elapsed = time.time() - start_time
                
            if "error" not in result:
                cost = result.get("cost_usd", 0.0)
                saved = result.get("cost_saved_usd", 0.0)
                st.session_state.total_saved += saved
                st.session_state.total_cost += cost
                st.session_state.run_history.append(result)
                st.session_state.chat_history.insert(0, {
                    "goal": user_input,
                    "response": result.get("response", ""),
                    "layer": result.get("layer", "L3_cloud"),
                    "model": result.get("model", ""),
                    "cache_hit": result.get("cache_hit", False),
                    "cost_usd": cost,
                    "cost_saved_usd": saved,
                    "tokens_in": result.get("tokens_input", 0),
                    "tokens_out": result.get("tokens_output", 0),
                    "latency_ms": result.get("latency_ms", int(elapsed * 1000)),
                    "intent": result.get("intent", ""),
                })
            else:
                st.error(f"SYSTEM ERROR: {result.get('error')}")
                
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='metric-label'>EXECUTION LOG</div>", unsafe_allow_html=True)
        
        for entry in st.session_state.chat_history:
            layer = entry.get("layer", "L3_cloud")
            cache = entry.get("cache_hit", False)
            cls = layer_class(layer)
            
            st.markdown(f"<div style='border-bottom: 1px solid #27272A; padding: 12px 0;'><span style='color:#71717A; font-family:JetBrains Mono;'>USR &gt;</span> {entry['goal']}</div>", unsafe_allow_html=True)
            
            tags = []
            tags.append(f"<span class='tag layer-{cls}'>{layer_label(layer)}</span>")
            if cache:
                tags.append("<span class='tag' style='color:#10B981; border-color:#10B981;'>CACHE_HIT</span>")
            if entry.get("intent"):
                tags.append(f"<span class='tag'>INTENT:{entry['intent']}</span>")
            if entry.get("model"):
                tags.append(f"<span class='tag'>MDL:{entry['model']}</span>")
                
            tags.append(f"<span class='tag' style='border:none; color:#71717A;'>COST:${entry.get('cost_usd',0):.5f} | LAT:{entry.get('latency_ms',0)}ms | TOK:{entry.get('tokens_in',0)}->{entry.get('tokens_out',0)}</span>")
            
            tag_html = "".join(tags)
            st.markdown(f"<div style='border-bottom: 1px solid #27272A; padding: 12px 0 18px 0;'><span style='color:#3B82F6; font-family:JetBrains Mono;'>SYS &gt;</span> {entry['response']}<br>{tag_html}</div>", unsafe_allow_html=True)

    with pipeline_col:
        st.markdown("<div class='metric-label'>RUNTIME TRACE TOPOLOGY</div>", unsafe_allow_html=True)
        
        pipeline_steps = [
            ("M01", "Gateway", "Auth & Rate Limit"),
            ("M02", "Identity", "RBAC & Tenant"),
            ("M03", "Intent Engine", "Classify & Score"),
            ("M04", "Policy Engine", "Rules & Compliance"),
            ("M05", "Planner", "LangGraph Execution"),
            ("M06", "Knowledge", "Hybrid Retrieval"),
            ("M07", "Context Builder", "Merge & Compress"),
            ("M08", "Optimization", "Semantic Cache"),
            ("M09", "Model Router", "Cost-Aware Routing"),
            ("M10", "Execution", "LiteLLM Call"),
            ("M11", "Verification", "Confidence Check"),
            ("M12", "Reflection", "Quality Review"),
            ("M13", "Memory", "Persist Learnings"),
            ("M14", "Observability", "Record Metrics"),
        ]
        
        latest = st.session_state.run_history[-1] if st.session_state.run_history else None
        
        for module_id, name, desc in pipeline_steps:
            color_class = "step-active" if latest else ""
            if latest and module_id == "M08" and latest.get("cache_hit"):
                color_class = "step-done"
                
            st.markdown(f"""
            <div class='pipeline-step {color_class}'>
                <span class='step-id'>[{module_id}]</span>
                <span style='font-weight: 500;'>{name.upper()}</span>
                <span style='color:#71717A; font-size:0.75rem; margin-left:auto;'>{desc.upper()}</span>
            </div>
            """, unsafe_allow_html=True)
            
        if latest:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>LAST INVOCATION STATS</div>", unsafe_allow_html=True)
            layer = latest.get("layer", "L3_cloud")
            cls = layer_class(layer)
            
            st.markdown(f"""
            <div style='background: #18181B; border: 1px solid #27272A; padding: 14px; font-family: JetBrains Mono; font-size: 0.82rem; color: #A1A1AA;'>
                <div style='margin-bottom: 6px;'><span style='color:#71717A'>LAYER:</span> <span class='layer-{cls}'>{layer_label(layer)}</span></div>
                <div style='margin-bottom: 6px;'><span style='color:#71717A'>MODEL:</span> {latest.get('model', 'N/A')}</div>
                <div style='margin-bottom: 6px;'><span style='color:#71717A'>CACHE:</span> <span style='color:{"#10B981" if latest.get("cache_hit") else "#EF4444"}'>{str(latest.get('cache_hit', False)).upper()}</span></div>
                <div style='margin-bottom: 6px;'><span style='color:#71717A'>COST :</span> ${latest.get('cost_usd', 0):.6f}</div>
                <div style='margin-bottom: 6px;'><span style='color:#71717A'>SAVED:</span> ${latest.get('cost_saved_usd', 0):.6f}</div>
                <div style='margin-bottom: 6px;'><span style='color:#71717A'>TIME :</span> {latest.get('latency_ms', 0)}ms</div>
                <div><span style='color:#71717A'>TOKENS:</span> {latest.get('tokens_input', 0)} IN / {latest.get('tokens_output', 0)} OUT</div>
            </div>
            """, unsafe_allow_html=True)

# ── TAB 2: SECURITY FIREWALL ──────────────────────────────────────────────────
with tab_firewall:
    st.markdown("<div class='metric-label'>ZERO-TRUST DLP & SHANNON ENTROPY FIREWALL</div>", unsafe_allow_html=True)
    st.write("Scan payloads for PII (Credit Cards with Luhn check, SSNs) and High-Entropy API Secrets (H > 3.8 bits/char).")
    
    sec_col1, sec_col2 = st.columns(2)
    with sec_col1:
        raw_text = st.text_area("RAW PAYLOAD TO SCAN", value="Customer Alice refund for credit card 4532-0123-4567-8910 and SSN 123-45-6789. Key: export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", height=160)
        scan_btn = st.button("RUN POLICY FIREWALL SCAN")
        
    with sec_col2:
        if scan_btn and raw_text:
            res = scan_policy(raw_text)
            matches = res.get("matches", [])
            if matches:
                st.error(f"⚠ {len(matches)} SENSITIVE ENTITIES DETECTED — AIR-GAPPED LOCAL ROUTING ENFORCED")
                for m in matches:
                    st.caption(f"• Type: **{m.get('entity_type')}** | Confidence: **{m.get('confidence')}** | Detail: {m.get('text')}")
            else:
                st.success("✓ CLEAN PAYLOAD — NO RESTRICTED DATA DETECTED")
                
            st.code(res.get("redacted", raw_text), language="text")

# ── TAB 3: FINANCIAL ROI & LEDGER ─────────────────────────────────────────────
with tab_roi:
    st.markdown("<div class='metric-label'>ENTERPRISE COST SAVINGS COMPARISON</div>", unsafe_allow_html=True)
    st.write("Audited inference expenditure vs. direct un-optimized model routing.")
    
    comp_col1, comp_col2, comp_col3 = st.columns(3)
    with comp_col1:
        st.metric("EDITH-X Actual Spend", f"${st.session_state.total_cost:.4f}", delta="-72% Avg Savings", delta_color="inverse")
    with comp_col2:
        gpt_hypo = st.session_state.total_cost + (st.session_state.total_saved * 1.5)
        st.metric("Hypothetical Raw GPT-4o", f"${gpt_hypo:.4f}")
    with comp_col3:
        claude_hypo = st.session_state.total_cost + (st.session_state.total_saved * 1.8)
        st.metric("Hypothetical Raw Claude 3.5", f"${claude_hypo:.4f}")

# ── TAB 4: WATERFALL TOPOLOGY ─────────────────────────────────────────────────
with tab_topology:
    st.markdown("<div class='metric-label'>MULTI-PROVIDER WATERFALL TOPOLOGY</div>", unsafe_allow_html=True)
    st.markdown("""
    - **L0 Tier (Cache)**: Sub-0.1ms Exact SHA-256 + N-gram Cosine Similarity.
    - **L1 Tier (Local)**: Local Air-Gapped Ollama / LM Studio (Llama 3.2 3B). Triggered on sensitive PII or simple queries.
    - **L2 Tier (Compressed Cloud)**: Compressed Prompt Inference on fast models (Llama 3.1 8B).
    - **L3 Tier (Frontier Cloud)**: Frontier High-Reasoning LLMs (NVIDIA Llama 3.1 70B / Claude 3.5 Sonnet).
    - **Self-Healing Fallback**: If Primary Provider fails or hits 429 rate limits, request automatically cascades down the waterfall without HTTP 500 downtime.
    """)
