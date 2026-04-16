"""Manufacturing Intelligence Wiki — Streamlit in Snowflake App.

Architecture: SiS app connecting to MANUFACTURING_WIKI.KNOWLEDGE schema.
Connection is obtained via get_active_session() (Snowpark, no external connectors).
"""

import os
from datetime import datetime

import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

from utils.wiki_ops import (
    answer_question,
    get_ingested_docs,
    get_ingestion_log,
    get_period_labels,
    get_source_pdfs,
    get_stage_files,
    get_wiki_index,
    get_wiki_page,
    get_wiki_stats,
    ingest_all_new,
    ingest_document,
    run_lint,
    upload_pdf_to_stage,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Manufacturing Wiki",
    page_icon="🏭",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Sidebar — dark navy */
[data-testid="stSidebar"] {
    background-color: #1B3A6B;
}
[data-testid="stSidebar"] * {
    color: rgba(255, 255, 255, 0.88) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.2);
}

/* Category + lane badges */
.mwiki-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    color: white;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-right: 4px;
}
.mwiki-cat-equipment   { background-color: #2196F3; }
.mwiki-cat-maintenance { background-color: #FF9800; }
.mwiki-cat-qc          { background-color: #4CAF50; }
.mwiki-cat-safety      { background-color: #F44336; }
.mwiki-cat-production  { background-color: #9C27B0; }
.mwiki-cat-supplier    { background-color: #009688; }
.mwiki-cat-fmea        { background-color: #FFC107; color: #333 !important; }
.mwiki-cat-synthesis   { background-color: #3F51B5; }
.mwiki-cat-default     { background-color: #607D8B; }

.mwiki-lane-point     { background-color: #1E88E5; }
.mwiki-lane-synthesis { background-color: #FB8C00; }

/* Answer container */
.mwiki-answer {
    background: #f8f9fb;
    border: 1px solid #dee2e8;
    border-radius: 8px;
    padding: 16px 20px;
}

/* Small latency label */
.mwiki-latency {
    font-size: 12px;
    color: #999;
    display: inline-block;
    margin-left: 8px;
}

/* Document chain */
.mwiki-chain {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    padding: 8px 0 12px 0;
}
.mwiki-chain-node {
    background: #E3F2FD;
    border: 1px solid #90CAF9;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
    color: #1565C0;
    white-space: nowrap;
    font-family: monospace;
}
.mwiki-chain-arrow {
    color: #90CAF9;
    font-size: 15px;
    font-weight: bold;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Snowflake session ─────────────────────────────────────────────────────────
session = get_active_session()

# ── Session state defaults ────────────────────────────────────────────────────
st.session_state.setdefault("wiki_index_cache", None)
st.session_state.setdefault("ask_question_input", "")
st.session_state.setdefault("last_answer", None)
st.session_state.setdefault("last_lint", None)
st.session_state.setdefault("lint_run_time", None)
st.session_state.setdefault("selected_page_id", None)
st.session_state.setdefault("stage_files_cache", None)


# ── Badge helpers ─────────────────────────────────────────────────────────────
def _cat_badge(category: str) -> str:
    cat = (category or "").lower().strip()
    valid = {"equipment", "maintenance", "qc", "safety", "production", "supplier", "fmea", "synthesis"}
    css_cls = f"mwiki-cat-{cat}" if cat in valid else "mwiki-cat-default"
    return f'<span class="mwiki-badge {css_cls}">{category or "—"}</span>'


def _lane_badge(lane: str) -> str:
    if lane == "point_lookup":
        return '<span class="mwiki-badge mwiki-lane-point">Point Lookup</span>'
    return '<span class="mwiki-badge mwiki-lane-synthesis">Synthesis</span>'


# ── Header ────────────────────────────────────────────────────────────────────
st.title("Manufacturing Intelligence Wiki")
st.caption("Powered by Karpathy LLM-Wiki Pattern on Snowflake")

try:
    stats = get_wiki_stats(session)
except Exception as _exc:
    stats = {"total_pages": 0, "pages_by_category": {}, "total_docs": 0, "last_updated": None}
    st.error(f"Could not load stats: {_exc}")

_last_upd = stats.get("last_updated")
_last_upd_str = _last_upd.strftime("%b %d, %Y") if _last_upd else "—"

_h1, _h2, _h3, _h4 = st.columns(4)
_h1.metric("Wiki Pages", stats["total_pages"])
_h2.metric("Documents Ingested", stats["total_docs"])
_h3.metric("Categories", len(stats["pages_by_category"]))
_h4.metric("Last Updated", _last_upd_str)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_ask, tab_wiki, tab_ingest, tab_health = st.tabs(
    ["💬 Ask", "📖 Wiki", "📥 Ingest", "🔍 Wiki Health"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASK
# ══════════════════════════════════════════════════════════════════════════════
with tab_ask:
    SAMPLE_QUESTIONS = [
        "Which production line had the most downtime in the week of October 1, 2025?",
        "What was the OEE performance across all lines in Q3 2025?",
        "Which machines had Cpk below 1.33 in Q2 2025?",
        "Which parts in the February 2026 catalog are below minimum stock?",
    ]

    # Sample question chip callbacks — run before script reruns
    def _set_sample(q: str) -> None:
        st.session_state["ask_question_input"] = q

    st.caption("Try a sample question:")
    _chip_cols = st.columns(len(SAMPLE_QUESTIONS))
    for _col, _sample in zip(_chip_cols, SAMPLE_QUESTIONS):
        _col.button(
            _sample,
            key=f"chip_{hash(_sample)}",
            on_click=_set_sample,
            args=(_sample,),
        )

    st.write("")
    question_input = st.text_area(
        "Your question",
        key="ask_question_input",
        placeholder="Ask anything about your manufacturing operations...",
        height=88,
        label_visibility="collapsed",
    )

    # Layout: answer area (left, 75%) + settings panel (right, 25%)
    col_ans, col_settings = st.columns([3, 1])

    with col_settings:
        with st.container():
            st.markdown("**Settings**")
            save_to_wiki = st.checkbox(
                "Save answer to wiki",
                value=False,
                help="Persist a successful answer as a new wiki page.",
            )
            try:
                _period_labels = get_period_labels(session)
            except Exception:
                _period_labels = []
            _period_options = ["All time"] + _period_labels
            _selected_period = st.selectbox(
                "Period",
                _period_options,
                key="ask_period",
                help="Filter wiki pages to a specific reporting period.",
            )
            _period_arg = None if _selected_period == "All time" else _selected_period
            ask_btn = st.button("Ask", type="primary", key="ask_btn")

    with col_ans:
        if ask_btn:
            q = (question_input or "").strip()
            if not q:
                st.warning("Please enter a question first.")
            else:
                with st.spinner("Searching wiki and synthesising answer..."):
                    try:
                        resp = answer_question(session, q, save_to_wiki, period=_period_arg)
                        st.session_state["last_answer"] = resp
                    except Exception as exc:
                        st.error(f"Failed to get answer: {exc}")
                        st.session_state["last_answer"] = None

        response = st.session_state.get("last_answer")

        if response:
            # Lane badge + period badge + latency
            _lane = response.get("lane_used", response.get("lane", "synthesis"))
            _latency = response.get("duration_ms", response.get("latency_ms"))
            _period_used = response.get("period_used")
            _meta = _lane_badge(_lane)
            if _period_used:
                _meta += (
                    f'<span class="mwiki-badge mwiki-cat-default" '
                    f'style="background:#546E7A">{_period_used}</span>'
                )
            if _latency:
                _meta += f'<span class="mwiki-latency">{_latency:,} ms</span>'
            st.markdown(_meta, unsafe_allow_html=True)
            st.write("")
            with st.container():
                st.markdown(response.get("answer", "_No answer returned._"))

            # Source wiki pages + PDF files
            _sources = response.get("sources", response.get("citations") or [])
            if _sources:
                _page_ids = [s.get("page_id", "") for s in _sources if s.get("page_id")]
                try:
                    _pdf_map = get_source_pdfs(session, _page_ids)
                except Exception:
                    _pdf_map = {}

                with st.expander(f"Source Documents ({len(_sources)} wiki pages)"):
                    # ── Doc-chain header ──────────────────────────────────────
                    # Build a horizontal pill-chain: doc1 page2 → doc3 page4 → ...
                    _chain_nodes = []
                    for _src in _sources:
                        _pid = _src.get("page_id", "")
                        _pdfs = _pdf_map.get(_pid, [])
                        _fname = _pdfs[0].split("/")[-1] if _pdfs else "unknown.pdf"
                        _page_label = _src.get("page_label", "")
                        _node_label = _fname + (f" — {_page_label}" if _page_label else "")
                        _chain_nodes.append(
                            f'<span class="mwiki-chain-node">📄 {_node_label}</span>'
                        )
                    _arrow = ' <span class="mwiki-chain-arrow">→</span> '
                    st.markdown(
                        f'<div class="mwiki-chain">{_arrow.join(_chain_nodes)}</div>',
                        unsafe_allow_html=True,
                    )

                    # ── Per-source section cards ──────────────────────────────
                    for _src in _sources:
                        _pid = _src.get("page_id", "")
                        _ptitle = _src.get("title", _pid)
                        _cat = _src.get("category", "")
                        _snip = _src.get("snippet", "")
                        _pdfs = _pdf_map.get(_pid, [])

                        # PDF filename(s) + exact page location — prominent
                        _page_label = _src.get("page_label", "")
                        _loc = f" &nbsp;—&nbsp; **{_page_label}**" if _page_label else ""
                        if _pdfs:
                            for _pdf in _pdfs:
                                st.markdown(
                                    f"📄 **`{_pdf}`**{_loc}",
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.markdown(f"📄 _PDF source not found_{_loc}")

                        # Wiki page title + category badge
                        _badge_html = _cat_badge(_cat) if _cat else ""
                        st.markdown(
                            f"{_badge_html}&nbsp;<span style='font-size:13px'>"
                            f"{_ptitle}</span>&nbsp;"
                            f"<span style='color:#aaa;font-size:11px'>`{_pid}`</span>",
                            unsafe_allow_html=True,
                        )

                        # Section view — raw PDF passage for this page
                        if _snip:
                            st.markdown(
                                f"<div style='border-left:3px solid #1B3A6B;"
                                f"padding:6px 12px;margin:6px 0 4px 0;"
                                f"background:#f4f6fa;color:#333;font-size:12.5px;"
                                f"border-radius:0 4px 4px 0'>{_snip}</div>",
                                unsafe_allow_html=True,
                            )

                        st.divider()

        elif not ask_btn:
            if stats["total_pages"] == 0:
                st.warning(
                    "The wiki is empty. Go to the **Ingest** tab to add documents first."
                )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — WIKI
# ══════════════════════════════════════════════════════════════════════════════
with tab_wiki:
    CATEGORIES = [
        "All", "equipment", "maintenance", "qc", "safety",
        "production", "supplier", "fmea", "catalog", "synthesis",
    ]

    col_filter, col_main = st.columns([1, 3])

    with col_filter:
        with st.container():
            st.markdown("**Category**")
            selected_cat = st.radio(
                "Category filter",
                options=CATEGORIES,
                label_visibility="collapsed",
                key="wiki_cat_filter",
            )
            st.divider()
            if st.button("Refresh Index", key="wiki_refresh"):
                st.session_state["wiki_index_cache"] = None
                st.session_state["selected_page_id"] = None
                st.experimental_rerun()

    with col_main:
        # Load and cache the wiki index
        if st.session_state.get("wiki_index_cache") is None:
            try:
                st.session_state["wiki_index_cache"] = get_wiki_index(session)
            except Exception as exc:
                st.error(f"Failed to load wiki index: {exc}")
                st.session_state["wiki_index_cache"] = []

        wiki_rows: list[dict] = st.session_state.get("wiki_index_cache") or []

        # Category filter
        filtered = wiki_rows
        if selected_cat and selected_cat.lower() != "all":
            filtered = [
                r for r in wiki_rows
                if (r.get("CATEGORY") or "").lower() == selected_cat.lower()
            ]

        # Keyword search
        search_q = st.text_input(
            "Search wiki",
            placeholder="Filter by title, summary, or keyword...",
            label_visibility="collapsed",
            key="wiki_search",
        )
        if search_q:
            _sq = search_q.lower()
            filtered = [
                r for r in filtered
                if _sq in (r.get("PAGE_TITLE") or "").lower()
                or _sq in (r.get("ONE_LINE_SUMMARY") or "").lower()
                or _sq in (r.get("KEYWORDS") or "").lower()
            ]

        if not filtered:
            if wiki_rows:
                st.info("No pages match the current filter.")
            else:
                st.warning(
                    "No wiki pages found. Go to the **Ingest** tab to add documents."
                )
        else:
            # Mini stats row
            _s1, _s2, _s3 = st.columns(3)
            _s1.metric("Showing", len(filtered))
            _s2.metric("Total Pages", len(wiki_rows))
            if stats["pages_by_category"]:
                _top = max(stats["pages_by_category"], key=stats["pages_by_category"].get)
                _s3.metric(
                    "Largest Category",
                    f"{_top} ({stats['pages_by_category'][_top]})",
                )

            st.write("")

            # Build display dataframe
            _display_df = pd.DataFrame(
                [
                    {
                        "Page ID": r.get("PAGE_ID", ""),
                        "Title": r.get("PAGE_TITLE", ""),
                        "Category": r.get("CATEGORY", ""),
                        "Summary": r.get("ONE_LINE_SUMMARY", ""),
                        "Sources": r.get("SOURCE_DOC_COUNT", 0),
                        "Updated": r.get("UPDATED_AT"),
                    }
                    for r in filtered
                ]
            )

            _event = st.dataframe(
                _display_df,
            )

            # Row selection via selectbox (on_select not available in SiS)
            _page_titles = ["— select a page to view —"] + [
                r.get("PAGE_TITLE", r.get("PAGE_ID", ""))
                for r in filtered
            ]
            _sel_title = st.selectbox(
                "View page", _page_titles, key="wiki_page_select"
            )
            _sel_rows = []
            if _sel_title and _sel_title != "— select a page to view —":
                for _i, r in enumerate(filtered):
                    if r.get("PAGE_TITLE", r.get("PAGE_ID", "")) == _sel_title:
                        _sel_rows = [_i]
                        break
            if _sel_rows:
                _idx = _sel_rows[0]
                if _idx < len(filtered):
                    st.session_state["selected_page_id"] = filtered[_idx].get("PAGE_ID", "")

        # ── Full wiki page view ───────────────────────────────────────────────
        _page_id = st.session_state.get("selected_page_id")
        if _page_id:
            st.divider()
            try:
                _page = get_wiki_page(session, _page_id)
            except Exception as exc:
                st.error(f"Failed to load page '{_page_id}': {exc}")
                _page = {}

            if _page:
                _col_ttl, _col_meta = st.columns([3, 1])

                with _col_ttl:
                    st.subheader(_page.get("PAGE_TITLE", _page_id))
                    st.markdown(
                        _cat_badge(_page.get("CATEGORY", "")),
                        unsafe_allow_html=True,
                    )

                with _col_meta:
                    st.caption(f"Version: {_page.get('VERSION', '—')}")
                    _upd = _page.get("UPDATED_AT")
                    if _upd:
                        _upd_str = (
                            _upd.strftime("%b %d, %Y")
                            if hasattr(_upd, "strftime")
                            else str(_upd)
                        )
                        st.caption(f"Updated: {_upd_str}")
                    _src = _page.get("SOURCE_DOCS", "")
                    if _src:
                        st.caption(f"Source docs: {_src}")

                st.write("")
                st.markdown(_page.get("CONTENT_MD", "_No content._"))

                with st.expander("Edit raw markdown"):
                    st.code(_page.get("CONTENT_MD", ""), language="markdown")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — INGEST
# ══════════════════════════════════════════════════════════════════════════════
with tab_ingest:
    col_stage, col_log = st.columns([3, 2])

    # ── Left column: stage browser + ingest controls ──────────────────────────
    with col_stage:

        # ── Upload PDF from local machine ─────────────────────────────────────
        with st.container():
            st.markdown("**Upload PDF**")
            _uploaded = st.file_uploader(
                "Drop a PDF to upload to @MFG_STAGE",
                type=["pdf"],
                key="pdf_upload",
                label_visibility="collapsed",
            )
            if _uploaded is not None:
                _ucol1, _ucol2 = st.columns(2)
                with _ucol1:
                    _upload_ingest_btn = st.button(
                        "Upload & Ingest", type="primary", key="upload_ingest_btn"
                    )
                with _ucol2:
                    _upload_only_btn = st.button(
                        "Upload Only", key="upload_only_btn"
                    )

                if _upload_ingest_btn:
                    _ok = False
                    with st.spinner(f"Uploading {_uploaded.name}…"):
                        try:
                            upload_pdf_to_stage(session, _uploaded)
                            st.session_state["stage_files_cache"] = None
                            _ok = True
                        except Exception as exc:
                            st.error(f"Upload failed: {exc}")
                    if _ok:
                        with st.spinner(f"Parsing and compiling {_uploaded.name}…"):
                            try:
                                _res = ingest_document(session, _uploaded.name)
                                _pages = _res.get("compile", {}).get("pages_created", 0)
                                st.success(
                                    f"Done — `{_uploaded.name}` uploaded and compiled "
                                    f"into {_pages} wiki page(s)."
                                )
                                st.session_state["wiki_index_cache"] = None
                            except Exception as exc:
                                st.error(f"Ingest failed: {exc}")

                if _upload_only_btn:
                    with st.spinner(f"Uploading {_uploaded.name}…"):
                        try:
                            upload_pdf_to_stage(session, _uploaded)
                            st.success(
                                f"`{_uploaded.name}` uploaded to @MFG_STAGE. "
                                "Use Scan Stage below to ingest it when ready."
                            )
                            st.session_state["stage_files_cache"] = None
                        except Exception as exc:
                            st.error(f"Upload failed: {exc}")

        st.divider()

        # ── Stage file browser ────────────────────────────────────────────────
        with st.container():
            st.markdown("**Stage Files**")

            if st.button("Scan Stage", key="scan_stage"):
                with st.spinner("Scanning @MFG_STAGE..."):
                    try:
                        _sfiles = get_stage_files(session)
                        _idocs = get_ingested_docs(session)
                        _ingested_names = {
                            d.get("FILE_NAME", "").split("/")[-1]
                            for d in _idocs
                        }
                        for _f in _sfiles:
                            _bn = (_f.get("RELATIVE_PATH") or "").split("/")[-1]
                            _f["STATUS"] = "Ingested" if _bn in _ingested_names else "New"
                        st.session_state["stage_files_cache"] = _sfiles
                    except Exception as exc:
                        st.error(f"Failed to scan stage: {exc}")

            stage_files = st.session_state.get("stage_files_cache")

            if stage_files is None:
                st.info("Click **Scan Stage** to list available PDFs.")
            elif not stage_files:
                st.info("No PDF files found in @MFG_STAGE.")
            else:
                _new_count = sum(1 for f in stage_files if f.get("STATUS") == "New")
                _ing_count = len(stage_files) - _new_count

                _p1, _p2, _p3 = st.columns(3)
                _p1.metric("Total PDFs", len(stage_files))
                _p2.metric("New", _new_count)
                _p3.metric("Ingested", _ing_count)

                _stage_df = pd.DataFrame(
                    [
                        {
                            "Filename": (_f.get("RELATIVE_PATH") or "").split("/")[-1],
                            "Path": _f.get("RELATIVE_PATH", ""),
                            "Size (KB)": round((_f.get("SIZE") or 0) / 1024, 1),
                            "Modified": _f.get("LAST_MODIFIED"),
                            "Status": _f.get("STATUS", "Unknown"),
                        }
                        for _f in stage_files
                    ]
                )

                _file_event = st.dataframe(
                    _stage_df,
                )

                # Multi-row selection via multiselect (on_select not available in SiS)
                _all_filenames = [
                    (_f.get("RELATIVE_PATH") or "").split("/")[-1]
                    for _f in stage_files
                ]
                _sel_filenames = st.multiselect(
                    "Select files to ingest", _all_filenames, key="stage_file_select"
                )
                _selected_files = [
                    _f for _f in stage_files
                    if (_f.get("RELATIVE_PATH") or "").split("/")[-1] in _sel_filenames
                ]

                _btn1, _btn2 = st.columns(2)
                with _btn1:
                    _ingest_all_btn = st.button(
                        f"Ingest All New ({_new_count})",
                        type="primary",
                        disabled=_new_count == 0,
                        key="ingest_all_btn",
                    )
                with _btn2:
                    _ingest_sel_btn = st.button(
                        f"Ingest Selected ({len(_selected_files)})",
                        disabled=len(_selected_files) == 0,
                        key="ingest_sel_btn",
                    )

                # Ingest All New
                if _ingest_all_btn:
                    _prog = st.progress(0, text="Starting ingestion…")
                    try:
                        _result = ingest_all_new(session, limit=20)
                        _prog.progress(100, text="Ingestion complete.")
                        st.success(f"Done. Result: {_result}")
                        st.session_state["stage_files_cache"] = None
                        st.session_state["wiki_index_cache"] = None
                    except Exception as exc:
                        _prog.empty()
                        st.error(f"Ingestion failed: {exc}")

                # Ingest Selected
                if _ingest_sel_btn and _selected_files:
                    _prog = st.progress(0, text="Starting…")
                    _errors: list[str] = []
                    for _i, _f in enumerate(_selected_files):
                        _fname = (_f.get("RELATIVE_PATH") or "").split("/")[-1]
                        _prog.progress(
                            int((_i + 1) / len(_selected_files) * 100),
                            text=f"Ingesting {_fname}…",
                        )
                        try:
                            ingest_document(session, _fname)
                        except Exception as exc:
                            _errors.append(f"{_fname}: {exc}")
                    _prog.progress(100, text="Done.")
                    if _errors:
                        st.error("Some files failed:\n" + "\n".join(_errors))
                    else:
                        st.success(
                            f"Ingested {len(_selected_files)} file(s) successfully."
                        )
                    st.session_state["stage_files_cache"] = None
                    st.session_state["wiki_index_cache"] = None

    # ── Right column: ingestion log ───────────────────────────────────────────
    with col_log:
        with st.container():
            st.markdown("**Ingestion Log**")

            _lcol1, _lcol2 = st.columns(2)
            with _lcol1:
                _log_limit = st.selectbox(
                    "Show last", [20, 50, 100], index=0, key="log_limit"
                )
            with _lcol2:
                _op_filter = st.selectbox(
                    "Operation",
                    ["All", "PARSE", "COMPILE", "INGEST_ALL", "ANSWER"],
                    index=0,
                    key="log_op_filter",
                )

            if st.button("Refresh Log", key="refresh_log"):
                st.experimental_rerun()

            try:
                _log_entries = get_ingestion_log(session, limit=_log_limit)
            except Exception as exc:
                st.error(f"Failed to load log: {exc}")
                _log_entries = []

            if _op_filter and _op_filter != "All":
                _log_entries = [
                    e for e in _log_entries if e.get("OPERATION") == _op_filter
                ]

            if _log_entries:
                _today = datetime.now().date()
                _today_ops = sum(
                    1
                    for e in _log_entries
                    if e.get("PERFORMED_AT")
                    and (
                        e["PERFORMED_AT"].date()
                        if hasattr(e["PERFORMED_AT"], "date")
                        else _today
                    )
                    == _today
                )
                _err_count = sum(
                    1
                    for e in _log_entries
                    if (e.get("STATUS") or "").upper() == "ERROR"
                )

                _l1, _l2 = st.columns(2)
                _l1.metric("Today", _today_ops)
                _l2.metric("Errors", _err_count)

                _log_df = pd.DataFrame(
                    [
                        {
                            "Operation": e.get("OPERATION", ""),
                            "Doc ID": e.get("DOC_ID", ""),
                            "Detail": e.get("DETAIL", ""),
                            "Status": e.get("STATUS", ""),
                            "ms": e.get("DURATION_MS"),
                            "At": e.get("PERFORMED_AT"),
                        }
                        for e in _log_entries
                    ]
                )

                st.dataframe(
                    _log_df,
                )
            else:
                st.info("No log entries found.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — WIKI HEALTH
# ══════════════════════════════════════════════════════════════════════════════
with tab_health:
    st.info(
        "Health check reads all wiki pages and calls an LLM — takes ~30–60 seconds."
    )

    _hcol1, _hcol2 = st.columns([3, 1])

    with _hcol1:
        _run_btn = st.button(
            "Run Health Check", type="primary", key="run_lint_btn"
        )

    if _run_btn:
        with st.spinner("Running wiki health check…"):
            try:
                _report = run_lint(session)
                st.session_state["last_lint"] = _report
                st.session_state["lint_run_time"] = datetime.now()
            except Exception as exc:
                st.error(f"Health check failed: {exc}")

    _last_lint: str | None = st.session_state.get("last_lint")
    _lint_time: datetime | None = st.session_state.get("lint_run_time")

    if _last_lint:
        with _hcol2:
            _ts = (
                _lint_time.strftime("%Y%m%d_%H%M%S")
                if _lint_time
                else "report"
            )
            st.download_button(
                "Export Report",
                data=_last_lint,
                file_name=f"wiki_health_{_ts}.md",
                mime="text/markdown",
                key="export_lint",
            )

        if _lint_time:
            st.caption(f"Last run: {_lint_time.strftime('%b %d, %Y %H:%M:%S')}")

        st.divider()
        st.markdown(_last_lint)
    else:
        st.info(
            "No health check report yet. Click **Run Health Check** to start."
        )
