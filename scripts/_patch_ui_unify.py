#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import ast

path = Path("frontend/streamlit_app.py")
text = path.read_text(encoding="utf-8")

# --- typography + shared section system ---
old_hero_title = """    .hero-title {
      margin: 0;
      font-size: clamp(2.4rem, 5.2vw, 4.6rem);
      line-height: 0.96;
      font-weight: 800;
      letter-spacing: -0.035em;
      color: #f5f5f7;
      max-width: 14ch;
    }"""

new_hero_title = """    .hero-title {
      margin: 0;
      font-size: clamp(2rem, 3.6vw, 3.15rem);
      line-height: 1.08;
      font-weight: 780;
      letter-spacing: -0.03em;
      color: #f5f5f7;
      max-width: 18ch;
    }"""

old_page = """    .page-kicker {
      color: var(--muted); font-size: .72rem; font-weight: 650;
      letter-spacing: .04em; text-transform: uppercase; margin: .7rem 0 .3rem;
    }
    .page-title {
      margin: 0; font-size: clamp(2.4rem, 5vw, 4.6rem); font-weight: 800;
      letter-spacing: -0.03em; color: var(--ink); line-height: 0.95;
    }
    .page-copy {
      margin: .55rem 0 1.25rem; color: var(--muted); font-size: 1rem;
      line-height: 1.5; max-width: 62ch;
    }"""

new_page = """    .page-kicker {
      color: rgba(245,245,247,.62); font-size: .72rem; font-weight: 650;
      letter-spacing: .08em; text-transform: uppercase; margin: 0 0 .7rem;
    }
    .page-title {
      margin: 0; font-size: clamp(2rem, 3.6vw, 3.15rem); font-weight: 780;
      letter-spacing: -0.03em; color: #f5f5f7; line-height: 1.08; max-width: 18ch;
    }
    .page-copy {
      margin: .85rem 0 0; color: rgba(245,245,247,.72); font-size: 1rem;
      line-height: 1.55; max-width: 54ch;
    }
    .page-hero {
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(1200px 420px at 12% -10%, rgba(255,255,255,.16), transparent 55%),
        radial-gradient(900px 380px at 88% 0%, rgba(255,255,255,.08), transparent 50%),
        linear-gradient(180deg, #141416 0%, #0b0b0c 100%);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 28px;
      padding: clamp(1.45rem, 2.6vw, 2rem) clamp(1.25rem, 2.8vw, 2rem);
      box-shadow: 0 24px 60px rgba(0,0,0,.22);
      margin: .15rem 0 1.1rem;
    }
    .section-card {
      background: #fff;
      border: 1px solid rgba(0,0,0,.07);
      border-radius: 22px;
      box-shadow: var(--shadow-soft);
      overflow: hidden;
      margin-bottom: 1rem;
    }
    .section-card-head {
      min-height: 74px;
      padding: 1rem 1.15rem;
      background: linear-gradient(180deg, #171718 0%, #111112 100%);
      border-bottom: 1px solid rgba(255,255,255,.08);
      display: flex;
      flex-direction: column;
      justify-content: center;
    }
    .section-card-head .panel-title {
      color: #f5f5f7;
      font-size: 1rem;
      margin: 0;
    }
    .section-card-head .panel-sub {
      color: rgba(245,245,247,.62);
      font-size: .82rem;
      margin: .28rem 0 0;
    }
    .section-card-body {
      padding: 1rem 1.15rem 1.15rem;
      background: #fff;
    }
    .stack-grid {
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 1rem;
      margin-bottom: 1rem;
      align-items: start;
    }
    .stack-grid > * { min-width: 0; }
    @media (max-width: 1100px) {
      .stack-grid { grid-template-columns: 1fr; }
    }"""

# normalize hero-stat value size so mixed CN/EN don't feel random
old_stat_val = """    .hero-stat-value {
      margin-top: .25rem;
      color: #fff;
      font-size: 1.35rem;
      font-weight: 750;
      letter-spacing: -0.02em;
      font-variant-numeric: tabular-nums;
    }"""
