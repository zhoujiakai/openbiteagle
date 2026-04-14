# RootData API Documentation

> 来源: https://cn.rootdata.com/Api/Doc
>
> 请确保在使用 API 时遵守相关的使用条款和限制，并在合适的地方提供适当的归属和引用。

## 通用说明

- Base URL: `https://api.rootdata.com/open/`
- Method: 所有接口均为 **POST**
- Content-Type: `application/json`
- 认证: 此 API 需要申请，不可以直接访问。每个 API Key 每分钟的请求限制为 **100 次**

### 通用请求头

所有接口均需在请求头中携带以下参数：

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| apikey | string | true | 您申请的 APIKEY |
| language | string | false | 语言版本（`en` 英文，`cn` 中文，默认 `en`） |

### 通用响应格式

成功:
```json
{
  "data": ...,
  "result": 200
}
```

失败:
```json
{
  "data": {},
  "result": 404,
  "message": "error message"
}
```

---

## 1. 搜索项目/机构/人物

- **URL**: `/ser_inv`
- **描述**: 根据关键词搜索项目/VC/人物简要信息，不限次数
- **支持的版本**: Basic, Plus, Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| query | string | true | 搜索关键词，可以是项目/机构名称、代币或其他相关词汇 |
| precise_x_search | boolean | false | 基于 X Handle（@...），精准搜索相应实体 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| id | int | 唯一标识符 |
| type | int | 1 项目；2 机构；3 人物 |
| name | string | 名称 |
| logo | string | logo 的 URL |
| introduce | string | 介绍 |
| active | boolean | true: 运营中；false: 停止运营 |
| rootdataurl | string | 对应的 RootData 链接 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"query": "ETH"}' \
  https://api.rootdata.com/open/ser_inv
```

### 响应示例

```json
{
  "data": [
    {
      "introduce": "Ethereum is the first decentralized...",
      "name": "Ethereum",
      "logo": "https://api.rootdata.com/uploads/public/b15/1666341829033.jpg",
      "rootdataurl": "https://api.rootdata.com/Projects/detail/Ethereum?k=MTI=",
      "id": 12,
      "type": 1
    }
  ],
  "result": 200
}
```

---

## 2. 查询 APIKEY 余额

- **URL**: `/quotacredits`
- **描述**: 查询 APIKEY 剩余 Credits 数量，免费
- **支持的版本**: Basic, Plus, Pro

### 请求参数

无

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| apikey | string | apikey |
| start | long | 有效期起（时间戳） |
| end | long | 有效期止（时间戳） |
| level | string | Level |
| total_credits | int | Credits 总额 |
| credits | int | 当前剩余 Credits |
| last_mo_credits | int | 上月结余 Credits |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  https://api.rootdata.com/open/quotacredits
```

### 响应示例

```json
{
  "data": {
    "last_mo_credits": 60000,
    "apikey": "XXX",
    "level": "pro",
    "credits": 59688,
    "total_credits": 60000,
    "start": 1721750400000,
    "end": 1787846399000
  },
  "result": 200
}
```

---

## 3. 获取 ID 列表

- **URL**: `/id_map`
- **描述**: 获取所有项目、人物与 VC 的 ID 列表，20 Credits/次
- **支持的版本**: Plus, Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| type | int | true | 类型: 1 项目 2 机构 3 人物 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| id | long | id |
| name | string | 实体名称 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"type": 1}' \
  https://api.rootdata.com/open/id_map
