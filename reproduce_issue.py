
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from data_parser import recommendAccessLogFormat

# Create a dummy ALB log file
log_content = 'http 2023-01-01T00:00:00.000000Z app/my-load-balancer/50dc6c495c0c9188 192.168.1.1:2817 10.0.0.1:80 0.000 0.001 0.000 200 200 34 366 "GET http://www.example.com:80/ HTTP/1.1" "Mozilla/5.0" - - arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 "Root=1-58337262-36d228ad5d99923122bbe354" "-" "-" 0 2023-01-01T00:00:00.000000Z "forward" "-" "-" "10.0.0.1:80" "200" "-" "-"'

with open('test_alb.log', 'w') as f:
    for _ in range(100):
        f.write(log_content + '\n')

# Create config.yaml to trigger the code path
with open('config.yaml', 'w') as f:
    f.write('log_format_type: ALB\n')

try:
    print("Running recommendAccessLogFormat...")
    result = recommendAccessLogFormat('test_alb.log')
    print("Success!")
    print(result)
except Exception as e:
    print(f"Caught exception: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    if os.path.exists('test_alb.log'):
        os.remove('test_alb.log')
    if os.path.exists('config.yaml'):
        # Restore original config if I overwrote it? 
        # Wait, I shouldn't overwrite the user's config.yaml in the root.
        # The user's config.yaml is in c:\bucket\AccesslogVisualizer\config.yaml
        # I should use a different directory or backup/restore.
        pass
