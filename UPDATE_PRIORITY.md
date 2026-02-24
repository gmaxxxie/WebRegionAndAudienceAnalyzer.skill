# AI 智能选择优化更新

## 更新日期
2026-02-13

## 优化内容

### 增强优先级规则

在 AI 智能选择和启发式算法中，增加以下页面类型的**高优先级**：

#### 新增高优先级页面类型

1. **产品详情页** (`/products/xxx`、`/item/xxx`、`/product/xxx`)
   - 重要性：高
   - 理由：包含具体产品信息、价格、描述，对地区适配评估关键

2. **Sales 推广页** (`/sales`、`/promotion`、`/deals`、`/discount`、`/offer`)
   - 重要性：高
   - 理由：反映营销策略、目标市场、价格定位

3. **推广落地页** (`/lp/`、`/landing/`、`/campaign/`)
   - 重要性：高
   - 理由：针对特定受众，包含定向内容和 CTA

### 优先级层级

#### 最高优先级（必须包含）
- 首页 (`/`、`/home`、`/index`)
- 产品列表页 (`/products`、`/shop`、`/catalog`)

#### 高优先级（优先包含）
- 产品详情页
- Sales 推广页
- 推广落地页
- 关于我们 (`/about`)
- 联系我们 (`/contact`)

#### 中优先级（视情况包含）
- 帮助中心/FAQ (`/help`、`/support`、`/faq`)
- 价格页 (`/pricing`)
- 博客 (`/blog`)

#### 低优先级（尽量避免）
- 法律页面 (`/privacy`、`/terms`)
- 账户管理 (`/login`、`/register`)
- 功能页面 (`/cart`、`/checkout`)

---

## Prompt 优化

### 更新后的 AI Prompt

```python
prompt = f"""你是一个网站分析专家。给定一个网站的链接列表，请分析网站结构并选出最能代表网站核心内容的页面。

任务：
1. 识别页面类型（首页、产品页、产品详情、sales推广页、推广落地页、关于我们、博客、帮助中心等）
2. 评估每个页面的重要性（对了解网站目标受众和地区适配的价值）
3. 选出 {max_pages} 个最重要的页面进行分析

优先级规则（从高到低）：
**最高优先级 - 必须包含：**
- 首页（/、/home、/index）
- 产品列表页（/products、/shop、/catalog）

**高优先级 - 优先包含：**
- 产品详情页（/products/xxx、/item/xxx、/product/xxx）
- Sales 推广页（/sales、/promotion、/deals、/discount、/offer）
- 推广落地页（/lp/、/landing/、/campaign/）

**中优先级 - 视情况包含：**
- 关于我们（/about、/company）
- 联系我们（/contact）
- 帮助中心/FAQ（/help、/support、/faq）
- 价格页（/pricing、/plans）
- 购物车（/cart）- 转化关键页面

**低优先级 - 尽量避免：**
- 隐私政策、服务条款等法律页面
- 登录、注册、账户管理
- 结账流程（/checkout、/payment）
- 站点地图、搜索

链接列表：
{links_text}

请以JSON格式返回，包含以下字段：
- selected_indices: 选中的链接索引数组（0-based）
- reasoning: 简要说明选择逻辑，特别说明优先选择的产品、推广页面
- page_types: 识别出的主要页面类型
"""
```

### 主要改进

1. **明确的优先级规则** - 四层级优先级说明
2. **详细的页面类型** - 包含产品详情、推广页等
3. **明确的排除规则** - 避免低价值页面
4. **强调核心价值** - 特别说明产品、推广页面的重要性

---

## 启发式算法优化

### 评分规则

| 优先级 | 模式 | 分数 |
|--------|------|------|
| 最高 | `/`、`/products` | +15 |
| 高 | 产品详情、Sales、推广页 | +10 |
| 中 | 关于、联系、帮助、博客、购物车 | +5 |
| 低 | 法律、登录、结账 | -5 |
| 惩罚 | 路径深度 | -1/层 |

### 测试结果

```python
输入链接：
1. / (首页)
2. /products (产品列表)
3. /products/item-123 (产品详情)
4. /sales (Sales 推广页)
5. /cart (购物车)
6. /checkout (结账)
7. /about (关于)
8. /blog/post-1 (博客)
9. /privacy (隐私)
10. /login (登录)

选择 7 页：
1. / (首页) ✓
2. /products (产品列表) ✓
3. /sales (Sales 推广页) ✓
4. /cart (购物车) ✓ - 转化关键页面
5. /about (关于) ✓
6. /products/item-123 (产品详情) ✓
7. /blog/post-1 (博客) ✓

排除：
- /checkout (结账) - 低优先级
- /privacy (隐私政策) - 低优先级
- /login (登录) - 低优先级
```

---

## 使用示例

```bash
# 使用 AI 智能选择
python3 scripts/analyze_webpage.py https://example.com --smart-crawl \
  --ai-api-base https://api.openai.com/v1 \
  --ai-api-key YOUR_API_KEY

# 使用启发式算法（无 AI）
python3 scripts/analyze_webpage.py https://example.com --smart-crawl
```

---

## 优势

### 更准确的页面选择

1. **产品页覆盖** - 包含产品列表和产品详情页
2. **推广页识别** - Sales 页和落地页获得高优先级
3. **地区适配** - 推广页通常针对特定市场，对地区分析有价值

### 更高效的资源利用

- 减少低价值页面抓取
- 聚焦核心商业页面
- 提升地区适配分析的准确性

---

## 代码统计

- 修改函数：2 个
  - `analyze_site_structure_with_ai()` - Prompt 优化
  - `select_pages_heuristics()` - 优先级规则优化
- 新增模式：10+ 个
- 测试通过：✅

---

## 后续改进

- [ ] 支持自定义优先级规则
- [ ] 支持更多页面类型识别
- [ ] 根据网站类型（电商/SaaS/Blog）动态调整优先级
