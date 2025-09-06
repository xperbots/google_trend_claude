# Google Trends「Trending now」抓取程序：开发需求说明（供 AI 直接生成代码用）

> 目标：用**Python + 无头浏览器**（Headless Browser）从 Google Trends 的 **Trending now** 页面按国家/地区与筛选条件抓取热点话题，并以结构化文件输出。默认筛选值等同于截图中所示：United States / Past 24 hours / All categories / All trends / By relevance（见页面可用筛选与导出项）。([Google Trends][1])
> Trending now 支持 100+ 国家/地区，时间窗口包含 Past 4 hours、Past 24 hours、Past 48 hours、Past 7 days。([Google Help][2])

---

## 1. 技术选型与运行环境

* 语言：Python ≥ 3.10
* 浏览器自动化：**Playwright**（首选）或 Selenium（备选），要求**默认无头模式**可切换有头调试。
* 依赖（Playwright 方案示例）：`playwright`, `pydantic`, `typer`（或 `argparse`）, `pandas`。
* 操作系统：macOS / Linux / Windows 任意。

---

## 2. 入口与运行方式

实现一个可执行脚本（例如 `trends_trending_now.py`），既可 **CLI 命令行参数** 运行，也可 **Python 函数** 调用。

* 模块主函数：`run(params: FetchParams) -> list[TrendItem]`
* CLI：`python trends_trending_now.py [OPTIONS]`

---

## 3. 可配置参数（与页面下拉菜单一一对应）

> 如运行时**不给参数，则全部使用默认值**（与截图一致）。页面上的真实枚举与命名如下：**Select location / Past 24 hours / All categories / All trends / By relevance**，并提供导出 CSV / RSS。([Google Trends][1])

### 3.1 基本筛选

* `--geo`（字符串，默认：`United States`）

  * 对应页面 **Select location**。可接受国家/地区英文名或 ISO/Google Trends 使用的地区代码（若传代码则直接定位；传名称需在搜索框选择）。([Google Trends][1], [Google Help][2])
* `--time-window`（枚举，默认：`past_24_hours`）

  * 取值：`past_4_hours` / `past_24_hours` / `past_48_hours` / `past_7_days`。对应页面 **Past X hours/days**。([Google Trends][1], [Google Help][2])
* `--category`（枚举，默认：`all`）

  * 取值与页面一致：`all`, `autos_and_vehicles`, `beauty_and_fashion`, `business_and_finance`, `climate`, `entertainment`, `food_and_drink`, `games`, `health`, `hobbies_and_leisure`, `jobs_and_education`, `law_and_government`, `other`, `pets_and_animals`, `politics`, `science`, `shopping`, `sports`, `technology`, `travel_and_transportation`。对应页面 **Category** 列表。([Google Trends][1])
* `--active-only`（布尔，默认：`false`）

  * 若为 `true`，在 **All trends / Trend status** 菜单中勾选 **Show active trends only**（仅显示 *Active*）。([Google Trends][1])
* `--sort`（枚举，默认：`relevance`）

  * 取值：`title` / `search_volume` / `recency` / `relevance`（页面显示为 **By title / By search volume / By recency / By relevance**）。([Google Trends][1])

### 3.2 抓取控制

* `--limit`（整数，默认：抓取当前筛选下所有可见条目；也可使用分页箭头继续翻页直至空或到达上限）。页面存在翻页箭头控件。([Google Trends][1])
* `--expand-breakdown`（布尔，默认：`false`）

  * 若为 `true`，尝试展开每条目 **Trend breakdown** 的“+ N more”，抓取更多相关查询（若存在弹层/列表）。([Google Trends][1])
* `--export-mode`（枚举，默认：`scrape`）

  * `scrape`：直接从 DOM 读取数据；
  * `export_csv`：调用页面 **Export → Download CSV** 并下载官方 CSV（若可用）；也可支持 `export_rss`。([Google Trends][1])
* `--headless`（布尔，默认：`true`），`--timeout`（秒，默认：30），`--max-retries`（默认：3）
* `--lang`（例如 `en-US`；默认：与浏览器 profile 一致），`--proxy`（可选）

### 3.3 输出

* `--out`（路径，默认：`./out/trending_{geo}_{yyyyMMdd_HHmmss}.json`）
* `--format`（枚举：`json|csv|parquet`，默认：`json`）

---

## 4. 数据字段与 Schema

每条 **TrendItem** 需输出如下字段（JSON Schema/Pydantic）：

```json
{
  "title": "chiefs",
  "search_volume_text": "2M+",
  "search_volume_bucket": "2M_plus",
  "started_relative": "9 hours ago",
  "started_iso": "2025-09-05T13:30:00-07:00",
  "status": "Active",               // Active 或 Lasted（页面释义见 Trend status） 
  "top_related": ["chargers", "justin herbert", "chiefs game"],
  "more_related_count": 285,        // 若有“+ 285 more”则解析为整数，否则 0
  "sparkline_svg_path": "M0,22L12,18...", // 可选：小图折线的 d 属性（若可获取）
  "page_index": 1,                  // 第几页（翻页抓取）
  "geo": "United States",
  "time_window": "past_24_hours",
  "category": "all",
  "active_only": false,
  "sort": "relevance",
  "retrieved_at": "2025-09-05T22:40:17-07:00"
}
```

* **Trend status** 两种状态解释（Active / Lasted）以页面说明为准。([Google Trends][1])
* 若 `export_mode=export_csv`，需把官方 CSV 字段映射回上述 Schema（尽量补全；缺失项置 `null`），并在结果中添加 `"source":"export_csv"`。([Google Trends][1])