```

### 响应示例

```json
{
  "data": [
    {
      "id": 600,
      "name": "XXX"
    }
  ],
  "result": 200
}
```

---

## 4. 获取项目

- **URL**: `/get_item`
- **描述**: 根据项目 ID 获取其详细信息，2 credits/次
- **支持的版本**: Basic, Plus, Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| project_id | int | false | 项目的唯一标识符。如同时提供 `project_id` 和 `contract_address`，`project_id` 优先 |
| contract_address | string | false | 项目的合约地址 |
| include_team | boolean | false | 是否包含团队成员信息，默认 false |
| include_investors | boolean | false | 是否包含投资方信息，默认 false |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| project_id | int | 项目 ID |
| project_name | string | 项目名称 |
| logo | string | 项目 logo 的 URL |
| token_symbol | string | 代币符号 |
| establishment_date | string | 成立时间 |
| one_liner | string | 一句话介绍 |
| description | string | 详细介绍 |
| active | boolean | true: 运营中; false: 停止运营 |
| total_funding | decimal | 融资总额 |
| tags | array | 项目标签（标签名数组） |
| rootdataurl | string | 项目对应的 RootData 链接 |
| investors | array | 投资方信息 |
| social_media | array | 社交媒体链接 |
| similar_project | array | 同类项目 |
| ecosystem | array | 项目所属生态 **[PRO]** |
| on_main_net | array | 已上线的主网 **[PRO]** |
| plan_to_launch | array | 计划上线的生态 **[PRO]** |
| on_test_net | array | 已上线的测试网 **[PRO]** |
| fully_diluted_market_cap | string | 完全稀释市值 **[PRO]** |
| market_cap | string | 流通市值 **[PRO]** |
| price | string | 价格 **[PRO]** |
| event | array | 项目重大事件 **[PRO]** |
| reports | array | 新闻动态数据 **[PRO]** |
| team_members | array | 团队成员信息 **[PRO]** |
| token_launch_time | string | 代币发行时间 yyyy-MM **[PRO]** |
| contracts | array | 合约 **[PRO]** |
| support_exchanges | array | 支持的交易所 **[PRO]** |
| heat | string | X 热度值 **[PRO]** |
| heat_rank | int | X 热度排名 **[PRO]** |
| influence | string | X 影响力 **[PRO]** |
| influence_rank | int | X 影响力排名 **[PRO]** |
| followers | int | X 关注者数量 **[PRO]** |
| following | int | 正在关注的数量 **[PRO]** |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 8719, "include_team": true, "include_investors": true}' \
  https://api.rootdata.com/open/get_item
```

### 响应示例

```json
{
  "data": {
    "ecosystem": [],
    "one_liner": "Building hardware for cryptography",
    "description": "Fabric Cryptography is a start-up company focusing on developing advanced crypto algorithm hardware...",
    "rootdataurl": "https://api.rootdata.com/Projects/detail/Fabric Cryptography?k=ODcxOQ==",
    "total_funding": 87033106304,
    "project_name": "Fabric Cryptography",
    "investors": [
      {
        "name": "Inflection",
        "logo": "https://api.rootdata.com/uploads/public/b17/1666870085112.jpg"
      }
    ],
    "establishment_date": "2022",
    "tags": ["Infra", "zk"],
    "project_id": 8719,
    "team_members": [
      {
        "medium": "",
        "website": "https://www.fabriccryptography.com/",
        "twitter": "",
        "discord": "",
        "linkedin": "https://www.linkedin.com/company/fabriccryptography/"
      }
    ],
    "logo": "https://api.rootdata.com/uploads/public/b6/1690306559722.jpg",
    "social_media": {
      "medium": "",
      "website": "https://llama.xyz/",
      "twitter": "https://twitter.com/llama",
      "discord": "",
      "linkedin": ""
    }
  },
  "result": 200
}
```

---

## 5. 获取机构

- **URL**: `/get_org`
- **描述**: 根据 VC ID 获取 VC 详细信息，2 credits/次
- **支持的版本**: Basic, Plus, Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| org_id | int | true | 机构 ID |
| include_team | boolean | false | 是否包含团队成员信息，默认 false |
| include_investments | boolean | false | 是否包含投资项目信息，默认 false |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| org_id | int | 机构 ID |
| org_name | string | 机构名称 |
| logo | string | 机构 logo 的 URL |
| establishment_date | string | 成立时间 |
| description | string | 详细介绍 |
| active | boolean | true: 运营中; false: 停止运营 |
| category | string | 投资者类型 |
| social_media | array | 社交媒体链接（官网、推特、LinkedIn） |
| investments | array | 投资项目（包括名称、logo） |
| rootdataurl | string | 机构对应的 RootData 链接 |
| team_members | array | 团队成员信息（包括姓名、职位）**[PRO]** |
| heat | string | X 热度值 **[PRO]** |
| heat_rank | int | X 热度排名 **[PRO]** |
| influence | string | X 影响力 **[PRO]** |
| influence_rank | int | X 影响力排名 **[PRO]** |
| followers | int | X 关注者数量 **[PRO]** |
| following | int | 正在关注的数量 **[PRO]** |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"org_id": 219, "include_team": true, "include_investments": true}' \
  https://api.rootdata.com/open/get_org
