#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import ast

path = Path("frontend/streamlit_app.py")
text = path.read_text(encoding="utf-8")

replacements: list[tuple[str, str]] = []

replacements.append(
    (
        """    :root {
      --bg: #f5f5f7;
      --panel: #ffffff;
      --ink: #1d1d1f;
      --muted: #6e6e73;
      --line: #d2d2d7;
      --soft: #ececef;
      --accent: #1d1d1f;
      --accent-ink: #000000;
      --accent-soft: #f2f2f2;
      --link: #0066cc;
      --ok: #34c759;
      --danger: #ff3b30;
      --shadow: 0 8px 28px rgba(0,0,0,.06);
      --radius: 18px;
      --nav-h: 58px;
    }""",
        """    :root {
      --bg: #ececee;
      --panel: #ffffff;
      --ink: #1d1d1f;
      --muted: #6e6e73;
      --line: #d2d2d7;
      --soft: #f0f0f2;
      --accent: #1d1d1f;
      --accent-ink: #000000;
      --accent-soft: #f2f2f2;
      --link: #0066cc;
      --ok: #34c759;
      --danger: #ff3b30;
      --shadow: 0 18px 50px rgba(0,0,0,.08);
      --shadow-soft: 0 8px 24px rgba(0,0,0,.05);
      --radius: 22px;
      --nav-h: 58px;
      --stage: #0b0b0c;
    }""",
    )
)

replacements.append(
    (
        """    .hero-entry {
      background: transparent;
      border: 0;
      border-radius: 0;
      padding: 1.4rem 0 1.35rem;
      box-shadow: none;
      margin: .1rem 0 .9rem;
      text-align: left;
    }
    .hero-kicker {
      color: var(--muted);
      font-size: .78rem;
      font-weight: 650;
      letter-spacing: .04em;
      text-transform: uppercase;
      margin-bottom: .55rem;
    }
    .hero-title {
      margin: 0;
      font-size: clamp(2.8rem, 6vw, 5.6rem);
      line-height: 0.92;
      font-weight: 800;
      letter-spacing: -0.035em;
      color: var(--ink);
      max-width: none;
    }
    .hero-copy {
      margin: .95rem 0 0;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.5;
      max-width: 62ch;
    }""",
        """    .hero-entry {
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(1200px 420px at 12% -10%, rgba(255,255,255,.16), transparent 55%),
        radial-gradient(900px 380px at 88% 0%, rgba(255,255,255,.08), transparent 50%),
        linear-gradient(180deg, #141416 0%, #0b0b0c 100%);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 28px;
      padding: clamp(1.6rem, 3vw, 2.4rem) clamp(1.4rem, 3vw, 2.2rem) clamp(1.5rem, 2.6vw, 2.1rem);
      box-shadow: 0 24px 60px rgba(0,0,0,.22);
      margin: .15rem 0 1.15rem;
      text-align: left;
      color: #f5f5f7;
    }
    .hero-entry::after {
      content: "";
      position: absolute;
      right: -40px;
      top: -60px;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255,255,255,.12), transparent 68%);
      pointer-events: none;
    }
    .hero-kicker {
      color: rgba(245,245,247,.62);
      font-size: .78rem;
      font-weight: 650;
      letter-spacing: .08em;
      text-transform: uppercase;
      margin-bottom: .7rem;
    }
    .hero-title {
      margin: 0;
      font-size: clamp(2.4rem, 5.2vw, 4.6rem);
      line-height: 0.96;
      font-weight: 800;
      letter-spacing: -0.035em;
      color: #f5f5f7;
      max-width: 14ch;
    }
    .hero-copy {
      margin: .95rem 0 0;
      color: rgba(245,245,247,.72);
      font-size: 1.05rem;
      line-height: 1.55;
      max-width: 54ch;
    }
    .hero-stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: .7rem;
      margin-top: 1.35rem;
      max-width: 720px;
    }
    .hero-stat {
      background: rgba(255,255,255,.06);
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 16px;
      padding: .85rem .9rem;
      backdrop-filter: blur(10px);
    }
    .hero-stat-label {
      color: rgba(245,245,247,.55);
      font-size: .68rem;
      font-weight: 650;
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    .hero-stat-value {
      margin-top: .25rem;
      color: #fff;
      font-size: 1.35rem;
      font-weight: 750;
      letter-spacing: -0.02em;
      font-variant-numeric: tabular-nums;
    }""",
    )
)