new_stat_val = """    .hero-stat-value {
      margin-top: .28rem;
      color: #fff;
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.015em;
      line-height: 1.25;
      min-height: 1.35em;
      font-variant-numeric: tabular-nums;
    }
    .hero-stat {
      min-height: 78px;
    }"""

# Fix duplicate .hero-stat if we inject min-height separately - merge into existing .hero-stat block later if needed
# Actually the second .hero-stat rule will override/add - OK in CSS

# Tighten panel title sizes
old_panel_title = """    .panel-title { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); margin: 0 0 .25rem; }
    .panel-sub { color: var(--muted); font-size: .84rem; margin: 0 0 .85rem; line-height: 1.45; }"""
new_panel_title = """    .panel-title { font-size: 1rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); margin: 0 0 .25rem; }
    .panel-sub { color: var(--muted); font-size: .82rem; margin: 0 0 .85rem; line-height: 1.45; }"""

# cluster cards more even
old_cluster = """    .cluster-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: .75rem; }
    .cluster-card { padding: 1rem; }
    .cluster-name { font-size: 1rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); }
    .cluster-count {
      color: var(--ink); font-size: 1.35rem; font-weight: 700; margin-top: .3rem;
      letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
    }
    .cluster-skills, .cluster-cats { color: var(--muted); font-size: .78rem; margin-top: .32rem; line-height: 1.45; }

    .agent-shell { padding: 1rem 1.05rem; margin-bottom: .8rem; }
    .agent-title { font-size: 1.12rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); }
    .agent-copy { color: var(--muted); font-size: .84rem; margin-top: .25rem; line-height: 1.45; }"""

new_cluster = """    .cluster-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
    .cluster-card {
      padding: 1.15rem 1.2rem;
      min-height: 180px;
      box-shadow: var(--shadow-soft);
      border: 1px solid rgba(0,0,0,.07);
      border-radius: 20px;
    }
    .cluster-name { font-size: 1rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); }
    .cluster-count {
      color: var(--ink); font-size: 1.2rem; font-weight: 750; margin-top: .4rem;
      letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
    }
    .cluster-skills, .cluster-cats { color: var(--muted); font-size: .8rem; margin-top: .4rem; line-height: 1.5; }

    .agent-shell {
      padding: 0;
      margin-bottom: 1rem;
      overflow: hidden;
      border-radius: 22px;
      border: 1px solid rgba(0,0,0,.07);
      box-shadow: var(--shadow-soft);
      background: #fff;
    }
    .agent-shell-head {
      padding: 1rem 1.15rem;
      background: linear-gradient(180deg, #171718 0%, #111112 100%);
      border-bottom: 1px solid rgba(255,255,255,.08);
    }
    .agent-title { font-size: 1rem; font-weight: 700; letter-spacing: -0.015em; color: #f5f5f7; }
    .agent-copy { color: rgba(245,245,247,.62); font-size: .82rem; margin-top: .28rem; line-height: 1.45; }
    .agent-shell-body { padding: 1rem 1.15rem 1.15rem; }"""

replacements = [
    (old_hero_title, new_hero_title),
    (old_page, new_page),
    (old_stat_val, new_stat_val),
    (old_panel_title, new_panel_title),
    (old_cluster, new_cluster),
]

# Update render_page_header to dark hero
old_header_fn = '''def render_page_header(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="page-kicker">{_safe(kicker)}</div>
        <h1 class="page-title">{_safe(title)}</h1>
        <p class="page-copy">{_safe(copy)}</p>
        """,
        unsafe_allow_html=True,
    )'''

