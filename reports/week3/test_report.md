# 系统测试与优化报告

## 结论

Week 3 接口回归测试共 14 项，14 项通过，0 项失败，耗时 14.623 秒。项目全量单元测试共 29 项，29 项通过，0 项失败。测试覆盖正常、边界和异常三条路径。

## 性能

- 优化前普通匹配中位数：13.1534 秒。
- 优化后冷启动首次匹配：13.3819 秒。
- 预热 Top-5 匹配中位数：0.1789 秒。
- 预热 Top-1 匹配中位数：0.2027 秒。
- 预热 Top-20 匹配中位数：0.2118 秒。

## 已修复

1. 复用 MatchingIndex，避免每次请求重建 12,000 条岗位的 TF-IDF 矩阵。
2. 增加纯空白简历校验和回归测试。
3. 新增可复跑的 Week 3 API 性能测量脚本和 JSON 结果。

## 部署状态

Docker 配置文件已完成，Compose 可解析。API 与前端容器均已启动，健康检查、FAISS+BGE 检索和 gpt-5.6-sol Responses Agent 真实工具调用均已验证。2026 年 9 月 20 日通过 Cloudflare Quick Tunnel 提供临时公网演示地址 `https://mesa-clip-weight-fleece.trycloudflare.com`，实测 HTTP 200。该地址依赖本机 Docker 与 cloudflared 进程持续运行，不等同于永久云服务器托管。
