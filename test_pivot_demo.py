#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Pivot Visualization Demo Script

이 스크립트는 createPivotVisualization 도구의 다양한 사용 케이스를 보여줍니다.
"""

import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
import random

from data_processor import createPivotVisualization
from core.logging_config import get_logger, enable_file_logging

# Enable logging
enable_file_logging()
logger = get_logger(__name__)


def create_sample_log_file(num_records=10000):
    """Create sample log file for testing"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')

    logger.info(f"Creating sample log file with {num_records} records...")

    # Sample data patterns
    urls = [
        '/api/users/list',
        '/api/users/details',
        '/api/products/search',
        '/api/products/details',
        '/api/orders/create',
        '/api/orders/list',
        '/web/index.html',
        '/web/dashboard.html',
        '/web/profile.html',
        '/api/auth/login',
        '/api/auth/logout',
        '/api/cart/add',
        '/api/cart/checkout',
        '/api/payment/process',
        '/api/notifications/list'
    ]

    client_ips = [f"192.168.{i}.{j}" for i in range(1, 6) for j in range(1, 21)]

    start_time = datetime.now() - timedelta(hours=24)

    for i in range(num_records):
        # Generate log entry
        timestamp = start_time + timedelta(seconds=i * (86400 / num_records))
        url = random.choice(urls)
        status = random.choices([200, 201, 400, 404, 500], weights=[70, 10, 10, 5, 5])[0]
        processing_time = random.uniform(0.001, 2.0) if status == 200 else random.uniform(0.5, 5.0)
        client_ip = random.choice(client_ips)
        sent_bytes = random.randint(100, 50000)
        received_bytes = random.randint(50, 5000)

        log_entry = {
            "time": timestamp.isoformat(),
            "request_url": url,
            "elb_status_code": status,
            "target_processing_time": processing_time,
            "client_ip": client_ip,
            "sent_bytes": sent_bytes,
            "received_bytes": received_bytes,
            "request_verb": "GET"
        }

        temp_file.write(json.dumps(log_entry) + '\n')

    temp_file.close()
    logger.info(f"Sample log file created: {temp_file.name}")

    return temp_file.name


