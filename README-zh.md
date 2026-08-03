# 🍲 GuaBao (掛包) — Antigravity Plugin Manager

[English Version](README.md)

**GuaBao** 是一套輕量型的 Antigravity 外掛生命週期管理工具。它能幫你追蹤、分類所有已安裝的外掛，並透過 GitHub API 自動判斷哪些第三方外掛有穩定的新版本可以更新。

---

## 🤔 為什麼需要 GuaBao？(Why GuaBao?)

在使用 AI Agent 時，你可能會發現外掛 (Skills) 越裝越多，甚至為了各種開發需求開始自己修改、擴充別人的外掛。這時會遇到幾個痛點：
1. **AI 擅自覆蓋檔案**：當你請 AI 幫忙「更新外掛」時，AI 有時會盲目覆蓋整個資料夾，導致你辛辛苦苦客製化的修改全部不見！
2. **追蹤困難**：到底裝了哪些外掛？哪些是自己寫的？哪些是別人寫的？根本無從得知。
3. **穩定性危機**：GitHub 上的最新 commit 不一定穩定，盲目 `git pull` 很容易把原本好好的環境弄壞。
4. **安裝來路不明的套件**：AI 有時會產生幻覺或隨意從網路上抓取來路不明的程式碼。

**GuaBao 解決了這些問題：**
GuaBao 作為 Agent 的「總管」，負責擋在 AI 與系統之間。它提供了防呆覆蓋檢查 (Diff Scan)、更新穩定期 (3天的觀察期)、閒置套件追蹤，以及可信任白名單 (Trusted Hosts)。讓你的 AI 助手可以自由且安全地管理你的開發環境，而你完全不用擔心它會把環境搞砸！

---

## 📦 如何安裝 (Installation)

安裝 `skill-guabao` 非常簡單，你完全不需要手動 clone 專案或複製檔案。

只要把這個 GitHub 專案庫的網址丟給你的 AI Agent (例如在 Antigravity IDE 的對話框中)，並這樣跟他說：

> "請幫我安裝這個外掛：https://github.com/YuJunWang/skill-guabao"

你的 AI Agent 就會全自動幫你把外掛抓下來、建立相關的 `SKILL.md` 指令規則，並為你完成所有必要的設定！

---

## 📁 目錄結構

```
guabao/
├── plugin.json                          # Plugin 元資料
├── plugins_inventory.template.yaml      # 外掛註冊表範本
├── skills/
│   └── skill-guabao/
│       └── SKILL.md                     # 給 AI Agent 讀的操作規範
└── scripts/
    ├── guabao_updater.py                # 更新檢查主程式
    └── test_guabao_updater.py           # TDD 測試案例
```

## 🤖 AI Agent 觸發情境指南 (For Agents)

如果你希望你的 AI 助理（如 Antigravity Agent）能主動使用 GuaBao 來幫你管理外掛，建議將以下規則加入到你的全域設定檔（如 `AGENTS.md` 或系統提示詞）中：

> **外掛與生態管理**：當遇到需要安裝新外掛、編輯 `config/plugins/` 檔案，或是詢問第三方套件是否需要更新時，**必須主動查閱 `skill-guabao` 技能**以確認全域註冊表 (`plugins_inventory.yaml`) 的規範與更新狀態。

這樣一來，AI 只要偵測到你在詢問外掛更新或是準備建立新外掛，就會自動啟動 GuaBao 的管理機制。

---

## 🚀 快速上手

### Step 1：初始化你的外掛註冊表

將範本拷貝到你的 Antigravity config 目錄：

**Windows:**
```powershell
Copy-Item .\plugins_inventory.template.yaml "$env:USERPROFILE\.gemini\config\plugins_inventory.yaml"
```

**macOS / Linux:**
```bash
cp plugins_inventory.template.yaml ~/.gemini/config/plugins_inventory.yaml
```

### Step 2：編輯你的外掛清單

開啟 `~/.gemini/config/plugins_inventory.yaml`，根據四大分類（見下方）填入你已安裝的外掛。

### Step 3：執行更新檢查

```bash
# 使用預設路徑 (~/.gemini/config/plugins_inventory.yaml)
python scripts/guabao_updater.py

# 或指定自訂路徑
python scripts/guabao_updater.py --inventory /path/to/your/plugins_inventory.yaml
```

---

## 🛡️ 安全防護機制 (Security Features)

GuaBao 內建多項安全檢查，防止不小心的覆蓋或衝突：
1. **命名衝突檢查**：在建立新外掛前，Agent 應呼叫 `check_naming_conflict` 確保該名稱未在任何分類中被使用。
2. **更新前本地 diff 掃描**：更新第三方外掛前，會透過比對本地與遠端的 Git Blob SHA1，掃描是否在本地有未預期的修改。若發現本地修改，將暫停更新並發出警告，防止心血被遠端程式碼覆蓋。

---

## 🗂️ 四大外掛分類

| 類別 | 適用情境 | AI 可否修改 | 更新方式 |
|:---:|---|:---:|---|
| `git_tracked_skills` | 自行開發並推上 GitHub 的外掛 | ✅ 可以 | 編輯後執行同步腳本 |
| `local_utility_skills` | 僅本地使用的小工具 | ✅ 可以 | 直接修改即可 |
| `third_party_git_skills` | 從開源社群抓取的第三方外掛 | 🔴 禁止 | 透過 GuaBao 檢查後手動 `git pull` |
| `system_bundled_skills` | Antigravity 系統內建外掛 | 🔴 禁止 | 隨系統自動更新 |

---

## 🧪 執行測試

```bash
cd scripts/
pytest test_guabao_updater.py -v
```

---

## ⚙️ 相依套件

- Python 3.8+
- `pyyaml`
- `requests`
- `pytest`（測試用）