replacements.append(
    (
        """    .panel {
      background: var(--panel);
      border: 1px solid rgba(0,0,0,.06);
      border-radius: var(--radius);
      padding: 1.15rem 1.2rem;
      box-shadow: var(--shadow);
      margin-bottom: 1rem;
    }
    .panel-title { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); margin: 0 0 .25rem; }
    .panel-sub { color: var(--muted); font-size: .84rem; margin: 0 0 .85rem; line-height: 1.45; }

    .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; margin: .8rem 0 1rem; }
    .metric {
      background: var(--soft); border: 0; border-radius: 16px; padding: .85rem .9rem;
    }
    .metric-label { color: var(--muted); font-size: .7rem; font-weight: 600; }
    .metric-value {
      color: var(--ink); font-size: 1.45rem; font-weight: 700; margin-top: .18rem;
      letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
    }""",
        """    .panel {
      background: var(--panel);
      border: 1px solid rgba(0,0,0,.06);
      border-radius: var(--radius);
      padding: 1.2rem 1.25rem;
      box-shadow: var(--shadow-soft);
      margin-bottom: 1rem;
    }
    .panel-title { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); margin: 0 0 .25rem; }
    .panel-sub { color: var(--muted); font-size: .84rem; margin: 0 0 .85rem; line-height: 1.45; }

    .workspace-card {
      background: linear-gradient(180deg, #ffffff 0%, #fbfbfc 100%);
      border: 1px solid rgba(0,0,0,.08);
      border-radius: 24px;
      box-shadow: 0 22px 55px rgba(0,0,0,.10);
      overflow: hidden;
      margin-bottom: .2rem;
    }
    .workspace-head {
      padding: 1.05rem 1.2rem .85rem;
      border-bottom: 1px solid rgba(0,0,0,.06);
      background: linear-gradient(180deg, #fafafa 0%, #ffffff 100%);
    }
    .workspace-head.dark {
      background: linear-gradient(180deg, #171718 0%, #111112 100%);
      border-bottom: 1px solid rgba(255,255,255,.08);
    }
    .workspace-head.dark .panel-title { color: #f5f5f7; }
    .workspace-head.dark .panel-sub { color: rgba(245,245,247,.62); margin-bottom: 0; }
    .workspace-side {
      background:
        radial-gradient(500px 220px at 100% 0%, rgba(255,255,255,.08), transparent 60%),
        #111112;
      color: #f5f5f7;
      border-radius: 24px;
      border: 1px solid rgba(255,255,255,.08);
      box-shadow: 0 22px 55px rgba(0,0,0,.18);
      padding: 1.15rem 1.15rem 1.2rem;
      margin-bottom: .2rem;
    }
    .workspace-side .panel-title { color: #f5f5f7; }
    .workspace-side .panel-sub { color: rgba(245,245,247,.62); }
    .match-focus {
      margin: .85rem 0 1rem;
      padding: 1rem 1.1rem;
      border-radius: 20px;
      background: #fff;
      border: 1px solid rgba(0,0,0,.06);
      box-shadow: var(--shadow-soft);
    }
    .match-focus-title {
      font-size: .78rem;
      font-weight: 700;
      letter-spacing: .06em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: .55rem;
    }

    .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; margin: .8rem 0 1rem; }
    .metric {
      background: #fff; border: 1px solid rgba(0,0,0,.06); border-radius: 16px; padding: .85rem .9rem;
      box-shadow: var(--shadow-soft);
    }
    .metric:first-child {
      background: #111112;
      border-color: #111112;
    }
    .metric:first-child .metric-label { color: rgba(245,245,247,.58); }
    .metric:first-child .metric-value { color: #fff; }
    .metric-label { color: var(--muted); font-size: .7rem; font-weight: 600; }
    .metric-value {
      color: var(--ink); font-size: 1.45rem; font-weight: 700; margin-top: .18rem;
      letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
    }""",
    )
)

