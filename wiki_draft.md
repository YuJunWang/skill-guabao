---
title: GuaBao (掛包) 外掛總管架構演進與設計決策
date: 2026-08-03
tags: [ai-agent, plugin-manager, antigravity, architecture]
---

# GuaBao (掛包) 外掛總管架構演進與設計決策

這份文件記錄了 GuaBao (skill-guabao) 的開發背景、v2 重大更新的設計思維，以及針對 AI Agent 生態系的安全防護考量。

## 📖 前世今生 (The Past and Present)

### 前世：單純的清單與更新腳本
在 Antigravity 剛起步時，使用者安裝了各種第三方外掛與自製腳本。隨著外掛數量增加，遇到了「不知道裝了什麼、忘記更新、無法集中管理」的痛點。
最初的 GuaBao 誕生於此，它的原型只是一份單純的 `plugins_inventory.yaml` 註冊表，搭配一支會呼叫 GitHub API 比較版本的簡單腳本。它解決了「追蹤」的問題，但尚未解決「AI 執行破壞性行為」的風險。

### 今生：Agent 的第一道防護牆 (A Skill for Skills)
隨著 Agent 能力越來越強，我們發現 AI 在被要求「幫我更新外掛」或「安裝新外掛」時，往往會盲目執行覆蓋或安裝來路不明的套件。
GuaBao 因此迎來了 v2 架構升級，定位正式轉變為 **「管理 Skill 的 Skill」**。它不僅是一個工具，更是介於 LLM 與底層檔案系統之間的「守門員」。它透過標準化的指令文件 (`SKILL.md`)，強迫 Agent 必須透過安全介面進行外掛的 CRUD（新增、讀取、更新、刪除）操作，完美解決了 AI 幻覺帶來的環境災難。

---

## 🛡️ 這次更新顧慮考量的點 (Design Considerations)

本次 v2 升級的核心精神是 **「防呆、防覆蓋、防來源不明」**，我們在架構上考量了以下四大痛點並提出解法：

1. **本地修改防護 (Diff Scan Protection)**
   - **痛點**：使用者常會微調第三方外掛，若 AI 盲目 `git pull` 會直接摧毀使用者的心血。
   - **解法**：不依賴傳統的 Git status。GuaBao 實作了與 GitHub Tree API 的同步比對機制，透過在本地精準計算 Git Blob SHA1，只要發現本地程式碼與遠端不同，就強制中斷更新並發出警告。
2. **外部來源信任邊界 (Trusted Hosts)**
   - **痛點**：AI 可能會因為幻覺或網路搜尋，試圖 clone 未知甚至惡意的 GitHub 儲存庫。
   - **解法**：導入 `trusted_hosts` 白名單機制。Agent 安裝前必須透過 `check_trusted_host` 比對來源；若不在名單內，強制 AI 必須停下來取得使用者的明確同意 (Human-in-the-loop)。
3. **軟刪除與路徑安全 (Safe Uninstall & Path Validation)**
   - **痛點**：放任 AI 使用 `rm -rf` 非常危險，也可能因為命名衝突蓋掉原本的套件。
   - **解法**：所有刪除動作強制轉換為「封存」至 `archive/` 目錄。並且在安裝前進行嚴格的路徑範圍檢查，確保套件不會被寫入系統其他敏感區域。
4. **跨平台相容性 (Cross-Platform via GUABAO_HOME)**
   - **痛點**：早期將路徑寫死在 `~/.gemini/config/`，導致其他主流 Agent (如 AutoGPT, OpenDevin) 無法使用。
   - **解法**：導入環境變數 `$GUABAO_HOME`，將 GuaBao 從 Antigravity 專屬工具提升為通用的 Agent 外掛管理生態。

---

## 🚀 未來的維護方向 (Future Directions)

1. **自動回滾機制 (Auto-Rollback)**
   - 結合目前的 `archive/` 封存機制，未來可實作 `/rollback` 指令。當某次更新導致系統崩潰時，Agent 能一鍵將套件退回前一個穩定的封存版本。
2. **多版本共存與鎖定 (Version Pinning)**
   - 允許在 `yaml` 註冊表中設定 `pin_version: "commit-hash"`。讓部分高度依賴穩定性的工具鎖定在特定版本，GuaBao 會自動忽略該工具的後續更新通知。
3. **封裝為標準 MCP Server (Model Context Protocol)**
   - 雖然目前依賴 `SKILL.md` 讓 LLM 閱讀指令，但未來可將 GuaBao 的能力（掃描、更新、移除）封裝成 MCP Tools。這樣任何支援 MCP 的大模型環境，都不需要看文件就能以原生 API 呼叫外掛管理功能，達成極致的自動化。
