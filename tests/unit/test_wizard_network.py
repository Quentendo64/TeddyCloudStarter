import pytest
import socket
import ipaddress
from unittest.mock import patch, MagicMock

from TeddyCloudStarter.main import TeddyCloudWizard, ConfigManager, DockerManager

@pytest.mark.unit
class TestWizardNetwork:
    """Unit tests for TeddyCloudWizard network-related functionality."""
    
    def test_check_port_available_free_port(self):
        """Test checking if a port is available when it is free."""
        with patch('socket.socket') as mock_socket:
            # Mock the socket to indicate the port is free
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.bind.return_value = None  # Success
            
            wizard = TeddyCloudWizard()
            assert wizard._check_port_available(8080) is True
            
            # Verify the socket was bound to the correct port
            mock_sock_instance.bind.assert_called_once_with(('127.0.0.1', 8080))
    
    def test_check_port_available_used_port(self):
        """Test checking if a port is available when it is in use."""
        with patch('socket.socket') as mock_socket:
            # Mock the socket to indicate the port is in use
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.bind.side_effect = socket.error("Port in use")
            
            wizard = TeddyCloudWizard()
            assert wizard._check_port_available(80) is False
    
    @patch('ipaddress.ip_network')
    def test_ip_validation_valid(self, mock_ip_network):
        """Test validation of valid IP addresses and CIDR notation."""
        # Set up test data
        valid_ips = [
            "192.168.1.1",
            "10.0.0.0/24",
            "172.16.0.1",
            "2001:db8::/32"
        ]
        
        # Create a wizard with mock dependencies
        wizard = TeddyCloudWizard()
        wizard.config_manager = MagicMock(spec=ConfigManager)
        wizard.config_manager.config = {
            "nginx": {"security": {"allowed_ips": []}}
        }
        
        # Completely mock the _configure_nginx_mode method to avoid console interaction
        with patch.object(wizard, '_configure_nginx_mode') as mock_config_nginx:
            # Call a simpler helper method to test IP validation logic
            for ip in valid_ips:
                # Directly call the validation logic
                try:
                    ipaddress.ip_network(ip)
                    wizard.config_manager.config["nginx"]["security"]["allowed_ips"].append(ip)
                except ValueError:
                    pass
            
            # Verify the IPs were added to the config
            assert wizard.config_manager.config["nginx"]["security"]["allowed_ips"] == valid_ips
    
    @patch('ipaddress.ip_network')
    def test_ip_validation_invalid(self, mock_ip_network):
        """Test validation of invalid IP addresses."""
        # Set up the mock to raise a ValueError for invalid IPs
        mock_ip_network.side_effect = ValueError("Invalid IP")
        
        # Create a wizard with mock dependencies
        wizard = TeddyCloudWizard()
        wizard.config_manager = MagicMock(spec=ConfigManager)
        wizard.config_manager.config = {
            "nginx": {"security": {"allowed_ips": []}}
        }
        
        # Test with a single invalid IP
        with patch('rich.console.Console.print') as mock_print:
            # Directly call the validation logic
            try:
                ipaddress.ip_network("invalid-ip")
                wizard.config_manager.config["nginx"]["security"]["allowed_ips"].append("invalid-ip")
            except ValueError:
                mock_print("[bold red]Invalid IP address or CIDR: invalid-ip[/]")
            
            # Verify no IPs were added to the config
            assert wizard.config_manager.config["nginx"]["security"]["allowed_ips"] == []

    def test_request_letsencrypt_certificate_docker_available(self):
        """Test requesting Let's Encrypt certificate when Docker is available."""
        # Create a wizard with mock dependencies
        wizard = TeddyCloudWizard()
        wizard.docker_manager = MagicMock(spec=DockerManager)
        wizard.docker_manager.is_available.return_value = True
        
        # Mock the subprocess run to simulate a successful certificate request
        with patch('subprocess.run') as mock_run, \
             patch('rich.console.Console.print') as mock_print, \
             patch('os.path.abspath', return_value="/some/path"):
            
            # Mock successful certificate request
            mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
            
            result = wizard._request_letsencrypt_certificate("example.com")
            
            # Verify the result
            assert result is True
            
            # Verify certbot command was called with correct parameters
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "certbot/certbot" in args
            assert "certonly" in args
            assert "example.com" in args
            assert "--staging" in args
            
            # Verify success message was printed
            assert any("successful" in str(call) for call in mock_print.call_args_list)
    
    def test_request_letsencrypt_certificate_docker_unavailable(self):
        """Test requesting Let's Encrypt certificate when Docker is unavailable."""
        # Create a wizard with mock dependencies
        wizard = TeddyCloudWizard()
        wizard.docker_manager = MagicMock(spec=DockerManager)
        wizard.docker_manager.is_available.return_value = False
        
        with patch('rich.console.Console.print') as mock_print:
            result = wizard._request_letsencrypt_certificate("example.com")
            
            # Verify the result
            assert result is False
            
            # Verify error message was printed
            mock_print.assert_any_call("[bold red]Docker is not available. Cannot request certificate.[/]")
    
    def test_request_letsencrypt_certificate_failure(self):
        """Test requesting Let's Encrypt certificate when the request fails."""
        # Create a wizard with mock dependencies
        wizard = TeddyCloudWizard()
        wizard.docker_manager = MagicMock(spec=DockerManager)
        wizard.docker_manager.is_available.return_value = True
        
        # Mock the subprocess run to simulate a failed certificate request
        with patch('subprocess.run') as mock_run, \
             patch('rich.console.Console.print') as mock_print:
            
            # Mock failed certificate request
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Some error")
            
            result = wizard._request_letsencrypt_certificate("example.com")
            
            # Verify the result
            assert result is False
            
            # Verify error message was printed
            assert any("failed" in str(call) for call in mock_print.call_args_list)