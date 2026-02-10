# 使用示例

本文档提供 Web Region & Audience Analyzer 的详细使用示例。

## 1. 单页面分析

### 基础分析

```bash
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com
```

输出包含：
- 地区判断（primaryRegion）
- 语言检测（primaryLanguage）
- 置信度评分（regionConfidence）
- 证据链（evidence）
- 优化建议（optimization）

### 导出 Markdown 报告

```bash
# 默认保存到系统下载目录（~/Downloads）
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://www.example.com \
  --format markdown

# 指定保存路径
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://www.example.com \
  --format markdown \
  -o report.md
```

### 禁用某些功能

```bash
# 不查询 IP 地理定位（仅分析页面内容）
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com --no-ip-geo

# 不生成优化建议
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com --no-recommendations
```

## 2. 多页面站点分析

### 基础站点爬取

```bash
# 爬取整个站点（默认最多 3 层，20 页）
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com --crawl
```

输出包含：
- `crawlSummary`: 爬取摘要（页面数、最大深度、URL 列表）
- `siteResult`: 全站聚合结果（综合所有页面的信号）
- `siteOptimization`: 全站优化建议（合并所有页面的问题）
- `pages[]`: 每个页面的详细分析

### 自定义爬取参数

```bash
# 只爬取 2 层，最多 10 页
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com --crawl \
  --max-depth 2 \
  --max-pages 10

# 保存到文件
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com --crawl \
  -o site_analysis.json
```

### 爬取工作原理

1. 从起始 URL 开始
2. 提取页面中的所有 `<a href>` 链接
3. 仅跟随同域名的链接（不会跳转到外部网站）
4. 使用广度优先搜索（BFS）遍历
5. 每个页面之间延迟 1 秒（避免过载服务器）
6. 达到 `max_depth` 或 `max_pages` 限制后停止

## 3. AI 内容质量分析

### 使用 OpenAI API

```bash
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com \
  --ai-api-base https://api.openai.com/v1 \
  --ai-api-key sk-your-openai-key-here \
  --ai-model gpt-4o
```

### 使用环境变量

```bash
# 设置环境变量
export AI_API_BASE=https://api.openai.com/v1
export AI_API_KEY=sk-your-openai-key-here

# 运行分析（自动读取环境变量）
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com
```

### AI 分析输出

AI 分析会在输出中添加 `aiContentAnalysis` 字段：

```json
{
  "aiContentAnalysis": {
    "inferredProductType": "E-commerce fashion retailer",
    "languageQuality": {
      "score": 8.5,
      "isNativeLevel": true,
      "machineTranslationDetected": false,
      "details": "语法自然流畅，使用了适当的敬语..."
    },
    "regionFit": {
      "score": 9.0,
      "culturallyApproriate": true,
      "issues": [],
      "strengths": [
        "正确使用本地货币 JPY",
        "提及本地节日和文化元素"
      ]
    },
    "contentProductAlignment": {
      "score": 8.0,
      "details": "价值主张清晰，针对目标受众..."
    },
    "suggestions": [
      "考虑添加更多本地支付方式如 PayPay",
      "可以引用日本时尚趋势"
    ]
  }
}
```

### AI 分析评估维度

1. **语言质量** (1-10 分)
   - 是否达到母语水平
   - 是否有机器翻译痕迹
   - 语法、自然度、词汇适当性

2. **区域适配度** (1-10 分)
   - 文化适应性
   - 具体问题（如：为德国受众使用美式日期格式）
   - 优点（如：正确使用本地货币）

3. **内容产品对齐** (1-10 分)
   - 文案、语气、信息传递是否匹配产品
   - 价值主张对目标受众是否清晰

4. **改进建议**
   - 可操作的本地化质量改进建议

## 4. 组合使用（推荐）

### 完整站点分析 + AI 评估

```bash
# 最全面的分析：多页面爬取 + AI 内容分析
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://www.example.com --crawl \
  --ai-api-base https://api.openai.com/v1 \
  --ai-api-key sk-your-key \
  --max-depth 3 \
  --max-pages 20 \
  -o full_analysis.json
```

这会：
1. 爬取最多 20 个页面（3 层深度）
2. 对每个页面进行完整的信号分析
3. 对每个页面进行 AI 内容质量评估
4. 聚合全站结果
5. 输出到 `full_analysis.json`

### 聚合 AI 分析结果

在站点模式下，AI 分析会被聚合：

```json
{
  "aiContentAnalysis": {
    "averageLanguageQuality": 8.5,      // 所有页面的平均分
    "averageRegionFit": 9.0,
    "averageContentAlignment": 8.0,
    "aggregatedSuggestions": [
      "建议 1（出现在多个页面）",
      "建议 2（出现在多个页面）",
      "..."
    ],
    "pageScores": [
      {"url": "...", "languageQuality": 8.5, "regionFit": 9.0, ...},
      // ... 每个页面的分数
    ]
  }
}
```