new_header_fn = '''def render_page_header(kicker: str, title: str, copy: str, stats: list | None = None) -> None:
    stats_html = ""
    if stats:
        cells = [].__class__(  # list
            f'<div class="hero-stat"><div class="hero-stat-label">{_safe(label)}</div><div class="hero-stat-value">{_safe(value)}</div></div>'
            for label, value in stats
        )
        stats_html = '<div class="hero-stats">' + "".join(cells) + "</div>"
    st.markdown(
        f"""
        <div class="page-hero">
          <div class="page-kicker">{_safe(kicker)}</div>
          <h1 class="page-title">{_safe(title)}</h1>
          <p class="page-copy">{_safe(copy)}</p>
          {stats_html}
        </div>
        """,
        unsafe_allow_html=True,
    )'''

# Fix the awkward list comprehension in new_header_fn - write cleanly
new_header_fn = '''def render_page_header(kicker: str, title: str, copy: str, stats: list | None = None) -> None:
    stats_html = ""
    if stats:
        cells = []
        for label, value in stats:
            cells.append(
                '<div class="hero-stat">'
                f'<div class="hero-stat-label">{_safe(label)}</div>'
                f'<div class="hero-stat-value">{_safe(value)}</div>'
                "</div>"
            )
        stats_html = '<div class="hero-stats">' + "".join(cells) + "</div>"
    st.markdown(
        f"""
        <div class="page-hero">
          <div class="page-kicker">{_safe(kicker)}</div>
          <h1 class="page-title">{_safe(title)}</h1>
          <p class="page-copy">{_safe(copy)}</p>
          {stats_html}
        </div>
        """,
        unsafe_allow_html=True,
    )'''

replacements.append((old_header_fn, new_header_fn))

# Match page: unify boxes + use shared header helper for result state already; fix entry/layout
old_match = '''if page == "match":
    result = st.session_state.get("match_result")
    jobs_count = f"{health_count:,}" if health else "—"
    if not result:
        st.markdown(
            f"""
            <div class="hero-entry">
              <div class="hero-kicker">BOSS！求聘</div>
              <h1 class="hero-title">上传简历，匹配更合适的远程岗位</h1>
              <p class="hero-copy">也可以先写几句求职要求。我们会识别技能和经验，从本地远程岗位库里给你排序。</p>
              <div class="hero-stats">
                <div class="hero-stat"><div class="hero-stat-label">岗位库</div><div class="hero-stat-value">{jobs_count}</div></div>
                <div class="hero-stat"><div class="hero-stat-label">匹配方式</div><div class="hero-stat-value">技能 + 经验</div></div>
                <div class="hero-stat"><div class="hero-stat-label">结果</div><div class="hero-stat-value">可追溯来源</div></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_page_header(
            "结果",
            "这些岗位更贴近你",
            "可以按类别继续筛选，也可以改完简历再匹配一次。",
        )

    if "resume_text_value" not in st.session_state:
        st.session_state.resume_text_value = ""

    left_col, right_col = st.columns([1.35, 1], gap="large")
    with left_col:
        st.markdown(
            """
            <div class="workspace-card">
              <div class="workspace-head dark">
                <div class="panel-title">你的简历 / 要求</div>
                <p class="panel-sub">粘贴简历、上传 PDF，或直接写技能、经验和期望。</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("填入演示简历", use_container_width=True):
                st.session_state.resume_text_value = DEMO_RESUME
                st.rerun()
        with b2:
            if st.button("清空输入", use_container_width=True):
                st.session_state.resume_text_value = ""
                st.session_state.pop("match_result", None)
                st.rerun()
        resume_text = st.text_area(
            "简历或求职要求",
            height=240,
            key="resume_text_value",
            placeholder="可以直接贴简历，也可以写：4年数据经验，Python / SQL / Pandas，希望远程数据岗位",
        )
        uploaded = st.file_uploader("上传 TXT / PDF", type=["txt", "pdf"])

    with right_col:
        st.markdown(
            """
            <div class="workspace-side">
              <div class="panel-title">匹配设置</div>
              <p class="panel-sub">先定地点和返回数量，再开始匹配。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        preferred = st.selectbox(
            "地点偏好（可选）",
            options=LOCATION_OPTIONS,
            index=0,
            help="默认不限。选择后会在匹配时作为地点偏好传入。",
        )
        if preferred == "不限":
            preferred = ""
        top_k = st.slider("返回岗位数", 3, 10, 5)
        st.write("")
        if st.button("开始匹配", type="primary", use_container_width=True):
            try:
                with st.spinner("思考中...."):
                    run_match(resume_text, uploaded, preferred, top_k)
                st.success("匹配完成")
            except Exception as exc:
                st.error(str(exc))
        st.caption("演示文件：submit/演示简历_张三_数据工程师.pdf")
'''

