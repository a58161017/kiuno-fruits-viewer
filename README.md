# kiuno-fruits-viewer

台灣水果圖鑑網頁 — **手機優先**設計，桌機相容。包含 116 種台灣常見水果，每筆有產季、產地、主要品種、營養價值、保存方式與 4 區市場價格。

## 特色

- 📱 **Mobile-first**：base CSS 為手機版，桌機是 progressive enhancement
- 🍎 **正盛產徽章**：自動依當前月份標示當季水果，可一鍵只看當季
- 💰 **四區價格**：北、中、南、東部市場大致範圍價格表
- 🔍 **關鍵字搜尋**：支援中文、別名、學名、英文、品種、產地、營養
- 🌐 **純靜態**：可部署到 GitHub Pages，無後端依賴

## 資料 Schema

每種水果包含：

- 中文名 / 別名 / 英文 / 學名
- 產季月份（陣列，支援跨年）
- 主要產地（縣市鄉鎮）
- 100-250 字介紹
- **主要品種**（如愛文、金煌、凱特等）
- **營養價值**（chips 顯示）
- **保存方式**
- **4 區價格範圍**（北/中/南/東）
- 維基百科連結與封面圖

## 資料來源

- 維基百科（中文版）— 學名、科別、產地等事實
- 維基百科 Commons — 封面圖（CC 授權）
- 人工撰寫 — 介紹、品種、營養、保存、價格範圍

## 使用方式

### 安裝相依套件

```bash
pip install -r requirements.txt
```

### 資料管線

```bash
python run.py seed         # raw/fruits_seed.yaml → fruits.json 骨架
python run.py enrich       # 維基百科補學名/科別/封面 URL
python run.py download     # 下載維基 Commons 封面圖
python run.py apply-drafts # 套用 raw/manual_drafts.json (介紹/品種/營養/保存/價格)
python run.py validate     # 驗證 schema 與 prices region
python run.py stats        # 統計各欄位覆蓋率
```

### 啟動本機伺服器

```bash
python run.py serve                          # 127.0.0.1:8000
python run.py serve --host 0.0.0.0           # LAN 可用，手機可連入測試
```

### URL 參數

- `?month=4` — 鎖定月份（debug / 預覽其他月份當季水果）
- `#mango` — 直接打開特定水果詳細頁

## 專案結構

```
kiuno-fruits-viewer/
├── config.py               路徑、API、限速、PRICE_REGIONS
├── run.py                  CLI 入點
├── index.html              手機優先 SPA (Alpine.js + Fuse.js)
├── styles.css              mobile-first CSS（暖橘綠主題）
├── pipeline/               資料管線
│   ├── seed.py             YAML → fruits.json 骨架
│   ├── enrich.py           維基百科抓事實
│   ├── download.py         維基 Commons 下載 + Pillow 縮圖
│   ├── apply_drafts.py     套用人工撰寫內容
│   ├── validate.py         schema 驗證（含 prices region 白名單）
│   └── llm_draft.py        Claude API 自動寫介紹（選用）
├── services/               HTTP / Wikipedia / Claude API 包裝
├── data/                   fruits.json + covers/ + cache/
└── raw/
    ├── fruits_seed.yaml    水果清單種子
    └── manual_drafts.json  人工撰寫的介紹/品種/營養/保存/價格
```

## 編輯水果內容

修改 `raw/manual_drafts.json` 後重跑：

```bash
python run.py apply-drafts
```

每筆 entry 結構：

```json
{
  "mango": {
    "intro": "100-250 字介紹...",
    "varieties": ["愛文", "金煌", "凱特"],
    "nutrition": ["維生素 A", "維生素 C", "膳食纖維"],
    "storage": "保存方式說明...",
    "prices": [
      {"region": "北部", "range": "60-120 元/斤", "note": "可選備註"},
      {"region": "南部", "range": "40-80 元/斤", "note": "產地直送"}
    ]
  }
}
```

`region` 必須為 `北部 / 中部 / 南部 / 東部` 之一。

## Mobile-first 原則

- Base CSS 直接寫手機版，用 `@media (min-width: ...)` 往上加桌機樣式
- 所有觸控目標 ≥ 44×44px
- 詳細頁手機版用底部抽屜，桌機切右側 panel
- 封面比例 1:1，圖片 lazy loading
- iOS safe-area 處理

## 部署到 GitHub Pages

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<你的帳號>/kiuno-fruits-viewer.git
git push -u origin main
```

然後在 GitHub repo 設定：
1. Settings → Pages
2. Source 選 `Deploy from a branch`
3. Branch 選 `main` / `root`
4. 等 1-2 分鐘，網址會顯示在 Pages 設定頁

## 環境

- Python 3.10+
- Windows / macOS / Linux 皆可
- 姊妹專案：[kiuno-flowers-viewer](https://github.com/a58161017/kiuno-flowers-viewer)（同樣架構的台灣花卉圖鑑）
