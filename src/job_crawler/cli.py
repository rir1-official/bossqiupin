import argparse
import json

from .config import load_config
from .himalayas import crawl_himalayas
from .pipeline import crawl, merge_and_dedupe, quality_summary, write_quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="公开招聘岗位采集与质量验收")
    commands = parser.add_subparsers(dest="command", required=True)
    crawl_parser = commands.add_parser("crawl", help="按配置采集公开 JSON 岗位页面")
    crawl_parser.add_argument("--config", required=True)
    crawl_parser.add_argument("--max-pages", type=int)
    crawl_parser.add_argument("--raw-dir", default="data/raw")
    merge_parser = commands.add_parser("merge", help="合并原始 JSONL 并去重")
    merge_parser.add_argument("--raw-dir", default="data/raw")
    merge_parser.add_argument("--output", default="data/raw/jobs_all.jsonl")
    quality_parser = commands.add_parser("quality", help="生成质量报告")
    quality_parser.add_argument("--input", required=True)
    quality_parser.add_argument("--report", default="reports/crawl_quality_report.md")
    himalayas_parser = commands.add_parser("crawl-himalayas", help="采集已获授权的 Himalayas 公开岗位 API")
    himalayas_parser.add_argument("--target-records", type=int, default=10000)
    himalayas_parser.add_argument("--delay-seconds", type=float, default=1.0)
    himalayas_parser.add_argument("--raw-dir", default="data/raw")
    himalayas_parser.add_argument("--state", default="logs/himalayas_state.json")
    himalayas_parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args()
    if args.command == "crawl":
        result = crawl(load_config(args.config), args.max_pages, args.raw_dir)
    elif args.command == "crawl-himalayas":
        result = crawl_himalayas(args.target_records, args.delay_seconds, args.raw_dir, args.state, args.timeout_seconds)
    elif args.command == "merge":
        result = merge_and_dedupe(args.raw_dir, args.output)
    else:
        result = quality_summary(args.input)
        write_quality_report(result, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
