---
name: skill-guabao
description: Global package manager for Antigravity skills. Must be consulted before modifying any local plugin files to determine the plugin's source and governance model. Includes an auto-updater script to check third-party GitHub skills for stable updates.
---

# GuaBao (掛包) 外掛總管

## 🌟 核心目標與啟動條件
GuaBao 是一個「管理 Skill 的 Skill」。當使用者要求新增、更新、整理或刪除任何第三方/本地外掛包 (Skills) 時，你必須嚴格遵守以下操作規範。
GuaBao 預設管理 `$GUABAO_HOME` 目錄下的外掛 (若未設定 `GUABAO_HOME` 環境變數，則預設為 `~/.gemini/config`)。

- **註冊表位置**：`$GUABAO_HOME/plugins_inventory.yaml`
- **外掛存放目錄**：`$GUABAO_HOME/plugins/`
- **更新檢查腳本**：`$GUABAO_HOME/plugins/skill-guabao/scripts/guabao_updater.py`

## 🍲 GuaBao Update Checker (更新檢查)
GuaBao 內建了自動化更新檢查腳本，能分析 `third_party_git_skills` 清單，並利用 GitHub API 幫使用者確認是否有更新。
- **穩定期判定**：基於系統安全性，腳本採用「3 天穩定期」機制。當發現最新 commit 時，必須該 commit 發布超過 3 天沒有其他改動，才會建議更新，否則將標示為「觀察期」。
- **更新前防護 (Diff Scan)**：在執行更新之前，`guabao_updater.py` 會利用 GitHub API 取得的 Blob SHA1 自動掃描本地的外掛資料夾。若發現有本地修改，會中斷並警告，防止使用者的心血被遠端覆蓋。
- **執行方式**：Agent 可透過執行 `python <guabao 安裝路徑>/scripts/guabao_updater.py` 來獲取精美的版本比對報表。若狀態為 `UP_TO_DATE`、`UPDATE_AVAILABLE` 且 `last_pulled_commit` 存在，腳本也會一併進行本地防護掃描。

## 📝 外掛註冊表初始化與新增/移除維護 (Initialization & Maintenance)
如果使用者是第一次使用 GuaBao，或者系統中尚未存在 `plugins_inventory.yaml`，請執行以下操作：
1. **初始化**：若 GuaBao 尚未初始化，請複製 `plugins_inventory.template.yaml` 並重新命名為 `$GUABAO_HOME/plugins_inventory.yaml`。
2. **新增外掛與建立**：當使用者要求安裝或建立新的外掛時，Agent 必須：
   - 先呼叫 `check_naming_conflict` 確保名稱無衝突。
   - 若為安裝外部來源 (GitHub)，必須呼叫 `check_trusted_host` 比對 `trusted_hosts` 清單。若不在清單內，必須先警告使用者「此來源並非已知白名單」，等待使用者同意後再安裝。
   - 呼叫 `validate_install_path` 確認建立路徑位於 `$GUABAO_HOME/plugins/` 且命名合法。
   - 將外掛依類別登記至 `plugins_inventory.yaml` 中（若為第三方，記錄 `github_url` 與 `last_pulled_commit`）。
3. **移除/解除安裝外掛**：當使用者要求刪除外掛時，Agent **不應該**直接用指令刪除，而必須呼叫 `guabao_updater.py` 裡的 `uninstall_plugin(plugin_name, inventory_path)` 來執行封存與清理作業，並提醒使用者清除全域規則中的殘留。
4. **紀錄使用狀態 (可選)**：當 Agent 主動使用某個第三方或本地工具外掛時，建議呼叫 `mark_plugin_used(plugin_name, inventory_path)` 來更新其 `last_used_date`。GuaBao 會自動掃描超過 60 天未使用的閒置外掛並提醒使用者。

## 🚦 行為約束 (Behavioral Constraints)
根據 `plugins_inventory.yaml` 中的分類，你必須遵守以下相應的檔案存取與版本管理規則：

### 1. `git_tracked_skills` (類別一：自行開發的核心專案)
這些外掛是使用者自行開發並推送到 GitHub 的開源專案，分為兩種子模式，**必須先讀取清單的 `status` 欄位**才能決定操作方式：

