# 特色数回题目生产系统

本项目用于编辑、验证、求解和生成两类数回：

- 经典方格数回；
- 以圆最密堆积为棋盘、同时包含圆单元格、圆隙三角形和 π 提示的特色数回。

软件采用统一图拓扑与精确约束求解。任何被判定为“唯一解”的题目都经过单闭环连通性验证，不会把多个互不相连的小环误认为答案。

新版生成器支持最长 30 分钟计算、强制包含 π 和四级目标难度选择；它会先返回可靠全提示基线，再利用贪心删减与反例驱动优化持续减少提示。

“练习模式”会隐藏题目文件中的目标曲线和答案，以独立临时状态记录玩家画线，提供重置、完整规则验证和计时，不会污染原题文件。

仓库同时包含移动优先的 React PWA。参与者扫描二维码后可在手机、平板或电脑上选择关卡，自动保存作答和计时，验证成功后生成截图凭证；网页题库不包含答案。公开题号采用 `TSH-年份-序号`，当前 20 道题为 `TSH-2026-01` 至 `TSH-2026-20`，后续年份的题目可继续追加并保留历史题库。

PWA 的学习中心包含三个独立教程：“数回基础”讲解画线、数字、顶点和单一闭环；“π 约束专题”通过点亮一个圆的六类弧、修正三个 π 区域的重复与缺失类型，以及相邻 π 区域公共弧只计一次的演示讲解特色规则；“π 小题引导”再用一道提示稀疏的简单题，引导玩家依次运用六方向、顶点和单一闭环规则完成推理。三个教程分别保存进度，均不计时并支持离线使用。

## 快速启动（Windows）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m shuhui
```

也可以运行 `scripts\run_gui.ps1`。命令行示例：

```powershell
.\.venv\Scripts\shuhui-cli.exe validate output\puzzles\easy\01.json
.\.venv\Scripts\shuhui-cli.exe solve output\puzzles\easy\01.json
.\.venv\Scripts\shuhui-cli.exe export-svg output\puzzles\easy\01.json -o puzzle.svg
```

## 主要目录

- `src/shuhui/`：数据模型、拓扑、求解器、生成器、GUI 和导出器；
- `tests/`：自动测试；
- `docs/`：规则、文件格式、用户与开发文档；
- `output/candidates/`：不少于 60 道经唯一性验证的候选题；
- `output/puzzles/`：共 20 道四级活动题；旧目录 `easy` 与 `medium` 合为初级，`hard`、`level-4`、`level-5` 依次为中级、高级、专家，其中高级与专家各 4 道；
- `output/pdf/`：可直接打印分发的 A4 题册与答案册，题面使用浅灰虚线，便于纸笔描线；
- `output/verification.json`：独立求解复验结果；
- `output/playtest-record.csv`：两名目标受众的试玩记录表。
- `web/`：跨平台活动游玩 PWA、网页验证器及浏览器测试；
- `.github/workflows/deploy-pages.yml`：自动测试并发布至 GitHub Pages；
- `scripts/start_web_lan.ps1`：现场局域网备用镜像与二维码服务。

## 质量状态

自动化部分可由 `pytest` 和验证报告复验。人工难度确认必须由活动组织方安排两名目标受众完成；在记录表填写前，题包元数据会保持 `pending_two_testers`，不会把自动评分冒充真人试玩结论。

详见 [规则与文件格式](docs/规则与文件格式.md)、[用户手册](docs/用户手册.md)、[开发说明](docs/开发说明.md)和[网页活动版](docs/网页活动版.md)。
