# Python 运行环境说明

## 结论

项目代码可以正常运行。2026 年 9 月 11 日出现的“Python 意外退出”不是 Python 语法错误，也不是岗位 Parquet 数据损坏，而是 macOS Command Line Tools 自带的 Python 3.9.6 在 PyTorch CPU/OpenMP 原生线程路径中发生 `SIGSEGV`。

崩溃报告位于：

- `~/Library/Logs/DiagnosticReports/Python-2026-09-11-155600.ips`
- `~/Library/Logs/DiagnosticReports/Python-2026-09-11-155719.ips`

报告中的进程是系统 `Python.app`，崩溃栈包含 PyTorch `index_select_out_cpu_` 和 OpenMP `__kmp_*`。这说明 Finder 双击 `.py` 或直接调用系统 Python 会绕过项目启动配置。

## 正确启动方式

在项目根目录执行：

```bash
./scripts/python.sh --version
PYTHON_DIAGNOSTICS=1 ./scripts/python.sh -c "import torch; print(torch.__version__)"
./scripts/python.sh -m unittest discover -s tests -v
```

运行 RAG：

```bash
HF_HUB_OFFLINE=1 ./scripts/python.sh -m job_analysis.rag_faiss search "Python 和 SQL 数据分析岗位" --top-k 3 --device auto
```

不要使用以下方式：

```bash
python3 src/job_analysis/rag_faiss.py
```

也不要在 Finder 中双击 `.py` 文件。统一入口会固定 `PYTHONPATH`，关闭 Tokenizers 并行，限制 OpenMP、MKL 和 Accelerate/vecLib 线程，并启用 MPS fallback，从而避开已确认的原生崩溃路径。

## 已验证状态

- 项目入口解释器：`.venv312/bin/python`
- Python：3.12.14 arm64
- PyTorch：2.8.0
- FAISS：1.13.0
- Sentence Transformers：3.4.1
- Apple MPS：可用
- RAG 正式运行：已完成，12,000 条岗位、55,984 个 Chunk、12 个测试问题
- 单元测试：14 项全部通过

`.venv312` 当前依赖已经安装完成。旧的 `.venv` 保留作为回退环境，但不再是项目默认入口。若未来迁移到另一台电脑，按 `README.md` 中的安装步骤创建 Python 3.12 虚拟环境，并始终通过 `scripts/python.sh` 运行。项目脚本还会优先加载依赖包自带的 `libomp.dylib`，不要求修改系统 Python 或安装 Homebrew。
