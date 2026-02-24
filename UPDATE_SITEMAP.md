# 智能爬取 Sitemap 优先更新

## 更新日期
2026-02-13

## 新增功能：Sitemap 优先策略

### 核心改进

在智能爬取中增加 **Sitemap 优先级**：
1. **首先尝试发现 Sitemap** - robots.txt、/sitemap.xml、/sitemap_index.xml
2. **如无 Sitemap，提取导航栏链接** - 从首页的 <nav>、header 等区域
3. **AI/启发式选择** - 对导航链接进行智能筛选

### 优势

| 指标 | Sitemap 模式 | 导航模式 | 改善 |
|-----|-------------|---------|------|
| **请求次数** | 1 (首页) + N | 1 (首页) + 1 (AI) + N | 1 次 AI 调用 ↓ |
| **准确性** | 最高（站长优先级） | 高（AI 智能选择） | 提升 |
| **速度** | 最快 | 快 | 5-10s ↑ |

### 新增函数

#### `discover_sitemap(base_url, max_pages, timeout)`
- 检查 robots.txt 中的 Sitemap 指令
- 尝试标准位置：/sitemap.xml、/sitemap_index.xml
- 解析 XML sitemap（支持 sitemap index）
- 返回 URL 列表和来源信息

#### `extract_navigation_links(html, base_url)`
- 从导航区域提取链接
- 支持 <nav>、[role="navigation"]、header、.nav、.menu 等选择器
- 返回带 `source: 'navigation'` 标记的链接列表

### 修改的函数

#### `crawl_site_smart(start_url, ...)`
- 更新为多策略流程
- 优先使用 Sitemap
- 降级到导航链接提取
- 最后使用 AI/启发式选择

### 输出格式变化

#### Sitemap 模式
```json
{
  "siteMap": {
    "totalLinks": 156,
    "selectedPages": 20,
    "selectionMethod": "sitemap",
    "sitemapSource": "robots.txt",
    "pageTypes": ["Sitemap-provided"],
    "reasoning": "Used sitemap from robots.txt"
  }
}
```

#### 导航模式
```json
{
  "siteMap": {
    "totalLinks": 25,
    "selectedPages": 20,
    "selectionMethod": "ai",
    "pageTypes": ["AI-selected from navigation"],
    "reasoning": "AI analyzed navigation links and selected most representative pages"
  }
}
```

### 策略优先级

```
1. Sitemap (robots.txt) → 最高优先级
2. Sitemap (/sitemap.xml) → 高优先级
3. Sitemap (/sitemap_index.xml) → 中优先级
4. 导航链接 → 降级选项
5. 全部链接 → 最后手段
```

### 测试

- `test_sitemap.py` - Sitemap 发现和导航提取测试
- 导航链接提取测试通过 ✓
- 需要网络测试 Sitemap 发现（可能超时）

### 使用示例

```bash
# 自动使用最佳策略
python3 scripts/analyze_webpage.py https://example.com --smart-crawl

# 如果网站有 sitemap，会自动使用
# 如果没有，会使用导航栏链接 + AI
```

### 已知限制

1. Sitemap 解析依赖 BeautifulSoup（可选依赖）
2. 没有 BeautifulSoup 时使用 regex 回退（功能受限）
3. 网络问题可能导致 Sitemap 发现超时

### 未来改进

- [ ] 支持 Sitemap 增量更新检测
- [ ] 支持 robots.txt 的 Crawl-delay 指令
- [ ] 支持自定义 Sitemap URL
- [ ] 支持更多导航选择器模式

## 代码统计

- 新增代码行数：~250 行
- 修改代码行数：~150 行
- 新增函数：2 个
- 修改函数：1 个
- 新增测试：2 个测试脚本
