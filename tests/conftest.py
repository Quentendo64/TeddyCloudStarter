import os
import pytest
import tempfile
import shutil
import json
from pathlib import Path

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_config_file(temp_dir):
    """Create a mock configuration file."""
    config_path = os.path.join(temp_dir, "config.json")
    config_data = {
        "version": "1.0.0",
        "mode": "direct",
        "ports": {
            "admin_http": 80,
            "admin_https": 8443,
            "teddycloud": 443
        },
        "nginx": {
            "domain": "test.example.com",
            "https_mode": "letsencrypt",
            "security": {
                "type": "none",
                "allowed_ips": []
            }
        },
        "language": "en"
    }
    
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    yield config_path

@pytest.fixture
def mock_empty_config_file(temp_dir):
    """Create an empty configuration file."""
    config_path = os.path.join(temp_dir, "config.json")
    with open(config_path, 'w') as f:
        f.write("")
    
    yield config_path

class MockSubprocess:
    """Mock for subprocess to avoid actual command execution."""
    def __init__(self, return_code=0, stdout="", stderr=""):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
    
    def __call__(self, *args, **kwargs):
        class CompletedProcess:
            def __init__(self, return_code, stdout, stderr):
                self.returncode = return_code
                self.stdout = stdout
                self.stderr = stderr
        
        return CompletedProcess(self.return_code, self.stdout, self.stderr)

@pytest.fixture
def mock_successful_subprocess(monkeypatch):
    """Mock subprocess.run to return successful completion."""
    mock = MockSubprocess(return_code=0, stdout="Success", stderr="")
    monkeypatch.setattr("subprocess.run", mock)
    yield mock

@pytest.fixture
def mock_failed_subprocess(monkeypatch):
    """Mock subprocess.run to return failed completion."""
    mock = MockSubprocess(return_code=1, stdout="", stderr="Error")
    monkeypatch.setattr("subprocess.run", mock)
    yield mock

@pytest.fixture
def mock_docker_available(monkeypatch):
    """Mock docker availability check to return True."""
    def mock_check(*args, **kwargs):
        return True
    monkeypatch.setattr("TeddyCloudStarter.main.DockerManager._check_docker", lambda self: None)
    monkeypatch.setattr("TeddyCloudStarter.main.DockerManager.docker_available", True, raising=False)
    yield

@pytest.fixture
def mock_docker_unavailable(monkeypatch):
    """Mock docker availability check to return False."""
    def mock_check(*args, **kwargs):
        return False
    monkeypatch.setattr("TeddyCloudStarter.main.DockerManager._check_docker", lambda self: None)
    monkeypatch.setattr("TeddyCloudStarter.main.DockerManager.docker_available", False, raising=False)
    yield