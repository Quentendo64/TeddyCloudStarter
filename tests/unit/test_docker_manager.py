import pytest
import subprocess
from unittest.mock import patch, MagicMock

from TeddyCloudStarter.main import DockerManager

@pytest.mark.unit
class TestDockerManager:
    """Unit tests for the DockerManager class."""

    def test_check_docker_available(self):
        """Test docker availability check when docker is available."""
        with patch('subprocess.run') as mock_run:
            # Mock successful docker check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Docker version 20.10.12"
            
            # Mock successful docker compose v2 check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Docker Compose version v2.2.3"
            
            docker_manager = DockerManager()
            assert docker_manager.docker_available is True
            assert docker_manager.compose_cmd == ["docker", "compose"]

    def test_check_docker_available_compose_v1(self):
        """Test docker availability with Docker Compose v1."""
        with patch('subprocess.run') as mock_run:
            # Set up the mock to return different values on consecutive calls
            mock_run.side_effect = [
                # First call: docker version (success)
                MagicMock(returncode=0, stdout="Docker version 20.10.12", stderr=""),
                # Second call: docker compose v2 (failure)
                MagicMock(returncode=1, stdout="", stderr="command not found"),
                # Third call: docker-compose v1 (success)
                MagicMock(returncode=0, stdout="docker-compose version 1.29.2", stderr="")
            ]
            
            docker_manager = DockerManager()
            assert docker_manager.docker_available is True
            assert docker_manager.compose_cmd == ["docker-compose"]

    def test_check_docker_unavailable(self):
        """Test docker availability check when docker is unavailable."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("Docker not found")
            
            docker_manager = DockerManager()
            assert docker_manager.docker_available is False

    def test_is_available(self):
        """Test is_available method."""
        docker_manager = DockerManager()
        
        # Mock docker_available property
        docker_manager.docker_available = True
        assert docker_manager.is_available() is True
        
        docker_manager.docker_available = False
        assert docker_manager.is_available() is False

    def test_restart_services_docker_available(self, mock_successful_subprocess):
        """Test restarting services when Docker is available."""
        docker_manager = DockerManager()
        docker_manager.docker_available = True
        docker_manager.compose_cmd = ["docker", "compose"]
        
        with patch('rich.console.Console.print') as mock_print:
            result = docker_manager.restart_services()
            
            assert result is True
            # Verify that appropriate messages were printed
            assert any("restarting" in str(call).lower() for call in mock_print.call_args_list)
            assert any("successfully" in str(call).lower() for call in mock_print.call_args_list)

    def test_restart_services_docker_unavailable(self):
        """Test restarting services when Docker is unavailable."""
        docker_manager = DockerManager()
        docker_manager.docker_available = False
        
        with patch('rich.console.Console.print') as mock_print:
            result = docker_manager.restart_services()
            
            assert result is False
            mock_print.assert_called_once()
            assert "not available" in str(mock_print.call_args[0][0]).lower()

    def test_restart_services_error(self):
        """Test restarting services when an error occurs."""
        docker_manager = DockerManager()
        docker_manager.docker_available = True
        docker_manager.compose_cmd = ["docker", "compose"]
        
        # Use a direct mock for subprocess.run instead of the fixture
        with patch('subprocess.run') as mock_run, \
             patch('rich.console.Console.print') as mock_print:
            
            # Have subprocess.run raise an exception to simulate an error
            mock_run.side_effect = subprocess.SubprocessError("Command failed")
            
            result = docker_manager.restart_services()
            
            assert result is False
            assert any("error" in str(call).lower() for call in mock_print.call_args_list)