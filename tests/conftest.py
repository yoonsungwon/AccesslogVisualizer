"""
Pytest configuration and fixtures for Access Log Analyzer tests
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_alb_log(temp_dir):
    """Create a sample ALB log file"""
    log_content = """https 2024-08-08T09:00:00.000000Z app/test-alb/123 1.2.3.4:443 10.0.0.1:8080 0.001 0.002 0.001 200 200 100 200 "GET https://example.com:443/api/test HTTP/1.1" "Mozilla/5.0" ECDHE-RSA-AES128 TLSv1.2
https 2024-08-08T09:00:01.000000Z app/test-alb/123 1.2.3.5:443 10.0.0.2:8080 0.002 0.003 0.002 404 404 150 250 "POST https://example.com:443/api/users/123 HTTP/1.1" "Mozilla/5.0" ECDHE-RSA-AES128 TLSv1.2
https 2024-08-08T09:00:02.000000Z app/test-alb/123 1.2.3.6:443 10.0.0.3:8080 0.003 0.004 0.003 500 500 200 300 "GET https://example.com:443/api/products HTTP/1.1" "Mozilla/5.0" ECDHE-RSA-AES128 TLSv1.2"""

    log_file = temp_dir / "sample_alb.log"
    log_file.write_text(log_content)
    return log_file


@pytest.fixture
def sample_apache_log(temp_dir):
    """Create a sample Apache/Nginx log file"""
    log_content = """127.0.0.1 - - [08/Aug/2024:09:00:00 +0000] "GET /api/test HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
127.0.0.2 - - [08/Aug/2024:09:00:01 +0000] "POST /api/users/123 HTTP/1.1" 404 567 "-" "Mozilla/5.0"
127.0.0.3 - - [08/Aug/2024:09:00:02 +0000] "GET /api/products HTTP/1.1" 500 890 "-" "Mozilla/5.0"""

    log_file = temp_dir / "sample_apache.log"
    log_file.write_text(log_content)
    return log_file


@pytest.fixture
def sample_json_log(temp_dir):
    """Create a sample JSON Lines log file"""
    log_content = """{"timestamp": "2024-08-08T09:00:00Z", "method": "GET", "url": "/api/test", "status": 200, "response_time": 0.001}
{"timestamp": "2024-08-08T09:00:01Z", "method": "POST", "url": "/api/users/123", "status": 404, "response_time": 0.002}
{"timestamp": "2024-08-08T09:00:02Z", "method": "GET", "url": "/api/products", "status": 500, "response_time": 0.003}"""

    log_file = temp_dir / "sample_json.log"
    log_file.write_text(log_content)
    return log_file