new_match = '''if page == "match":
    result = st.session_state.get("match_result")
    jobs_count = f"{health_count:,}" if health else "—"
    if not result:
        render_page_header(
            "BOSS！求聘",
            "上传简历，匹配更合适的远程岗位",
            "也可以先写几句求职要求。我们会识别技能和经验，从本地远程岗位库里给你排序。",
            stats=[
                ("岗位库", jobs_count),
                ("匹配维度", "技能 / 经验 / 地点"),
                ("输出", "岗位 + 来源"),
            ],
        )
    else:
        render_page_header(
            "结果",
            "这些岗位更贴近你",
            "可以按类别继续筛选，也可以改完简历再匹配一次。",
            stats=[
                ("识别技能", str(len(result.get("resume_skills", [])))),
                ("经验", str(result.get("resume_years") or "—")),
                ("候选", str(len(result.get("results", [])))),
            ],
        )

    if "resume_text_value" not in st.session_state:
        st.session_state.resume_text_value = ""

    left_col, right_col = st.columns([1.35, 1], gap="medium")
    with left_col:
        st.markdown(
            """
            <div class="section-card">
              <div class="section-card-head">
                <div class="panel-title">你的简历 / 要求</div>
                <p class="panel-sub">粘贴简历、上传 PDF，或直接写技能、经验和期望。</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("填入演示简历", use_container_width=True):
                st.session_state.resume_text_value = DEMO_RESUME
                st.rerun()
        with b2:
            if st.button("清空输入", use_container_width=True):
                st.session_state.resume_text_value = ""
                st.session_state.pop("match_result", None)
                st.rerun()
        resume_text = st.text_area(
            "简历或求职要求",
            height=220,
            key="resume_text_value",
            placeholder="可以直接贴简历，也可以写：4年数据经验，Python / SQL / Pandas，希望远程数据岗位",
        )
        uploaded = st.file_uploader("上传 TXT / PDF", type=["txt", "pdf"])

    with right_col:
        st.markdown(
            """
            <div class="section-card">
              <div class="section-card-head">
                <div class="panel-title">匹配设置</div>
                <p class="panel-sub">先定地点和返回数量，再开始匹配。</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        preferred = st.selectbox(
            "地点偏好（可选）",
            options=LOCATION_OPTIONS,
            index=0,
            help="默认不限。选择后会在匹配时作为地点偏好传入。",
        )
        if preferred == "不限":
            preferred = ""
        top_k = st.slider("返回岗位数", 3, 10, 5)
        st.write("")
        if st.button("开始匹配", type="primary", use_container_width=True):
            try:
                with st.spinner("思考中...."):
                    run_match(resume_text, uploaded, preferred, top_k)
                st.success("匹配完成")
            except Exception as exc:
                st.error(str(exc))
        st.caption("演示文件：submit/演示简历_张三_数据工程师.pdf")
'''

replacements.append((old_match, new_match))