replacements.append(
    (
        """    .empty-card { padding: 1.5rem 1rem; text-align: center; color: var(--muted); }
    .empty-title { color: var(--ink); font-weight: 700; margin-top: .3rem; }""",
        """    .empty-card {
      padding: 2.2rem 1.3rem;
      text-align: left;
      color: var(--muted);
      background: linear-gradient(180deg, #ffffff 0%, #f7f7f8 100%);
      box-shadow: var(--shadow);
      border: 1px solid rgba(0,0,0,.06);
      border-radius: 24px;
      min-height: 220px;
    }
    .empty-kicker {
      color: var(--muted);
      font-size: .72rem;
      font-weight: 700;
      letter-spacing: .06em;
      text-transform: uppercase;
    }
    .empty-title {
      color: var(--ink);
      font-weight: 800;
      font-size: clamp(1.5rem, 2.5vw, 2rem);
      letter-spacing: -0.03em;
      margin-top: .45rem;
      line-height: 1.1;
      max-width: 16ch;
    }
    .empty-copy { margin-top: .55rem; max-width: 42ch; line-height: 1.5; }""",
    )
)

replacements.append(
    (
        """    @media (max-width: 1100px) {
      .metrics, .cluster-grid, .detail-score-row { grid-template-columns: 1fr 1fr; }
    }""",
        """    @media (max-width: 1100px) {
      .metrics, .cluster-grid, .detail-score-row, .hero-stats { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 720px) {
      .hero-stats, .metrics { grid-template-columns: 1fr; }
      .hero-title { max-width: none; }
    }""",
    )
)

old_match = '''if page == "match":
    result = st.session_state.get("match_result")
    if not result:
        st.markdown(
            """
            <div class="hero-entry">
              <div class="hero-kicker">BOSS！求聘</div>
              <h1 class="hero-title">上传简历，匹配更合适的远程岗位</h1>
              <p class="hero-copy">也可以先写几句求职要求。我们会识别技能和经验，从本地远程岗位库里给你排序。</p>
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

    st.markdown(
        '<div class="panel"><div class="panel-title">你的简历 / 要求</div><p class="panel-sub">粘贴简历、上传 PDF，或直接写技能、经验和期望。</p>',
        unsafe_allow_html=True,
    )
    input_left, input_right = st.columns([1.7, 1], gap="large")
    with input_left:
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
            height=210,
            key="resume_text_value",
            placeholder="可以直接贴简历，也可以写：4年数据经验，Python / SQL / Pandas，希望远程数据岗位",
        )
        uploaded = st.file_uploader("上传 TXT / PDF", type=["txt", "pdf"])
    with input_right:
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
        st.caption("演示文件也可使用：submit/演示简历_张三_数据工程师.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

    result = st.session_state.get("match_result")
    if result:
        skills = result.get("resume_skills", [])
        st.markdown(
            f"""
            <div class="metrics">
              <div class="metric"><div class="metric-label">识别技能</div><div class="metric-value">{len(skills)}</div></div>
              <div class="metric"><div class="metric-label">经验</div><div class="metric-value">{_safe(result.get("resume_years") or "—")}</div></div>
              <div class="metric"><div class="metric-label">候选岗位</div><div class="metric-value">{len(result.get("results", []))}</div></div>
            </div>
            <div>{_pills(skills, limit=12)}</div>
            """,
            unsafe_allow_html=True,
        )
        render_job_board(result)
    else:
        st.caption("匹配完成后，岗位会出现在这里。如果你只想先问问有没有某类岗位，也可以去“搜索”。")
'''

new_match = '''if page == "match":
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

    result = st.session_state.get("match_result")
    if result:
        skills = result.get("resume_skills", [])
        st.markdown(
            f"""
            <div class="match-focus">
              <div class="match-focus-title">本次识别</div>
              <div class="metrics">
                <div class="metric"><div class="metric-label">识别技能</div><div class="metric-value">{len(skills)}</div></div>
                <div class="metric"><div class="metric-label">经验</div><div class="metric-value">{_safe(result.get("resume_years") or "—")}</div></div>
                <div class="metric"><div class="metric-label">候选岗位</div><div class="metric-value">{len(result.get("results", []))}</div></div>
              </div>
              <div>{_pills(skills, limit=12)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_job_board(result)
    else:
        st.markdown(
            """
            <div class="empty-card">
              <div class="empty-kicker">匹配结果区</div>
              <div class="empty-title">岗位会按匹配分出现在这里</div>
              <div class="empty-copy">先上传或粘贴简历，点“开始匹配”。如果你只想先问问有没有某类岗位，也可以去“搜索”。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
'''

replacements.append((old_match, new_match))

for i, (old, new) in enumerate(replacements, 1):
    if old not in text:
        raise SystemExit(f"block {i} not found")
    text = text.replace(old, new, 1)
    print(f"replaced block {i}")

ast.parse(text)
path.write_text(text, encoding="utf-8")
print("ok", path)