```

### 响应示例

```json
{
  "data": {
    "org_id": 219,
    "team_members": [
      {"name": "Shan Aggarwal", "position": "Head"},
      {"name": "Jonathan King", "position": "Principal"}
    ],
    "logo": "https://rdbk.rootdata.com/uploads/public/b17/1666777683240.jpg",
    "description": "Coinbase Ventures is an investment arm of Coinbase...",
    "rootdataurl": "https://api.rootdata.com/Investors/detail/Coinbase Ventures?k=MjE5",
    "org_name": "Coinbase Ventures",
    "category": ["Seed Plus"],
    "investments": [
      {
        "name": "zkSync / Matter Labs",
        "logo": "https://public.rootdata.com/uploads/public/b16/1666624791085.jpg"
      }
    ],
    "establishment_date": "2018",
    "social_media": {
      "website": "https://www.coinbase.com/ventures",
      "twitter": "https://twitter.com/cbventures",
      "linkedin": ""
    }
  },
  "result": 200
}
```

---

## 6. 获取人物 (Pro)

- **URL**: `/get_people`
- **描述**: 根据人物 ID 获取人物详细信息，2 credits/次
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| people_id | long | true | 人物 ID |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| people_id | long | ID |
| introduce | string | 人物介绍 |
| head_img | string | 头像 |
| one_liner | string | 简介 |
| X | string | X 链接 |
| people_name | string | 人物名称 |
| linkedin | string | 领英链接 |
| heat | string | X 热度值 |
| heat_rank | int | X 热度排名 |
| influence | string | X 影响力 |
| influence_rank | int | X 影响力排名 |
| followers | int | X 关注者数量 |
| following | int | 正在关注的数量 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"people_id": 12972}' \
  https://api.rootdata.com/open/get_people
```

### 响应示例

```json
{
  "data": {
    "people_id": 12972,
    "introduce": "Cai Wensheng, also known as Mike Cai, is the founder and chairman of Meitu.",
    "head_img": "https://public.rootdata.com/images/b30/1687197351918.jpg",
    "one_liner": "",
    "X": "",
    "people_name": "Cai Wensheng",
    "linkedin": ""
  },
  "result": 200
}
```

---

## 7. 批量获取投资者信息 (Plus, Pro)

- **URL**: `/get_invest`
- **描述**: 批量获取投资者的详细信息（投资组合、数据分析等），2 credits/条
- **支持的版本**: Plus, Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| page | int | false | 页码，默认 1 |
| page_size | int | false | 每页条数，默认 10，最大 100 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| invest_name | string | 投资者名称 |
| type | int | 类型: 1 项目 2 机构 3 人物 |
| invest_id | int | 投资者 ID |
| logo | string | 投资者 Logo |
| area | array | 地区列表 |
| last_fac_date | string | 最近投资时间 |
| last_invest_num | int | 近一年投资次数 |
| invest_range | array | 参投规模 |
| description | string | 投资者介绍 |
| invest_overview | object | 投资概览 |
| investments | array | 对外投资项目 |
| establishment_date | string | 成立时间 |
| invest_num | int | 投资次数 |
| invest_stics | array | 投资版图 |
| team_members | array | 团队成员信息 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"page": 1, "page_size": 10}' \
  https://api.rootdata.com/open/get_invest