## 5. 实际使用场景

### 场景 1: 快速检查单个页面

```bash
# 分析一个落地页
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://www.example.com/landing-page
```

**用途**: 快速了解页面的目标地区和语言，检查基本的本地化配置。

### 场景 2: 全站本地化审计

```bash
# 完整的站点审计
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://www.example.com --crawl \
  -o audit_report.json
```

**用途**:
- 检查整个网站的本地化一致性
- 发现全站性的配置问题（如缺少 hreflang）
- 评估不同页面的语言/地区一致性

### 场景 3: 深度内容质量评估

```bash
# 使用 AI 深度分析内容质量
export AI_API_BASE=https://api.openai.com/v1
export AI_API_KEY=sk-your-key

python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://www.example.com --crawl
```

**用途**:
- 评估内容是否符合目标地区的购买习惯
- 检测机器翻译痕迹
- 发现文化适配问题
- 获得具体的改进建议

### 场景 4: 竞品分析

```bash
# 分析竞争对手的本地化策略
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://competitor.com --crawl \
  --ai-api-base https://api.openai.com/v1 \
  --ai-api-key sk-your-key \
  -o competitor_analysis.json
```

**用途**:
- 了解竞品的目标市场
- 学习竞品的本地化策略
- 对比自己网站与竞品的差距

## 6. 高级用法

### 使用 NLP Cloud 增强语言检测

```bash
# NLP Cloud 提供更高精度的语言检测
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://www.example.com \
  --nlpcloud-token your-nlpcloud-token
```

### 自定义超时时间

```bash
# 对于响应慢的网站，增加超时时间
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://slow-website.com \
  --timeout 30
```

### 仅分析页面内容（不查 IP）

```bash
# 对于使用 CDN 的网站，IP 地理定位可能不准确
# 可以禁用 IP 查询，仅依赖页面内容信号
python3 web-region-audience-analyzer/scripts/analyze_webpage.py \
  https://cdn-hosted-site.com \
  --no-ip-geo
```

## 7. 输出解读

### 置信度评分

- **> 0.6**: 高置信度（多个信号一致）
- **0.3 - 0.6**: 中等置信度（部分信号一致）
- **< 0.3**: 低置信度（全球化站点或信号冲突）

### 优化建议等级

- **A (80-100)**: 优秀，仅有少量非关键建议
- **B (60-79)**: 良好，存在一些警告项
- **C (40-59)**: 及格，存在较多问题
- **D (20-39)**: 较差，存在关键缺失
- **F (0-19)**: 极差，基本未做本地化配置

### AI 分析评分

- **9-10**: 优秀，接近完美
- **7-8**: 良好，有改进空间
- **5-6**: 及格，存在明显问题
- **< 5**: 较差，需要大幅改进

## 8. 故障排除

### 问题: "Language detection failed"

**解决方案**:
```bash
pip install langdetect
# 或使用 NLP Cloud
python3 ... --nlpcloud-token YOUR_TOKEN
```

### 问题: "IP Geolocation failed"

**原因**: 网络连接问题或 API 限频（45 次/分钟）

**解决方案**:
```bash
# 禁用 IP 查询
python3 ... --no-ip-geo
```

### 问题: 低置信度评分

**原因**: 全球化站点（.com + 英语 + US CDN）缺乏明确的地区信号

**这是正常的**: 对于真正的全球化网站，低置信度是正确的行为。

### 问题: AI 分析失败

**检查**:
1. API 密钥是否正确
2. API 地址是否正确
3. 网络连接是否正常
4. 页面是否有足够的文本内容（至少 20 字符）

## 9. 性能考虑

### 单页面分析

- 耗时: 2-5 秒（取决于网络和页面大小）
- 无 AI: ~2 秒
- 有 AI: ~5 秒（取决于 LLM API 响应时间）

### 多页面爬取

- 耗时: 20-60 秒（20 页，每页 1 秒延迟 + 分析时间）
- 无 AI: ~30 秒
- 有 AI: ~60 秒（每页额外 2-3 秒）

### 优化建议

1. 使用 `--max-pages` 限制页面数
2. 使用 `--max-depth` 限制爬取深度
3. 对于大型站点，分批分析不同部分
4. 使用 `-o` 保存结果到文件，避免重复分析

## 10. API 兼容性

### 支持的 AI API

- **OpenAI**: `https://api.openai.com/v1`
- **Azure OpenAI**: `https://your-resource.openai.azure.com/openai/deployments/your-deployment`
- **任何 OpenAI 兼容 API**: 如 Anthropic Claude via proxy

### 模型选择

```bash
# GPT-4o (推荐，平衡质量和速度)
--ai-model gpt-4o

# GPT-4 Turbo (更快)
--ai-model gpt-4-turbo

# GPT-3.5 Turbo (最快，成本最低)
--ai-model gpt-3.5-turbo
```
