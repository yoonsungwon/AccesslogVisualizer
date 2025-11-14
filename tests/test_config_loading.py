#!/usr/bin/env python3
"""
Test script to verify that multiprocessing configuration is loaded correctly
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils import MultiprocessingConfig
from core.config import ConfigManager
from core.logging_config import get_logger, set_log_level

# Set log level to INFO to see all messages
set_log_level('INFO')

logger = get_logger(__name__)

def main():
    print("=" * 60)
    print("Testing Multiprocessing Configuration Loading")
    print("=" * 60)

    # Test 1: Check if config.yaml exists
    print("\n[Test 1] Checking for config.yaml...")
    config_mgr = ConfigManager()
    config_path = config_mgr.find_config()

    if config_path:
        print(f"✓ Found config.yaml at: {config_path}")
    else:
        print("✗ config.yaml not found in standard locations")
        return 1

    # Test 2: Load full configuration
    print("\n[Test 2] Loading full configuration...")
    config = config_mgr.load_config()
    print(f"Full config: {config}")

    # Test 3: Check multiprocessing section
    print("\n[Test 3] Checking multiprocessing section...")
    if 'multiprocessing' in config:
        mp_section = config['multiprocessing']
        print(f"Multiprocessing section found:")
        print(f"  enabled: {mp_section.get('enabled')}")
        print(f"  num_workers: {mp_section.get('num_workers')}")
        print(f"  chunk_size: {mp_section.get('chunk_size')}")
        print(f"  min_lines_for_parallel: {mp_section.get('min_lines_for_parallel')}")
    else:
        print("✗ No multiprocessing section in config.yaml")
        return 1

    # Test 4: Load multiprocessing config via MultiprocessingConfig
    print("\n[Test 4] Loading via MultiprocessingConfig.get_config()...")
    mp_config = MultiprocessingConfig.get_config()
    print(f"Loaded config:")
    print(f"  enabled: {mp_config['enabled']}")
    print(f"  num_workers: {mp_config['num_workers']}")
    print(f"  chunk_size: {mp_config['chunk_size']}")
    print(f"  min_lines_for_parallel: {mp_config['min_lines_for_parallel']}")

    # Test 5: Verify num_workers value
    print("\n[Test 5] Verifying num_workers value...")
    expected_num_workers = 8
    actual_num_workers = mp_config['num_workers']

    if actual_num_workers == expected_num_workers:
        print(f"✓ num_workers correctly loaded: {actual_num_workers}")
    else:
        print(f"✗ num_workers mismatch! Expected: {expected_num_workers}, Got: {actual_num_workers}")
        return 1

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return 0

if __name__ == '__main__':
    sys.exit(main())