```

### 响应示例

```json
{
  "data": {
    "items": [
      {
        "area": ["Singapore", "United Arab Emirates"],
        "last_fac_date": "2023-10-12 00:00:00",
        "last_invest_num": 25,
        "description": "Binance Labs is the...",
        "invest_overview": {
          "lead_invest_num": 38,
          "last_invest_round": 25,
          "his_invest_round": 141,
          "invest_num": 171
        },
        "type": 2,
        "investments": [
          {
            "name": "zkSync / Matter Labs",
            "logo": "https://public.rootdata.com/uploads/public/b16/1666624791085.jpg"
          }
        ],
        "establishment_date": "2017",
        "invest_num": 171,
        "invest_stics": [
          {"track": "Infrastructure", "invest_num": 69}
        ],
        "invest_id": 229,
        "invest_range": [
          {
            "lead_invest_num": 11,
            "amount_range": "1-3M",
            "lead_not_invest_num": 17,
            "invest_num": 28
          }
        ],
        "team_members": [
          {
            "head_img": "https://public.rootdata.com/uploads/public/b12/1669630219503.jpg",
            "name": "Yi He",
            "X": "https://twitter.com/heyibinance",
            "position": "Head"
          }
        ],
        "logo": "https://public.rootdata.com/uploads/public/b11/1666594924745.jpg",
        "invest_name": "Binance Labs"
      }
    ],
    "total": 1
  },
  "result": 200
}
```

---

## 8. 批量导出 X 数据

- **URL**: `/twitter_map`
- **描述**: 批量导出项目的 X 数据（热度、影响力等），50 Credits/次
- **支持的版本**: Plus, Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| type | int | true | 类型: 1 项目 2 机构 3 人物 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| id | long | id |
| name | string | 实体名称 |
| X | string | X 链接 |
| followers | int | X 关注者数量 |
| following | int | 正在关注的数量 |
| heat | string | X 热度值 |
| influence | string | X 影响力 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"type": 1}' \
  https://api.rootdata.com/open/twitter_map
```

### 响应示例

```json
{
  "data": [
    {
      "id": 600,
      "name": "XXX",
      "X": "XXX"
    }
  ],
  "result": 200
}
```

---

## 9. 批量获取投资轮次信息 (Plus, Pro)

- **URL**: `/get_fac`
- **描述**: 批量获取投融资轮次（限 2018 年至今），2 credits/条
- **支持的版本**: Plus, Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| page | int | false | 页码，默认 1 |
| page_size | int | false | 每页条数，默认 10，最大 200 |
| start_time | string | false | 融资公布日期（起）yyyy-MM |
| end_time | string | false | 融资公布日期（止）yyyy-MM |
| min_amount | int | false | 融资金额最小范围（美元） |
| max_amount | int | false | 融资金额最大范围（美元） |
| project_id | int | false | 项目 ID |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| logo | string | 项目 logo 的 URL |
| name | string | 项目名称 |
| rounds | string | 轮次名称 |
| published_time | string | 融资公布日期 |
| amount | long | 融资金额（美元） |
| project_id | int | 项目 ID |
| valuation | long | 估值（美元） |
| invests | array | 投资方信息数组（包含 Logo、名称） |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{}' \
  https://api.rootdata.com/open/get_fac
```

### 响应示例

```json
{
  "data": {
    "total": 2870,
    "items": [
      {
        "amount": 2500000,
        "valuation": 30000000,
        "published_time": "2023-10",
        "name": "Convergence",
        "logo": "https://public.rootdata.com/uploads/public/b6/1671983908027.jpg",
        "rounds": "Pre-Seed",
        "invests": [
          {
            "name": "C2 Ventures",
            "logo": "https://public.rootdata.com/uploads/public/b17/1666777874118.jpg"
          }
        ]
      }
    ]
  },
  "result": 200
}
```

---

## 10. 同步更新 (Pro)

- **URL**: `/ser_change`
- **描述**: 获取单位时间内数据更新的项目列表，1 credits/条
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| begin_time | long | true | 开始时间，时间戳 |
| end_time | long | false | 结束时间，时间戳 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| id | int | ID |
| type | int | 1: 项目; 2: 机构 |
| name | string | 项目/机构名称 |
| update_time | long | 更新时间，时间戳 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"begin_time": 1693974909261, "end_time": 1694476800000}' \
  https://api.rootdata.com/open/ser_change
```

### 响应示例

```json
{
  "data": [
    {
      "update_time": 1693974909261,
      "name": "Ethereum",
      "id": 12,
      "type": 1
    }
  ],
  "result": 200
}
```

---

## 11. 热门项目 Top100 (Pro)

