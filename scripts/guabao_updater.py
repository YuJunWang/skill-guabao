import yaml
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import hashlib
import re
import shutil
import argparse
from urllib.parse import urlparse

def get_guabao_home():
    """Return the base config directory for GuaBao. 
    Uses GUABAO_HOME if set, otherwise defaults to ~/.gemini/config/"""
    env_home = os.environ.get("GUABAO_HOME")
    if env_home:
        return Path(env_home).resolve()
    return (Path.home() / ".gemini" / "config").resolve()

def parse_inventory(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data

def check_trusted_host(github_url, inventory_data):
    """Check if the github_url belongs to a trusted host."""
    trusted_hosts = inventory_data.get("trusted_hosts", [])
    
    try:
        parsed = urlparse(github_url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 1:
            domain = parsed.netloc
            owner = path_parts[0]
            host_str = f"{domain}/{owner}"
            return host_str in trusted_hosts
    except Exception:
        pass
    return False

def mark_plugin_used(plugin_name, inventory_path):
    """Update the last_used_date for a plugin to today."""
    inventory_path = Path(inventory_path).resolve()
    try:
        with open(inventory_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        updated = False
        today = datetime.now().strftime("%Y-%m-%d")
        for category, plugins in data.items():
            if isinstance(plugins, dict) and plugin_name in plugins:
                plugins[plugin_name]["last_used_date"] = today
                updated = True
                
        if updated:
            with open(inventory_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return True
    except Exception:
        pass
    return False

def check_idle_plugins(inventory_data, days=60):
    """Return a list of plugins that haven't been used in `days` days."""
    idle_plugins = []
    threshold_date = datetime.now() - timedelta(days=days)
    
    for category, plugins in inventory_data.items():
        if not isinstance(plugins, dict):
            continue
        for name, info in plugins.items():
            # Only consider tracked or utility skills for idle checking
            if category in ["system_bundled_skills"]:
                continue
                
            last_used = info.get("last_used_date")
            if last_used:
                try:
                    used_date = datetime.strptime(last_used, "%Y-%m-%d")
                    if used_date < threshold_date:
                        idle_plugins.append((name, last_used))
                except ValueError:
                    pass
            else:
                # If never marked used, maybe it's been idle since pull/update
                last_pulled = info.get("last_pulled_date") or info.get("last_updated")
                if last_pulled:
                    try:
                        pulled_date = datetime.strptime(last_pulled, "%Y-%m-%d")
                        if pulled_date < threshold_date:
                            idle_plugins.append((name, f"Never used (Pulled: {last_pulled})"))
                    except ValueError:
                        pass
                        
    return idle_plugins

def check_naming_conflict(skill_name, inventory):
    """Check if the plugin name already exists in any category."""
    for category, plugins in inventory.items():
        if isinstance(plugins, dict) and skill_name in plugins:
            return True
    return False

def calculate_git_blob_sha(filepath):
    """Calculate the git blob SHA1 of a file."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
    except Exception:
        return None
    # Handle Windows CRLF -> LF conversion for git blob SHA
    content = content.replace(b'\r\n', b'\n')
    blob = f"blob {len(content)}\0".encode('utf-8') + content
    return hashlib.sha1(blob).hexdigest()

def fetch_github_tree(github_url, commit_sha):
    """Fetch the git tree of a commit."""
    parts = github_url.rstrip('/').split('/')
    owner, repo = parts[-2], parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1"
    headers = {"User-Agent": "GuaBao-Updater"}
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.json().get("tree", [])
    return []

def pre_update_scan(plugin_dir, github_url, commit_sha):
    """Scan local plugin directory against remote github tree. Returns list of modified files."""
    tree = fetch_github_tree(github_url, commit_sha)
    if not tree:
        return None # Failed to fetch tree
        
    remote_shas = {} 
    for item in tree:
        if item["type"] == "blob":
            name = os.path.basename(item["path"])
            if name not in remote_shas:
                remote_shas[name] = set()
            remote_shas[name].add(item["sha"])
            
    modified_files = []
    if not os.path.exists(plugin_dir):
        return []

    for root, dirs, files in os.walk(plugin_dir):
        for file in files:
            if file == ".DS_Store" or file.endswith(".pyc"):
                continue
                
            local_path = os.path.join(root, file)
            local_sha = calculate_git_blob_sha(local_path)
            
            if file in remote_shas:
                if local_sha not in remote_shas[file]:
                    modified_files.append(local_path)
                    
    return modified_files

def validate_install_path(target_path):
    """Validate if the given path is a valid installation path for a plugin."""
    target = Path(target_path).resolve()
    base_plugins = get_guabao_home() / "plugins"
    
    if base_plugins not in target.parents:
        return False, f"Target path must be inside {base_plugins}"
        
    if target.parent != base_plugins:
        return False, "Target path must be directly under the plugins/ directory."
        
    plugin_name = target.name
    import re
    if not re.match(r'^[\w\-]+$', plugin_name):
        return False, "Plugin name can only contain alphanumeric characters, hyphens, and underscores."
        
    return True, "Valid path"

def uninstall_plugin(plugin_name, inventory_path):
    """Safely uninstall a plugin by archiving it and removing from inventory."""
    inventory_path = Path(inventory_path).resolve()
    base_plugins = get_guabao_home() / "plugins"
    archive_dir = get_guabao_home() / "archive"
    
    plugin_dir = base_plugins / plugin_name
    
    if plugin_dir.exists():
        archive_dir.mkdir(parents=True, exist_ok=True)
        date_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived_path = archive_dir / f"{plugin_name}_{date_suffix}"
        shutil.move(str(plugin_dir), str(archived_path))
        print(f"📦 已將外掛資料夾封存至: {archived_path}")
    else:
        print(f"⚠️ 找不到外掛資料夾: {plugin_dir}，僅清除註冊紀錄。")
        
    try:
        with open(inventory_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        removed = False
        for category in data.keys():
            if isinstance(data[category], dict) and plugin_name in data[category]:
                del data[category][plugin_name]
                removed = True
                
        if removed:
            with open(inventory_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"🗑️ 已從註冊表中移除 `{plugin_name}`。")
    except Exception as e:
        print(f"⚠️ 處理註冊表時發生錯誤: {e}")
    
    print("\n🚨 【重要提醒】 🚨")
    print(f"請務必檢查你的全域設定檔 (如 `AGENTS.md` 或其他系統提示詞) 中，")
    print(f"是否還有殘留指向 `{plugin_name}` 的觸發規則或路由！如果有，請記得手動刪除以避免 AI 發生混淆。")

def bump_plugin_version(plugin_name, inventory_path):
    """Update the last_updated date to today for a git_tracked_skill."""
    inventory_path = Path(inventory_path).resolve()
    try:
        with open(inventory_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        updated = False
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check in git_tracked_skills
        if "git_tracked_skills" in data and plugin_name in data["git_tracked_skills"]:
            data["git_tracked_skills"][plugin_name]["last_updated"] = today
            updated = True
        
        # Also check third_party just in case (update last_pulled_date)
        if "third_party_git_skills" in data and plugin_name in data["third_party_git_skills"]:
            data["third_party_git_skills"][plugin_name]["last_pulled_date"] = today
            updated = True
            
        if updated:
            with open(inventory_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"✅ 已成功將外掛 `{plugin_name}` 的更新日期同步為 {today}！")
            return True
        else:
            print(f"⚠️ 找不到外掛 `{plugin_name}`，請確認名稱是否正確。")
            return False
    except Exception as e:
        print(f"⚠️ 處理註冊表時發生錯誤: {e}")
        return False

def get_api_url(github_url):
    # github_url e.g., https://github.com/anthropics/skills
    parts = github_url.rstrip('/').split('/')
    owner, repo = parts[-2], parts[-1]
    return f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

def check_plugin_status(github_url, last_pulled_date_str, stable_days=3):
    api_url = get_api_url(github_url)
    # Add a user-agent to avoid GitHub API 403 errors
    headers = {"User-Agent": "GuaBao-Updater"}
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        return "ERROR", None
    
    commits = response.json()
    if not commits:
        return "ERROR", None
        
    latest_commit_date_str = commits[0]["commit"]["committer"]["date"]
    # Parse ISO 8601 from GitHub: e.g., 2026-06-16T10:00:00Z
    # Some older pythons don't parse Z well with fromisoformat, so we handle it:
    latest_commit_date_str = latest_commit_date_str.replace("Z", "+00:00")
    try:
        latest_commit_date = datetime.fromisoformat(latest_commit_date_str)
    except ValueError:
        return "ERROR", None
        
    latest_date_only = latest_commit_date.strftime("%Y-%m-%d")
    
    # Compare with last_pulled_date_str
    last_pulled_date = datetime.strptime(last_pulled_date_str, "%Y-%m-%d").date()
    latest_date_obj = datetime.strptime(latest_date_only, "%Y-%m-%d").date()
    
    if latest_date_obj <= last_pulled_date:
        return "UP_TO_DATE", latest_date_only
        
    # It's newer. Check if it's stable.
    # Current date
    now = datetime.now(latest_commit_date.tzinfo)
    age_days = (now - latest_commit_date).days
    
    if age_days >= stable_days:
        return "UPDATE_AVAILABLE", latest_date_only
    else:
        return "BLEEDING_EDGE", latest_date_only

def main():
    parser = argparse.ArgumentParser(description="GuaBao Plugin Updater")
    default_inventory = get_guabao_home() / "plugins_inventory.yaml"
    parser.add_argument("--inventory", default=str(default_inventory), help="Path to plugins_inventory.yaml")
    parser.add_argument("--bump", metavar="PLUGIN_NAME", help="Update the last_updated/last_pulled_date to today for the specified plugin")
    args = parser.parse_args()
    
    # 解決 Windows 終端機 Emoji 輸出編碼問題
    sys.stdout.reconfigure(encoding='utf-8')
    
    if args.bump:
        bump_plugin_version(args.bump, args.inventory)
        return
    
    print("=========================================")
    print(" GuaBao Updater: 第三方外掛狀態掃描")
    print("=========================================\n")
    
    try:
        inventory_data = parse_inventory(args.inventory)
        plugins = inventory_data.get("third_party_git_skills", {})
    except Exception as e:
        print(f"Failed to read inventory: {e}")
        sys.exit(1)
        
    print(f"Found {len(plugins)} third-party skills to check.\n")
    
    for name, info in plugins.items():
        github_url = info.get("github_url")
        last_pulled_date = str(info.get("last_pulled_date", "2000-01-01"))  # 保護：YAML 有時會將日期自動解析為 date 物件
        
        if not github_url:
            print(f"- {name}: No GitHub URL found, skipping.")
            continue
            
        print(f"🔍 檢查 {name}...")
        status, latest_date = check_plugin_status(github_url, last_pulled_date)
        
        if status == "UP_TO_DATE":
            print(f"   ✅ 最新版本 (目前: {last_pulled_date}, 遠端: {latest_date})")
        elif status == "UPDATE_AVAILABLE":
            print(f"   🌟 穩定更新可用！ (目前: {last_pulled_date} -> 遠端: {latest_date})")
            print(f"      [動作建議] 可執行 git pull 來更新！網址: {github_url}")
        elif status == "BLEEDING_EDGE":
            print(f"   ⚠️ 有新版本但在觀察期內 (目前: {last_pulled_date} -> 遠端: {latest_date})")
            print(f"      [動作建議] 剛發布不久，建議再等幾天穩定後更新。")
        else:
            print(f"   ❌ 檢查失敗，無法取得 GitHub 資訊。")
            
        last_pulled_commit = info.get("last_pulled_commit")
        
        # 檢查本地防護 (Diff Scan)
        plugin_dir = get_guabao_home() / "plugins" / name
        if status in ["UP_TO_DATE", "UPDATE_AVAILABLE", "BLEEDING_EDGE"] and last_pulled_commit:
            modified = pre_update_scan(plugin_dir, github_url, last_pulled_commit)
            if modified is None:
                print(f"   ❌ 無法取得 GitHub tree ({last_pulled_commit})，略過本地 diff 比對。")
            elif modified:
                print(f"   ⚠️ 警告：偵測到本地檔案有未預期修改，請確認或備份！")
                for m in modified:
                    print(f"      - {m}")
        print()
        
    print("=========================================")
    print("檢查完畢！")

if __name__ == "__main__":
    main()
