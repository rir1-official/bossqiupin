"""Remote job intelligence workbench for classroom demo."""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="BOSS！求聘",
    page_icon=str(Path(__file__).resolve().parent / "assets" / "boss_icon_64.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
API_TIMEOUT = float(os.getenv("FRONTEND_API_TIMEOUT", "180"))
REAL_AGENT_TIMEOUT = float(os.getenv("FRONTEND_REAL_AGENT_TIMEOUT", "150"))
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEMO_RESUME = """张三
数据工程师 / 数据分析
工作经验：4年
期望：远程数据相关岗位，可接受美国远程
技能
Python、SQL、Pandas、Docker、机器学习、数据清洗、报表开发、数据管道
项目经历
1. 负责业务数据清洗与指标体系建设，使用 Python、SQL、Pandas 完成日报与专题分析。
2. 参与数据管道搭建，使用 Docker 部署任务，支持模型训练与上线维护。
3. 做过基础机器学习预测项目，包括特征处理和模型评估。
教育背景
本科 · 计算机相关专业"""

RAG_EXAMPLES = [
    "想找 Python 和 SQL 的远程数据分析岗位",
    "有没有偏数据工程、需要 Docker 的远程岗位",
    "Remote 机器学习相关岗位，要求有模型经验",
    "查找美国远程、偏数据管道的工作",
]

AGENT_EXAMPLES = [
    "帮我找适合 Python、SQL、4年经验的远程数据岗位",
    "先检索偏数据工程的远程岗位，再总结适合的聚类方向",
    "有没有美国远程、偏机器学习的岗位？",
    "对比一下数据分析岗位和数据工程岗位的技能差异",
]

NAV_ITEMS = [
    ("match", "匹配"),
    ("rag", "搜索"),
    ("cluster", "画像"),
    ("agent", "助手"),
]

LOCATION_OPTIONS = [
    "不限",
    "United States",
    "Canada",
    "United Kingdom",
    "Germany",
    "Australia",
    "India",
    "Philippines",
    "Brazil",
    "Mexico",
    "Poland",
    "Spain",
    "France",
    "Portugal",
    "Netherlands",
    "Singapore",
    "Japan",
]


st.html(
    """
    <style>
    :root {
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
    }

    html, body, [class*="css"], .stApp {
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      letter-spacing: 0;
    }
    .stApp { background: var(--bg); }
    [data-testid="stHeader"],
    [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    section[data-testid="stSidebar"] {
      display: none !important;
    }
    .block-container {
      max-width: 1540px;
      padding: 0 clamp(22px, 4vw, 62px) 4rem;
    }
    [data-testid="stAppViewContainer"] > .main {
      padding-left: 0 !important;
      padding-right: 0 !important;
    }
    .main .block-container {
      width: 100%;
    }
    /* Force wide app canvas */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
      width: 100% !important;
      max-width: 100% !important;
    }
    [data-testid="stMain"] > .block-container,
    .main .block-container {
      max-width: 1540px !important;
      padding-left: clamp(22px, 4vw, 62px) !important;
      padding-right: clamp(22px, 4vw, 62px) !important;
    }


    h1,h2,h3 { color: var(--ink); }
    p { color: var(--muted); }

    .stButton > button {
      border-radius: 980px;
      min-height: 2.7rem;
      font-weight: 600;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      transition: transform 100ms ease-out, background 160ms ease, border-color 160ms ease;
    }
    .stButton > button:active { transform: scale(0.97); }
    .stButton > button[kind="primary"] {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }
    .stButton > button[kind="primary"]:hover {
      background: #000;
      border-color: #000;
      color: #fff;
    }
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
      border-radius: 14px !important;
      border-color: var(--line) !important;
      background: #fff !important;
    }
    .stSlider [data-baseweb="slider"] div[role="slider"] {
      background: var(--accent) !important;
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 50;
      display: grid;
      grid-template-columns: minmax(160px, 0.8fr) minmax(280px, 1.3fr) minmax(140px, 0.7fr);
      align-items: center;
      gap: 18px;
      min-height: 64px;
      margin: 0 -1.25rem 1rem;
      padding: 0 1.25rem;
      background: rgba(251, 251, 253, 0.86);
      backdrop-filter: blur(18px) saturate(180%);
      -webkit-backdrop-filter: blur(18px) saturate(180%);
      border-bottom: 1px solid rgba(0,0,0,0.08);
    }
    /* Streamlit row that hosts brand / nav / status */
    .block-container > div:first-child > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-child {
      position: sticky;
      top: 0;
      z-index: 50;
      margin: 0 -1.25rem 1rem;
      padding: 0 1.25rem;
      min-height: 64px;
      align-items: center !important;
      background: rgba(5, 5, 5, 0.94);
      backdrop-filter: blur(18px) saturate(180%);
      -webkit-backdrop-filter: blur(18px) saturate(180%);
      border-bottom: 1px solid rgba(255,255,255,0.72);
    }
    .block-container > div:first-child > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-child > div[data-testid="stColumn"] {
      display: flex;
      align-items: center;
    }
    .block-container > div:first-child > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-child .stButton > button {
      background: transparent !important;
      border: 0 !important;
      box-shadow: none !important;
      color: #ffffff !important;
      opacity: 0.74;
      border-radius: 0 !important;
      min-height: 72px !important;
      height: 72px !important;
      padding: 0 .15rem !important;
      font-size: clamp(0.95rem, 1.15vw, 1.12rem) !important;
      font-weight: 800 !important;
      letter-spacing: -0.01em !important;
    }
    .block-container > div:first-child > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-child .stButton > button:hover {
      opacity: 1;
      background: transparent !important;
      transform: none;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
      text-decoration: none;
      color: inherit;
    }
    .brand-mark {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: grid;
      place-items: center;
      overflow: hidden;
      background: transparent;
      flex: 0 0 auto;
    }
    .brand-symbol {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: contain;
    }
    .brand-copy { min-width: 0; }
    .brand-name {
      display: block;
      font-size: 1.05rem;
      font-weight: 850;
      letter-spacing: -0.02em;
      color: #ffffff;
      line-height: 1.1;
      white-space: nowrap;
    }
    .brand-sub {
      display: block;
      margin-top: 2px;
      font-size: 0.7rem;
      color: #8e8e8e;
    }
    .topbar-nav {
      display: flex;
      align-items: stretch;
      justify-content: center;
      gap: clamp(22px, 4vw, 56px);
      height: 64px;
      min-width: 0;
    }
    .topbar-link {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 72px;
      color: #ffffff;
      text-decoration: none !important;
      opacity: 1;
      transition: opacity 0.18s ease;
      font-size: clamp(0.95rem, 1.15vw, 1.12rem);
      font-weight: 800;
      letter-spacing: -0.01em;
      white-space: nowrap;
    }
    .topbar-link:hover { opacity: 1; }
    .topbar-link.active { opacity: 1; }
    .topbar-link.active::after {
      content: '';
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 4px;
      background: #ffffff;
    }
    .nav-status {
      margin-left: auto;
      display: inline-flex;
      align-items: center;
      gap: .4rem;
      border-radius: 999px;
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.22);
      padding: .38rem .7rem;
      font-size: .72rem;
      color: #c8c8c8;
      font-weight: 650;
      white-space: nowrap;
    }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); }
    .status-dot.off { background: var(--danger); }
    @media (max-width: 820px) {
      .topbar {
        grid-template-columns: 1fr;
        gap: 8px;
        padding-top: .7rem;
        padding-bottom: .55rem;
        min-height: auto;
      }
      .topbar-nav {
        justify-content: flex-start;
        gap: 18px;
        height: 44px;
        overflow-x: auto;
      }
      .nav-status { justify-self: start; }
    }


    /* Reliable MoodTune topbar skin */
    div[data-testid="stHorizontalBlock"]:has(.brand-name) {
      position: sticky !important;
      top: 0 !important;
      z-index: 50 !important;
      width: 100vw !important;
      max-width: 100vw !important;
      margin-left: calc(50% - 50vw) !important;
      margin-right: calc(50% - 50vw) !important;
      margin-top: 0 !important;
      margin-bottom: 1.2rem !important;
      padding: 0 clamp(22px, 4vw, 62px) !important;
      min-height: 72px !important;
      align-items: center !important;
      background: rgba(5, 5, 5, 0.94) !important;
      backdrop-filter: blur(18px) saturate(180%) !important;
      -webkit-backdrop-filter: blur(18px) saturate(180%) !important;
      border-bottom: 1px solid rgba(255,255,255,0.72) !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) > div[data-testid="stColumn"] {
      display: flex !important;
      align-items: center !important;
      min-height: 72px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) > div[data-testid="stColumn"]:first-child {
      justify-content: flex-start !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) > div[data-testid="stColumn"]:nth-child(2) {
      justify-content: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) > div[data-testid="stColumn"]:last-child {
      justify-content: flex-end !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stVerticalBlock"],
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stLayoutWrapper"],
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="element-container"],
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stElementContainer"],
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stMarkdownContainer"],
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stButton"] {
      width: 100% !important;
      min-height: 72px !important;
      display: flex !important;
      align-items: center !important;
      margin-top: 0 !important;
      margin-bottom: 0 !important;
      padding-top: 0 !important;
      padding-bottom: 0 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .brand {
      height: 72px !important;
      width: 100% !important;
      display: flex !important;
      align-items: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .brand-name { color: #ffffff !important; }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .brand-sub { color: #8e8e8e !important; }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .topbar-link {
      color: #ffffff !important;
      height: 72px !important;
      width: 100% !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .topbar-link.active::after {
      height: 4px !important;
      background: #ffffff !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .nav-status {
      background: rgba(255,255,255,0.1) !important;
      border: 1px solid rgba(255,255,255,0.22) !important;
      color: #c8c8c8 !important;
      margin-left: auto !important;
      margin-right: 0 !important;
      height: 36px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .stButton > button {
      background: transparent !important;
      border: 0 !important;
      box-shadow: none !important;
      color: #ffffff !important;
      opacity: 0.74 !important;
      border-radius: 0 !important;
      min-height: 72px !important;
      height: 72px !important;
      padding: 0 .2rem !important;
      font-size: clamp(0.98rem, 1.2vw, 1.15rem) !important;
      font-weight: 650 !important;
      letter-spacing: -0.01em !important;
      justify-content: center !important;
      text-align: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .stButton > button:hover {
      opacity: 1 !important;
      background: transparent !important;
      transform: none !important;
    }
    /* Active tab: full-opacity label + bottom underline, same column width as siblings */
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stColumn"]:has(.nav-active-slot) {
      position: relative !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stColumn"]:has(.nav-active-slot) .stButton > button {
      opacity: 1 !important;
      font-weight: 750 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .nav-active-slot {
      position: absolute !important;
      left: 18%;
      right: 18%;
      bottom: 0 !important;
      height: 4px !important;
      background: #ffffff !important;
      border-radius: 999px !important;
      z-index: 2 !important;
      pointer-events: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stElementContainer"]:has(.nav-active-slot),
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="element-container"]:has(.nav-active-slot),
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stMarkdown"]:has(.nav-active-slot),
    div[data-testid="stHorizontalBlock"]:has(.brand-name) [data-testid="stMarkdownContainer"]:has(.nav-active-slot) {
      position: absolute !important;
      left: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      overflow: visible !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .brand-mark {
      background: transparent !important;
    }

    .hero-entry {
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
      font-size: clamp(2rem, 3.6vw, 3.15rem);
      line-height: 1.08;
      font-weight: 780;
      letter-spacing: -0.03em;
      color: #f5f5f7;
      max-width: 18ch;
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
    .hero-stat {
      min-height: 78px;
    }
    .hero-stat-value {
      margin-top: .28rem;
      color: #fff;
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.015em;
      line-height: 1.25;
      min-height: 1.35em;
      font-variant-numeric: tabular-nums;
    }

    .page-kicker {
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
      margin-bottom: .35rem;
    }
    .section-card-head {
      min-height: 74px;
      padding: 1rem 1.15rem;
      background: linear-gradient(180deg, #171718 0%, #111112 100%) !important;
      border-bottom: 1px solid rgba(255,255,255,.08);
      display: flex;
      flex-direction: column;
      justify-content: center;
      color: #f5f5f7 !important;
    }
    .section-card-head,
    .section-card-head * {
      color: #f5f5f7 !important;
    }
    .section-card-head .panel-title,
    [data-testid="stMarkdownContainer"] .section-card-head .panel-title {
      color: #f5f5f7 !important;
      font-size: 1rem !important;
      margin: 0 !important;
      font-weight: 700 !important;
    }
    .section-card-head .panel-sub,
    .section-card-head p,
    .section-card-head p.panel-sub,
    [data-testid="stMarkdownContainer"] .section-card-head .panel-sub,
    [data-testid="stMarkdownContainer"] .section-card-head p {
      color: rgba(245,245,247,.72) !important;
      font-size: .82rem !important;
      margin: .28rem 0 0 !important;
    }
    .agent-shell-head,
    .agent-shell-head * {
      color: #f5f5f7 !important;
    }
    .agent-shell-head .agent-title {
      color: #f5f5f7 !important;
    }
    .agent-shell-head .agent-copy,
    .agent-shell-head p {
      color: rgba(245,245,247,.72) !important;
    }
    .page-hero,
    .page-hero *,
    .hero-entry,
    .hero-entry * {
      color: #f5f5f7 !important;
    }
    .page-hero .page-kicker,
    .page-hero .hero-stat-label,
    .hero-entry .hero-kicker,
    .hero-entry .hero-stat-label {
      color: rgba(245,245,247,.62) !important;
    }
    .page-hero .page-copy,
    .hero-entry .hero-copy {
      color: rgba(245,245,247,.72) !important;
    }
    .page-hero .page-title,
    .page-hero .hero-stat-value,
    .hero-entry .hero-title,
    .hero-entry .hero-stat-value {
      color: #ffffff !important;
    }

    .panel {
      background: var(--panel);
      border: 1px solid rgba(0,0,0,.06);
      border-radius: var(--radius);
      padding: 1.2rem 1.25rem;
      box-shadow: var(--shadow-soft);
      margin-bottom: 1rem;
    }
    .panel-title { font-size: 1rem; font-weight: 700; letter-spacing: -0.015em; color: var(--ink); margin: 0 0 .25rem; }
    .panel-sub { color: var(--muted); font-size: .82rem; margin: 0 0 .85rem; line-height: 1.45; }

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
    }

    .pill {
      display: inline-flex; align-items: center; border-radius: 999px; padding: .22rem .58rem;
      background: var(--accent-soft); color: var(--ink); font-size: .72rem; font-weight: 650;
      margin: .12rem .18rem .12rem 0;
    }
    .pill.missing { background: #f5f5f7; color: #6e6e73; }

    .board-list-item, .job-card, .detail-toolbar, .answer-panel, .cluster-card, .agent-shell, .empty-card {
      background: #fff; border: 1px solid rgba(0,0,0,.06); border-radius: 16px;
    }
    .board-list-item { padding: .78rem .85rem; margin-bottom: .45rem; }
    .board-list-item.active {
      border-color: rgba(0,0,0,.18);
      box-shadow: 0 0 0 3px rgba(0,0,0,.06);
    }
    .board-list-company { color: var(--muted); font-size: .7rem; font-weight: 600; }
    .board-list-title { color: var(--ink); font-size: .92rem; font-weight: 700; margin-top: .12rem; letter-spacing: -0.01em; }
    .board-list-meta { display: flex; flex-wrap: wrap; gap: .28rem; margin-top: .35rem; align-items: center; }
    .board-list-tag {
      background: var(--soft); color: var(--muted); border-radius: 999px;
      padding: .12rem .42rem; font-size: .66rem; font-weight: 600;
    }
    .board-list-score {
      margin-left: auto; color: var(--ink); font-weight: 700; font-size: .9rem;
      font-variant-numeric: tabular-nums;
    }

    .detail-toolbar {
      display: flex; justify-content: space-between; align-items: center;
      padding: .7rem .85rem; margin-bottom: .7rem;
    }
    .detail-label { color: var(--muted); font-size: .68rem; font-weight: 650; letter-spacing: .04em; }
    .detail-badge {
      background: var(--accent-soft); color: var(--ink); border-radius: 999px;
      padding: .18rem .5rem; font-size: .68rem; font-weight: 650;
    }
    .detail-title {
      font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em;
      color: var(--ink); margin: .15rem 0; line-height: 1.15;
    }
    .detail-company, .detail-meta, .detail-copy { color: var(--muted); font-size: .86rem; }
    .detail-meta { display: flex; flex-wrap: wrap; gap: .7rem; margin: .45rem 0 .8rem; }
    .detail-score-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: .55rem; margin: .7rem 0 1rem; }
    .detail-score { background: var(--soft); border: 0; border-radius: 14px; padding: .6rem .7rem; }
    .detail-score-label { display: block; color: var(--muted); font-size: .66rem; }
    .detail-score-value {
      display: block; color: var(--ink); font-size: 1rem; font-weight: 700; margin-top: .12rem;
      letter-spacing: -0.015em; font-variant-numeric: tabular-nums;
    }
    .detail-section { margin-top: .85rem; }
    .detail-section-title { font-size: .8rem; font-weight: 700; color: var(--ink); margin-bottom: .3rem; }

    .job-card {
      display: grid; grid-template-columns: 40px 1fr auto; gap: .8rem;
      padding: .95rem 1rem; margin-bottom: .65rem;
    }
    .job-index {
      width: 34px; height: 34px; border-radius: 11px; background: var(--soft); color: var(--ink);
      display: grid; place-items: center; font-weight: 700;
    }
    .job-kicker { color: var(--muted); font-size: .7rem; }
    .job-title { color: var(--ink); font-size: 1rem; font-weight: 700; margin-top: .08rem; letter-spacing: -0.015em; }
    .job-meta { color: var(--muted); font-size: .72rem; margin-top: .22rem; }
    .job-tags { margin-top: .4rem; }
    .job-source {
      display: inline-block; margin-top: .5rem; color: var(--link);
      font-size: .78rem; font-weight: 600; text-decoration: none;
    }
    .job-score { text-align: right; min-width: 86px; }
    .score-number {
      color: var(--ink); font-size: 1.28rem; font-weight: 700;
      letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
    }
    .score-label { color: var(--muted); font-size: .66rem; }

    .cluster-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
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
    .agent-badge {
      display: inline-flex; margin-top: .55rem; background: rgba(255,255,255,.12); color: #f5f5f7;
      border-radius: 999px; padding: .18rem .55rem; font-size: .7rem; font-weight: 650;
      border: 1px solid rgba(255,255,255,.14);
    }
    .agent-badge.local { background: rgba(255,255,255,.08); color: rgba(245,245,247,.7); }
    .answer-panel { padding: 1rem; color: var(--ink); line-height: 1.6; margin: .55rem 0; }
    .call-chain { display: flex; flex-wrap: wrap; gap: .32rem; align-items: center; margin: .45rem 0 .9rem; }
    .call-step {
      background: var(--accent-soft); color: var(--ink); border-radius: 999px;
      padding: .22rem .55rem; font-size: .72rem; font-weight: 650;
    }
    .call-arrow { color: var(--muted); }

    .chat-shell {
      background: #fff;
      border: 1px solid rgba(0,0,0,.07);
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
      margin: .2rem 0 1rem;
      min-height: 0;
      display: flex;
      flex-direction: column;
    }
    .chat-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .8rem;
      padding: .85rem 1.1rem;
      border-bottom: 1px solid rgba(0,0,0,.06);
      background: #fafafa;
    }
    .chat-toolbar-title {
      font-size: .95rem;
      font-weight: 700;
      color: var(--ink);
      letter-spacing: -0.015em;
    }
    .chat-toolbar-sub {
      color: var(--muted);
      font-size: .78rem;
      margin-top: .15rem;
    }
    .chat-thread {
      /* base; agent page enhances below */
      padding: .9rem 1.15rem .35rem;
      min-height: 0;
      max-height: 420px;
      overflow-y: auto;
      background: #fff;
    }
    .chat-row {
      display: flex;
      margin: 0 0 .9rem;
    }
    .chat-row.user { justify-content: flex-end; }
    .chat-row.assistant { justify-content: flex-start; }
    .chat-bubble {
      max-width: min(760px, 88%);
      border-radius: 18px;
      padding: .85rem 1rem;
      line-height: 1.55;
      font-size: .95rem;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .chat-bubble.user {
      background: #111112;
      color: #f5f5f7;
      border-bottom-right-radius: 8px;
    }
    .chat-bubble.assistant {
      background: #f4f4f6;
      color: var(--ink);
      border: 1px solid rgba(0,0,0,.05);
      border-bottom-left-radius: 8px;
    }
    .chat-meta {
      margin-top: .45rem;
      color: var(--muted);
      font-size: .72rem;
    }
    .chat-empty {
      color: var(--muted);
      text-align: center;
      padding: 2.4rem 1rem .35rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .chat-empty-title {
      color: var(--ink);
      font-size: clamp(1.85rem, 3.4vw, 2.55rem);
      font-weight: 750;
      letter-spacing: -0.03em;
      margin-bottom: 1.1rem;
      line-height: 1.15;
    }
    .agent-mini-note {
      color: var(--muted);
      font-size: .8rem;
      padding-top: .45rem;
    }
    /* Agent stage: one calm surface */
    div[data-testid="stVerticalBlock"]:has(.agent-page-mark) {
      /* keep default */
    }
    .agent-stage-note {
      display: none;
    }
    /* Suggestion cards: ONLY the row immediately after agent-suggest-wrap */
    div[data-testid="stElementContainer"]:has(.agent-suggest-wrap) + div[data-testid="stHorizontalBlock"] .stButton > button,
    div[data-testid="element-container"]:has(.agent-suggest-wrap) + div[data-testid="stHorizontalBlock"] .stButton > button {
      background: #ffffff !important;
      color: #1d1d1f !important;
      border: 1px solid rgba(0,0,0,.08) !important;
      border-radius: 18px !important;
      box-shadow: 0 10px 28px rgba(0,0,0,.05) !important;
      min-height: 78px !important;
      height: auto !important;
      padding: .95rem 1rem !important;
      text-align: left !important;
      justify-content: flex-start !important;
      white-space: normal !important;
      line-height: 1.45 !important;
      font-size: .92rem !important;
      font-weight: 560 !important;
      letter-spacing: -0.01em !important;
    }
    div[data-testid="stElementContainer"]:has(.agent-suggest-wrap) + div[data-testid="stHorizontalBlock"] .stButton > button:hover,
    div[data-testid="element-container"]:has(.agent-suggest-wrap) + div[data-testid="stHorizontalBlock"] .stButton > button:hover {
      background: #f7f7f8 !important;
      border-color: rgba(0,0,0,.14) !important;
    }
    /* Protect clear button in mini bar */
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(.agent-mini-note) .stButton > button:not([kind="primary"]) {
      background: #ffffff !important;
      color: #1d1d1f !important;
      border: 1px solid rgba(0,0,0,.1) !important;
      border-radius: 999px !important;
      box-shadow: none !important;
      min-height: 40px !important;
      height: 40px !important;
      padding: 0 .9rem !important;
      font-size: .85rem !important;
      font-weight: 600 !important;
      justify-content: center !important;
      text-align: center !important;
      white-space: nowrap !important;
      line-height: 1 !important;
    }
    /* Final top-nav shield: always win over agent suggestion styles */
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .stButton > button,
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(.brand-name) .stButton > button,
    div[data-testid="stVerticalBlock"]:has(.agent-page-mark) div[data-testid="stHorizontalBlock"]:has(.brand-name) .stButton > button {
      background: transparent !important;
      border: 0 !important;
      box-shadow: none !important;
      color: #ffffff !important;
      opacity: 0.74 !important;
      border-radius: 0 !important;
      min-height: 72px !important;
      height: 72px !important;
      width: 100% !important;
      padding: 0 .2rem !important;
      font-size: clamp(0.98rem, 1.2vw, 1.15rem) !important;
      font-weight: 650 !important;
      justify-content: center !important;
      text-align: center !important;
      white-space: nowrap !important;
      line-height: 1 !important;
      letter-spacing: -0.01em !important;
      transform: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .stButton > button:hover,
    div[data-testid="stVerticalBlock"]:has(.agent-page-mark) div[data-testid="stHorizontalBlock"]:has(.brand-name) .stButton > button:hover {
      opacity: 1 !important;
      background: transparent !important;
      color: #ffffff !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .topbar-link,
    div[data-testid="stVerticalBlock"]:has(.agent-page-mark) div[data-testid="stHorizontalBlock"]:has(.brand-name) .topbar-link {
      color: #ffffff !important;
      opacity: 1 !important;
      visibility: visible !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-name) .nav-status,
    div[data-testid="stVerticalBlock"]:has(.agent-page-mark) div[data-testid="stHorizontalBlock"]:has(.brand-name) .nav-status {
      display: inline-flex !important;
      visibility: visible !important;
      opacity: 1 !important;
    }
    /* Solid floating composer: target container that has anchor but not the whole page mark */
    div[data-testid="stVerticalBlock"]:has(.composer-anchor):not(:has(.agent-page-mark)) {
      position: sticky !important;
      bottom: 14px !important;
      z-index: 40 !important;
      margin: 1.25rem auto .7rem !important;
      padding: 1.05rem 1.1rem .9rem !important;
      background: #ffffff !important;
      border: 1px solid rgba(0,0,0,.16) !important;
      border-radius: 28px !important;
      box-shadow: 0 22px 60px rgba(0,0,0,.18) !important;
      max-width: 860px !important;
    }
    div[data-testid="stVerticalBlock"]:has(.composer-anchor):not(:has(.agent-page-mark)) [data-testid="stTextArea"] > div,
    div[data-testid="stVerticalBlock"]:has(.composer-anchor):not(:has(.agent-page-mark)) [data-baseweb="textarea"],
    div[data-testid="stVerticalBlock"]:has(.composer-anchor):not(:has(.agent-page-mark)) textarea {
      border: 0 !important;
      box-shadow: none !important;
      background: #ffffff !important;
      color: #1d1d1f !important;
      font-size: 1.05rem !important;
      line-height: 1.5 !important;
      caret-color: #1d1d1f !important;
    }
    div[data-testid="stVerticalBlock"]:has(.composer-anchor):not(:has(.agent-page-mark)) textarea::placeholder {
      color: #8e8e93 !important;
      opacity: 1 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.composer-anchor):not(:has(.agent-page-mark)) .stButton > button {
      width: 44px !important;
      min-width: 44px !important;
      height: 44px !important;
      min-height: 44px !important;
      border-radius: 999px !important;
      padding: 0 !important;
      font-size: 1.08rem !important;
      font-weight: 700 !important;
      background: #1d1d1f !important;
      color: #ffffff !important;
      border: 0 !important;
    }
    .agent-suggest-wrap { display: block; height: 0; overflow: hidden; }
    div[data-testid="stElementContainer"]:has(.agent-suggest-wrap) + div[data-testid="stHorizontalBlock"],
    div[data-testid="element-container"]:has(.agent-suggest-wrap) + div[data-testid="stHorizontalBlock"] {
      max-width: 760px !important;
      margin-left: auto !important;
      margin-right: auto !important;
    }
    /* Chat thread card when there are messages */
    .chat-thread {
      max-width: 860px;
      margin: .4rem auto 0;
      padding: 1rem 1.1rem .2rem;
      background: #ffffff;
      border: 1px solid rgba(0,0,0,.08);
      border-radius: 24px;
      box-shadow: 0 10px 30px rgba(0,0,0,.06);
      min-height: 180px;
      max-height: 460px;
      overflow-y: auto;
    }
    .composer-footer {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: .45rem;
      margin-top: .1rem;
    }
    .composer-model {
      display: inline-flex;
      align-items: center;
      gap: .35rem;
      margin: 0;
      padding: .34rem .7rem;
      border-radius: 999px;
      background: #f2f2f4;
      border: 1px solid rgba(0,0,0,.08);
      color: #3a3a3c;
      font-size: .78rem;
      font-weight: 650;
      white-space: nowrap;
      height: 36px;
    }
    .composer-model-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #34c759;
    }
    /* Hide agent page footnote for cleaner chat stage */
    div[data-testid="stVerticalBlock"]:has(.agent-page-mark) ~ div .footnote,
    div[data-testid="stVerticalBlock"]:has(.agent-page-mark) .footnote {
      display: none !important;
    }

    .empty-card {
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
    .empty-copy { margin-top: .55rem; max-width: 42ch; line-height: 1.5; }
    .footnote { color: #86868b; font-size: .72rem; margin-top: 1.4rem; text-align: center; }

    @media (prefers-reduced-transparency: reduce) {
      .topbar { background: #fbfbfd; backdrop-filter: none; }
    }
    @media (max-width: 1100px) {
      .metrics, .cluster-grid, .detail-score-row, .hero-stats { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 720px) {
      .hero-stats, .metrics { grid-template-columns: 1fr; }
      .hero-title { max-width: none; }
    }
    </style>
    """
)


def call_api(method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    try:
        timeout = kwargs.pop("timeout", API_TIMEOUT)
        response = requests.request(method, f"{API_URL}{path}", timeout=timeout, **kwargs)
        payload = response.json()
        if response.status_code >= 400:
            raise RuntimeError(payload.get("detail", response.text))
        return payload
    except Exception as exc:
        raise RuntimeError(f"API 请求失败：{exc}") from exc


def _safe(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return html.escape(str(value))


def _clean_display_text(value: Any, limit: Optional[int] = None) -> str:
    text_value = str(value or "")
    text_value = re.sub(r"[#*_`>~]+", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if limit is not None and len(text_value) > limit:
        text_value = text_value[:limit].rstrip() + "…"
    return text_value


def _pills(items: Iterable[Any], missing: bool = False, limit: int = 8) -> str:
    class_name = "pill missing" if missing else "pill"
    values = [str(item) for item in items if str(item).strip()]
    return "".join(f'<span class="{class_name}">{_safe(item)}</span>' for item in values[:limit])


@st.cache_data(show_spinner=False)
def load_featured_jobs(limit: int = 8) -> List[Dict[str, Any]]:
    frame = pd.read_parquet(PROJECT_ROOT / "data/processed/jobs_cleaned.parquet")
    frame = frame[frame["job_title"].fillna("").str.strip().ne("")].copy()
    frame["quality_score"] = pd.to_numeric(frame.get("quality_score"), errors="coerce").fillna(0)
    chosen: List[pd.Series] = []
    for _, group in frame.groupby(frame["broad_category"].fillna("Other"), sort=True):
        chosen.append(group.sort_values(["quality_score", "job_title"], ascending=[False, True]).iloc[0])
    if len(chosen) < limit:
        remaining = frame.sort_values(["quality_score", "job_title"], ascending=[False, True])
        for i in range(len(remaining)):
            row = remaining.iloc[i]
            if any(str(existing.get("job_id")) == str(row.get("job_id")) for existing in chosen):
                continue
            chosen.append(row)
            if len(chosen) >= limit:
                break
    return [row.to_dict() for row in chosen[:limit]]


def _job_score(job: Dict[str, Any], matched: bool) -> str:
    value = job.get("match_score") if matched else job.get("quality_score")
    if value in (None, ""):
        value = job.get("similarity", job.get("faiss_score"))
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def render_empty(title: str, copy: str, icon: str = "○") -> None:
    st.markdown(
        (
            '<div class="empty-card">'
            f'<div class="empty-kicker">{_safe(icon)}</div>'
            f'<div class="empty-title">{_safe(title)}</div>'
            f'<div class="empty-copy">{_safe(copy)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_page_header(kicker: str, title: str, copy: str, stats: list | None = None) -> None:
    stats_html = ""
    if stats:
        cells = []
        for label, value in stats:
            cells.append(
                "<div class=\"hero-stat\">"
                f"<div class=\"hero-stat-label\">{_safe(label)}</div>"
                f"<div class=\"hero-stat-value\">{_safe(value)}</div>"
                "</div>"
            )
        stats_html = "<div class=\"hero-stats\">" + "".join(cells) + "</div>"
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
    )


def render_job_detail(job: Dict[str, Any], matched: bool = False, sample: bool = False) -> None:
    title = _clean_display_text(job.get("job_title") or "未命名岗位")
    company = _clean_display_text(job.get("company_name") or "未披露公司")
    district = job.get("district") or job.get("city") or "Remote"
    category = job.get("broad_category") or job.get("job_category") or "类别未识别"
    description = _clean_display_text(
        job.get("description_clean") or job.get("job_description") or "暂无岗位描述。",
        limit=720,
    )
    skills = job.get("matched_skills") or []
    if not skills:
        raw_skills = job.get("skills_normalized") or job.get("skills") or ""
        skills = [item.strip() for item in str(raw_skills).replace("，", "|").split("|") if item.strip()]
    skill_html = _pills(skills, limit=10) or '<span class="pill missing">暂无明确技能标签</span>'
    source = str(job.get("source_url") or "").strip()
    source_html = (
        f'<a class="job-source" href="{html.escape(source, quote=True)}" target="_blank">打开来源链接 ↗</a>'
        if source
        else ""
    )
    badge = "本地样本" if sample else "匹配结果"
    score_label = "匹配分" if matched else "信息质量分"
    score = _job_score(job, matched)
    match_detail = job.get("explanation") or "输入简历后，这里会显示技能、类别、经验和地点的匹配解释。"
    st.markdown(
        f"""
        <div class="detail-toolbar">
          <span class="detail-label">岗位详情</span>
          <span class="detail-badge">{_safe(badge)}</span>
        </div>
        <div class="detail-title">{_safe(title)}</div>
        <div class="detail-company">{_safe(company)} · {_safe(category)}</div>
        <div class="detail-meta">
          <span>{_safe(district)}</span>
          <span>{_safe(job.get("experience_raw") or "经验见原岗位")}</span>
          <span>Remote</span>
        </div>
        <div class="detail-score-row">
          <div class="detail-score"><span class="detail-score-label">{_safe(score_label)}</span><span class="detail-score-value">{_safe(score)}</span></div>
          <div class="detail-score"><span class="detail-score-label">技能交集</span><span class="detail-score-value">{len(job.get("matched_skills") or skills)}</span></div>
          <div class="detail-score"><span class="detail-score-label">薪资参考</span><span class="detail-score-value">{_safe(job.get("salary_raw") or "未披露")}</span></div>
        </div>
        <div class="detail-section"><div class="detail-section-title">岗位技能</div><div class="job-tags">{skill_html}</div></div>
        <div class="detail-section"><div class="detail-section-title">岗位描述</div><div class="detail-copy">{_safe(description)}</div></div>
        <div class="detail-section"><div class="detail-section-title">匹配说明</div><div class="detail-copy">{_safe(match_detail)}</div></div>
        <div class="detail-actions">{source_html}</div>
        """,
        unsafe_allow_html=True,
    )


def render_job_board(result: Optional[Dict[str, Any]]) -> None:
    matched = bool(result)
    jobs = (result or {}).get("results", []) if result else load_featured_jobs()
    if not jobs:
        render_empty("暂无岗位结果", "先上传或粘贴简历，再点“开始匹配”。")
        return
    categories = sorted({str(job.get("broad_category") or "Other") for job in jobs})
    left, right = st.columns([1.05, 1.45], gap="large")
    with left:
        st.markdown(
            '<div class="panel-title">岗位列表</div><p class="panel-sub">先筛类别，再选择岗位查看详情。</p>',
            unsafe_allow_html=True,
        )
        category_filter = st.selectbox("岗位类别", ["全部岗位", *categories], key="board_category_filter")
        filtered = (
            jobs
            if category_filter == "全部岗位"
            else [job for job in jobs if str(job.get("broad_category") or "Other") == category_filter]
        )
        filtered = sorted(
            filtered,
            key=lambda item: float(item.get("match_score") or item.get("quality_score") or 0),
            reverse=True,
        ) or jobs[:1]
        options = [
            f'{index:02d} · {_clean_display_text(job.get("job_title") or "未命名岗位", limit=42)} · {_job_score(job, matched)}'
            for index, job in enumerate(filtered, 1)
        ]
        selected_option = st.selectbox("选择岗位", options, index=0, key="board_job_select")
        selected_index = max(0, options.index(selected_option))
        preview = filtered[selected_index]
        preview_skills = preview.get("matched_skills") or str(preview.get("skills_normalized") or "").split("|")[:4]
        preview_tags = "".join(
            f'<span class="board-list-tag">{_safe(item)}</span>' for item in preview_skills if str(item).strip()
        )
        st.markdown(
            f'<div class="board-list-item active"><div class="board-list-company">{_safe(_clean_display_text(preview.get("company_name") or "未披露公司"))}</div><div class="board-list-title">{_safe(_clean_display_text(preview.get("job_title") or "未命名岗位"))}</div><div class="board-list-meta"><span class="board-list-tag">{_safe(preview.get("district") or "Remote")}</span>{preview_tags}<span class="board-list-score">{_job_score(preview, matched)}</span></div></div>',
            unsafe_allow_html=True,
        )
        st.caption(f"当前列表共 {len(filtered)} 个岗位。")
    with right:
        st.markdown(
            '<div class="panel-title">岗位详情</div><p class="panel-sub">匹配分、技能和来源都在这里。</p>',
            unsafe_allow_html=True,
        )
        render_job_detail(filtered[selected_index], matched=matched, sample=not matched)


def render_job(job: Dict[str, Any], index: int, score_label: str = "匹配分") -> None:
    matched = job.get("matched_skills") or []
    missing = job.get("missing_skills") or []
    score = job.get("match_score")
    if score is None:
        score = job.get("faiss_score", job.get("similarity", 0))
    try:
        score_text = f"{float(score):.4f}" if score_label == "检索相似度" else f"{float(score):.2f}"
    except (TypeError, ValueError):
        score_text = "—"
    source = job.get("source_url") or ""
    source_link = (
        f'<a class="job-source" href="{html.escape(str(source), quote=True)}" target="_blank">查看来源 ↗</a>'
        if source
        else ""
    )
    tag_html = _pills(matched) + _pills(missing, missing=True, limit=6)
    if not tag_html:
        tag_html = '<span class="pill missing">暂无明确技能交集</span>'
    st.markdown(
        f"""
        <div class="job-card">
          <div class="job-index">{index:02d}</div>
          <div>
            <div class="job-kicker">{_safe(_clean_display_text(job.get("company_name") or "未披露公司"))} · {_safe(job.get("district") or "Remote")}</div>
            <div class="job-title">{_safe(_clean_display_text(job.get("job_title") or "未命名岗位"))}</div>
            <div class="job-meta">采集时间 · {_safe(job.get("crawl_time") or "—")}</div>
            <div class="job-tags">{tag_html}</div>
            {source_link}
          </div>
          <div class="job-score">
            <div class="score-number">{score_text}</div>
            <div class="score-label">{_safe(score_label)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_clusters(clusters: List[Dict[str, Any]]) -> None:
    cards = []
    for item in clusters:
        skills = item.get("top_skills") or item.get("skills") or []
        if isinstance(skills, list):
            skill_text = "、".join(
                (_clean_display_text(x.get("skill") if isinstance(x, dict) else x) for x in skills[:5])
            )
        else:
            skill_text = _clean_display_text(skills)
        cats = item.get("top_job_categories") or item.get("top_categories") or item.get("categories") or []
        if isinstance(cats, list):
            cat_text = "、".join(str(x.get("category") if isinstance(x, dict) else x) for x in cats[:4])
        else:
            cat_text = str(cats)
        if not cat_text:
            dist = item.get("category_distribution") or {}
            if isinstance(dist, dict) and dist:
                cat_text = "、".join(list(dist.keys())[:4])
        cards.append(
            (
                '<div class="cluster-card">'
                f'<div class="cluster-name">{_safe(_clean_display_text(item.get("business_name") or ("Cluster " + str(item.get("cluster_id")))))}</div>'
                f'<div class="cluster-count">{_safe(item.get("job_count") or item.get("count") or 0)} 个岗位</div>'
                f'<div class="cluster-skills">主要技能：{_safe(skill_text or "—")}</div>'
                f'<div class="cluster-cats">主要类别：{_safe(cat_text or "—")}</div>'
                "</div>"
            )
        )
    st.markdown('<div class="cluster-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def fetch_health() -> Optional[Dict[str, Any]]:
    try:
        return call_api("GET", "/api/health")
    except Exception:
        return None


@st.cache_data(ttl=30, show_spinner=False)
def fetch_agent_runtime() -> Dict[str, Any]:
    try:
        return call_api("GET", "/api/agent_runtime")
    except Exception:
        return {}



def queue_agent_send() -> None:
    """Enqueue chat only when the send button is clicked."""
    typed = str(st.session_state.get("agent_draft") or "").strip()
    if typed:
        st.session_state["agent_send_request"] = typed

def display_model_name(runtime: Optional[Dict[str, Any]] = None, result: Optional[Dict[str, Any]] = None) -> str:
    """UI-facing model label. Do not expose provider marketing names."""
    return "gpt-5.6-sol"


def run_match(resume_text: str, uploaded, preferred: str, top_k: int) -> None:
    if uploaded is not None:
        params: Dict[str, Any] = {"top_k": top_k}
        if preferred.strip():
            params["preferred_locations"] = preferred.strip()
        response = requests.post(
            f"{API_URL}/api/match/upload",
            files={"file": (uploaded.name, uploaded.getvalue())},
            params=params,
            timeout=API_TIMEOUT,
        )
        if response.status_code >= 400:
            raise RuntimeError(response.json().get("detail", response.text))
        st.session_state.match_result = response.json()
        return
    if resume_text.strip():
        st.session_state.match_result = call_api(
            "POST",
            "/api/match",
            json={
                "resume_text": resume_text,
                "top_k": top_k,
                "preferred_locations": [preferred] if preferred.strip() else None,
            },
        )
        return
    raise RuntimeError("请先粘贴简历，或上传 TXT/PDF 文件")


health = fetch_health()
health_count = int(health.get("data_records", 0)) if health else 0
health_label = f"{health_count:,} 条岗位在线" if health else "API 未连接"
status_dot = "" if health else " off"

valid_pages = {key for key, _ in NAV_ITEMS}
page = st.query_params.get("page", "match")
if page not in valid_pages:
    page = "match"

# MoodTune-style single-row topbar: brand | centered labels | status
brand_col, nav_col, status_col = st.columns([1.2, 2.0, 1.2], gap="small")
with brand_col:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-mark" aria-hidden="true">
            <img class="brand-symbol" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAH10lEQVR4nO1azY8cRxWvj/6cXu/OhjgYlAgSWUBwiALGMgkCrfEiWQooCCRLAYOEkKJwQPkLwL7BCcEFJLjAdSVOECnkssMBn8wFbAErlBWW1uNZze5Mf1RXd1V1F3o91XbveD27qzXeTWZ+Um9Xd716/T6q3ntVswjNMMMMM8wwwwwzzDCdwEfxUa01fBcu3ZBDY4zr58cGgo4IGOMyjtkvGOO/hPZROcM6As8D5nq94YcRQi+C43u93mmEUFdrnR7FLHhs0FpXBg/D+K2iKFQcszxJ0hzaSZJ8z9BQ9EGE1rpabv1+/3nO82GeC50kaQmXEFJznvW2t7c/BrOkpv2gxQACf1y39ZbnOQtSKokNhJDS89ynbNv9oVkC5H0bA/RondcKlI01DYEOEYI+adpNJaFdYkyer9nsg98jAXmUzGDqgoAY48JcujGdq3tZ6v9AW2tdNMZBm2hd/tu8wvvgd7ygTYS/ceNGi3P+lTjmF1ZXV726DwSHe7e79QLnWQaa1DEA2mnKw7t37z5X0169erVS9ObNm3Oc84txHC+trKw4zW8dG2jjlSiKvpTnYk0b5Ln4V78fnq9p7gfC4bKU8u+cZ5LzXEopb/R6W6+M0w0G8QUhxHs1PyHEPxhjZ5vfPHLokcfw7du3n2As3TSelXCZ9sZgMGjXdHWa29jYeDJNM8YYj9fX19uGF63per3eKcb4YJxfHLP1brcb1HSHlZ8clkGn06GwNufn55dbLf8kYxyiuwUXtIPA/yilzsVmdAdFg2DhrOs6Ldd15hYXF881PFrxC4Lg1VbLa4PiNb8k4WpurvVx3/e/+KiyBTksg6WlpeqOsXVvvY/TYIz9ujl6xAVC5SVCMKKUIELoV8fLYTMGAmCD04h3WZYVv06ng488DV67dq1Kb0UhOpxbyvc9i/OsSlW+79tpmmV5nnaMYYC2iuRxzC4WhUYj/ciy6YdsUL1RSr2bZUI7jmMLIYCfDoIWTVOeZFl2vUF/9NBm+sZx/G0hZJymWZGmmZJSRcPh8HXoW1lZoY1g+SnOM8UYL9M0gypQDIfD0+NBcDgcviGlTIEX53mR52IQRdFrzW8+TiUx1PLm2jH16sAGKS7L8mGWiSLLcnnnzp0vN/vrvQBj/M0Hg2Xy/SZNfd/c3H41z0UJPDnPNrvdwbO7GWCSfJNA9ql8XZAoc90rSMy97Ha7T7XbwTu2bS8opZTrOlYQnPi86a8FqpZGWRbL5rkhKL7YpKmVcl37vOPYWEqpPM89ubDg/bnf789Df10rTJLv0NDGmpC24ji9kqbp6420BdMVpjZNEvYXk6ZUkqSFUkWVsrTWTjNlQQqLItaVstCM8WJEW+ooiv+7trbmNhXr9XpzjPGelKoqmoC3+cafoH91tfJ2Rbu2tnYyTdMrcbxDvsMFSX1/LZ7Lc7FRFyRZlq9vb29/pp6mcZz8aiRYKhnjoBgIrMqy1GEYfs0IWCk3GAyWwDigeE0LhoAdYb/fP9+kDcPwiuGrGnyrJTMchj8zMlIY15Qvz8V7W1vxmUPvLLXxcByzvxnLw/7dlLHsryPjxD+CZ8buK18bAN6HYfSO4VWVsXHMflqv/3Gloij5saG14R5F8XUwIvBq8ob6YsQ7/O6Ijt00PO/JF0XJ6n4MQCYpD7k5TdNThJAznOewEwPBnKKAdEaeiSL2mu+7P89zUWiNdhxkYIwpRHjXdZfjOD4Du97RlMTLWo+KgSZ5JQyhVRzAGEvG2Bc8z3vZfHcHb3CKELJ0Xf/XYRh+nVJySggFsaOSL89lSQj5LEJoHnSYtBTI5AmgcavVGpSl3nacyimq+qMkwVjPEYJ+jzGxpFRgrAc+Ars813Wo1vgNeA7D7FlKyQt5LsajOBECWOvPJUnyEXhRluhN27aArqozxowLZwiYUhpQav8OZkxDSWnbNkZIbyKEUng/aQtNHtZRl5oY47Qo1DVKCQkC37YsC5dlCd5atCx7AYoUAiXd7qBSKqj2vrO6umohpM75vusVhYKtbbPqw0KIMgj8E0qhFyFQUkq/leey4rGr4ITgLMu1ZVlPUErntdYIZAsC3yEEYaXkT2Am7ZXprEmdULJCRG63538ThuFdz/N/IKU4ixAuHMd+BqIzxniSETEsj7m51odeeunsNxDSL5ueBzxiSmGCcfGK5wVP+74LGQBS2kNlJARjpVRp2xYRQq4jpF2M0XXOxW/b7fa7xvsTq0WM9gGo4i5fvlxA/vW81m2McWA8s+d4mMKu64Ah/omQ9lzXey7P80qycTrPcwnn2Rr0ua5zGs4NJxm4OZxSqoqi2Hr77T8+DbJCnNhL+X3vBW7dugXxgHLO22WJXUqppVTl/T3HggIwlW3b/jRMUyHEeABs0Amg+wQ8CyF3pdsNwJcQYhdF4V66dGlRaz2oj+D2AtkPkREQrFqMYuPBjuVADSmlBqPtRQs0+6Ebh5FJl2VZHZ8dux9G8D69uV+6RwWCphwETTkImnIQNOUgaMpB0JSDoCkHQVMOgqYcBE05rIMOwBjBUVd1enGMfqWtZIET4f+rATDGxHG8E5QeF713gjH+5EH/2wwfgA6sDL/9fxNjamld6LJ8vBuXh4EQDecBuCiK3Pf9P8AB01HL9L4BPuiA+reA44hOp4MuXLhw4DgwwwwzzDDDDDPMMMMMaPrwP/ZqQrIPrt+1AAAAAElFTkSuQmCC" alt="BOSS！求聘" />
          </div>
          <div class="brand-copy">
            <span class="brand-name">BOSS！求聘</span>
            <span class="brand-sub">远程人岗匹配</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with nav_col:
    nav_cols = st.columns(len(NAV_ITEMS), gap="small")
    for col, (key, label) in zip(nav_cols, NAV_ITEMS):
        with col:
            # Always use equal-width buttons so active/inactive spacing stays aligned.
            active = page == key
            if active:
                st.markdown('<div class="nav-active-slot"></div>', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True) and not active:
                st.query_params["page"] = key
                st.rerun()

with status_col:
    st.markdown(
        f'<div class="nav-status"><span class="status-dot{status_dot}"></span>{_safe(health_label)}</div>',
        unsafe_allow_html=True,
    )

if page == "match":
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

elif page == "rag":
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

elif page == "cluster":
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
    force_reload = st.session_state.pop("cluster_force_reload", False)
    clusters = st.session_state.get("cluster_results")
    if force_reload or not clusters:
        try:
            with st.spinner("思考中...."):
                clusters = call_api("GET", "/api/clusters").get("results", [])
            st.session_state["cluster_results"] = clusters
        except Exception as exc:
            st.session_state["cluster_results"] = []
            clusters = []
            st.error(f"画像加载失败：{exc}")
            if st.button("重新加载画像", type="primary"):
                st.session_state["cluster_force_reload"] = True
                st.session_state.pop("cluster_results", None)
                st.rerun()
            render_empty("岗位画像暂时不可用", "请确认后端 API 已启动，然后点击重新加载。")
    if clusters:
        render_clusters(clusters)
        if st.button("刷新画像"):
            st.session_state["cluster_force_reload"] = True
            st.session_state.pop("cluster_results", None)
            st.rerun()

else:
    st.markdown('<div class="agent-page-mark"></div>', unsafe_allow_html=True)
    runtime = fetch_agent_runtime()
    runtime_model = display_model_name(runtime)
    runtime_ready = bool(runtime.get("api_key_configured"))
    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []
    if "agent_draft" not in st.session_state:
        st.session_state.agent_draft = ""
    if "agent_use_real" not in st.session_state:
        st.session_state.agent_use_real = True

    # Process an explicitly queued send first. Never auto-send on draft/suggestion/toggle.
    pending_question = st.session_state.pop("agent_send_request", None)
    if pending_question:
        st.session_state.agent_messages.append({"role": "user", "content": pending_question})
        st.session_state.agent_draft = ""
        real = bool(st.session_state.agent_use_real)
        try:
            with st.spinner("思考中...."):
                result = call_api(
                    "POST",
                    "/api/chat",
                    json={"task": pending_question, "top_k": 3, "use_real_model": real},
                    timeout=REAL_AGENT_TIMEOUT if real else API_TIMEOUT,
                )
            answer = (
                result.get("answer")
                or result.get("final_answer")
                or result.get("explanation")
                or "没有返回文本结果。"
            )
            tools = []
            for call in result.get("tool_calls", []) or []:
                if isinstance(call, dict):
                    tools.append(call.get("tool") or call.get("name") or "tool")
                else:
                    tools.append(str(call))
            meta = "model={model} · {elapsed}s".format(
                model=display_model_name(runtime, result) if result.get("model_call") else "local-router",
                elapsed=result.get("elapsed_seconds", "—"),
            )
            st.session_state.agent_messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "meta": meta,
                    "tools": tools,
                    "raw": {
                        "tool_calls": result.get("tool_calls", []),
                        "tool_results": result.get("tool_results", []),
                        "elapsed_seconds": result.get("elapsed_seconds"),
                    },
                }
            )
        except Exception as exc:
            st.session_state.agent_messages.append(
                {
                    "role": "assistant",
                    "content": f"这次没有成功：{exc}",
                    "meta": "error",
                    "tools": [],
                }
            )
        st.rerun()

    messages = st.session_state.agent_messages
    # Keep agent page calm like Codex: no dark page hero.
    top_l, top_r = st.columns([3.6, 1.15], gap="small")
    with top_l:
        status_txt = "已接入" if runtime_ready else "未接入"
        st.markdown(
            f'<div class="agent-mini-note">助手 · {_safe(runtime_model)} · {status_txt}</div>',
            unsafe_allow_html=True,
        )
    with top_r:
        st.session_state.agent_use_real = st.toggle(
            "真实模型",
            value=bool(st.session_state.agent_use_real),
            help="关闭后使用本地规则路由",
        )
        if st.button("清空对话", use_container_width=True):
            st.session_state.agent_messages = []
            st.session_state.agent_draft = ""
            st.session_state.pop("agent_send_request", None)
            st.rerun()

    draft_preview = str(st.session_state.get("agent_draft") or "").strip()
    if not messages and not draft_preview:
        st.markdown(
            """
            <div class="chat-empty">
              <div class="chat-empty-title">有什么可以帮忙的？</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="agent-suggest-wrap"></div>', unsafe_allow_html=True)
        suggestion_cols = st.columns(2, gap="small")
        for idx, example in enumerate(AGENT_EXAMPLES):
            with suggestion_cols[idx % 2]:
                if st.button(example, key=f"agent_ex_{idx}", use_container_width=True):
                    # Fill only. Do not send / do not show 思考中.
                    st.session_state.agent_draft = example
                    st.rerun()
    elif messages:
        bubbles = []
        for item in messages:
            role = item.get("role", "assistant")
            content = _safe(item.get("content") or "")
            meta = item.get("meta") or ""
            meta_html = f'<div class="chat-meta">{_safe(meta)}</div>' if meta else ""
            tools = item.get("tools") or []
            tools_html = ""
            if tools:
                steps = []
                for name in tools:
                    if steps:
                        steps.append('<span class="call-arrow">→</span>')
                    steps.append(f'<span class="call-step">{_safe(name)}</span>')
                tools_html = f'<div class="call-chain">{"".join(steps)}</div>'
            bubbles.append(
                f'<div class="chat-row {role}"><div class="chat-bubble {role}">{content}{tools_html}{meta_html}</div></div>'
            )
        st.markdown('<div class="chat-thread">' + "".join(bubbles) + "</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="composer-anchor"></div>', unsafe_allow_html=True)
        st.text_area(
            "发送消息",
            height=88,
            key="agent_draft",
            label_visibility="collapsed",
            placeholder="询问远程岗位、技能匹配、聚类方向或检索问题…",
        )
        _spacer, model_col, send_col = st.columns([2.6, 1.35, 0.45], gap="small")
        with model_col:
            st.markdown(
                f'<div class="composer-footer"><div class="composer-model"><span class="composer-model-dot"></span>{_safe(runtime_model)}</div></div>',
                unsafe_allow_html=True,
            )
        with send_col:
            # secondary avoids Streamlit "Enter submits first primary button" behavior
            st.button(
                "↑",
                key="agent_send_btn",
                type="secondary",
                use_container_width=True,
                on_click=queue_agent_send,
            )

    # latest tool details for inspection
    for item in reversed(st.session_state.agent_messages):
        if item.get("role") == "assistant" and item.get("raw"):
            with st.expander("最近一次工具调用详情"):
                st.json(item["raw"])
            break


st.markdown(
    '<div class="footnote">匹配分用于岗位排序；信息质量分表示岗位信息完整度。当前岗位库来自 Himalayas 远程岗位数据。</div>',
    unsafe_allow_html=True,
)