- **URL**: `/hot_index`
- **描述**: 获取 Top100 项目列表及其基本信息，10 credits/次
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| days | int | true | 仅支持查询近 1 天/7 天数据，值为 1 或 7 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| project_id | long | 项目 ID |
| eval | double | 热度值 |
| rank | int | 排名 |
| logo | string | 项目 Logo |
| one_liner | string | 简介 |
| token_symbol | string | 代币 |
| project_name | string | 项目名称 |
| tags | array | 项目标签（标签名数组） |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"days": 1}' \
  https://api.rootdata.com/open/hot_index
```

### 响应示例

```json
{
  "data": [
    {
      "eval": 907.936508,
      "project_id": 13671,
      "one_liner": "Hemi Network is a modular Layer...",
      "logo": "https://public.rootdata.com/images/b6/1721840384466.png",
      "rank": 1,
      "token_symbol": "",
      "project_name": "Hemi Network",
      "tags": ["Infra"]
    }
  ],
  "result": 200
}
```

---

## 12. X 热门项目 (Pro)

- **URL**: `/hot_project_on_x`
- **描述**: 获取 X 热门项目列表，10 credits/次
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| heat | boolean | true | 是否获取 X 热度榜单 |
| influence | boolean | true | 是否获取 X 影响力榜单 |
| followers | boolean | true | 是否获取 X 关注者榜单 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| heat | array | 热度榜 |
| influence | array | 影响力榜 |
| followers | array | 关注者数量榜单 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"heat": false, "influence": true, "followers": false}' \
  https://api.rootdata.com/open/hot_project_on_x
```

### 响应示例

```json
{
  "data": {
    "influence": [
      {
        "score": "5615",
        "project_id": 3875,
        "one_liner": "Cryptocurrency exchange",
        "logo": "https://public.rootdata.com/images/b16/1666878846006.jpg",
        "project_name": "Coinbase"
      }
    ]
  },
  "result": 200
}
```

---

## 13. X 热门人物 (Pro)

- **URL**: `/leading_figures_on_crypto_x`
- **描述**: 获取当前 X 热门人物列表，10 credits/次
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| page | int | false | 页码，默认 1 |
| page_size | int | false | 每页条数，默认 10，最大 100 |
| rank_type | string | true | 榜单类型: `heat` 或 `influence` |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| people_id | long | ID |
| score | string | 热度值/影响力指数 |
| head_img | string | 头像 |
| one_liner | string | 简介 |
| people_name | string | 人物名称 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"page": 1, "page_size": 100, "rank_type": "heat"}' \
  https://api.rootdata.com/open/leading_figures_on_crypto_x
```

### 响应示例

```json
{
  "data": {
    "total": 1000,
    "items": [
      {
        "people_id": 13994,
        "score": "86",
        "head_img": "https://public.rootdata.com/images/b12/1676887718722.jpg",
        "one_liner": "",
        "people_name": "Jieyi Long"
      }
    ]
  },
  "result": 200
}
```

---

## 14. 人物职位动态 (Pro)

- **URL**: `/job_changes`
- **描述**: 获取人物职位动态数据，10 credits/次
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| recent_joinees | boolean | true | 是否获取近期入职 |
| recent_resignations | boolean | true | 是否获取近期离职 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| recent_joinees | array | 近期入职列表 |
| recent_resignations | array | 近期离职列表 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"recent_joinees": true, "recent_resignations": true}' \
  https://api.rootdata.com/open/job_changes
```

### 响应示例

```json
{
  "data": {
    "recent_resignations": [
      {
        "people_id": 17262,
        "head_img": "https://public.rootdata.com/images/b6/1702801244037.jpg",
        "company": "Kraken",
        "people_name": "Curtis Ting",
        "position": "VP & Head of Global Operations"
      }
    ],
    "recent_joinees": [
      {
        "people_id": 17316,
        "head_img": "https://public.rootdata.xyz/images/b35/1717668332921.jpg",
        "company": "HTX",
        "people_name": "Test",
        "position": "CTO"
      }
    ]
  },
  "result": 200
}
```

---

## 15. 近期发币项目 (Pro)

- **URL**: `/new_tokens`
- **描述**: 获取近三个月新发行的代币列表，10 credits/次
- **支持的版本**: Pro

### 请求参数