---

## 5. 页面自动化流程（Playwright 参考实现）

1. 启动浏览器（可选代理、UA、语言；默认 **headless**）。
2. 访问 `https://trends.google.com/trending`。等待主列表加载（视口中出现“Trends”“Sort by…”等元素）。([Google Trends][1])
3. **选择地区**：点击 **Select location**，在搜索框输入 `--geo` 值并选择匹配项。([Google Trends][1])
4. **选择时间**：点击 **Past 24 hours** 下拉，选择与 `--time-window` 对应项。([Google Trends][1], [Google Help][2])
5. **选择分类**：点击 **All categories**，选择 `--category`。([Google Trends][1])
6. **趋势状态**：点击 **All trends（Trend status）**，若 `--active-only=true` 则勾选 **Show active trends only**。([Google Trends][1])
7. **排序**：点击 **By relevance** 下拉，选择 `--sort`。([Google Trends][1])
8. **数据收集**：

   * 遍历当前页列表行，提取：标题、搜索量文本、开始时间相对值、状态（Active/Lasted）、Top related（及“+N more”数字）、小图折线 `path@d`（若存在且易获取）。
   * 如 `--expand-breakdown=true`，尝试点击每行的“+ N more”或“Trend breakdown”入口，采集完整列表（注意关闭弹层后继续）。([Google Trends][1])
9. **翻页**：点击 **arrow\_forward\_ios** 直至没有新数据或达到 `--limit`。记录 `page_index`。([Google Trends][1])
10. **导出模式（可选）**：若 `--export-mode=export_csv`，点击 **Export → Download CSV**，等待下载完成，解析 CSV 并映射为统一结构；如 `export_rss`，则抓取 RSS 并解析。([Google Trends][1])
11. 写入输出文件（JSON/CSV/Parquet），并在 stdout 打印摘要（抓取条数、用时、筛选条件）。

> 兼容性：如出现 Google 同意/隐私弹窗，需自动点击“同意/继续”；等待列表渲染使用**显式等待**（locator.waitFor）而非固定 `sleep`。

---

## 6. 选择器策略（稳健性要求）

* **禁止使用易变的类名**（如随机 hash）；优先用 `role`、`aria-label`、按钮文本、图标文本（例如 “Export”、“Sort by”）、标题文字等稳定标识。
* 通过**文本+层级**定位（如：先定位到“Trends”区域，再查询内部行元素）。
* 解析搜索量与“+N more”时，容错逗号/空格/“+”号；将 `N` 提取为整数。

---

## 7. 速率与反封策略

* 控制并发：单页串行抓取，翻页之间随机延时 200–600ms。
* 设置常见桌面浏览器 UA，支持自定义 `--proxy`。
* 失败重试：网络/超时/元素缺失时退避重试（最多 `--max-retries` 次）。

---

## 8. 错误处理与返回码

* 非零返回码表示失败；同时输出统一的错误 JSON（包含 `stage`, `message`, `screenshot_path`）。
* 关键步骤失败（无法选定地区/时间或列表为空）要给出**可诊断日志**与**截图**（`./logs/`）。

---

## 9. 单元与端到端验收

* **默认参数**（与截图一致）应返回 ≥1 条记录，并落地 JSON 文件。([Google Trends][1])
* **变更地区**：`--geo="United Kingdom"` + `--time-window=past_7_days` 返回记录且字段完整。([Google Help][2])
* **仅展示 Active**：`--active-only=true` 时，所有记录 `status` 均为 `Active`。([Google Trends][1])
* **排序校验**：`--sort=search_volume` 时，`search_volume_text` 应大致降序（按桶比较）。([Google Trends][1])
* **导出模式**：`--export-mode=export_csv` 可成功下载并解析 CSV。([Google Trends][1])

---

## 10. CLI 使用示例

```bash
# 1) 使用默认（US / Past 24 hours / All / All trends / By relevance）
python trends_trending_now.py

# 2) 指定地区与时间，并仅抓取前 50 条
python trends_trending_now.py --geo="United Kingdom" --time-window=past_7_days --limit=50

# 3) 只看 Active，分类为 Sports，按搜索量排序，导出 CSV
python trends_trending_now.py --active-only=true --category=sports --sort=search_volume --export-mode=export_csv

# 4) 调试（有头浏览器）并保存 parquet
python trends_trending_now.py --headless=false --format=parquet
```

---

## 11. 目录结构（建议）

```
project/
  trends_trending_now.py
  models.py            # Pydantic 模型与枚举
  scraper.py           # Playwright/Selenium 交互与 DOM 解析
  exporter.py          # JSON/CSV/Parquet/RSS/CSV 映射
  utils.py             # 重试、日志、时间解析、下载处理
  requirements.txt
  out/
  logs/
```

---

## 12. 合规与备注

* 本工具基于公开网页**只做只读抓取**，遵守网站使用条款与当地法律；如站点提供官方导出（CSV/RSS），优先使用导出能力。([Google Trends][1])
* Trending now 的时间窗、国家/地区覆盖范围参见官方帮助页描述（内容会更新，需兼容变更）。([Google Help][2])

---

若需要，我可以在此规范之上直接产出 **Playwright 实现的可运行 Python 脚本**（含下载 CSV 与 DOM 抓取两种模式）。

[1]: https://trends.google.com/trending "Trending Now - Google Trends"
[2]: https://support.google.com/trends/answer/3076011?hl=en&utm_source=chatgpt.com "Explore the searches that are Trending now"