---

#### 子模式 A：`status: Symlink / Repo = Runtime`（如 `skill-guabao`）
`plugins/<skill_name>/` 目錄**本身就是 Git Repo 根目錄**（裡面有 `.git`）。執行環境與版控環境合而為一。
- **可否編輯**：🟢 完全可以。
- **操作流程**：
  1. 直接在 `plugins/<skill_name>/` 編輯檔案，修改立即生效。
  2. 在同一目錄執行 `git add`、`git commit`、`git push`。**不需要 sync_script**。
  3. Push 完畢後執行 `--bump` 更新清單日期。

---

#### 子模式 B：`status: Monorepo / Sync Required`（如 `presentation_architect`、`antigravity-image-master`）
這類 skill 屬於某個 **monorepo**（多個 plugin 共用一個 GitHub Repo）。由於 Antigravity 系統**不支援 Junction/Symlink 讀取**，`plugins/` 底下只能是實體目錄拷貝，因此執行環境與 Git Repo 必然是兩個獨立的位置，透過 `sync_script` 橋接。
- **可否編輯**：🟢 完全可以。
- **`repo_local_path` 的意義**：指向 monorepo 的**根目錄**（例如 `agy-pptx-studio/`），而非 plugin 子目錄。
- **操作流程（同步方向：執行環境 → Repo）**：
  1. 直接在 `plugins/<skill_name>/` 編輯並測試，修改立即生效。
  2. 測試完成後，**必須**執行清單中的 `sync_script`，將改動從執行環境單向複製回 monorepo 的對應子目錄。
  3. 切換至 `repo_local_path` 目錄，執行 `git add`、`git commit`、`git push`。
  4. 執行 `--bump` 更新清單日期。
- **⚠️ 重要警告**：若跳過 sync_script 直接 push，Git Repo 將**不會**包含你在執行環境做的改動，造成版本落後！
- **反向部署（Repo → 執行環境）**：若從其他裝置更新了 Repo，需在 monorepo 執行 `git pull`，再**手動**將對應子目錄內容複製回 `plugins/<skill_name>/`（可撰寫反向 deploy 腳本）。

### 2. `local_utility_skills` (類別二：本地小工具)
這些是使用者僅在本地使用的輕量級工具包，不受 Git 版本控管。
- **可否編輯**：🟢 完全可以。
- **編輯規則**：可直接修改 `config/plugins/` 內的檔案。
- **強制操作**：無須 commit。

### 3. `third_party_git_skills` (類別三：第三方 GitHub 專案)
這些是使用者手動從開源社群抓取下來的第三方外掛。
- **可否編輯**：🔴 嚴格禁止。除非使用者明確下達「強制客製化第三方套件」的指令。
- **更新規則**：如需更新至最新版本，請依照以下標準流程操作：
  1. **版本確認**：執行 `python <guabao_dir>/scripts/guabao_updater.py` 確認版本狀態為 `UPDATE_AVAILABLE`（非觀察期）。
  2. **安全封存舊版**：將現有的 `$GUABAO_HOME/plugins/<skill_name>/` 目錄移動至 `$GUABAO_HOME/archive/<skill_name>_YYYYMMDD/` 備份。
  3. **重新 Clone**：從清單中的 `github_url` 執行 `git clone` 下載最新版本至原外掛目錄。
  4. **移除 `.git` 目錄**：第三方外掛以靜態快照管理，Clone 完成後刪除 `.git` 資料夾防止混淆。
  5. **同步版本紀錄**：取得新版的 Commit SHA（`git rev-parse HEAD`），更新清單的 `last_pulled_date` 與 `last_pulled_commit`（可用 `--bump` 指令更新日期）。

### 4. `system_bundled_skills` (類別四：系統原生外掛)
伴隨 Antigravity 核心引擎更新的官方外掛，通常沒有單獨的版本號與外部連結。
- **可否編輯**：🔴 嚴格禁止。這些外掛屬於系統核心邊界，任何修改都可能導致不可預期的系統崩潰。
- **更新規則**：它們會隨著 Antigravity 軟體本體自動更新，Agent 不應介入。
