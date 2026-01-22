
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from data_parser import recommendAccessLogFormat

def test_config_output():
    log_file = r"c:\bucket\AccesslogVisualizer\access_2026-01-16_00_00_00.log.gz"
    
    # Remove existing logformat files to force fresh detection
    for f in Path(log_file).parent.glob("logformat_*.json"):
        try:
            os.remove(f)
        except:
            pass

    print(f"Testing with file: {log_file}")
    
    try:
        result = recommendAccessLogFormat(log_file)
        print("\nResult:")
        print(json.dumps(result, indent=2))
        
        if 'configSource' in result and 'configType' in result:
            print("\nSUCCESS: Found configSource and configType")
            print(f"configSource: {result['configSource']}")
            print(f"configType: {result['configType']}")
        else:
            print("\nFAILURE: Missing configSource or configType")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_config_output()