def create_format_file():
    """Create log format file for JSON logs"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')

    format_info = {
        'logPattern': 'JSON',
        'patternType': 'JSON',
        'fieldMap': {
            'timestamp': 'time',
            'url': 'request_url',
            'status': 'elb_status_code',
            'responseTime': 'target_processing_time',
            'clientIp': 'client_ip'
        },
        'responseTimeUnit': 's',
        'timezone': 'UTC'
    }

    json.dump(format_info, temp_file, indent=2)
    temp_file.close()

    logger.info(f"Format file created: {temp_file.name}")

    return temp_file.name


def demo_case_1_time_series():
    """케이스 1: sent_bytes 상위 20개 URI의 시간대별 호출건수"""
    logger.info("\n" + "="*80)
    logger.info("케이스 1: sent_bytes 상위 20개 URI의 시간대별 호출건수 (Line Chart)")
    logger.info("="*80)

    log_file = create_sample_log_file(10000)
    format_file = create_format_file()

    try:
        result = createPivotVisualization(
            inputFile=log_file,
            logFormatFile=format_file,
            rowField="url",
            columnField="time",
            valueField="count",
            valueAggFunc="count",
            rowFilter="top:10:sum:sent_bytes",
            topN=10,
            chartType="line",
            outputFormat="html",
            params="timeInterval=1h"
        )

        logger.info(f"✓ Generated: {result['filePath']}")
        logger.info(f"  Chart Type: {result['chartType']}")
        logger.info(f"  Rows: {result['rows']}, Columns: {result['columns']}")
        logger.info(f"  Total Records: {result['totalRecords']}")

        return result['filePath']

    finally:
        import os
        os.unlink(log_file)
        os.unlink(format_file)


def demo_case_2_status_heatmap():
    """케이스 2: Status Code별 분석 (Heatmap)"""
    logger.info("\n" + "="*80)
    logger.info("케이스 2: 호출 상위 10개 URI의 Status Code별 분포 (Heatmap)")
    logger.info("="*80)

    log_file = create_sample_log_file(10000)
    format_file = create_format_file()

    try:
        result = createPivotVisualization(
            inputFile=log_file,
            logFormatFile=format_file,
            rowField="url",
            columnField="elb_status_code",
            valueField="count",
            valueAggFunc="count",
            rowFilter="top:10:count",
            topN=10,
            chartType="heatmap",
            outputFormat="html",
            params="statusGroups=2xx,4xx,5xx"
        )

        logger.info(f"✓ Generated: {result['filePath']}")
        logger.info(f"  Chart Type: {result['chartType']}")
        logger.info(f"  Rows: {result['rows']}, Columns: {result['columns']}")

        return result['filePath']

    finally:
        import os
        os.unlink(log_file)
        os.unlink(format_file)


def demo_case_3_response_time_p95():
    """케이스 3: 응답시간 p95 분석 (Heatmap)"""
    logger.info("\n" + "="*80)
    logger.info("케이스 3: 평균 응답시간 상위 15개 URI의 5분 단위 p95 추이 (Heatmap)")
    logger.info("="*80)

    log_file = create_sample_log_file(10000)
    format_file = create_format_file()

    try:
        result = createPivotVisualization(
            inputFile=log_file,
            logFormatFile=format_file,
            rowField="url",
            columnField="time",
            valueField="target_processing_time",
            valueAggFunc="p95",
            rowFilter="top:15:avg:target_processing_time",
            topN=15,
            chartType="heatmap",
            outputFormat="html",
            params="timeInterval=30m"
        )

        logger.info(f"✓ Generated: {result['filePath']}")
        logger.info(f"  Chart Type: {result['chartType']}")
        logger.info(f"  Rows: {result['rows']}, Columns: {result['columns']}")

        return result['filePath']

    finally:
        import os
        os.unlink(log_file)
        os.unlink(format_file)


def demo_case_4_traffic_analysis():
    """케이스 4: Client IP별 트래픽 분석 (Stacked Area)"""
    logger.info("\n" + "="*80)
    logger.info("케이스 4: 전송량 상위 20개 IP의 10분 단위 트래픽 추이 (Stacked Area)")
    logger.info("="*80)

    log_file = create_sample_log_file(10000)
    format_file = create_format_file()

    try:
        result = createPivotVisualization(
            inputFile=log_file,
            logFormatFile=format_file,
            rowField="client_ip",
            columnField="time",
            valueField="sent_bytes",
            valueAggFunc="sum",
            rowFilter="top:15:sum:sent_bytes",
            topN=15,
            chartType="stacked_area",
            outputFormat="html",
            params="timeInterval=1h"
        )

        logger.info(f"✓ Generated: {result['filePath']}")
        logger.info(f"  Chart Type: {result['chartType']}")
        logger.info(f"  Rows: {result['rows']}, Columns: {result['columns']}")

        return result['filePath']

    finally:
        import os
        os.unlink(log_file)
        os.unlink(format_file)


def demo_case_5_error_rate_facet():
    """케이스 5: 에러율 분석 (Facet Chart)"""
    logger.info("\n" + "="*80)
    logger.info("케이스 5: 호출 상위 12개 URI의 30분 단위 에러율 추이 (Facet)")
    logger.info("="*80)

    log_file = create_sample_log_file(10000)
    format_file = create_format_file()

    try:
        result = createPivotVisualization(
            inputFile=log_file,
            logFormatFile=format_file,
            rowField="url",
            columnField="time",
            valueField="error_rate",
            valueAggFunc="error_rate",
            rowFilter="top:12:count",
            topN=12,
            chartType="facet",
            outputFormat="html",
            params="timeInterval=2h"
        )

        logger.info(f"✓ Generated: {result['filePath']}")
        logger.info(f"  Chart Type: {result['chartType']}")
        logger.info(f"  Rows: {result['rows']}, Columns: {result['columns']}")

        return result['filePath']

    finally:
        import os
        os.unlink(log_file)
        os.unlink(format_file)


def demo_case_6_stacked_bar():
    """케이스 6: URL별 시간대별 호출 패턴 (Stacked Bar)"""
    logger.info("\n" + "="*80)
    logger.info("케이스 6: 상위 8개 URL의 시간대별 호출 패턴 (Stacked Bar)")
    logger.info("="*80)

    log_file = create_sample_log_file(10000)
    format_file = create_format_file()

    try:
        result = createPivotVisualization(
            inputFile=log_file,
            logFormatFile=format_file,
            rowField="url",
            columnField="time",
            valueField="count",
            valueAggFunc="count",
            rowFilter="top:8:count",
            topN=8,
            chartType="stacked_bar",
            outputFormat="html",
            params="timeInterval=2h"
        )

        logger.info(f"✓ Generated: {result['filePath']}")
        logger.info(f"  Chart Type: {result['chartType']}")
        logger.info(f"  Rows: {result['rows']}, Columns: {result['columns']}")

        return result['filePath']

    finally:
        import os
        os.unlink(log_file)
        os.unlink(format_file)


def main():
    """Run all demo cases"""
    logger.info("\n" + "="*80)
    logger.info("Pivot Visualization Demo - All Use Cases")
    logger.info("="*80)

    generated_files = []

    try:
        # Run all demos
        generated_files.append(demo_case_1_time_series())
        generated_files.append(demo_case_2_status_heatmap())
        generated_files.append(demo_case_3_response_time_p95())
        generated_files.append(demo_case_4_traffic_analysis())
        generated_files.append(demo_case_5_error_rate_facet())
        generated_files.append(demo_case_6_stacked_bar())

        # Summary
        logger.info("\n" + "="*80)
        logger.info("All demos completed successfully!")
        logger.info("="*80)
        logger.info("\nGenerated files:")
        for i, file_path in enumerate(generated_files, 1):
            logger.info(f"  {i}. {file_path}")

        logger.info("\n✓ Open these HTML files in your browser to see the interactive visualizations!")

    except Exception as e:
        logger.error(f"Error during demo: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
