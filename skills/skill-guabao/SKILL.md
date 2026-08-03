---
name: skill-guabao
description: Global package manager for Antigravity skills. Must be consulted before modifying any local plugin files to determine the plugin's source and governance model. Includes an auto-updater script to check third-party GitHub skills for stable updates.
---

# GuaBao (掛包) 外掛總管

## 🎯 核心原則 (Core Principle)
GuaBao 是一套針對 Antigravity 生態系外掛 (`config/plugins/`) 的自動化管理與版本控管工具。
為了避免破壞系統核心或是造成開發版本混亂，**任何 Agent 在嘗試編輯、刪除或新增外掛檔案前，都必須先讀取這份核心註冊表**：
`C:\Users\wang6\.gemini\config\plugins_inventory.yaml`

## 🍲 GuaBao Update Checker (更新檢查)
GuaBao 內建了自動化更新檢查腳本，能分析 `third_party_git_skills` 清單，並利用 GitHub API 幫使用者確認是否有更新。
- **穩定期判定**：基於系統安全性，腳本採用「3 天穩定期」機制。當發現最新 commit 時，必須該 commit 發布超過 3 天沒有其他改動，才會建議更新，否則將標示為「觀察期」。
- **更新前防護 (Diff Scan)**：在執行更新之前，`guabao_updater.py` 會利用 GitHub API 取得的 Blob SHA1 自動掃描本地的外掛資料夾。若發現有本地修改，會中斷並警告，防止使用者的心血被遠端覆蓋。
- **執行方式**：Agent 可透過執行 `python <guabao 安裝路徑>/scripts/guabao_updater.py` 來獲取精美的版本比對報表。若狀態為 `UP_TO_DATE`、`UPDATE_AVAILABLE` 且 `last_pulled_commit` 存在，腳本也會一併進行本地防護掃描。

## 📝 外掛註冊表初始化與新增/移除維護 (Initialization & Maintenance)
如果使用者是第一次使用 GuaBao，或者系統中尚未存在 `plugins_inventory.yaml`，請執行以下操作：
1. **初始化**：將 GuaBao 資料夾下的 `plugins_inventory.template.yaml` 拷貝並重新命名為 `~/.gemini/config/plugins_inventory.yaml`。
2. **新增外掛與建立**：當使用者要求安裝或建立新的外掛時，Agent 必須：
   - 先呼叫 `check_naming_conflict` 確保名稱無衝突。
   - 若為安裝外部來源 (GitHub)，必須呼叫 `check_trusted_host` 比對 `trusted_hosts` 清單。若不在清單內，必須先警告使用者「此來源並非已知白名單」，等待使用者同意後再安裝。
   - 呼叫 `validate_install_path` 確認建立路徑位於 `~/.gemini/config/plugins/` 且命名合法。
   - 將外掛依類別登記至 `plugins_inventory.yaml` 中（若為第三方，記錄 `github_url` 與 `last_pulled_commit`）。
3. **移除/解除安裝外掛**：當使用者要求刪除外掛時，Agent **不應該**直接用指令刪除，而必須呼叫 `guabao_updater.py` 裡的 `uninstall_plugin(plugin_name, inventory_path)` 來執行封存與清理作業，並提醒使用者清除全域規則中的殘留。
4. **紀錄使用狀態 (可選)**：當 Agent 主動使用某個第三方或本地工具外掛時，建議呼叫 `mark_plugin_used(plugin_name, inventory_path)` 來更新其 `last_used_date`。GuaBao 會自動掃描超過 60 天未使用的閒置外掛並提醒使用者。

## 🚦 行為約束 (Behavioral Constraints)
根據 `plugins_inventory.yaml` 中的分類，你必須遵守以下相應的檔案存取與版本管理規則：

### 1. `git_tracked_skills` (類別一：自行開發的核心專案)
這些外掛是使用者自行開發並推送到 GitHub 的開源專案。為配合前端 UI 限制，它們在 `config/plugins/` 目錄下是「實體檔案拷貝」，而非軟連結。
- **可否編輯**：🟢 完全可以。
- **編輯規則**：請直接對 `config/plugins/` 內的實體檔案進行編輯。
- **強制操作**：編輯完成後，你 **必須** 記錄並提醒使用者執行專屬的同步腳本 (`sync_script`)。

### 2. `local_utility_skills` (類別二：本地小工具)
這些是使用者僅在本地使用的輕量級工具包，不受 Git 版本控管。
- **可否編輯**：🟢 完全可以。
- **編輯規則**：可直接修改 `config/plugins/` 內的檔案。
- **強制操作**：無須 commit。

### 3. `third_party_git_skills` (類別三：第三方 GitHub 專案)
這些是使用者手動從開源社群抓取下來的第三方外掛。
- **可否編輯**：🔴 嚴格禁止。除非使用者明確下達「強制客製化第三方套件」的指令。
- **更新規則**：如需更新，請先執行 GuaBao updater 檢查版本，再引導使用者進行手動更新或 `git pull`。

### 4. `system_bundled_skills` (類別四：系統原生外掛)
伴隨 Antigravity 核心引擎更新的官方外掛，通常沒有單獨的版本號與外部連結。
- **可否編輯**：🔴 嚴格禁止。這些外掛屬於系統核心邊界，任何修改都可能導致不可預期的系統崩潰。
- **更新規則**：它們會隨著 Antigravity 軟體本體自動更新，Agent 不應介入。
