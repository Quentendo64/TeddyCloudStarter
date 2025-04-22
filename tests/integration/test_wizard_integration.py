import os
import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from TeddyCloudStarter.main import TeddyCloudWizard, ConfigManager, DockerManager, Translator

@pytest.mark.integration
class TestWizardIntegration:
    """Integration tests for TeddyCloudWizard components working together."""
    
    def test_wizard_initialization(self):
        """Test the wizard initializes all required components."""
        with patch.object(Translator, '_load_translations'), \
             patch.object(ConfigManager, '_load_config'), \
             patch.object(DockerManager, '_check_docker'):
            
            wizard = TeddyCloudWizard()
            
            # Check that all components are initialized
            assert isinstance(wizard.translator, Translator)
            assert isinstance(wizard.config_manager, ConfigManager)
            assert isinstance(wizard.docker_manager, DockerManager)
            assert 'docker-compose-direct' in wizard.templates
            assert 'docker-compose-nginx' in wizard.templates
    
    @pytest.mark.skip(reason="This test has console interaction issues in CI environments")
    @patch('rich.console.Console.print')
    def test_full_direct_mode_configuration(self, mock_print, temp_dir):
        """Test a full direct mode configuration scenario."""
        # Set up a config path in the temp directory
        config_path = os.path.join(temp_dir, "test_config.json")
        
        # Create a wizard with mocked components
        with patch.object(Translator, '_load_translations'), \
             patch.object(DockerManager, '_check_docker'):
            
            wizard = TeddyCloudWizard()
            wizard.config_manager = ConfigManager(config_path=config_path)
            wizard.docker_manager.docker_available = True
            wizard.docker_manager.compose_cmd = ["docker", "compose"]
            
            # Mock network checks
            with patch.object(wizard, '_check_port_available', return_value=True):
                # Mock questionary responses for direct mode
                with patch('questionary.select') as mock_select, \
                     patch('questionary.confirm') as mock_confirm, \
                     patch('questionary.text') as mock_text:
                    
                    # Mock responses for selecting direct mode
                    mock_select.return_value.ask.return_value = "Direct (For internal networks)"
                    
                    # Mock responses for HTTP settings
                    mock_confirm.return_value.ask.side_effect = [
                        True,   # Use HTTP port
                        False,  # Don't restart services
                    ]
                    
                    # Run the wizard
                    wizard.run_wizard()
                    
                    # Verify configuration was saved
                    assert os.path.exists(config_path)
                    
                    # Verify the configuration content
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        assert config["mode"] == "direct"
                        assert config["ports"]["admin_http"] == 80
    
    @pytest.mark.skip(reason="This test has console interaction issues in CI environments")
    @patch('questionary.select')
    @patch('questionary.confirm')
    @patch('questionary.text')
    def test_nginx_mode_configuration_integration(self, mock_text, mock_confirm, mock_select, temp_dir):
        """Test the integration between Nginx configuration and certificate handling."""
        # Set up a config path in the temp directory
        config_path = os.path.join(temp_dir, "test_config.json")
        
        # Create test directories
        server_certs_dir = Path(temp_dir) / "data" / "server_certs"
        server_certs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dummy cert files
        (server_certs_dir / "server.crt").touch()
        (server_certs_dir / "server.key").touch()
        
        # Create a wizard with mocked components
        with patch.object(Translator, '_load_translations'), \
             patch.object(DockerManager, '_check_docker'), \
             patch('pathlib.Path.mkdir'), \
             patch('rich.console.Console.print'), \
             patch('os.path.abspath', return_value="/mocked/path"):
            
            wizard = TeddyCloudWizard()
            wizard.config_manager = ConfigManager(config_path=config_path)
            wizard.docker_manager.docker_available = True
            
            # Mock network checks and file operations
            with patch.object(wizard, '_check_port_available', return_value=True), \
                 patch.object(wizard, '_generate_docker_compose', return_value=True), \
                 patch.object(wizard, '_request_letsencrypt_certificate', return_value=True), \
                 patch.object(wizard, '_generate_nginx_configs', return_value=True), \
                 patch('pathlib.Path.exists', return_value=True):
                
                # Set up questionary responses
                mock_select.return_value.ask.side_effect = [
                    "With Nginx (For internet-facing deployments)",  # Deployment mode
                    "Custom certificates (provide your own)",        # HTTPS mode
                    "Client Certificates",                          # Security type
                    "Generate certificates for me"                  # Certificate handling
                ]
                
                mock_confirm.return_value.ask.side_effect = [
                    True,   # Port warning continue
                    False,  # No IP restrictions
                    False   # Don't restart services
                ]
                
                mock_text.return_value.ask.side_effect = [
                    "example.com",      # Domain name
                    "TeddyCloudClient"  # Client certificate name
                ]
                
                # Run the wizard with nginx mode
                with patch.object(wizard, '_generate_client_certificates', return_value=True):
                    wizard.run_wizard()
                
                # Verify configuration was saved
                assert os.path.exists(config_path)
                
                # Verify the configuration content
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    assert config["mode"] == "nginx"
                    assert config["nginx"]["domain"] == "example.com"
                    assert config["nginx"]["https_mode"] == "custom"
                    assert config["nginx"]["security"]["type"] == "client_cert"
    
    @patch('rich.console.Console.print')
    def test_template_generation_integration(self, mock_print, temp_dir):
        """Test the integration between configuration and template generation."""
        # Set up a config path in the temp directory
        config_path = os.path.join(temp_dir, "test_config.json")
        
        # Create data directory
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a wizard with mocked components
        with patch.object(Translator, '_load_translations'), \
             patch.object(DockerManager, '_check_docker'), \
             patch('os.chdir'), \
             patch('os.getcwd', return_value=temp_dir):
            
            wizard = TeddyCloudWizard()
            wizard.config_manager = ConfigManager(config_path=config_path)
            
            # Configure for direct mode
            wizard.config_manager.config["mode"] = "direct"
            wizard.config_manager.config["ports"]["admin_http"] = 8080
            wizard.config_manager.config["ports"]["admin_https"] = 8443
            wizard.config_manager.config["ports"]["teddycloud"] = 4443
            
            # Provide template content for testing
            wizard.templates = {
                "docker-compose-direct": "version: '3'\nservices:\n  admin-http:\n    ports:\n      - \"{{ admin_http }}:80\"",
                "docker-compose-nginx": "version: '3'\nservices:\n  nginx:\n    environment:\n      - DOMAIN={{ domain }}"
            }
            
            # Import jinja2 for template rendering
            with patch('jinja2.Environment') as mock_env:
                # Mock the template rendering
                mock_template = MagicMock()
                mock_template.render.return_value = "Rendered template"
                mock_env.return_value.from_string.return_value = mock_template
                
                # Mock the file write operation
                with patch("builtins.open", mock_open()) as mock_file:
                    result = wizard._generate_docker_compose()
                    
                    # Check the result
                    assert result is True
                    
                    # Verify template was rendered with correct context
                    mock_env.return_value.from_string.assert_called_with(wizard.templates["docker-compose-direct"])
                    mock_template.render.assert_called_once()
                    context = mock_template.render.call_args[1]
                    assert context["admin_http"] == 8080
                    assert context["admin_https"] == 8443
                    assert context["teddycloud"] == 4443
            
            # Test with nginx mode
            wizard.config_manager.config["mode"] = "nginx"
            wizard.config_manager.config["nginx"]["domain"] = "test.example.com"
            
            # Import jinja2 for template rendering
            with patch('jinja2.Environment') as mock_env, \
                 patch.object(wizard, '_generate_nginx_configs', return_value=True):
                
                # Mock the template rendering
                mock_template = MagicMock()
                mock_template.render.return_value = "Rendered nginx template"
                mock_env.return_value.from_string.return_value = mock_template
                
                # Mock the file write operation
                with patch("builtins.open", mock_open()) as mock_file:
                    result = wizard._generate_docker_compose()
                    
                    # Check the result
                    assert result is True
                    
                    # Verify template was rendered with correct context
                    mock_env.return_value.from_string.assert_called_with(wizard.templates["docker-compose-nginx"])
                    mock_template.render.assert_called_once()
                    context = mock_template.render.call_args[1]
                    assert context["domain"] == "test.example.com"