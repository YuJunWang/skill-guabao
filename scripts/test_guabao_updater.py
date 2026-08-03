import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
import yaml

import guabao_updater

@pytest.fixture
def mock_yaml_data():
    return """
third_party_git_skills:
  test_plugin_stable:
    status: "Static / Tracked"
    github_url: "https://github.com/user/repo-stable"
    last_pulled_date: "2026-07-20"
  test_plugin_bleeding:
    status: "Static / Tracked"
    github_url: "https://github.com/user/repo-bleeding"
    last_pulled_date: "2026-07-20"
  test_plugin_up_to_date:
    status: "Static / Tracked"
    github_url: "https://github.com/user/repo-uptodate"
    last_pulled_date: "2026-08-01"
"""

def test_parse_inventory(tmp_path, mock_yaml_data):
    # 建立一個暫時的 yaml 檔案
    inventory_file = tmp_path / "plugins_inventory.yaml"
    inventory_file.write_text(mock_yaml_data)

    inventory_data = guabao_updater.parse_inventory(str(inventory_file))
    plugins = inventory_data.get("third_party_git_skills", {})
    
    assert len(plugins) == 3
    assert plugins["test_plugin_stable"]["github_url"] == "https://github.com/user/repo-stable"
    assert plugins["test_plugin_stable"]["last_pulled_date"] == "2026-07-20"

def test_check_naming_conflict():
    inventory = {
        "third_party_git_skills": {"anthropic-design": {}},
        "local_custom_skills": {"my-custom-skill": {}}
    }
    assert guabao_updater.check_naming_conflict("my-custom-skill", inventory) is True
    assert guabao_updater.check_naming_conflict("nonexistent-skill", inventory) is False

def test_check_trusted_host():
    inventory = {
        "trusted_hosts": ["github.com/anthropics", "github.com/langchain-ai"]
    }
    
    # Valid
    assert guabao_updater.check_trusted_host("https://github.com/anthropics/skills", inventory) is True
    assert guabao_updater.check_trusted_host("https://github.com/langchain-ai/langchain-skills", inventory) is True
    
    # Invalid
    assert guabao_updater.check_trusted_host("https://github.com/evil-hacker/skills", inventory) is False
    assert guabao_updater.check_trusted_host("https://gitlab.com/anthropics/skills", inventory) is False

def test_validate_install_path():
    from pathlib import Path
    base = (Path.home() / ".gemini" / "config" / "plugins").resolve()
    
    # Valid
    valid_path = base / "my-plugin"
    is_valid, msg = guabao_updater.validate_install_path(str(valid_path))
    assert is_valid is True
    
    # Invalid: nested too deep
    invalid_nested = base / "my-plugin" / "nested"
    is_valid, msg = guabao_updater.validate_install_path(str(invalid_nested))
    assert is_valid is False
    assert "directly under" in msg
    
    # Invalid: outside plugins dir
    invalid_outside = Path.home() / ".gemini" / "config" / "some-plugin"
    is_valid, msg = guabao_updater.validate_install_path(str(invalid_outside))
    assert is_valid is False
    assert "inside" in msg
    
    # Invalid: special chars in name
    invalid_name = base / "my plugin!"
    is_valid, msg = guabao_updater.validate_install_path(str(invalid_name))
    assert is_valid is False
    assert "alphanumeric" in msg