# RAG page
old_rag = '''elif page == "rag":
    render_page_header(
        "搜索",
        "用一句话搜索岗位",
        "例如“要 Python 和 SQL 的远程数据分析岗”。结果会带来源链接。",
    )
    st.markdown(
        '<div class="panel"><div class="panel-title">你想找什么样的工作？</div><p class="panel-sub">先点示例，或自己输入后再搜索。</p>',
        unsafe_allow_html=True,
    )
    if "rag_query" not in st.session_state:
        st.session_state.rag_query = RAG_EXAMPLES[0]
    example_cols = st.columns(2)
    for idx, example in enumerate(RAG_EXAMPLES):
        with example_cols[idx % 2]:
            if st.button(example, key=f"rag_ex_{idx}", use_container_width=True):
                st.session_state.rag_query = example
                st.rerun()
    query = st.text_input("检索问题", key="rag_query")
    if st.button("搜索岗位", type="primary") and query.strip():
        try:
            with st.spinner("思考中...."):
                st.session_state.retrieve_result = call_api(
                    "POST",
                    "/api/retrieve",
                    json={"question": query, "top_k": 5},
                )
        except Exception as exc:
            st.error(str(exc))
    st.markdown("</div>", unsafe_allow_html=True)

    retrieved = st.session_state.get("retrieve_result")
    if retrieved:
        st.caption(f"检索方法：{retrieved.get('method')}")
        for idx, item in enumerate(retrieved.get("results", []), 1):
            render_job(item, idx, score_label="检索相似度")
    else:
        render_empty("还没有搜索结果", "选一个示例，或自己输入后点“搜索岗位”。")
'''

new_rag = '''elif page == "rag":
    render_page_header(
        "搜索",
        "用一句话搜索岗位",
        "例如“要 Python 和 SQL 的远程数据分析岗”。结果会带来源链接。",
        stats=[
            ("岗位库", f"{health_count:,}" if health else "—"),
            ("检索", "FAISS / Embedding"),
            ("输出", "Top-k + 来源"),
        ],
    )
    st.markdown(
        """
        <div class="section-card">
          <div class="section-card-head">
            <div class="panel-title">你想找什么样的工作？</div>
            <p class="panel-sub">先点示例，或自己输入后再搜索。</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "rag_query" not in st.session_state:
        st.session_state.rag_query = RAG_EXAMPLES[0]
    example_cols = st.columns(2)
    for idx, example in enumerate(RAG_EXAMPLES):
        with example_cols[idx % 2]:
            if st.button(example, key=f"rag_ex_{idx}", use_container_width=True):
                st.session_state.rag_query = example
                st.rerun()
    query = st.text_input("检索问题", key="rag_query")
    if st.button("搜索岗位", type="primary") and query.strip():
        try:
            with st.spinner("思考中...."):
                st.session_state.retrieve_result = call_api(
                    "POST",
                    "/api/retrieve",
                    json={"question": query, "top_k": 5},
                )
        except Exception as exc:
            st.error(str(exc))

    retrieved = st.session_state.get("retrieve_result")
    if retrieved:
        st.caption(f"检索方法：{retrieved.get('method')}")
        for idx, item in enumerate(retrieved.get("results", []), 1):
            render_job(item, idx, score_label="检索相似度")
    else:
        render_empty("还没有搜索结果", "选一个示例，或自己输入后点“搜索岗位”。")
'''

replacements.append((old_rag, new_rag))

# Cluster page
old_cluster_page = '''elif page == "cluster":
    render_page_header(
        "画像",
        "远程岗位长什么样",
        "我们把岗位分成 4 类，方便快速看清主要方向。",
    )
    st.markdown(
        '<div class="panel"><div class="panel-title">四类岗位画像</div><p class="panel-sub">每类都汇总了常见技能和岗位方向。</p></div>',
        unsafe_allow_html=True,
    )
'''

new_cluster_page = '''elif page == "cluster":
    render_page_header(
        "画像",
        "远程岗位长什么样",
        "我们把岗位分成 4 类，方便快速看清主要方向。",
        stats=[
            ("聚类", "K-Means"),
            ("类别数", "4"),
            ("用途", "岗位画像"),
        ],
    )
    st.markdown(
        """
        <div class="section-card">
          <div class="section-card-head">
            <div class="panel-title">四类岗位画像</div>
            <p class="panel-sub">每类都汇总了常见技能和岗位方向。</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
'''

