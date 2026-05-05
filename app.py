import streamlit as st
import traceback
from pathlib import Path
from datetime import datetime

from utils.config import load_config, save_config
from utils.code_reader import (
    read_pasted_code, read_single_file, read_folder,
    build_review_payload
)
from utils.ai import (
    call_ai, test_connection,
    prompt_full_review,
    prompt_security_review,
    prompt_logic_review,
    prompt_scalability_review,
    prompt_code_quality_review
)
from utils.analyzer import parse_full_review, ReviewResult
from utils.reporter import generate_markdown_report
from utils.brain import (
    init_brain_db, save_audit_to_brain, get_audit_history,
    add_test_case, get_test_cases, delete_test_case,
    add_criteria, get_criteria, delete_criteria,
    export_to_obsidian, import_from_obsidian
)

st.set_page_config(
    page_title="VibeAudit",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
:root {
    --primary: #7F77DD;
    --primary-dark: #534AB7;
    --critical: #DC2626;
    --high: #EA580C;
    --medium: #D97706;
    --low: #65A30D;
    --safe: #16A34A;
    --bg: #0F172A;
    --bg2: #1E293B;
    --bg3: #334155;
    --text: #F1F5F9;
    --text2: #CBD5E1;
    --text3: #94A3B8;
    --border: #475569;
}
.stApp { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); }
[data-testid="stSidebar"] { background: #1E293B; border-right: 1px solid #334155; }
.block-container { padding-top: 1.5rem; }
.score-circle { width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700; margin: 0 auto 8px; }
.issue-card { background: #1E293B; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; border-left: 4px solid; }
.issue-card.CRITICAL { border-left-color: #DC2626; }
.issue-card.HIGH     { border-left-color: #EA580C; }
.issue-card.MEDIUM   { border-left-color: #D97706; }
.issue-card.LOW      { border-left-color: #65A30D; }
.issue-title { font-size: 14px; font-weight: 600; color: #F1F5F9; margin-bottom: 4px; }
.issue-meta  { font-size: 12px; color: #94A3B8; margin-bottom: 8px; }
.issue-body  { font-size: 13px; color: #CBD5E1; line-height: 1.6; }
.issue-fix   { font-size: 13px; color: #9DCC24; margin-top: 8px; padding-top: 8px; border-top: 0.5px solid #475569; }
.verdict-safe    { background: rgba(22,163,74,0.1); border: 1px solid rgba(22,163,74,0.3); border-radius: 10px; padding: 14px; color: #86EFAC; }
.verdict-risky   { background: rgba(220,38,38,0.1); border: 1px solid rgba(220,38,38,0.3); border-radius: 10px; padding: 14px; color: #FCA5A5; }
.sev { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-right: 6px; }
.sev.CRITICAL { background: rgba(220,38,38,0.2); color: #FCA5A5; }
.sev.HIGH     { background: rgba(234,88,12,0.2); color: #FDBA74; }
.sev.MEDIUM   { background: rgba(217,119,6,0.2); color: #FDE68A; }
.sev.LOW      { background: rgba(101,163,13,0.2); color: #BBF7D0; }
.status-bar { background: rgba(127,119,221,0.1); border: 1px solid rgba(127,119,221,0.3); border-radius: 8px; padding: 10px 14px; font-size: 13px; color: #C7D2FE; margin-bottom: 12px; }
[data-testid="stTextArea"] textarea { background: #1E293B !important; color: #F1F5F9 !important; border: 1px solid #475569 !important; font-family: 'JetBrains Mono', 'Fira Code', monospace !important; font-size: 13px !important; border-radius: 8px !important; }
[data-testid="metric-container"] { background: #1E293B !important; border: 1px solid #334155 !important; border-radius: 10px !important; padding: 12px !important; }
</style>
""", unsafe_allow_html=True)

if "config"       not in st.session_state: st.session_state.config       = load_config()
if "result"       not in st.session_state: st.session_state.result       = None
if "code_source"  not in st.session_state: st.session_state.code_source  = ""
if "active_page"  not in st.session_state: st.session_state.active_page  = "Audit"
if "brain_init"   not in st.session_state:
    init_brain_db()
    st.session_state.brain_init = True

cfg = load_config()


def _run_audit(code_data: dict, review_type: str, config: dict):
    payload = build_review_payload(code_data)
    if not payload.strip():
        st.error("No code content found to review.")
        return

    progress = st.progress(0)
    status   = st.empty()

    try:
        status.markdown('<div class="status-bar">🔍 Sending code to AI reviewer...</div>', unsafe_allow_html=True)
        progress.progress(20)

        if review_type == "full":
            prompt = prompt_full_review(payload)
        elif review_type == "security":
            prompt = prompt_security_review(payload)
        elif review_type == "logic":
            prompt = prompt_logic_review(payload)
        elif review_type == "scale":
            prompt = prompt_scalability_review(payload)
        elif review_type == "quality":
            prompt = prompt_code_quality_review(payload)
        else:
            prompt = prompt_full_review(payload)

        status.markdown('<div class="status-bar">🤖 AI is reviewing... (this takes 20-40s)</div>', unsafe_allow_html=True)
        progress.progress(40)

        raw_output = call_ai(prompt, config)

        status.markdown('<div class="status-bar">📊 Parsing results...</div>', unsafe_allow_html=True)
        progress.progress(80)

        result = parse_full_review(raw_output)
        st.session_state.result = result

        progress.progress(100)
        status.empty()
        progress.empty()

        st.success(f"✅ Audit complete — overall score: **{result.overall_score}/100** ({result.overall_label})")

        if result.critical_count > 0:
            st.error(f"🔴 {result.critical_count} CRITICAL issue(s) found. Do NOT ship until fixed.")
        elif result.high_count > 0:
            st.warning(f"🟠 {result.high_count} HIGH severity issue(s) found. Fix before shipping.")

        st.session_state.active_page = "Results"
        st.rerun()

    except Exception as e:
        progress.empty()
        status.empty()
        st.error(f"Audit failed: {e}")
        if st.checkbox("Show technical details"):
            st.code(traceback.format_exc())


with st.sidebar:
    st.markdown("## 🔍 VibeAudit")
    st.markdown("*AI Code Reviewer*")
    st.markdown("---")

    pages = ["Audit", "Results", "History", "Brain", "Settings"]
    icons  = ["🔍", "📊", "📋", "🧠", "⚙️"]

    for icon, page in zip(icons, pages):
        active = st.session_state.active_page == page
        if st.button(
            f"{icon}  {page}",
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if active else "secondary"
        ):
            st.session_state.active_page = page
            st.rerun()

    st.markdown("---")

    provider = cfg.get("provider", "ollama")
    st.markdown(f"**Provider:** {provider.title()}")
    if provider == "ollama":
        model = cfg.get("ollama_model", "llama3")
        st.markdown(f"**Model:** {model}")
        st.markdown("*100% local")
    else:
        model_key = f"{provider}_model"
        st.markdown(f"**Model:** {cfg.get(model_key, 'default')}")

    if st.session_state.result and not st.session_state.result.error:
        r = st.session_state.result
        st.markdown("---")
        st.markdown("**Last audit**")
        score_color = "green" if r.overall_score >= 75 else "orange" if r.overall_score >= 50 else "red"
        st.markdown(f"Score: **:{score_color}[{r.overall_score}/100]**")
        if r.critical_count:
            st.markdown(f":red[{r.critical_count} critical]")


if st.session_state.active_page == "Audit":
    st.markdown("## 🔍 Code Audit")
    st.markdown("Paste your code — AI reviews it like a senior engineer would. Privately. Locally.")

    input_tab, file_tab, folder_tab = st.tabs(["📋 Paste code", "📄 Upload file", "📁 Scan folder"])

    code_data = None
    review_type = "full"

    with input_tab:
        col1, col2 = st.columns([3, 1])
        with col1:
            pasted = st.text_area(
                "Paste your code here",
                height=320,
                placeholder="# Paste any code — Python, JS, Go, Rust, SQL...",
                key="paste_input"
            )
        with col2:
            st.markdown("**Review type**")
            review_type_select = st.radio(
                "Review type",
                ["Full audit", "Security only", "Logic only", "Scale only", "Quality only"],
                key="review_type_paste",
                label_visibility="collapsed"
            )
            review_type = {
                "Full audit": "full", "Security only": "security",
                "Logic only": "logic", "Scale only": "scale", "Quality only": "quality"
            }[review_type_select]
            st.markdown("**Language** (optional)")
            lang_hint = st.text_input("Language hint", placeholder="python, js, sql...", key="lang_paste")

        if st.button("🔍 Run Audit", type="primary", use_container_width=True, key="run_paste"):
            if not pasted.strip():
                st.error("Please paste some code first.")
            else:
                code_data = read_pasted_code(pasted)
                st.session_state.code_source = f"pasted {lang_hint or 'code'} ({len(pasted.splitlines())} lines)"

    with file_tab:
        file_path = st.text_input("File path", placeholder="/Users/you/project/main.py", key="file_path_input")
        if st.button("🔍 Run Audit", type="primary", key="run_file"):
            if not file_path.strip():
                st.error("Please enter a file path.")
            else:
                try:
                    code_data = read_single_file(file_path.strip())
                    st.session_state.code_source = f"file: {Path(file_path).name}"
                    review_type = "full"
                except Exception as e:
                    st.error(f"Could not read file: {e}")

    with folder_tab:
        folder_path = st.text_input("Folder path", placeholder="/Users/you/project/src", key="folder_path_input")
        max_files = st.slider("Max files to scan", 5, 30, 10, key="max_files")
        if st.button("🔍 Scan & Audit", type="primary", key="run_folder"):
            if not folder_path.strip():
                st.error("Please enter a folder path.")
            else:
                try:
                    code_data = read_folder(folder_path.strip(), max_files)
                    st.session_state.code_source = f"folder: {Path(folder_path).name} ({len(code_data['files'])} files)"
                    review_type = "full"
                except Exception as e:
                    st.error(f"Could not read folder: {e}")

    if code_data:
        _run_audit(code_data, review_type, cfg)


elif st.session_state.active_page == "Results":
    if not st.session_state.result:
        st.info("No results yet. Go to Audit and run a review first.")
        st.stop()

    r: ReviewResult = st.session_state.result
    source = st.session_state.code_source

    st.markdown(f"## 📊 Results — {source}")

    if r.error:
        st.warning(f"Parse error: {r.error}")
        st.markdown("**Raw AI output:**")
        st.text(r.raw_output)
        st.stop()

    if st.button("💾 Save to Second Brain"):
        save_audit_to_brain(source, r, st.session_state.result.raw_output)
        st.success("Saved to Second Brain!")

    verdict_class = "verdict-safe" if r.is_safe_to_ship else "verdict-risky"
    verdict_icon  = "✅ Safe to ship" if r.is_safe_to_ship else "🚫 Do not ship yet"

    st.markdown(f"""
    <div class="{verdict_class}">
        <strong>{verdict_icon}</strong><br>
        {r.verdict or "Review complete. See issues below."}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    col1, col2, col3, col4, col5 = st.columns(5)
    cols = [col1, col2, col3, col4, col5]
    scores = [("Overall", r.overall_score), ("Security", r.security_score),
              ("Logic", r.logic_score), ("Scale", r.scale_score), ("Quality", r.quality_score)]
    for col, (label, score) in zip(cols, scores):
        with col:
            color = "#16A34A" if score >= 75 else "#D97706" if score >= 50 else "#DC2626"
            st.markdown(f"""
            <div style="text-align:center;background:#1E293B;border-radius:10px;padding:14px 8px">
                <div style="font-size:26px;font-weight:700;color:{color}">{score}</div>
                <div style="font-size:11px;color:#94A3B8;margin-top:4px">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f"""
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">
        <span class="sev CRITICAL">{r.critical_count} Critical</span>
        <span class="sev HIGH">{r.high_count} High</span>
        <span class="sev MEDIUM">{r.medium_count} Medium</span>
        <span class="sev LOW">{r.low_count} Low</span>
        <span style="font-size:12px;color:#94A3B8;margin-left:8px">{len(r.issues)} total</span>
    </div>""", unsafe_allow_html=True)

    report_md = generate_markdown_report(r, source)
    st.download_button("⬇️ Download report (.md)", data=report_md,
        file_name=f"vibeaudit_{datetime.now().strftime('%Y%m%d_%H%M')}.md", mime="text/markdown")

    st.markdown("---")
    tab_all, tab_sec, tab_logic, tab_scale, tab_quality = st.tabs([
        f"All ({len(r.issues)})", f"Security ({r.security_score})",
        f"Logic ({r.logic_score})", f"Scale ({r.scale_score})", f"Quality ({r.quality_score})"
    ])

    def _render_issues(issues, empty_msg="No issues found."):
        if not issues: st.success(empty_msg); return
        for issue in sorted(issues, key=lambda x: ["CRITICAL","HIGH","MEDIUM","LOW"].index(x.severity)):
            st.markdown(f"""
            <div class="issue-card {issue.severity}">
                <div class="issue-title">{issue.name}</div>
                <div class="issue-meta">
                    <span class="sev {issue.severity}">{issue.severity}</span>
                    📍 {issue.line_ref} · 📁 {issue.category}
                </div>
                <div class="issue-body">{issue.explanation}</div>
                <div class="issue-fix">💡 Fix: {issue.fix}</div>
            </div>""", unsafe_allow_html=True)

    with tab_all: _render_issues(r.issues, "🎉 No issues found!")
    with tab_sec: _render_issues([i for i in r.issues if i.category == "security"], "🔒 No security issues")
    with tab_logic: _render_issues([i for i in r.issues if i.category == "logic"], "✅ No logic errors")
    with tab_scale: _render_issues([i for i in r.issues if i.category == "scalability"], "⚡ No scale issues")
    with tab_quality: _render_issues([i for i in r.issues if i.category == "quality"], "✨ Quality good")

    with st.expander("View raw AI output"): st.text(r.raw_output)


elif st.session_state.active_page == "History":
    st.markdown("## 📋 Audit History")
    history = get_audit_history(20)
    if not history:
        st.info("No audits saved yet. Run an audit and save to Second Brain.")
    else:
        for audit in history:
            with st.expander(f"📁 {audit['source']} - {audit['score']}/100 - {audit['date']}"):
                st.markdown(f"**Score:** {audit['score']}/100")
                st.markdown(f"**Issues:** {audit['issue_count']}")
                st.markdown(f"**Verdict:** {audit.get('verdict', 'N/A')[:200]}...")


elif st.session_state.active_page == "Brain":
    st.markdown("## 🧠 Second Brain")
    st.markdown("Your knowledge base for audits, test cases, and criteria")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Audit History", "🧪 Test Cases", "✅ Criteria", "📦 Obsidian"])

    with tab1:
        st.markdown("### Saved Audits")
        history = get_audit_history(50)
        if not history:
            st.info("No audits saved yet")
        else:
            for audit in history:
                st.markdown(f"**{audit['source']}** - {audit['score']}/100 - {audit['date']}")

    with tab2:
        st.markdown("### Test Case Templates")
        col1, col2 = st.columns([3, 1])
        with col1:
            new_test = st.text_input("Add test case template", key="new_test")
        with col2:
            if st.button("Add", key="add_test"):
                if new_test.strip():
                    add_test_case(new_test.strip())
                    st.success("Test case added!")
                    st.rerun()
        tests = get_test_cases()
        for t in tests:
            col1, col2 = st.columns([4, 1])
            with col1: st.markdown(f"- {t['text']}")
            with col2:
                if st.button("🗑️", key=f"del_test_{t['id']}"):
                    delete_test_case(t['id'])
                    st.rerun()

    with tab3:
        st.markdown("### Custom Review Criteria")
        col1, col2 = st.columns([3, 1])
        with col1:
            new_crit = st.text_input("Add criteria", key="new_crit")
        with col2:
            if st.button("Add", key="add_crit"):
                if new_crit.strip():
                    add_criteria(new_crit.strip())
                    st.success("Criteria added!")
                    st.rerun()
        criteria = get_criteria()
        for c in criteria:
            col1, col2 = st.columns([4, 1])
            with col1: st.markdown(f"- {c['text']}")
            with col2:
                if st.button("🗑️", key=f"del_crit_{c['id']}"):
                    delete_criteria(c['id'])
                    st.rerun()

    with tab4:
        st.markdown("### Obsidian Integration")
        obsidian_path = cfg.get("obsidian_path", "")
        if not obsidian_path:
            st.warning("⚠️ Set Obsidian vault path in Settings first")
        else:
            st.success(f"📁 Vault: {obsidian_path}")
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Export to Obsidian"):
                if obsidian_path:
                    result = export_to_obsidian(obsidian_path)
                    st.success(result)
                else:
                    st.error("Set Obsidian path in Settings")
        with col2:
            if st.button("📥 Import from Obsidian"):
                if obsidian_path:
                    result = import_from_obsidian(obsidian_path)
                    st.success(result)
                else:
                    st.error("Set Obsidian path in Settings")


elif st.session_state.active_page == "Settings":
    st.markdown("## ⚙️ Settings")
    st.markdown("Your config is saved to `~/.vibeaudit/config.json`")

    st.markdown("### 🤖 AI Provider")
    provider = st.selectbox(
        "Provider",
        ["ollama", "anthropic", "openai", "kimi", "minimax"],
        index=["ollama", "anthropic", "openai", "kimi", "minimax"].index(cfg.get("provider", "ollama")),
        format_func=lambda x: {
            "ollama": "💻 Ollama (local, free)", "anthropic": "🧠 Anthropic Claude",
            "openai": "📘 OpenAI GPT-4o", "kimi": "🌙 Kimi (Moonshot)", "minimax": "🌟 MiniMax"
        }[x]
    )

    with st.form("settings_form"):
        st.markdown("---")

        ollama_model = ""
        ollama_url = "http://localhost:11434"
        kimi_model = "moonshot-v1-32k"
        openai_model = "gpt-4o"
        anthropic_model = "claude-3-5-sonnet-20241022"
        minimax_model = "abab6.5-chat"
        api_key = ""

        if provider == "ollama":
            st.markdown("#### ⚙️ Ollama Settings")
            ollama_model = st.text_input("Model name", value=cfg.get("ollama_model","llama3"),
                placeholder="llama3, deepseek-coder, codellama")
            ollama_url = st.text_input("Server URL", value=cfg.get("ollama_url","http://localhost:11434"))
            st.info("💡 Run `ollama serve` in terminal, then `ollama pull <model>`")

        elif provider == "anthropic":
            st.markdown("#### 🔑 Anthropic Settings")
            api_key = st.text_input("API Key", value=cfg.get("api_key",""), type="password",
                placeholder="sk-ant-...")
            anthropic_model = st.selectbox("Model",
                ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
                index=0)

        elif provider == "openai":
            st.markdown("#### 🔑 OpenAI Settings")
            api_key = st.text_input("API Key", value=cfg.get("api_key",""), type="password",
                placeholder="sk-...")
            openai_model = st.selectbox("Model",
                ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                index=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"].index(cfg.get("openai_model","gpt-4o")))

        elif provider == "kimi":
            st.markdown("#### 🔑 Kimi (Moonshot) Settings")
            api_key = st.text_input("API Key", value=cfg.get("api_key",""), type="password",
                placeholder="your-kimi-api-key")
            kimi_model = st.selectbox("Model",
                ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
                index=["moonshot-v1-8k","moonshot-v1-32k","moonshot-v1-128k"].index(cfg.get("kimi_model","moonshot-v1-32k")))

        elif provider == "minimax":
            st.markdown("#### 🌟 MiniMax Settings")
            api_key = st.text_input("API Key", value=cfg.get("api_key",""), type="password",
                placeholder="your-minimax-api-key")
            minimax_model = st.selectbox("Model",
                ["abab6.5-chat", "abab6.5s-chat", "abab6-chat"],
                index=["abab6.5-chat","abab6.5s-chat","abab6-chat"].index(cfg.get("minimax_model","abab6.5-chat")))

        st.markdown("---")
        st.markdown("### 📂 Storage")

        obsidian_path = st.text_input("Obsidian Vault Path",
            value=cfg.get("obsidian_path",""),
            placeholder="C:/Users/You/Documents/Obsidian/VaultName")

        reports_dir = st.text_input("Reports directory",
            value=cfg.get("reports_dir","C:/Users/JASPRIT SREE/VibeAuditReports"))

        auto_save = st.checkbox("Auto-save audits to Second Brain",
            value=cfg.get("auto_save_reports", False))

        max_file_kb = st.slider("Max file size (KB)", 100, 2000, cfg.get("max_file_size_kb",500))

        submitted = st.form_submit_button("💾 Save Settings", type="primary")
        if submitted:
            new_cfg = {
                "provider": provider,
                "api_key": api_key,
                "ollama_model": ollama_model or "llama3",
                "ollama_url": ollama_url or "http://localhost:11434",
                "kimi_model": kimi_model,
                "openai_model": openai_model,
                "anthropic_model": anthropic_model,
                "minimax_model": minimax_model,
                "auto_save_reports": auto_save,
                "reports_dir": reports_dir,
                "max_file_size_kb": max_file_kb,
                "obsidian_path": obsidian_path
            }
            save_config(new_cfg)
            cfg = load_config()
            st.success("✅ Settings saved!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🔌 Test Connection")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Test AI connection", use_container_width=True):
            with st.spinner("Testing..."):
                ok, msg = test_connection(cfg)
            if ok: st.success(f"✅ {msg}")
            else: st.error(f"❌ {msg}")
    with col2:
        if cfg.get("provider") == "ollama":
            if st.button("Check Ollama models", use_container_width=True):
                import requests as req
                try:
                    r = req.get(f"{cfg.get('ollama_url','http://localhost:11434')}/api/tags", timeout=5)
                    models = [m["name"] for m in r.json().get("models", [])]
                    st.success(f"Available: {', '.join(models) or 'none'}")
                except Exception as e:
                    st.error(f"Ollama not reachable: {e}")

    st.markdown("---")
    st.markdown("### 📦 Recommended Ollama Models")
    st.markdown("""
    | Model | Good for |
    |-------|----------|
    | `deepseek-coder` | Best code understanding |
    | `codellama` | General code review |
    | `llama3` | Balanced |
    """)
    st.code("ollama pull deepseek-coder", language="bash")


if __name__ == "__main__":
    pass