def test_uninstall_plugin(tmp_path, mock_yaml_data):
    from pathlib import Path
    import yaml
    import shutil
    
    # Setup inventory
    inventory_file = tmp_path / "plugins_inventory.yaml"
    inventory_file.write_text(mock_yaml_data)
    
    # Mock Path.home() to point to tmp_path
    with patch('guabao_updater.Path.home') as mock_home:
        mock_home.return_value = tmp_path
        
        # Create a fake plugin folder
        plugin_dir = tmp_path / ".gemini" / "config" / "plugins" / "test_plugin_stable"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "test.txt").write_text("hello")
        
        # Run uninstall
        guabao_updater.uninstall_plugin("test_plugin_stable", str(inventory_file))
        
        # Check folder moved
        assert not plugin_dir.exists()
        archive_dir = tmp_path / ".gemini" / "config" / "archive"
        assert archive_dir.exists()
        archived_folders = list(archive_dir.glob("test_plugin_stable_*"))
        assert len(archived_folders) == 1
        
        # Check inventory updated
        with open(inventory_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        assert "test_plugin_stable" not in data["third_party_git_skills"]
        assert "test_plugin_bleeding" in data["third_party_git_skills"]

def test_mark_plugin_used(tmp_path, mock_yaml_data):
    import yaml
    from datetime import datetime
    
    inventory_file = tmp_path / "plugins_inventory.yaml"
    inventory_file.write_text(mock_yaml_data)
    
    res = guabao_updater.mark_plugin_used("test_plugin_stable", str(inventory_file))
    assert res is True
    
    with open(inventory_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    today = datetime.now().strftime("%Y-%m-%d")
    assert data["third_party_git_skills"]["test_plugin_stable"]["last_used_date"] == today
    assert "last_used_date" not in data["third_party_git_skills"]["test_plugin_bleeding"]

def test_check_idle_plugins():
    from datetime import datetime, timedelta
    
    today = datetime.now()
    recent_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    old_date = (today - timedelta(days=70)).strftime("%Y-%m-%d")
    
    inventory_data = {
        "third_party_git_skills": {
            "active_plugin": {"last_used_date": recent_date},
            "idle_plugin": {"last_used_date": old_date},
            "never_used_old_plugin": {"last_pulled_date": old_date},
            "never_used_new_plugin": {"last_pulled_date": recent_date}
        }
    }
    
    idle = guabao_updater.check_idle_plugins(inventory_data, days=60)
    idle_names = [p[0] for p in idle]
    
    assert "idle_plugin" in idle_names
    assert "never_used_old_plugin" in idle_names
    assert "active_plugin" not in idle_names
    assert "never_used_new_plugin" not in idle_names

def test_api_url_conversion():
    github_url = "https://github.com/anthropics/skills"
    api_url = guabao_updater.get_api_url(github_url)
    assert api_url == "https://api.github.com/repos/anthropics/skills/commits?per_page=1"

@patch('guabao_updater.requests.get')
def test_check_update_stable(mock_get):
    # Mock GitHub API response for a commit 5 days ago (Stable)
    five_days_ago = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"commit": {"committer": {"date": five_days_ago}}}]

    status, latest_date = guabao_updater.check_plugin_status("https://github.com/user/repo-stable", "2026-07-20")
    
    # 5 days ago is > 3 days (stable), and newer than 2026-07-20
    assert status == "UPDATE_AVAILABLE"
    assert latest_date == (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

@patch('guabao_updater.requests.get')
def test_check_update_bleeding(mock_get):
    # Mock GitHub API response for a commit 1 day ago (Bleeding Edge)
    one_day_ago = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"commit": {"committer": {"date": one_day_ago}}}]

    status, latest_date = guabao_updater.check_plugin_status("https://github.com/user/repo-bleeding", "2026-07-20")
    
    # 1 day ago is < 3 days (bleeding edge), but newer than 2026-07-20
    assert status == "BLEEDING_EDGE"
    assert latest_date == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

@patch('guabao_updater.requests.get')
def test_check_up_to_date(mock_get):
    # Mock GitHub API response for a commit older than or equal to last pulled date
    old_date = "2026-07-15T10:00:00Z"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"commit": {"committer": {"date": old_date}}}]

    status, latest_date = guabao_updater.check_plugin_status("https://github.com/user/repo-uptodate", "2026-08-01")
    
    assert status == "UP_TO_DATE"
    assert latest_date == "2026-07-15"