replacements.append((old_cluster_page, new_cluster_page))

# Agent page
old_agent = '''else:
    render_page_header(
        "助手",
        "让助手帮你串起来",
        "直接说目标即可。助手会调用匹配、搜索、评分等能力，并给出可追溯结果。",
    )
    real = st.toggle("使用真实模型 Function Calling", value=True)
    st.markdown(
        f"""
        <div class="agent-shell">
          <div class="agent-title">求职助手</div>
          <div class="agent-copy">适合复杂需求：先找岗，再说明为什么匹配，并带来源。</div>
          <div class="agent-badge {'local' if not real else ''}">{'真实模型' if real else '本地规则路由'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
'''

new_agent = '''else:
    render_page_header(
        "助手",
        "让助手帮你串起来",
        "直接说目标即可。助手会调用匹配、搜索、评分等能力，并给出可追溯结果。",
        stats=[
            ("工具", "search / match / score"),
            ("编排", "Function Calling"),
            ("结果", "可追溯"),
        ],
    )
    real = st.toggle("使用真实模型 Function Calling", value=True)
    st.markdown(
        f"""
        <div class="agent-shell">
          <div class="agent-shell-head">
            <div class="agent-title">求职助手</div>
            <div class="agent-copy">适合复杂需求：先找岗，再说明为什么匹配，并带来源。</div>
            <div class="agent-badge {'local' if not real else ''}">{'真实模型' if real else '本地规则路由'}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
'''

replacements.append((old_agent, new_agent))

# empty render uses empty-kicker optionally - update render_empty
old_empty_fn = '''def render_empty(title: str, copy: str, icon: str = "○") -> None:
    st.markdown(
        f'<div class="empty-card"><div>{_safe(icon)}</div><div class="empty-title">{_safe(title)}</div><div>{_safe(copy)}</div></div>',
        unsafe_allow_html=True,
    )'''

new_empty_fn = '''def render_empty(title: str, copy: str, icon: str = "○") -> None:
    st.markdown(
        f'''
        <div class="empty-card">
          <div class="empty-kicker">{_safe(icon)}</div>
          <div class="empty-title">{_safe(title)}</div>
          <div class="empty-copy">{_safe(copy)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )'''

replacements.append((old_empty_fn, new_empty_fn))

# Fix agent-badge color on dark head
if ".agent-badge {" in text and ".agent-shell-head .agent-badge" not in text:
    text = text.replace(
        """    .agent-badge {
      display: inline-flex; margin-top: .5rem; background: var(--accent-soft); color: var(--ink);
      border-radius: 999px; padding: .18rem .55rem; font-size: .7rem; font-weight: 650;
    }
    .agent-badge.local { background: #f5f5f7; color: #6e6e73; }""",
        """    .agent-badge {
      display: inline-flex; margin-top: .55rem; background: rgba(255,255,255,.12); color: #f5f5f7;
      border-radius: 999px; padding: .18rem .55rem; font-size: .7rem; font-weight: 650;
      border: 1px solid rgba(255,255,255,.14);
    }
    .agent-badge.local { background: rgba(255,255,255,.08); color: rgba(245,245,247,.7); }""",
    )

for i, (old, new) in enumerate(replacements, 1):
    if old not in text:
        raise SystemExit(f"block {i} not found")
    text = text.replace(old, new, 1)
    print(f"replaced block {i}")

# Remove duplicate .hero-stat if we now have two definitions - check
# The new_stat_val includes a second .hero-stat { min-height } which is fine.

# Also sync .hero-entry title styles aren't used as much now - keep for safety.

ast.parse(text)
path.write_text(text, encoding="utf-8")
print("ok")