无

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| project_id | long | 项目 ID |
| project_name | string | 项目名称 |
| logo | string | 项目 Logo |
| one_liner | string | 简介 |
| token_symbol | string | 代币符号 |
| hap_date | string | 事件发生时间 |
| market_cap | string | 流通市值 |
| fully_diluted_market_cap | string | 完全稀释市值 |
| exchanges | string | 交易所 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  https://api.rootdata.com/open/new_tokens
```

### 响应示例

```json
{
  "data": [
    {
      "fully_diluted_market_cap": "23372320.99",
      "market_cap": "0",
      "project_id": 12062,
      "one_liner": "Decentralized AI Agent Public Chain",
      "exchanges": "Gate.io,KCEX",
      "logo": "https://public.rootdata.com/images/b12/1711444046699.jpg",
      "hap_date": "2024-09-18",
      "token_symbol": "AGENT",
      "project_name": "AgentLayer"
    }
  ],
  "result": 200
}
```

---

## 16. 生态版图 (Pro)

- **URL**: `/ecosystem_map`
- **描述**: 获取生态版图列表，50 credits/次
- **支持的版本**: Pro

### 请求参数

无

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| ecosystem_id | long | 生态 ID |
| ecosystem_name | string | 生态名称 |
| project_num | int | 项目数量 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  https://api.rootdata.com/open/ecosystem_map
```

### 响应示例

```json
{
  "data": [
    {
      "ecosystem_name": "Ethereum",
      "ecosystem_id": 52,
      "project_num": 2158
    }
  ],
  "result": 200
}
```

---

## 17. 标签版图 (Pro)

- **URL**: `/tag_map`
- **描述**: 获取标签版图列表，50 credits/次
- **支持的版本**: Pro

### 请求参数

无

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| tag_id | long | 标签 ID |
| tag_name | string | 标签名称 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  https://api.rootdata.com/open/tag_map
```

### 响应示例

```json
{
  "data": [
    {
      "tag_name": "Bug Bounty",
      "tag_id": 52
    }
  ],
  "result": 200
}
```

---

## 18. 根据生态获取项目 (Pro)

- **URL**: `/projects_by_ecosystems`
- **描述**: 根据生态批量获取项目信息，20 credits/次
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| ecosystem_ids | string | true | 生态 ID，多个用逗号分隔 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| project_id | long | 项目 ID |
| project_name | string | 项目名称 |
| logo | string | 项目 Logo |
| one_liner | string | 简介 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"ecosystem_ids": "52,54"}' \
  https://api.rootdata.com/open/projects_by_ecosystems
```

### 响应示例

```json
{
  "data": [
    {
      "project_id": 2297,
      "one_liner": "Crypto bug bounty platform",
      "logo": "https://public.rootdata.com/images/b26/1666654548967.jpg",
      "project_name": "Immunefi"
    }
  ],
  "result": 200
}
```

---

## 19. 根据标签查项目 (Pro)

- **URL**: `/projects_by_tags`
- **描述**: 根据标签批量获取项目信息，20 credits/次
- **支持的版本**: Pro

### 请求参数

| 参数 | Type | Required | 描述 |
|------|------|----------|------|
| tag_ids | string | true | 标签 ID，多个用逗号分隔 |

### 响应字段

| 参数 | Type | 描述 |
|------|------|------|
| project_id | long | 项目 ID |
| project_name | string | 项目名称 |
| logo | string | 项目 Logo |
| one_liner | string | 简介 |

### 请求示例

```bash
curl -X POST \
  -H "apikey: Your APIKEY" \
  -H "language: en" \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": "100,101"}' \
  https://api.rootdata.com/open/projects_by_tags
```

### 响应示例

```json
{
  "data": [
    {
      "project_id": 2297,
      "one_liner": "Crypto bug bounty platform",
      "logo": "https://public.rootdata.com/images/b26/1666654548967.jpg",
      "project_name": "Immunefi"
    }
  ],
  "result": 200
}
```

---

## 错误处理

| 错误码 | 描述 |
|--------|------|
| 110 | Authentication Failed: 鉴权失败 |
| 400 | Bad Request: 请求参数无效或缺失 |
| 403 | Forbidden: 访问被拒绝，剩余 Credits 不足 |
| 404 | Not Found: 未找到匹配的信息 |
| 410 | High visit frequency: 访问频次过高，请等待一分钟后重置 |
| 500 | Internal Server Error: 服务器内部错误 |
