import os
import pytest
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from TeddyCloudStarter.main import ConfigManager

@pytest.mark.unit
class TestConfigManager:
    """Unit tests for the ConfigManager class."""

    def test_load_config_existing_file(self, mock_config_file):
        """Test loading configuration from an existing file."""
        config_manager = ConfigManager(config_path=mock_config_file)
        assert config_manager.config["mode"] == "direct"
        assert config_manager.config["ports"]["admin_http"] == 80

    def test_load_config_invalid_json(self, mock_empty_config_file):
        """Test loading configuration with invalid JSON."""
        with patch('rich.console.Console.print') as mock_print:
            config_manager = ConfigManager(config_path=mock_empty_config_file)
            mock_print.assert_called_once()
            assert "defaults" in mock_print.call_args[0][0].lower()
        
        # Should use defaults
        assert config_manager.config["mode"] == "direct"
        assert "ports" in config_manager.config

    def test_load_config_nonexistent_file(self, temp_dir):
        """Test loading configuration from a nonexistent file."""
        config_path = os.path.join(temp_dir, "nonexistent_config.json")
        config_manager = ConfigManager(config_path=config_path)
        
        # Should use defaults
        assert config_manager.config["version"] == "1.0.0"
        assert config_manager.config["mode"] == "direct"
        assert "ports" in config_manager.config

    def test_save_config(self, temp_dir):
        """Test saving configuration to file."""
        config_path = os.path.join(temp_dir, "test_config.json")
        config_manager = ConfigManager(config_path=config_path)
        
        # Modify the configuration
        config_manager.config["mode"] = "nginx"
        config_manager.config["nginx"]["domain"] = "example.com"
        
        # Save the configuration
        with patch('rich.console.Console.print') as mock_print:
            config_manager.save()
        
        # Verify the file was saved
        assert os.path.exists(config_path)
        
        # Load the configuration again to verify it was saved correctly
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["mode"] == "nginx"
        assert saved_config["nginx"]["domain"] == "example.com"

    def test_backup_config(self, mock_config_file):
        """Test backing up configuration."""
        config_manager = ConfigManager(config_path=mock_config_file)
        
        with patch('shutil.copy2') as mock_copy, \
             patch('rich.console.Console.print') as mock_print, \
             patch('time.time', return_value=123456789):
            config_manager.backup()
            
            # Verify backup was created
            expected_backup_path = f"{mock_config_file}.backup.123456789"
            mock_copy.assert_called_once_with(mock_config_file, expected_backup_path)
            mock_print.assert_called_once()
            assert "backup created" in mock_print.call_args[0][0].lower()

    def test_delete_config(self, mock_config_file):
        """Test deleting configuration file."""
        config_manager = ConfigManager(config_path=mock_config_file)
        
        with patch('os.remove') as mock_remove, \
             patch('rich.console.Console.print') as mock_print:
            config_manager.delete()
            
            # Verify file was deleted
            mock_remove.assert_called_once_with(mock_config_file)
            mock_print.assert_called_once()
            assert "deleted" in mock_print.call_args[0][0].lower()
            
            # Config should be reset to defaults
            assert config_manager.config["mode"] == "direct"