#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Data Visualizer Module for Access Log Analyzer
Implements MCP tools: generateXlog, generateRequestPerURI
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import re
from datetime import datetime
from pathlib import Path
import numpy as np
from typing import Dict, List, Optional, Any

# Import core modules
from core.exceptions import (
    FileNotFoundError as CustomFileNotFoundError,
    ValidationError
)
from core.logging_config import get_logger
from core.utils import FieldMapper

# Setup logger
logger = get_logger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _normalize_interval(interval: str) -> str:
    """
    Normalize time interval string to pandas-compatible format.

    Converts common abbreviations to pandas-compatible frequency strings:
    - '1m', '5m', '10m' -> '1min', '5min', '10min' (minutes)
    - '1h', '2h' -> '1h', '2h' (hours)
    - '1s', '10s' -> '1s', '10s' (seconds)
    - '1d' -> '1d' (days)

    Args:
        interval (str): Time interval string (e.g., '1m', '10s', '1h')

    Returns:
        str: Normalized pandas-compatible interval string

    Raises:
        ValidationError: If interval format is invalid
    """
    if not interval or not isinstance(interval, str):
        raise ValidationError('interval', f"Invalid interval: {interval}")

    # Common interval patterns: number + unit
    import re
    match = re.match(r'^(\d+)([a-zA-Z]+)$', interval.strip())
    if not match:
        raise ValidationError('interval',
            f"Invalid interval format: '{interval}'. Expected format: number + unit (e.g., '1min', '10s', '1h')")

    number, unit = match.groups()

    # Normalize unit abbreviations
    # 'm' is ambiguous (month vs minute), default to minute for access logs
    unit_map = {
        'm': 'min',      # Default 'm' to minutes for access logs
        'min': 'min',
        'mins': 'min',
        'minute': 'min',
        'minutes': 'min',
        's': 's',
        'sec': 's',
        'secs': 's',
        'second': 's',
        'seconds': 's',
        'h': 'h',
        'hr': 'h',
        'hrs': 'h',
        'hour': 'h',
        'hours': 'h',
        'd': 'd',
        'day': 'd',
        'days': 'd',
    }

    normalized_unit = unit_map.get(unit.lower())
    if not normalized_unit:
        raise ValidationError('interval',
            f"Unknown time unit: '{unit}'. Supported units: s, min, h, d")

    normalized_interval = f"{number}{normalized_unit}"

    # Log if conversion occurred
    if normalized_interval != interval:
        logger.info(f"Normalized interval '{interval}' to '{normalized_interval}'")

    return normalized_interval


def _generate_interactive_enhancements(
    patterns: List[str],
    colors: List[str],
    div_id: str,
    filter_label: str = "Filter Patterns:",
    hover_format: str = "default"
) -> tuple:
    """
    Generate checkbox filter panel, hover text display, and JavaScript for interactive visualizations.

    Args:
        patterns: List of pattern names to display in checkboxes
        colors: List of colors matching each pattern (Plotly color format)
        div_id: The Plotly div ID for targeting in JavaScript
        filter_label: Label text for the filter panel (default: "Filter Patterns:")
        hover_format: Format for hover text display ("default", "count", "time", or custom)

    Returns:
        tuple: (checkbox_html, hover_text_html, javascript_code)
    """
    # Plotly default color palette
    plotly_default_colors = [
        '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
        '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'
    ]

    # Create checkbox HTML for each pattern
    checkbox_html = '<div id="filterCheckboxPanel" style="position: fixed; right: 20px; top: 80px; width: 220px; max-height: 500px; overflow-y: auto; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); color: #444; font-family: \'Open Sans\', verdana, arial, sans-serif;">'
    checkbox_html += f'<div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">{filter_label}</div>'
    checkbox_html += '<div style="margin-bottom: 8px; position: relative;"><input type="text" id="patternFilterInput" placeholder="Regex filter..." style="width: 100%; padding: 4px 24px 4px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 11px; box-sizing: border-box;"><span id="clearFilterBtn" style="position: absolute; right: 6px; top: 50%; transform: translateY(-50%); cursor: pointer; font-size: 14px; color: #999; display: none;" title="Clear filter">×</span></div>'
    checkbox_html += '<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkAll" checked> <strong>All</strong></label></div>'
    checkbox_html += '<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkNone"> <strong>None</strong></label></div>'
    checkbox_html += '<hr style="margin: 8px 0;">'

    # Create checkbox items using the same patterns list
    for i, pattern in enumerate(patterns):
        pattern_id = f'pattern_{i}'
        pattern_display = pattern[:60] + ('...' if len(pattern) > 60 else '')
        # Use colors if provided, otherwise fall back to plotly default colors
        trace_color = colors[i] if i < len(colors) else plotly_default_colors[i % len(plotly_default_colors)]
        checkbox_html += f'<div class="pattern-item" style="margin-bottom: 3px; font-size: 11px;" data-pattern="{pattern}"><label class="pattern-label" data-index="{i}"><input type="checkbox" class="pattern-checkbox" id="{pattern_id}" data-index="{i}" checked> <span class="pattern-text" style="color: {trace_color}; font-weight: bold;">{pattern_display}</span></label></div>'

    checkbox_html += '</div>'

    # Add hover text display area and clipboard copy feature
    hover_text_html = '''
    <div id="hoverTextDisplay" style="position: fixed; bottom: 20px; right: 20px; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; max-width: 300px; max-height: 150px; overflow-y: auto; display: none; z-index: 2000; box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-size: 12px; color: #444; font-family: 'Open Sans', verdana, arial, sans-serif;">
        <div style="font-weight: bold; margin-bottom: 5px;">Hover Info:</div>
        <div id="hoverTextContent" style="white-space: pre-wrap; word-break: break-word;"></div>
        <div style="margin-top: 5px; font-size: 10px; color: #666;">Click or press Ctrl+C to copy</div>
    </div>
    '''

    # JavaScript for checkbox functionality and hover text copy
    js_code = f'''
    <script>
    (function() {{
        // Hover text storage and clipboard functionality
        let lastHoverText = '';
        let hoverTextDisplay = null;
        let hoverTextContent = null;

        // Function to get hover text elements (lazy initialization)
        function getHoverTextElements() {{
            if (!hoverTextDisplay) {{
                hoverTextDisplay = document.getElementById('hoverTextDisplay');
            }}
            if (!hoverTextContent) {{
                hoverTextContent = document.getElementById('hoverTextContent');
            }}
            return {{ display: hoverTextDisplay, content: hoverTextContent }};
        }}

        // Function to copy text to clipboard
        function copyToClipboard(text) {{
            const elements = getHoverTextElements();
            const hoverTextContent = elements.content;

            if (!hoverTextContent) return;

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => {{
                    console.log('Copied to clipboard:', text);
                    // Show feedback
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{
                        hoverTextContent.innerHTML = originalContent;
                    }}, 1000);
                }}).catch(err => {{
                    console.error('Failed to copy:', err);
                    fallbackCopyToClipboard(text);
                }});
            }} else {{
                fallbackCopyToClipboard(text);
            }}
        }}

        // Fallback copy method
        function fallbackCopyToClipboard(text) {{
            const elements = getHoverTextElements();
            const hoverTextContent = elements.content;

            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {{
                document.execCommand('copy');
                console.log('Copied to clipboard (fallback):', text);
                if (hoverTextContent) {{
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{
                        hoverTextContent.innerHTML = originalContent;
                    }}, 1000);
                }}
            }} catch (err) {{
                console.error('Fallback copy failed:', err);
            }}
            document.body.removeChild(textArea);
        }}

        // Handle Ctrl+C keyboard shortcut
        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'c' && lastHoverText) {{
                const elements = getHoverTextElements();
                if (elements.display && elements.display.style.display !== 'none') {{
                    e.preventDefault();
                    copyToClipboard(lastHoverText);
                }}
            }}
        }});

        // Wait for DOM to be ready, then setup click handler
        function setupHoverTextClick() {{
            const elements = getHoverTextElements();
            if (elements.display) {{
                console.log('✓ hoverTextDisplay found, setting up click handler');
                elements.display.addEventListener('click', function() {{
                    if (lastHoverText) {{
                        copyToClipboard(lastHoverText);
                    }}
                }});
            }} else {{
                // Retry if not ready yet
                console.log('hoverTextDisplay not found, retrying...');
                setTimeout(setupHoverTextClick, 100);
            }}
        }}

        // Initialize hover text click handler when DOM is ready
        function initHoverText() {{
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    setTimeout(setupHoverTextClick, 100);
                }});
            }} else {{
                setTimeout(setupHoverTextClick, 100);
            }}
        }}

        // Start hover text initialization
        initHoverText();

        // Wait for Plotly to be ready
        function initCheckboxes() {{
            const checkAll = document.getElementById('checkAll');
            const checkNone = document.getElementById('checkNone');
            const checkboxes = document.querySelectorAll('.pattern-checkbox');

            if (!checkAll || !checkNone || checkboxes.length === 0) {{
                console.warn('Checkbox elements not found. Retrying...');
                setTimeout(initCheckboxes, 200);
                return;
            }}

            console.log('✓ Checkbox elements found:', checkboxes.length, 'checkboxes');

            if (!window.Plotly) {{
                console.warn('Plotly not loaded yet');
                setTimeout(initCheckboxes, 100);
                return;
            }}

            // Find Plotly div
            let plotlyDiv = null;
            const targetDivId = "{div_id}";

            // Method 1: Find by the specific ID
            if (targetDivId && targetDivId !== '') {{
                plotlyDiv = document.getElementById(targetDivId);
            }}

            // Method 2: Use window.gd if available
            if (!plotlyDiv && window.gd) {{
                plotlyDiv = window.gd;
            }}

            // Method 3: Find div with class 'js-plotly-plot'
            if (!plotlyDiv) {{
                const plotDivs = document.querySelectorAll('.js-plotly-plot');
                if (plotDivs.length > 0) {{
                    plotlyDiv = plotDivs[0];
                }}
            }}

            if (!plotlyDiv) {{
                console.error('Plotly div not found. Target ID:', targetDivId);
                setTimeout(initCheckboxes, 200);
                return;
            }}

            console.log('Found Plotly div:', plotlyDiv.id || plotlyDiv.className);

            // Setup hover event handler to capture and display hover text
            plotlyDiv.on('plotly_hover', function(data) {{
                if (data && data.points && data.points.length > 0) {{
                    // Collect all points
                    const pointInfo = data.points.map(pt => {{
                        const yValue = pt.y !== undefined ? pt.y : pt.y0 || 0;
                        const traceName = pt.data?.name || pt.fullData?.name || 'Unknown';
                        return {{
                            value: yValue,
                            name: traceName,
                            point: pt
                        }};
                    }});

                    // Sort by value in descending order
                    pointInfo.sort((a, b) => b.value - a.value);

                    // Format hover text
                    let displayText = '';
                    pointInfo.forEach((info, index) => {{
                        if (index > 0) displayText += '\\n';
                        displayText += `Value: ${{info.value}}, Series: ${{info.name}}`;
                    }});

                    // Store for clipboard copy
                    lastHoverText = displayText;

                    // Display in hover text area
                    const elements = getHoverTextElements();
                    if (elements.content && elements.display) {{
                        elements.content.textContent = displayText;
                        elements.display.style.display = 'block';
                    }}
                }}
            }});

            // Keep hover text visible for copying
            plotlyDiv.on('plotly_unhover', function(data) {{
                // Don't hide - keep visible for copying
            }});

            // Store original trace data
            let originalTraceData = null;

            const saveOriginalData = function() {{
                if (!originalTraceData && plotlyDiv.data) {{
                    originalTraceData = JSON.parse(JSON.stringify(plotlyDiv.data));
                    console.log('Saved original trace data:', originalTraceData.length, 'traces');
                }}
            }};

            setTimeout(saveOriginalData, 100);

            const updateVisibility = function() {{
                const visible = [];
                checkboxes.forEach((cb) => {{
                    visible.push(cb.checked);
                }});

                console.log('Updating visibility:', visible);

                if (!originalTraceData && plotlyDiv.data) {{
                    originalTraceData = JSON.parse(JSON.stringify(plotlyDiv.data));
                }}

                const currentTraceCount = plotlyDiv.data?.length || plotlyDiv._fullData?.length || 0;
                const originalTraceCount = originalTraceData ? originalTraceData.length : visible.length;
                const checkedCount = visible.filter(v => v).length;

                try {{
                    if (checkedCount === visible.length) {{
                        // All selected - restore all traces
                        if (currentTraceCount !== originalTraceCount && originalTraceData) {{
                            console.log('Restoring all original traces');
                            if (currentTraceCount > 0) {{
                                for (let i = currentTraceCount - 1; i >= 0; i--) {{
                                    try {{ Plotly.deleteTraces(plotlyDiv, i); }} catch (e) {{}}
                                }}
                            }}
                            if (originalTraceData.length > 0) {{
                                Plotly.addTraces(plotlyDiv, originalTraceData);
                            }}
                        }} else {{
                            const visibleArray = Array(currentTraceCount).fill(true);
                            const traceIndices = Array.from({{length: currentTraceCount}}, (_, i) => i);
                            Plotly.restyle(plotlyDiv, {{visible: visibleArray}}, traceIndices);
                        }}
                    }} else if (checkedCount === 0) {{
                        // None selected - hide all
                        const visibleArray = Array(currentTraceCount).fill(false);
                        const traceIndices = Array.from({{length: currentTraceCount}}, (_, i) => i);
                        Plotly.restyle(plotlyDiv, {{visible: visibleArray}}, traceIndices);
                    }} else {{
                        // Some selected - show only selected
                        if (originalTraceData) {{
                            const selectedTraces = [];
                            for (let i = 0; i < originalTraceData.length && i < visible.length; i++) {{
                                if (visible[i]) selectedTraces.push(originalTraceData[i]);
                            }}
                            console.log('Selected traces to show:', selectedTraces.length);
                            if (currentTraceCount > 0) {{
                                for (let i = currentTraceCount - 1; i >= 0; i--) {{
                                    try {{ Plotly.deleteTraces(plotlyDiv, i); }} catch (e) {{}}
                                }}
                            }}
                            if (selectedTraces.length > 0) {{
                                Plotly.addTraces(plotlyDiv, selectedTraces);
                            }}
                        }}
                    }}
                }} catch (e) {{
                    console.error('Error updating plotly:', e);
                }}
            }};

            // Helper function to check if checkbox is visible
            const isCheckboxVisible = function(checkbox) {{
                const patternItem = checkbox.closest('.pattern-item');
                return patternItem && patternItem.style.display !== 'none';
            }};

            // Check all - only visible items
            checkAll.addEventListener('change', function() {{
                if (this.checked) {{
                    checkNone.checked = false;
                    checkboxes.forEach(cb => {{
                        if (isCheckboxVisible(cb)) {{
                            cb.checked = true;
                        }} else {{
                            cb.checked = false;
                        }}
                    }});
                    updateVisibility();
                }}
            }});

            // Check none
            checkNone.addEventListener('change', function() {{
                if (this.checked) {{
                    checkAll.checked = false;
                    checkboxes.forEach(cb => cb.checked = false);
                    updateVisibility();
                }}
            }});

            // Individual checkboxes
            checkboxes.forEach(cb => {{
                cb.addEventListener('change', function() {{
                    if (this.checked) {{
                        checkNone.checked = false;
                    }}

                    const visibleCheckboxes = Array.from(checkboxes).filter(c => isCheckboxVisible(c));
                    const allVisibleChecked = visibleCheckboxes.length > 0 && visibleCheckboxes.every(c => c.checked);
                    if (allVisibleChecked) {{
                        checkAll.checked = true;
                        checkNone.checked = false;
                    }} else {{
                        checkAll.checked = false;
                    }}

                    updateVisibility();
                }});
            }});

            // Pattern filter input functionality
            const patternFilterInput = document.getElementById('patternFilterInput');
            const clearFilterBtn = document.getElementById('clearFilterBtn');

            if (patternFilterInput) {{
                const filterPatterns = function() {{
                    const filterText = patternFilterInput.value.trim();
                    const patternItems = document.querySelectorAll('.pattern-item');

                    if (clearFilterBtn) {{
                        clearFilterBtn.style.display = filterText ? 'block' : 'none';
                    }}

                    if (!filterText) {{
                        patternItems.forEach(item => {{
                            item.style.display = '';
                        }});
                        return;
                    }}

                    try {{
                        const regex = new RegExp(filterText, 'i');
                        let visibleCount = 0;
                        patternItems.forEach(item => {{
                            const pattern = item.getAttribute('data-pattern') || '';
                            if (regex.test(pattern)) {{
                                item.style.display = '';
                                visibleCount++;
                            }} else {{
                                item.style.display = 'none';
                            }}
                        }});
                        console.log(`Filtered patterns: ${{visibleCount}} visible out of ${{patternItems.length}} total`);
                    }} catch (e) {{
                        console.warn('Invalid regex pattern:', filterText, e);
                        patternItems.forEach(item => {{
                            item.style.display = '';
                        }});
                    }}
                }};

                patternFilterInput.addEventListener('input', filterPatterns);
                patternFilterInput.addEventListener('keyup', filterPatterns);

                if (clearFilterBtn) {{
                    clearFilterBtn.addEventListener('click', function() {{
                        patternFilterInput.value = '';
                        filterPatterns();
                        patternFilterInput.focus();
                    }});

                    clearFilterBtn.addEventListener('mouseenter', function() {{
                        this.style.color = '#333';
                    }});
                    clearFilterBtn.addEventListener('mouseleave', function() {{
                        this.style.color = '#999';
                    }});
                }}
            }}
        }}

        // Initialize when DOM and Plotly are ready
        function waitForPlotly() {{
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    setTimeout(waitForPlotly, 100);
                }});
                return;
            }}

            const checkAll = document.getElementById('checkAll');
            const hoverTextDisplay = document.getElementById('hoverTextDisplay');

            if (!checkAll || !hoverTextDisplay) {{
                console.log('Waiting for HTML elements to be inserted...');
                setTimeout(waitForPlotly, 100);
                return;
            }}

            console.log('✓ HTML elements found, waiting for Plotly...');

            if (window.Plotly) {{
                console.log('✓ Plotly loaded, initializing checkboxes...');
                setTimeout(initCheckboxes, 300);
            }} else {{
                let retryCount = 0;
                const maxRetries = 50;
                const checkPlotly = setInterval(function() {{
                    retryCount++;
                    if (window.Plotly) {{
                        clearInterval(checkPlotly);
                        console.log('✓ Plotly loaded after', retryCount * 100, 'ms');
                        setTimeout(initCheckboxes, 300);
                    }} else if (retryCount >= maxRetries) {{
                        clearInterval(checkPlotly);
                        console.error('Plotly not loaded after', maxRetries * 100, 'ms');
                        setTimeout(initCheckboxes, 300);
                    }}
                }}, 100);
            }}
        }}

        // Start initialization
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', waitForPlotly);
        }} else {{
            waitForPlotly();
        }}
    }})();
    </script>
    '''

    return checkbox_html, hover_text_html, js_code


# ============================================================================
# MCP Tool: generateXlog
# ============================================================================

def generateXlog(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html'
) -> Dict[str, Any]:
    """
    Generate XLog (response time scatter plot) visualization.
    
    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        outputFormat (str): Output format ('html' only supported)
        
    Returns:
        dict: {
            'filePath': str (absolute path to xlog_*.html),
            'totalTransactions': int
        }
    """
    # Validate inputs
    if not inputFile or not os.path.exists(inputFile):
        raise CustomFileNotFoundError(inputFile)
    if not logFormatFile or not os.path.exists(logFormatFile):
        raise CustomFileNotFoundError(logFormatFile)
    if outputFormat != 'html':
        raise ValidationError('outputFormat', "Only 'html' output format is currently supported")
    
    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)
    
    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)
    
    if log_df.empty:
        raise ValueError("No data to visualize")
    
    # Get field mappings
    time_field = format_info['fieldMap'].get('timestamp', 'time')
    url_field = format_info['fieldMap'].get('url', 'request_url')
    status_field = format_info['fieldMap'].get('status', 'elb_status_code')
    rt_field = format_info['fieldMap'].get('responseTime', 'target_processing_time')
    
    # Debug: Check available columns in DataFrame (for ALB parsing)
    if format_info.get('patternType') == 'ALB':
        # For ALB, check if columns are available from config.yaml
        available_columns = list(log_df.columns)
        print(f"  Available columns in DataFrame: {len(available_columns)} columns")
        
        # If url_field is not found, try to find it in available columns
        if url_field not in available_columns:
            possible_url_fields = ['request_url', 'url', 'request_uri', 'uri']
            for field in possible_url_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as URL field (instead of '{url_field}')")
                    url_field = field
                    break
        
        # If time_field is not found, try to find it
        if time_field not in available_columns:
            possible_time_fields = ['time', 'timestamp', '@timestamp', 'datetime']
            for field in possible_time_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as time field (instead of '{time_field}')")
                    time_field = field
                    break
        
        # If status_field is not found, try to find it
        if status_field not in available_columns:
            possible_status_fields = ['elb_status_code', 'status_code', 'status', 'http_status']
            for field in possible_status_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as status field (instead of '{status_field}')")
                    status_field = field
                    break
        
        # If rt_field is not found, try to find it
        if rt_field not in available_columns:
            possible_rt_fields = ['target_processing_time', 'response_time', 'duration', 'elapsed']
            for field in possible_rt_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as response time field (instead of '{rt_field}')")
                    rt_field = field
                    break
    
    # Check if required fields exist
    if time_field not in log_df.columns:
        raise ValueError(f"Time field '{time_field}' not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    if rt_field not in log_df.columns:
        raise ValueError(f"Response time field '{rt_field}' not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    
    # Convert types
    log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    log_df[rt_field] = pd.to_numeric(log_df[rt_field], errors='coerce')
    if status_field in log_df.columns:
        log_df[status_field] = pd.to_numeric(log_df[status_field], errors='coerce')
    
    # Drop invalid rows (only if rt_field exists)
    if rt_field and rt_field in log_df.columns:
        log_df = log_df.dropna(subset=[time_field, rt_field])
    else:
        log_df = log_df.dropna(subset=[time_field])
    
    # Convert response time to milliseconds if needed
    if rt_field and rt_field in log_df.columns:
        rt_unit = format_info.get('responseTimeUnit', 'ms')
    if rt_unit == 's':
        log_df[rt_field] = log_df[rt_field] * 1000
    elif rt_unit == 'us':
        log_df[rt_field] = log_df[rt_field] / 1000
    elif rt_unit == 'ns':
        log_df[rt_field] = log_df[rt_field] / 1000000
    else:
        # If response time field is not available, create a dummy field
        print(f"  Warning: Response time field not available, using default value")
        rt_field = None
    
    # Sampling for performance (if data is too large)
    max_points = 50000  # Maximum points to display
    if len(log_df) > max_points:
        print(f"  Note: Sampling {max_points} points from {len(log_df)} total transactions for performance")
        log_df = log_df.sample(n=max_points, random_state=42)
    
    # Create color mapping based on status code
    def get_color(status):
        if pd.isna(status):
            return 'gray'
        try:
            status = int(status)
            if status < 300:
                return 'green'
            elif status < 400:
                return 'blue'
            elif status < 500:
                return 'orange'
            else:
                return 'red'
        except:
            return 'gray'
    
    if status_field and status_field in log_df.columns:
        log_df['color'] = log_df[status_field].apply(get_color)
    else:
        # If status field is not available, use default color
        log_df['color'] = 'gray'
    
    # Create interactive scatter plot using WebGL for better performance
    fig = go.Figure()
    
    # Add scatter plot with WebGL rendering (Scattergl)
    for color_name, color_val in [('green', 'Success (2xx)'), ('blue', 'Redirect (3xx)'), 
                                   ('orange', 'Client Error (4xx)'), ('red', 'Server Error (5xx)'),
                                   ('gray', 'Unknown')]:
        mask = log_df['color'] == color_name
        if mask.any():
            subset = log_df[mask]
            # Pre-format hover text efficiently
            hover_text = []
            for _, row in subset.iterrows():
                text = f"Time: {row[time_field]}<br>"
                if url_field and url_field in row and pd.notna(row[url_field]):
                    text += f"URL: {row[url_field]}<br>"
                if rt_field and rt_field in row and pd.notna(row[rt_field]):
                    text += f"Response Time: {row[rt_field]:.2f} ms<br>"
                if status_field and status_field in row and pd.notna(row[status_field]):
                    try:
                        text += f"Status: {int(row[status_field])}"
                    except:
                        text += f"Status: {row[status_field]}"
                hover_text.append(text)
            
            # Use Scattergl for WebGL rendering (much faster for large datasets)
            # Only plot if rt_field is available
            if rt_field and rt_field in subset.columns:
                fig.add_trace(go.Scattergl(
                x=subset[time_field],
                y=subset[rt_field],
                mode='markers',
                name=color_val,
                marker=dict(
                    color=color_name,
                    size=4,  # Slightly smaller for better performance
                    opacity=0.6,
                    line=dict(width=0)  # No border for better performance
                    ),
                    hovertext=hover_text,
                    hoverinfo='text'
                ))
            else:
                # If no response time, plot by count
                fig.add_trace(go.Scattergl(
                    x=subset[time_field],
                    y=[1] * len(subset),  # Dummy y-axis
                    mode='markers',
                    name=color_val,
                    marker=dict(
                        color=color_name,
                        size=4,
                        opacity=0.6,
                        line=dict(width=0)
                ),
                hovertext=hover_text,
                hoverinfo='text'
            ))
    
    # Collect trace names and colors for checkbox filter
    trace_names = []
    trace_colors = []
    for trace in fig.data:
        trace_names.append(trace.name)
        trace_colors.append(trace.marker.color)

    # Update layout with checkbox filter enhancements
    fig.update_layout(
        title='XLog - Response Time Scatter Plot',
        xaxis_title='Time',
        yaxis_title='Response Time (ms)',
        hovermode='closest',
        height=600,
        showlegend=False,  # Use checkbox filter instead
        margin=dict(r=250),  # Add right margin for checkbox panel
        dragmode='zoom'  # Enable box select zoom (both horizontal and vertical)
    )

    # Add zoom and pan features
    fig.update_xaxes(rangeslider_visible=True)

    # Enable vertical zoom
    fig.update_yaxes(
        autorange=True,
        fixedrange=False  # Allow manual zoom on y-axis
    )

    # Generate output file
    input_path = Path(inputFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"xlog_{timestamp}.html"

    # Save as HTML with plotly div ID
    plotly_div_id = f'plotly-div-{timestamp}'
    fig.write_html(str(output_file), include_plotlyjs='cdn', div_id=plotly_div_id)

    # Generate interactive enhancements (checkbox filter, hover text, vertical zoom)
    checkbox_html, hover_text_html, js_code = _generate_interactive_enhancements(
        patterns=trace_names,
        colors=trace_colors,
        div_id=plotly_div_id,
        filter_label="Filter Status Codes:",
        hover_format="xlog"
    )

    # Read the generated HTML and insert enhancements
    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract the actual div ID from HTML (Plotly may modify it)
    div_id_match = re.search(r'<div id="([^"]+)"[^>]*class="[^"]*plotly[^"]*"', html_content)
    actual_div_id = div_id_match.group(1) if div_id_match else plotly_div_id

    # Update js_code with actual div ID
    js_code = js_code.replace(f'"{plotly_div_id}"', f'"{actual_div_id}"')

    # Insert checkbox HTML, hover text display, and JavaScript before closing body tag
    inserted = False
    if '</body>' in html_content:
        html_content = html_content.rsplit('</body>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_html + hover_text_html + js_code + '</body>' + html_content[1]
            inserted = True

    # Fallback: Insert before </html>
    if not inserted and '</html>' in html_content:
        html_content = html_content.rsplit('</html>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_html + hover_text_html + js_code + '</html>' + html_content[1]
            inserted = True

    # Fallback: Append at the end
    if not inserted:
        html_content += checkbox_html + hover_text_html + js_code

    # Write modified HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"  ✓ filterCheckboxPanel inserted for XLog")
    logger.info(f"  ✓ hoverTextDisplay inserted for XLog")

    return {
        'filePath': str(output_file.resolve()),
        'totalTransactions': len(log_df)
    }


# ============================================================================
# MCP Tool: generateRequestPerURI
# ============================================================================

def generateRequestPerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 20,
    interval: str = '10s',
    patternsFile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate Request Count per URI time-series visualization.
    
    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        outputFormat (str): Output format ('html' only supported)
        topN (int): Number of top URI patterns to display (default: 20)
        interval (str): Time interval for aggregation (default: '10s'). 
                       Examples: '1s', '10s', '1min', '5min', '1h'
        patternsFile (str, optional): Path to JSON file containing URL patterns.
                                    If provided, uses these patterns for visualization.
                                    If not provided, extracts top N patterns and saves to file.
        
    Returns:
        dict: {
            'filePath': str (requestcnt_*.html),
            'totalTransactions': int,
            'patternsFile': str (path to saved patterns file)
        }
    """
    if outputFormat != 'html':
        raise ValueError("Only 'html' output format is currently supported")

    # Normalize interval parameter to pandas-compatible format
    interval = _normalize_interval(interval)

    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)
    
    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)
    
    if log_df.empty:
        raise ValueError("No data to visualize")
    
    # Get field mappings
    time_field = format_info['fieldMap'].get('timestamp', 'time')
    url_field = format_info['fieldMap'].get('url', 'request_url')
    
    # Debug: Check available columns in DataFrame (for ALB parsing)
    if format_info.get('patternType') == 'ALB':
        # For ALB, check if columns are available from config.yaml
        available_columns = list(log_df.columns)
        print(f"  Available columns in DataFrame: {len(available_columns)} columns")
        
        # If url_field is not found, try to find it in available columns
        if url_field not in available_columns:
            # Try common ALB URL field names
            possible_url_fields = ['request_url', 'url', 'request_uri', 'uri']
            for field in possible_url_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as URL field (instead of '{url_field}')")
                    url_field = field
                    break
        
        # If time_field is not found, try to find it
        if time_field not in available_columns:
            possible_time_fields = ['time', 'timestamp', '@timestamp', 'datetime']
            for field in possible_time_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as time field (instead of '{time_field}')")
                    time_field = field
                    break
    
    # Check if required fields exist
    if url_field not in log_df.columns:
        raise ValueError(f"URL field '{url_field}' not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    if time_field not in log_df.columns:
        raise ValueError(f"Time field '{time_field}' not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    
    # Convert types
    log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    log_df = log_df.dropna(subset=[time_field])
    
    # Determine input path for output file location
    input_path = Path(inputFile)
    
    # Load patterns from file if provided first (to use pattern rules for generalization)
    patterns_file_for_generalize = None
    top_patterns = None
    
    if patternsFile and os.path.exists(patternsFile):
        # Load patterns from file
        try:
            with open(patternsFile, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)
            
            # Extract pattern rules from file
            if isinstance(patterns_data, dict):
                if 'patternRules' in patterns_data and isinstance(patterns_data['patternRules'], list):
                    patterns_file_for_generalize = patternsFile
                    # Extract replacement values from patternRules as top_patterns
                    top_patterns = [rule.get('replacement', '') for rule in patterns_data['patternRules'] if isinstance(rule, dict) and 'replacement' in rule]
                    top_patterns = [p for p in top_patterns if p]  # Remove empty strings
                    print(f"  Using pattern rules from {patternsFile} for URL generalization")
                    print(f"  Loaded {len(top_patterns)} patterns from patternRules")
                else:
                    # Fallback for old format (backward compatibility)
                    if 'patterns' in patterns_data:
                        top_patterns = patterns_data['patterns']
                        patterns_file_for_generalize = patternsFile
                        print(f"  Using patterns from {patternsFile} (will be converted to rules)")
                    elif 'urls' in patterns_data:
                        top_patterns = patterns_data['urls']
                        patterns_file_for_generalize = patternsFile
                        print(f"  Using URLs from {patternsFile} (will be converted to rules)")
                    else:
                        raise ValueError(f"No patternRules, patterns, or urls found in {patternsFile}")
            else:
                raise ValueError(f"Unexpected patterns file format: {type(patterns_data)}")
            
            # Ensure patterns are strings and unique
            top_patterns = list(set([str(p) for p in top_patterns if p]))
            
        except Exception as e:
            print(f"  Warning: Could not load patterns file {patternsFile}: {e}")
            print(f"  Falling back to extracting top {topN} patterns")
            patternsFile = None
            top_patterns = None
    
    # Generalize URLs (remove IDs) using pattern file if available
    from data_processor import _generalize_url
    log_df['url_pattern'] = log_df[url_field].apply(
        lambda x: _generalize_url(x, patterns_file_for_generalize) if pd.notna(x) else 'Unknown'
    )
    
    # Group by time interval and URL pattern
    log_df['time_bucket'] = log_df[time_field].dt.floor(interval)
    
    # If patterns were loaded from file, keep all data but mark non-matching patterns as "Others"
    if top_patterns:
        # If top_patterns contains URLs (not patterns), generalize them first
        # to match with generalized url_pattern
        if patterns_file_for_generalize:
            # URLs will be generalized using pattern rules, so we need to generalize
            # the patterns from file to match
            generalized_top_patterns = [
                _generalize_url(pattern, patterns_file_for_generalize) 
                for pattern in top_patterns
            ]
            # Update top_patterns to use generalized versions for consistency
            top_patterns = list(set(generalized_top_patterns))
        
        # Mark patterns not in top_patterns as "Others"
        log_df.loc[~log_df['url_pattern'].isin(top_patterns) & (log_df['url_pattern'] != 'Unknown'), 'url_pattern'] = 'Others'
    
    # Extract top N patterns if not loaded from file
    if not patternsFile or not os.path.exists(patternsFile):
        # Get top N URL patterns by count
        pattern_counts = log_df['url_pattern'].value_counts()
        top_patterns = pattern_counts.head(topN).index.tolist()
        
        # Mark patterns not in top_patterns as "Others"
        log_df.loc[~log_df['url_pattern'].isin(top_patterns) & (log_df['url_pattern'] != 'Unknown'), 'url_pattern'] = 'Others'
        
        # Generate pattern rules from patterns
        pattern_rules = []
        for pattern in top_patterns:
            # Convert pattern with * wildcards to regex
            # First, replace * with a placeholder
            temp_pattern = pattern.replace('*', '__WILDCARD__')
            # Escape special regex characters
            escaped_pattern = re.escape(temp_pattern)
            # Replace placeholder with .* (regex wildcard)
            regex_pattern = escaped_pattern.replace('__WILDCARD__', '.*')
            
            pattern_rules.append({
                'pattern': f'^{regex_pattern}$',
                'replacement': pattern
            })
        
        # Save patterns to file with pattern rules only
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        patterns_file_path = input_path.parent / f"patterns_{timestamp}.json"
        
        patterns_data = {
            'patternRules': pattern_rules,
            'totalPatterns': len(top_patterns),
            'extractedAt': datetime.now().isoformat(),
            'sourceFile': str(inputFile),
            'topN': topN
        }
        
        with open(patterns_file_path, 'w', encoding='utf-8') as f:
            json.dump(patterns_data, f, indent=2, ensure_ascii=False)
        
        print(f"  Extracted top {len(top_patterns)} patterns and saved to {patterns_file_path}")
        patternsFile = str(patterns_file_path)
    
    # Use log_df directly - patterns not in top_patterns are already marked as "Others"
    log_df_combined = log_df.copy()
    
    # Pivot table: time x url_pattern (already aggregated, so performance is good)
    pivot = log_df_combined.groupby(['time_bucket', 'url_pattern']).size().unstack(fill_value=0)
    
    # Create interactive line chart (use Scattergl for better performance)
    fig = go.Figure()
    
    # Plotly's default color palette (same order as Plotly uses)
    plotly_default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
        '#393b79', '#5254a3', '#6b6ecf', '#9c9ede', '#637939',
        '#8ca252', '#b5cf6b', '#cedb9c', '#8c6d31', '#bd9e39',
        '#e7ba52', '#e7cb94', '#843c39', '#ad494a', '#d6616b'
    ]

    # Get actual patterns from pivot (sorted by total count, excluding "Others")
    # This ensures we use the exact pattern strings that exist in the data
    pattern_counts = pivot.sum().sort_values(ascending=False)
    actual_patterns = [p for p in pattern_counts.index if p != 'Others'][:topN]

    # Add top patterns first
    for i, pattern in enumerate(actual_patterns):
        if pattern in pivot.columns:
            # Use Scattergl for WebGL rendering
            # Explicitly set color to match Plotly's default palette
            trace_color = plotly_default_colors[i % len(plotly_default_colors)]
            trace = go.Scattergl(
                x=pivot.index,
                y=pivot[pattern],
                mode='lines+markers',
                name=pattern,
                line=dict(width=2, color=trace_color),
                marker=dict(size=4, color=trace_color),
                hovertemplate=f'Count: %{{y}}, Pattern: {pattern}<extra></extra>',
                visible=True
            )
            fig.add_trace(trace)
    
    # Add "Others" trace if it exists
    if 'Others' in pivot.columns:
        others_color = '#808080'  # Gray color for Others
        others_trace = go.Scattergl(
            x=pivot.index,
            y=pivot['Others'],
            mode='lines+markers',
            name='Others',
            line=dict(width=2, color=others_color),
            marker=dict(size=4, color=others_color),
            hovertemplate='Count: %{y}, Pattern: Others<extra></extra>',
            visible=True
        )
        fig.add_trace(others_trace)
    
    # Update layout with enhanced features
    # Note: Filtering is handled by the checkbox panel (JavaScript) added later
    # Legend is hidden since we use checkboxes instead
    # Add right margin to make space for checkbox panel
    fig.update_layout(
        title=f'Request Count per URI Pattern (Top {topN}, Interval: {interval})',
        xaxis_title='Time',
        yaxis_title='Request Count',
        hovermode='x unified',
        height=600,
        showlegend=False,  # Hide legend, use checkboxes instead
        margin=dict(r=250),  # Add right margin for checkbox panel
        # Enable zoom and pan features
        dragmode='zoom'  # Box select for zoom
    )
    
    # Add range slider for time navigation
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1h", step="hour", stepmode="backward"),
                dict(count=6, label="6h", step="hour", stepmode="backward"),
                dict(count=12, label="12h", step="hour", stepmode="backward"),
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(step="all")
            ])
        )
    )
    
    # Enable y-axis autorange and manual adjustment
    fig.update_yaxes(
        autorange=True,
        fixedrange=False  # Allow manual zoom on y-axis
    )
    
    # Generate output file
    input_path = Path(inputFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"requestcnt_{timestamp}.html"
    
    # Save as HTML with full interactivity
    # Use a specific div_id to make it easier to find
    plotly_div_id = f'plotly-div-{timestamp}'
    fig.write_html(str(output_file), include_plotlyjs='cdn', div_id=plotly_div_id)
    
    # Add enhanced checkbox controls and JavaScript for better filtering
    # Read the generated HTML
    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract the actual div ID from HTML (Plotly may modify it)
    div_id_match = re.search(r'<div id="([^"]+)"[^>]*class="[^"]*plotly[^"]*"', html_content)
    actual_div_id = div_id_match.group(1) if div_id_match else plotly_div_id
    
    # Create checkbox HTML for each pattern
    # Position it in the right margin area, not overlapping with the graph
    # Use fixed position to ensure it's always visible
    # Use Plotly's default text color (#444) for consistency
    checkbox_html = '<div id="filterCheckboxPanel" style="position: fixed; right: 20px; top: 80px; width: 220px; max-height: 500px; overflow-y: auto; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); color: #444; font-family: \'Open Sans\', verdana, arial, sans-serif;">'
    checkbox_html += '<div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">Filter URI Patterns:</div>'
    checkbox_html += '<div style="margin-bottom: 8px; position: relative;"><input type="text" id="patternFilterInput" placeholder="Regex filter..." style="width: 100%; padding: 4px 24px 4px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 11px; box-sizing: border-box;"><span id="clearFilterBtn" style="position: absolute; right: 6px; top: 50%; transform: translateY(-50%); cursor: pointer; font-size: 14px; color: #999; display: none;" title="Clear filter">×</span></div>'
    checkbox_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkAll" checked> <strong>All</strong></label></div>'
    checkbox_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkNone"> <strong>None</strong></label></div>'
    checkbox_html += '<hr style="margin: 8px 0;">'
    
    # Create checkbox items using the same actual_patterns list as traces
    # This ensures exact color match between chart lines and checkbox labels
    for i, pattern in enumerate(actual_patterns):
        pattern_id = f'pattern_{i}'
        pattern_display = pattern[:60] + ('...' if len(pattern) > 60 else '')
        # Use the same color index as the corresponding trace
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        checkbox_html += f'<div class="pattern-item" style="margin-bottom: 3px; font-size: 11px;" data-pattern="{pattern}"><label class="pattern-label" data-index="{i}"><input type="checkbox" class="pattern-checkbox" id="{pattern_id}" data-index="{i}" checked> <span class="pattern-text" style="color: {trace_color}; font-weight: bold;">{pattern_display}</span></label></div>'

    # Add "Others" checkbox if it exists (same logic as "Others" trace)
    if 'Others' in pivot.columns:
        pattern_id = f'pattern_{len(actual_patterns)}'
        others_color = '#808080'  # Same gray color as Others trace
        checkbox_html += f'<div class="pattern-item" style="margin-bottom: 3px; font-size: 11px;" data-pattern="Others"><label class="pattern-label" data-index="{len(actual_patterns)}"><input type="checkbox" class="pattern-checkbox" id="{pattern_id}" data-index="{len(actual_patterns)}" checked> <span class="pattern-text" style="color: {others_color}; font-weight: bold;">Others</span></label></div>'
    
    checkbox_html += '</div>'
    
    # Add hover text display area and clipboard copy feature
    hover_text_html = '''
    <div id="hoverTextDisplay" style="position: fixed; bottom: 20px; right: 20px; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; max-width: 300px; max-height: 150px; overflow-y: auto; display: none; z-index: 2000; box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-size: 12px; color: #444; font-family: 'Open Sans', verdana, arial, sans-serif;">
        <div style="font-weight: bold; margin-bottom: 5px;">Hover Info:</div>
        <div id="hoverTextContent" style="white-space: pre-wrap; word-break: break-word;"></div>
        <div style="margin-top: 5px; font-size: 10px; color: #666;">Click or press Ctrl+C to copy</div>
    </div>
    '''
    
    # JavaScript for checkbox functionality and hover text copy
    js_code = f'''
    <script>
    (function() {{
        // Hover text storage and clipboard functionality
        let lastHoverText = '';
        let hoverTextDisplay = null;
        let hoverTextContent = null;
        
        // Function to get hover text elements (lazy initialization)
        function getHoverTextElements() {{
            if (!hoverTextDisplay) {{
                hoverTextDisplay = document.getElementById('hoverTextDisplay');
            }}
            if (!hoverTextContent) {{
                hoverTextContent = document.getElementById('hoverTextContent');
            }}
            return {{ display: hoverTextDisplay, content: hoverTextContent }};
        }}
        
        // Function to copy text to clipboard
        function copyToClipboard(text) {{
            const elements = getHoverTextElements();
            const hoverTextContent = elements.content;
            
            if (!hoverTextContent) return;
            
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => {{
                    console.log('Copied to clipboard:', text);
                    // Show feedback
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{
                        hoverTextContent.innerHTML = originalContent;
                    }}, 1000);
                }}).catch(err => {{
                    console.error('Failed to copy:', err);
                    fallbackCopyToClipboard(text);
                }});
            }} else {{
                fallbackCopyToClipboard(text);
            }}
        }}
        
        // Fallback copy method
        function fallbackCopyToClipboard(text) {{
            const elements = getHoverTextElements();
            const hoverTextContent = elements.content;
            
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {{
                document.execCommand('copy');
                console.log('Copied to clipboard (fallback):', text);
                if (hoverTextContent) {{
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{
                        hoverTextContent.innerHTML = originalContent;
                    }}, 1000);
                }}
            }} catch (err) {{
                console.error('Fallback copy failed:', err);
            }}
            document.body.removeChild(textArea);
        }}
        
        // Handle Ctrl+C keyboard shortcut
        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'c' && lastHoverText) {{
                const elements = getHoverTextElements();
                if (elements.display && elements.display.style.display !== 'none') {{
                    e.preventDefault();
                    copyToClipboard(lastHoverText);
                }}
            }}
        }});
        
        // Wait for DOM to be ready, then setup click handler
        function setupHoverTextClick() {{
            const elements = getHoverTextElements();
            if (elements.display) {{
                console.log('✓ hoverTextDisplay found, setting up click handler');
                elements.display.addEventListener('click', function() {{
                    if (lastHoverText) {{
                        copyToClipboard(lastHoverText);
                    }}
                }});
            }} else {{
                // Retry if not ready yet
                console.log('hoverTextDisplay not found, retrying...');
                setTimeout(setupHoverTextClick, 100);
            }}
        }}
        
        // Initialize hover text click handler when DOM is ready
        function initHoverText() {{
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    setTimeout(setupHoverTextClick, 100);
                }});
            }} else {{
                setTimeout(setupHoverTextClick, 100);
            }}
        }}
        
        // Start hover text initialization
        initHoverText();
        
        // Wait for Plotly to be ready
        function initCheckboxes() {{
            const checkAll = document.getElementById('checkAll');
            const checkNone = document.getElementById('checkNone');
            const checkboxes = document.querySelectorAll('.pattern-checkbox');
            
            if (!checkAll || !checkNone || checkboxes.length === 0) {{
                console.warn('Checkbox elements not found. Retrying...');
                console.warn('  checkAll:', checkAll);
                console.warn('  checkNone:', checkNone);
                console.warn('  checkboxes:', checkboxes.length);
                // Retry after a delay
                setTimeout(initCheckboxes, 200);
                return;
            }}
            
            console.log('✓ Checkbox elements found:', checkboxes.length, 'checkboxes');
            
            if (!window.Plotly) {{
                console.warn('Plotly not loaded yet');
                setTimeout(initCheckboxes, 100);
                return;
            }}
            
            // Find Plotly div - use the specific div ID we set
            let plotlyDiv = null;
            const targetDivId = "{actual_div_id}";
            
            // Method 1: Find by the specific ID we set
            if (targetDivId && targetDivId !== '') {{
                plotlyDiv = document.getElementById(targetDivId);
            }}
            
            // Method 2: Use window.gd if available (Plotly's global variable)
            if (!plotlyDiv && window.gd) {{
                plotlyDiv = window.gd;
            }}
            
            // Method 3: Find div with class 'js-plotly-plot' (most reliable)
            if (!plotlyDiv) {{
                const plotDivs = document.querySelectorAll('.js-plotly-plot');
                if (plotDivs.length > 0) {{
                    plotlyDiv = plotDivs[0];
                }}
            }}
            
            // Method 4: Find div with class 'plotly' that has an id starting with 'plotly'
            if (!plotlyDiv) {{
                const plotDivs = document.querySelectorAll('.plotly');
                for (const div of plotDivs) {{
                    if (div.id && (div.id.startsWith('plotly') || div.id === targetDivId)) {{
                        plotlyDiv = div;
                        break;
                    }}
                }}
                // If no id found, use first plotly div
                if (!plotlyDiv && plotDivs.length > 0) {{
                    plotlyDiv = plotDivs[0];
                }}
            }}
            
            if (!plotlyDiv) {{
                console.error('Plotly div not found. Target ID:', targetDivId);
                console.error('Available elements:', document.querySelectorAll('.plotly, .js-plotly-plot'));
                // Retry after a delay
                setTimeout(initCheckboxes, 200);
                return;
            }}
            
            console.log('Found Plotly div:', plotlyDiv.id || plotlyDiv.className);
            
            // Setup hover event handler to capture and display hover text
            // Display all points sorted by Count in descending order
            plotlyDiv.on('plotly_hover', function(data) {{
                if (data && data.points && data.points.length > 0) {{
                    // Collect all points with their count and pattern name
                    const pointInfo = data.points.map(pt => {{
                        const count = pt.y !== undefined ? pt.y : pt.y0 || 0;
                        const traceName = pt.data?.name || 
                                        pt.fullData?.name || 
                                        (pt.data && pt.data.fullData && pt.data.fullData.name) ||
                                        'Unknown';
                        return {{
                            count: count,
                            pattern: traceName,
                            point: pt
                        }};
                    }});
                    
                    // Sort by count in descending order
                    pointInfo.sort((a, b) => {{
                        return b.count - a.count;
                    }});
                    
                    // Format hover text: Show all points sorted by count
                    let displayText = '';
                    pointInfo.forEach((info, index) => {{
                        if (index > 0) {{
                            displayText += '\\n';
                        }}
                        displayText += `Count: ${{info.count}}, Pattern: ${{info.pattern}}`;
                    }});
                    
                    // Store for clipboard copy
                    lastHoverText = displayText;
                    
                    // Display in hover text area
                    const elements = getHoverTextElements();
                    if (elements.content && elements.display) {{
                        elements.content.textContent = displayText;
                        elements.display.style.display = 'block';
                        console.log('Hover text displayed:', displayText.substring(0, 50) + '...');
                    }} else {{
                        console.warn('hoverTextDisplay or hoverTextContent not found:', {{
                            display: !!elements.display,
                            content: !!elements.content
                        }});
                    }}
                }}
            }});
            
            // Keep hover text visible even after mouse leaves for copying
            plotlyDiv.on('plotly_unhover', function(data) {{
                // Don't hide - keep it visible so user can copy
            }});
            
            // Colors are already applied directly in HTML, so no need to apply them here
            // The colors match Plotly's default palette and are set in the span elements
            
            // Store original trace data for restoration
            let originalTraceData = null;
            
            const saveOriginalData = function() {{
                if (!originalTraceData && plotlyDiv.data) {{
                    originalTraceData = JSON.parse(JSON.stringify(plotlyDiv.data));
                    console.log('Saved original trace data:', originalTraceData.length, 'traces');
                }}
            }};
            
            // Save original data when first initialized
            setTimeout(saveOriginalData, 100);
            
            const updateVisibility = function() {{
                const visible = [];
                checkboxes.forEach((cb) => {{
                    visible.push(cb.checked);
                }});
                
                console.log('Updating visibility:', visible);
                
                // Ensure we have original data
                if (!originalTraceData && plotlyDiv.data) {{
                    originalTraceData = JSON.parse(JSON.stringify(plotlyDiv.data));
                }}
                
                // Get current trace count
                const currentTraceCount = plotlyDiv.data?.length || plotlyDiv._fullData?.length || 0;
                const originalTraceCount = originalTraceData ? originalTraceData.length : visible.length;
                
                // Count checked items
                const checkedCount = visible.filter(v => v).length;
                
                console.log('Current traces:', currentTraceCount, 'Original traces:', originalTraceCount, 'Checked:', checkedCount, 'Total:', visible.length);
                
                try {{
                    // If all are selected, restore all original traces if needed
                    if (checkedCount === visible.length) {{
                        // All selected - restore all traces if they were deleted
                        if (currentTraceCount !== originalTraceCount && originalTraceData) {{
                            console.log('Restoring all original traces');
                            // Remove all current traces
                            if (currentTraceCount > 0) {{
                                for (let i = currentTraceCount - 1; i >= 0; i--) {{
                                    try {{
                                        Plotly.deleteTraces(plotlyDiv, i);
                                    }} catch (e) {{
                                        console.warn('Error deleting trace ' + i + ':', e);
                                    }}
                                }}
                            }}
                            // Add back all original traces
                            if (originalTraceData.length > 0) {{
                                Plotly.addTraces(plotlyDiv, originalTraceData);
                            }}
                        }} else {{
                            // All traces are already present, just make them all visible
                            const visibleArray = Array(currentTraceCount).fill(true);
                            const traceIndices = Array.from({{length: currentTraceCount}}, (_, i) => i);
                            Plotly.restyle(plotlyDiv, {{
                                visible: visibleArray
                            }}, traceIndices);
                        }}
                    }} else if (checkedCount === 0) {{
                        // None selected - hide all (but keep traces)
                        const visibleArray = Array(currentTraceCount).fill(false);
                        const traceIndices = Array.from({{length: currentTraceCount}}, (_, i) => i);
                        Plotly.restyle(plotlyDiv, {{
                            visible: visibleArray
                        }}, traceIndices);
                    }} else {{
                        // Some selected - show only selected traces
                        // Ensure we have original data
                        if (!originalTraceData && plotlyDiv.data) {{
                            originalTraceData = JSON.parse(JSON.stringify(plotlyDiv.data));
                        }}
                        
                        if (originalTraceData) {{
                            // Get data for selected traces only
                            const selectedTraces = [];
                            for (let i = 0; i < originalTraceData.length && i < visible.length; i++) {{
                                if (visible[i]) {{
                                    selectedTraces.push(originalTraceData[i]);
                                }}
                            }}
                            
                            console.log('Selected traces to show:', selectedTraces.length);
                            
                            // Remove all current traces
                            if (currentTraceCount > 0) {{
                                for (let i = currentTraceCount - 1; i >= 0; i--) {{
                                    try {{
                                        Plotly.deleteTraces(plotlyDiv, i);
                                    }} catch (e) {{
                                        console.warn('Error deleting trace ' + i + ':', e);
                                    }}
                                }}
                            }}
                            
                            // Add back only selected traces
                            if (selectedTraces.length > 0) {{
                                Plotly.addTraces(plotlyDiv, selectedTraces);
                            }}
                        }} else {{
                            // Fallback: use visibility if original data not available
                            const visibleArray = [];
                            for (let i = 0; i < currentTraceCount; i++) {{
                                visibleArray.push(i < visible.length ? visible[i] : false);
                            }}
                            const traceIndices = Array.from({{length: visibleArray.length}}, (_, i) => i);
                            Plotly.restyle(plotlyDiv, {{
                                visible: visibleArray
                            }}, traceIndices);
                        }}
                    }}
                }} catch (e) {{
                    console.error('Error updating plotly:', e);
                    // Fallback: Use visibility toggle
                    try {{
                        const visibleArray = [];
                        for (let i = 0; i < currentTraceCount; i++) {{
                            visibleArray.push(i < visible.length ? visible[i] : false);
                        }}
                        const traceIndices = Array.from({{length: visibleArray.length}}, (_, i) => i);
                        Plotly.restyle(plotlyDiv, {{
                            visible: visibleArray
                        }}, traceIndices);
                    }} catch (e2) {{
                        console.error('Fallback also failed:', e2);
                    }}
                }}
            }};
            
            // Helper function to check if a checkbox's parent pattern-item is visible
            const isCheckboxVisible = function(checkbox) {{
                const patternItem = checkbox.closest('.pattern-item');
                return patternItem && patternItem.style.display !== 'none';
            }};
            
            // Check all - only check visible (filtered) items
            checkAll.addEventListener('change', function() {{
                if (this.checked) {{
                    checkNone.checked = false;
                    // Only check visible checkboxes
                    checkboxes.forEach(cb => {{
                        if (isCheckboxVisible(cb)) {{
                            cb.checked = true;
                        }} else {{
                            cb.checked = false;
                        }}
                    }});
                    updateVisibility();
                }}
            }});
            
            // Check none
            checkNone.addEventListener('change', function() {{
                if (this.checked) {{
                    checkAll.checked = false;
                    checkboxes.forEach(cb => cb.checked = false);
                    updateVisibility();
                }}
            }});
            
            // Individual checkboxes
            checkboxes.forEach(cb => {{
                cb.addEventListener('change', function() {{
                    if (this.checked) {{
                        checkNone.checked = false;
                    }}
                    
                    // Check if all visible checkboxes are checked
                    const visibleCheckboxes = Array.from(checkboxes).filter(c => isCheckboxVisible(c));
                    const allVisibleChecked = visibleCheckboxes.length > 0 && visibleCheckboxes.every(c => c.checked);
                    if (allVisibleChecked) {{
                        checkAll.checked = true;
                        checkNone.checked = false;
                    }} else {{
                        checkAll.checked = false;
                    }}
                    
                    updateVisibility();
                }});
            }});
            
            // Pattern filter input functionality
            const patternFilterInput = document.getElementById('patternFilterInput');
            const clearFilterBtn = document.getElementById('clearFilterBtn');
            
            if (patternFilterInput) {{
                const filterPatterns = function() {{
                    const filterText = patternFilterInput.value.trim();
                    const patternItems = document.querySelectorAll('.pattern-item');
                    
                    // Show/hide clear button
                    if (clearFilterBtn) {{
                        clearFilterBtn.style.display = filterText ? 'block' : 'none';
                    }}
                    
                    if (!filterText) {{
                        // Show all items when filter is empty
                        patternItems.forEach(item => {{
                            item.style.display = '';
                        }});
                        return;
                    }}
                    
                    try {{
                        // Create regex pattern (case-insensitive by default)
                        const regex = new RegExp(filterText, 'i');
                        
                        // Filter pattern items
                        let visibleCount = 0;
                        patternItems.forEach(item => {{
                            const pattern = item.getAttribute('data-pattern') || '';
                            if (regex.test(pattern)) {{
                                item.style.display = '';
                                visibleCount++;
                            }} else {{
                                item.style.display = 'none';
                            }}
                        }});
                        
                        // Update checkboxes array to only include visible ones
                        // This ensures updateVisibility() works correctly with filtered items
                        console.log(`Filtered patterns: ${{visibleCount}} visible out of ${{patternItems.length}} total`);
                    }} catch (e) {{
                        // Invalid regex - show error or ignore
                        console.warn('Invalid regex pattern:', filterText, e);
                        // Show all items on invalid regex
                        patternItems.forEach(item => {{
                            item.style.display = '';
                        }});
                    }}
                }};
                
                // Add event listeners for real-time filtering
                patternFilterInput.addEventListener('input', filterPatterns);
                patternFilterInput.addEventListener('keyup', filterPatterns);
                
                // Clear filter button functionality
                if (clearFilterBtn) {{
                    clearFilterBtn.addEventListener('click', function() {{
                        patternFilterInput.value = '';
                        filterPatterns();
                        patternFilterInput.focus();
                    }});
                    
                    // Hover effect for clear button
                    clearFilterBtn.addEventListener('mouseenter', function() {{
                        this.style.color = '#333';
                    }});
                    clearFilterBtn.addEventListener('mouseleave', function() {{
                        this.style.color = '#999';
                    }});
                }}
            }}
        }}
        
        // Initialize when DOM and Plotly are ready
        function waitForPlotly() {{
            // Check if DOM is ready
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    setTimeout(waitForPlotly, 100);
                }});
                return;
            }}
            
            // Check if required elements exist
            const checkAll = document.getElementById('checkAll');
            const hoverTextDisplay = document.getElementById('hoverTextDisplay');
            
            if (!checkAll || !hoverTextDisplay) {{
                console.log('Waiting for HTML elements to be inserted...');
                setTimeout(waitForPlotly, 100);
                return;
            }}
            
            console.log('✓ HTML elements found, waiting for Plotly...');
            
            // Check if Plotly is loaded
            if (window.Plotly) {{
                console.log('✓ Plotly loaded, initializing checkboxes...');
                // Wait a bit more for Plotly to finish rendering
                setTimeout(initCheckboxes, 300);
            }} else {{
                // Wait for Plotly to load
                let retryCount = 0;
                const maxRetries = 50; // 5 seconds max
                const checkPlotly = setInterval(function() {{
                    retryCount++;
                    if (window.Plotly) {{
                        clearInterval(checkPlotly);
                        console.log('✓ Plotly loaded after', retryCount * 100, 'ms');
                        setTimeout(initCheckboxes, 300);
                    }} else if (retryCount >= maxRetries) {{
                        clearInterval(checkPlotly);
                        console.error('Plotly not loaded after', maxRetries * 100, 'ms');
                        // Try to initialize anyway
                        setTimeout(initCheckboxes, 300);
                    }}
                }}, 100);
            }}
        }}
        
        // Start initialization
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', waitForPlotly);
        }} else {{
            waitForPlotly();
        }}
    }})();
    </script>
    '''
    
    # Insert checkbox HTML, hover text display, and JavaScript before closing body tag
    # Try multiple methods to ensure insertion
    inserted = False
    
    # Method 1: Insert before </body> tag (most common)
    if '</body>' in html_content:
        # Find the last </body> tag and insert before it
        html_content = html_content.rsplit('</body>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_html + hover_text_html + js_code + '</body>' + html_content[1]
            inserted = True
    
    # Method 2: If no </body>, insert before </html>
    if not inserted and '</html>' in html_content:
        html_content = html_content.rsplit('</html>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_html + hover_text_html + js_code + '</html>' + html_content[1]
            inserted = True
    
    # Method 3: Fallback - append at the end
    if not inserted:
        html_content += checkbox_html + hover_text_html + js_code
    
    # Debug: verify insertion
    if 'filterCheckboxPanel' not in html_content:
        print("  Warning: filterCheckboxPanel not found in HTML output")
    else:
        print("  ✓ filterCheckboxPanel inserted successfully")
    if 'hoverTextDisplay' not in html_content:
        print("  Warning: hoverTextDisplay not found in HTML output")
    else:
        print("  ✓ hoverTextDisplay inserted successfully")
    
    # Write modified HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return {
        'filePath': str(output_file.resolve()),
        'totalTransactions': len(log_df),
        'topN': topN,
        'interval': interval,
        'patternsDisplayed': len(top_patterns),
        'patternsFile': patternsFile
    }


# ============================================================================
# MCP Tool: generateReceivedBytesPerURI
# ============================================================================

def generateReceivedBytesPerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 10,
    interval: str = '10s',
    patternsFile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate Received Bytes per URI time-series visualization with Sum and Average Top N.

    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        outputFormat (str): Output format ('html' only supported)
        topN (int): Number of top URI patterns to display (default: 10)
        interval (str): Time interval for aggregation (default: '10s').
                       Examples: '1s', '10s', '1min', '5min', '1h'
        patternsFile (str, optional): Path to JSON file containing URL patterns.
                                    If provided, uses these patterns for visualization.
                                    If not provided, extracts top N patterns and saves to file.

    Returns:
        dict: {
            'filePath': str (receivedbytes_*.html),
            'totalTransactions': int,
            'patternsFile': str (path to saved patterns file),
            'topNSum': list (top N URIs by sum),
            'topNAvg': list (top N URIs by average)
        }
    """
    if outputFormat != 'html':
        raise ValidationError('outputFormat', "Only 'html' output format is currently supported")

    # Normalize interval parameter to pandas-compatible format
    interval = _normalize_interval(interval)

    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)

    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)

    if log_df.empty:
        raise ValueError("No data to visualize")

    # Get field mappings using FieldMapper
    time_field = FieldMapper.find_field(log_df, 'time', format_info)
    url_field = FieldMapper.find_field(log_df, 'url', format_info)

    # For bytes field, provide possible alternative names
    possible_bytes_fields = ['received_bytes', 'bytes_received', 'sent_bytes', 'bytes_sent',
                             'body_bytes_sent', 'response_size', 'bytes', 'size']
    bytes_field = FieldMapper.find_field(log_df, 'receivedBytes', format_info,
                                         possible_names=possible_bytes_fields)

    # Validate required fields
    if not time_field or time_field not in log_df.columns:
        raise ValueError(f"Time field not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    if not url_field or url_field not in log_df.columns:
        raise ValueError(f"URL field not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    if not bytes_field or bytes_field not in log_df.columns:
        raise ValueError(f"Received bytes field not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")

    # Convert types
    log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    log_df[bytes_field] = pd.to_numeric(log_df[bytes_field], errors='coerce')
    log_df = log_df.dropna(subset=[time_field, bytes_field])

    # Determine input path for output file location
    input_path = Path(inputFile)

    # Load patterns from file if provided first (to use pattern rules for generalization)
    patterns_file_for_generalize = None
    top_patterns = None

    if patternsFile and os.path.exists(patternsFile):
        # Load patterns from file
        try:
            with open(patternsFile, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)

            # Extract pattern rules from file
            if isinstance(patterns_data, dict):
                if 'patternRules' in patterns_data and isinstance(patterns_data['patternRules'], list):
                    patterns_file_for_generalize = patternsFile
                    # Extract replacement values from patternRules as top_patterns
                    top_patterns = [rule.get('replacement', '') for rule in patterns_data['patternRules'] if isinstance(rule, dict) and 'replacement' in rule]
                    top_patterns = [p for p in top_patterns if p]  # Remove empty strings
                    logger.info(f"Using pattern rules from {patternsFile} for URL generalization")
                    logger.info(f"Loaded {len(top_patterns)} patterns from patternRules")
                else:
                    # Fallback for old format (backward compatibility)
                    if 'patterns' in patterns_data:
                        top_patterns = patterns_data['patterns']
                        patterns_file_for_generalize = patternsFile
                        logger.info(f"Using patterns from {patternsFile} (will be converted to rules)")
                    elif 'urls' in patterns_data:
                        top_patterns = patterns_data['urls']
                        patterns_file_for_generalize = patternsFile
                        logger.info(f"Using URLs from {patternsFile} (will be converted to rules)")
                    else:
                        raise ValueError(f"No patternRules, patterns, or urls found in {patternsFile}")
            else:
                raise ValueError(f"Unexpected patterns file format: {type(patterns_data)}")

            # Ensure patterns are strings and unique
            top_patterns = list(set([str(p) for p in top_patterns if p]))

        except Exception as e:
            logger.warning(f"Could not load patterns file {patternsFile}: {e}")
            logger.info(f"Falling back to extracting top {topN} patterns")
            patternsFile = None
            top_patterns = None

    # Generalize URLs (remove IDs) using pattern file if available
    from data_processor import _generalize_url
    log_df['url_pattern'] = log_df[url_field].apply(
        lambda x: _generalize_url(x, patterns_file_for_generalize) if pd.notna(x) else 'Unknown'
    )

    # Group by time interval and URL pattern
    log_df['time_bucket'] = log_df[time_field].dt.floor(interval)

    # Calculate sum and average for each time bucket and URL pattern
    bytes_stats = log_df.groupby(['time_bucket', 'url_pattern'])[bytes_field].agg(['sum', 'mean']).reset_index()
    bytes_stats.columns = ['time_bucket', 'url_pattern', 'sum_bytes', 'avg_bytes']

    # If patterns were not loaded from file, extract top N by sum
    if not patternsFile or not os.path.exists(patternsFile):
        # Get top N URL patterns by total sum of bytes
        pattern_total_sum = bytes_stats.groupby('url_pattern')['sum_bytes'].sum().sort_values(ascending=False)
        top_patterns = pattern_total_sum.head(topN).index.tolist()

        # Generate pattern rules from patterns
        pattern_rules = []
        for pattern in top_patterns:
            # Convert pattern with * wildcards to regex
            temp_pattern = pattern.replace('*', '__WILDCARD__')
            escaped_pattern = re.escape(temp_pattern)
            regex_pattern = escaped_pattern.replace('__WILDCARD__', '.*')

            pattern_rules.append({
                'pattern': f'^{regex_pattern}$',
                'replacement': pattern
            })

        # Save patterns to file with pattern rules only
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        patterns_file_path = input_path.parent / f"patterns_{timestamp}.json"

        patterns_data = {
            'patternRules': pattern_rules,
            'totalPatterns': len(top_patterns),
            'extractedAt': datetime.now().isoformat(),
            'sourceFile': str(inputFile),
            'topN': topN,
            'criteria': 'sum_received_bytes'
        }

        with open(patterns_file_path, 'w', encoding='utf-8') as f:
            json.dump(patterns_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Extracted top {len(top_patterns)} patterns and saved to {patterns_file_path}")
        patternsFile = str(patterns_file_path)

    # Filter data to only include top patterns
    bytes_stats_filtered = bytes_stats[bytes_stats['url_pattern'].isin(top_patterns)].copy()

    # Get top N by sum
    pattern_sum = bytes_stats_filtered.groupby('url_pattern')['sum_bytes'].sum().sort_values(ascending=False)
    top_patterns_sum = pattern_sum.head(topN).index.tolist()

    # Get top N by average
    pattern_avg = bytes_stats_filtered.groupby('url_pattern')['avg_bytes'].mean().sort_values(ascending=False)
    top_patterns_avg = pattern_avg.head(topN).index.tolist()

    # Create pivot tables for sum and average
    pivot_sum = bytes_stats_filtered[bytes_stats_filtered['url_pattern'].isin(top_patterns_sum)].pivot_table(
        index='time_bucket',
        columns='url_pattern',
        values='sum_bytes',
        fill_value=0
    )

    pivot_avg = bytes_stats_filtered[bytes_stats_filtered['url_pattern'].isin(top_patterns_avg)].pivot_table(
        index='time_bucket',
        columns='url_pattern',
        values='avg_bytes',
        fill_value=0
    )

    # Sort columns by total sum/avg (descending)
    if len(pivot_sum.columns) > 0:
        pivot_sum = pivot_sum[pattern_sum.head(topN).index]
    if len(pivot_avg.columns) > 0:
        pivot_avg = pivot_avg[pattern_avg.head(topN).index]

    # Create subplots with two charts
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            f'Received Bytes Sum per URI Pattern (Top {topN}, Interval: {interval})',
            f'Received Bytes Average per URI Pattern (Top {topN}, Interval: {interval})'
        ),
        vertical_spacing=0.15
    )

    # Plotly's default color palette
    plotly_default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
    ]

    # Add Sum Top N traces
    for i, pattern in enumerate(pivot_sum.columns):
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        fig.add_trace(
            go.Scattergl(
                x=pivot_sum.index,
                y=pivot_sum[pattern],
                mode='lines+markers',
                name=pattern,
                line=dict(width=2, color=trace_color),
                marker=dict(size=4, color=trace_color),
                legendgroup='sum',
                showlegend=True,
                hovertemplate=f'Sum: %{{y:,.0f}} bytes<br>Pattern: {pattern}<extra></extra>'
            ),
            row=1, col=1
        )

    # Add Average Top N traces
    for i, pattern in enumerate(pivot_avg.columns):
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        fig.add_trace(
            go.Scattergl(
                x=pivot_avg.index,
                y=pivot_avg[pattern],
                mode='lines+markers',
                name=pattern,
                line=dict(width=2, color=trace_color),
                marker=dict(size=4, color=trace_color),
                legendgroup='avg',
                showlegend=True,
                hovertemplate=f'Avg: %{{y:,.0f}} bytes<br>Pattern: {pattern}<extra></extra>'
            ),
            row=2, col=1
        )

    # Update layout - hide legend since we use checkboxes
    fig.update_layout(
        height=900,
        showlegend=False,  # Hide legend, use checkboxes instead
        title_text=f"Received Bytes per URI Pattern Analysis",
        hovermode='x unified',
        margin=dict(r=280),  # Add right margin for checkbox panels
        dragmode='zoom'  # Enable box select zoom (both horizontal and vertical)
    )

    # Update axes with vertical zoom enabled
    fig.update_xaxes(title_text='Time', row=2, col=1)
    fig.update_yaxes(title_text='Sum Bytes', row=1, col=1, fixedrange=False)  # Allow vertical zoom
    fig.update_yaxes(title_text='Average Bytes', row=2, col=1, fixedrange=False)  # Allow vertical zoom

    # Add range slider for time navigation on bottom chart
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1h", step="hour", stepmode="backward"),
                dict(count=6, label="6h", step="hour", stepmode="backward"),
                dict(count=12, label="12h", step="hour", stepmode="backward"),
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(step="all")
            ])
        ),
        row=2, col=1
    )

    # Generate output file
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"receivedbytes_{timestamp}.html"

    # Save as HTML with specific div_id
    plotly_div_id = f'plotly-div-{timestamp}'
    fig.write_html(str(output_file), include_plotlyjs='cdn', div_id=plotly_div_id)

    # Add checkbox controls and JavaScript for filtering
    # Read the generated HTML
    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract the actual div ID from HTML
    div_id_match = re.search(r'<div id="([^"]+)"[^>]*class="[^"]*plotly[^"]*"', html_content)
    actual_div_id = div_id_match.group(1) if div_id_match else plotly_div_id

    # Create checkbox HTML for Sum chart (top)
    checkbox_sum_html = '<div id="filterCheckboxPanelSum" style="position: fixed; right: 20px; top: 80px; width: 250px; max-height: 350px; overflow-y: auto; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); color: #444; font-family: \'Open Sans\', verdana, arial, sans-serif;">'
    checkbox_sum_html += '<div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">Sum Top N:</div>'
    checkbox_sum_html += '<div style="margin-bottom: 8px; position: relative;"><input type="text" id="patternFilterInputSum" placeholder="Regex filter..." style="width: 100%; padding: 4px 24px 4px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 11px; box-sizing: border-box;"><span id="clearFilterBtnSum" style="position: absolute; right: 6px; top: 50%; transform: translateY(-50%); cursor: pointer; font-size: 14px; color: #999; display: none;" title="Clear filter">×</span></div>'
    checkbox_sum_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkAllSum" checked> <strong>All</strong></label></div>'
    checkbox_sum_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkNoneSum"> <strong>None</strong></label></div>'
    checkbox_sum_html += '<hr style="margin: 8px 0;">'

    for i, pattern in enumerate(pivot_sum.columns):
        pattern_id = f'pattern_sum_{i}'
        pattern_display = pattern[:50] + ('...' if len(pattern) > 50 else '')
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        checkbox_sum_html += f'<div class="pattern-item-sum" style="margin-bottom: 3px; font-size: 11px;" data-pattern="{pattern}"><label><input type="checkbox" class="pattern-checkbox-sum" id="{pattern_id}" data-index="{i}" checked> <span style="color: {trace_color}; font-weight: bold;">{pattern_display}</span></label></div>'

    checkbox_sum_html += '</div>'

    # Create checkbox HTML for Average chart (bottom)
    checkbox_avg_html = '<div id="filterCheckboxPanelAvg" style="position: fixed; right: 20px; top: 460px; width: 250px; max-height: 350px; overflow-y: auto; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); color: #444; font-family: \'Open Sans\', verdana, arial, sans-serif;">'
    checkbox_avg_html += '<div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">Average Top N:</div>'
    checkbox_avg_html += '<div style="margin-bottom: 8px; position: relative;"><input type="text" id="patternFilterInputAvg" placeholder="Regex filter..." style="width: 100%; padding: 4px 24px 4px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 11px; box-sizing: border-box;"><span id="clearFilterBtnAvg" style="position: absolute; right: 6px; top: 50%; transform: translateY(-50%); cursor: pointer; font-size: 14px; color: #999; display: none;" title="Clear filter">×</span></div>'
    checkbox_avg_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkAllAvg" checked> <strong>All</strong></label></div>'
    checkbox_avg_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkNoneAvg"> <strong>None</strong></label></div>'
    checkbox_avg_html += '<hr style="margin: 8px 0;">'

    for i, pattern in enumerate(pivot_avg.columns):
        pattern_id = f'pattern_avg_{i}'
        pattern_display = pattern[:50] + ('...' if len(pattern) > 50 else '')
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        checkbox_avg_html += f'<div class="pattern-item-avg" style="margin-bottom: 3px; font-size: 11px;" data-pattern="{pattern}"><label><input type="checkbox" class="pattern-checkbox-avg" id="{pattern_id}" data-index="{i + len(pivot_sum.columns)}" checked> <span style="color: {trace_color}; font-weight: bold;">{pattern_display}</span></label></div>'

    checkbox_avg_html += '</div>'

    # Add hover text display area
    hover_text_html = '''
    <div id="hoverTextDisplay" style="position: fixed; bottom: 20px; right: 20px; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; max-width: 300px; max-height: 150px; overflow-y: auto; display: none; z-index: 2000; box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-size: 12px; color: #444; font-family: 'Open Sans', verdana, arial, sans-serif; cursor: pointer;">
        <div style="font-weight: bold; margin-bottom: 5px;">Hover Info (Click to copy):</div>
        <div id="hoverTextContent" style="white-space: pre-wrap; word-break: break-word;"></div>
        <div style="margin-top: 5px; font-size: 10px; color: #666;">Click or press Ctrl+C to copy</div>
    </div>
    '''

    # JavaScript for checkbox functionality and hover text copy
    js_code = f'''
    <script>
    (function() {{
        let lastHoverText = '';
        const sumTraceCount = {len(pivot_sum.columns)};
        const avgTraceCount = {len(pivot_avg.columns)};

        function copyToClipboard(text) {{
            const hoverTextContent = document.getElementById('hoverTextContent');
            if (!hoverTextContent) return;

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => {{
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{ hoverTextContent.innerHTML = originalContent; }}, 1000);
                }}).catch(() => {{ fallbackCopy(text); }});
            }} else {{
                fallbackCopy(text);
            }}
        }}

        function fallbackCopy(text) {{
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {{
                document.execCommand('copy');
                const hoverTextContent = document.getElementById('hoverTextContent');
                if (hoverTextContent) {{
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{ hoverTextContent.innerHTML = originalContent; }}, 1000);
                }}
            }} catch (err) {{ console.error('Copy failed:', err); }}
            document.body.removeChild(textArea);
        }}

        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'c' && lastHoverText) {{
                const hoverTextDisplay = document.getElementById('hoverTextDisplay');
                if (hoverTextDisplay && hoverTextDisplay.style.display !== 'none') {{
                    e.preventDefault();
                    copyToClipboard(lastHoverText);
                }}
            }}
        }});

        function initCheckboxes() {{
            const plotlyDiv = document.getElementById("{actual_div_id}") ||
                             document.querySelector('.js-plotly-plot') ||
                             document.querySelector('.plotly');

            if (!plotlyDiv || !window.Plotly) {{
                setTimeout(initCheckboxes, 100);
                return;
            }}

            // Setup hover event
            plotlyDiv.on('plotly_hover', function(data) {{
                if (data && data.points && data.points.length > 0) {{
                    const pointInfo = data.points.map(pt => {{
                        const count = pt.y !== undefined ? pt.y : 0;
                        const traceName = pt.data?.name || pt.fullData?.name || 'Unknown';
                        return {{ count: count, pattern: traceName }};
                    }});

                    pointInfo.sort((a, b) => b.count - a.count);

                    let displayText = '';
                    pointInfo.forEach((info, index) => {{
                        if (index > 0) displayText += '\\n';
                        displayText += `Count: ${{info.count.toLocaleString()}}, Pattern: ${{info.pattern}}`;
                    }});

                    lastHoverText = displayText;

                    const hoverTextContent = document.getElementById('hoverTextContent');
                    const hoverTextDisplay = document.getElementById('hoverTextDisplay');
                    if (hoverTextContent && hoverTextDisplay) {{
                        hoverTextContent.textContent = displayText;
                        hoverTextDisplay.style.display = 'block';
                    }}
                }}
            }});

            // Click to copy
            const hoverTextDisplay = document.getElementById('hoverTextDisplay');
            if (hoverTextDisplay) {{
                hoverTextDisplay.addEventListener('click', function() {{
                    if (lastHoverText) copyToClipboard(lastHoverText);
                }});
            }}

            // Checkbox handlers for Sum chart
            const checkAllSum = document.getElementById('checkAllSum');
            const checkNoneSum = document.getElementById('checkNoneSum');
            const checkboxesSum = document.querySelectorAll('.pattern-checkbox-sum');

            // Checkbox handlers for Average chart
            const checkAllAvg = document.getElementById('checkAllAvg');
            const checkNoneAvg = document.getElementById('checkNoneAvg');
            const checkboxesAvg = document.querySelectorAll('.pattern-checkbox-avg');

            function updateVisibility() {{
                const visible = [];

                // Sum traces
                checkboxesSum.forEach(cb => visible.push(cb.checked));
                // Average traces
                checkboxesAvg.forEach(cb => visible.push(cb.checked));

                try {{
                    Plotly.restyle(plotlyDiv, {{ visible: visible }},
                                  Array.from({{length: visible.length}}, (_, i) => i));
                }} catch (e) {{
                    console.error('Error updating visibility:', e);
                }}
            }}

            // Sum chart controls
            checkAllSum.addEventListener('change', function() {{
                if (this.checked) {{
                    checkNoneSum.checked = false;
                    // Only check visible items (filtered items)
                    checkboxesSum.forEach(cb => {{
                        const item = cb.closest('.pattern-item-sum');
                        if (item && item.style.display !== 'none') {{
                            cb.checked = true;
                        }}
                    }});
                    updateVisibility();
                }}
            }});

            checkNoneSum.addEventListener('change', function() {{
                if (this.checked) {{
                    checkAllSum.checked = false;
                    checkboxesSum.forEach(cb => cb.checked = false);
                    updateVisibility();
                }}
            }});

            checkboxesSum.forEach(cb => {{
                cb.addEventListener('change', function() {{
                    if (this.checked) checkNoneSum.checked = false;
                    // Check if all visible items are checked
                    const visibleCheckboxes = Array.from(checkboxesSum).filter(c => {{
                        const item = c.closest('.pattern-item-sum');
                        return item && item.style.display !== 'none';
                    }});
                    const allVisibleChecked = visibleCheckboxes.length > 0 && visibleCheckboxes.every(c => c.checked);
                    checkAllSum.checked = allVisibleChecked;
                    updateVisibility();
                }});
            }});

            // Average chart controls
            checkAllAvg.addEventListener('change', function() {{
                if (this.checked) {{
                    checkNoneAvg.checked = false;
                    // Only check visible items (filtered items)
                    checkboxesAvg.forEach(cb => {{
                        const item = cb.closest('.pattern-item-avg');
                        if (item && item.style.display !== 'none') {{
                            cb.checked = true;
                        }}
                    }});
                    updateVisibility();
                }}
            }});

            checkNoneAvg.addEventListener('change', function() {{
                if (this.checked) {{
                    checkAllAvg.checked = false;
                    checkboxesAvg.forEach(cb => cb.checked = false);
                    updateVisibility();
                }}
            }});

            checkboxesAvg.forEach(cb => {{
                cb.addEventListener('change', function() {{
                    if (this.checked) checkNoneAvg.checked = false;
                    // Check if all visible items are checked
                    const visibleCheckboxes = Array.from(checkboxesAvg).filter(c => {{
                        const item = c.closest('.pattern-item-avg');
                        return item && item.style.display !== 'none';
                    }});
                    const allVisibleChecked = visibleCheckboxes.length > 0 && visibleCheckboxes.every(c => c.checked);
                    checkAllAvg.checked = allVisibleChecked;
                    updateVisibility();
                }});
            }});

            // Pattern filter functionality for Sum panel
            const patternFilterInputSum = document.getElementById('patternFilterInputSum');
            const clearFilterBtnSum = document.getElementById('clearFilterBtnSum');

            if (patternFilterInputSum) {{
                const filterPatternsSum = function() {{
                    const filterText = patternFilterInputSum.value.trim();
                    const patternItems = document.querySelectorAll('.pattern-item-sum');

                    if (clearFilterBtnSum) {{
                        clearFilterBtnSum.style.display = filterText ? 'block' : 'none';
                    }}

                    if (!filterText) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                        return;
                    }}

                    try {{
                        const regex = new RegExp(filterText, 'i');
                        patternItems.forEach(item => {{
                            const pattern = item.getAttribute('data-pattern') || '';
                            item.style.display = regex.test(pattern) ? '' : 'none';
                        }});
                    }} catch (e) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                    }}
                }};

                patternFilterInputSum.addEventListener('input', filterPatternsSum);
                patternFilterInputSum.addEventListener('keyup', filterPatternsSum);

                if (clearFilterBtnSum) {{
                    clearFilterBtnSum.addEventListener('click', function() {{
                        patternFilterInputSum.value = '';
                        filterPatternsSum();
                        patternFilterInputSum.focus();
                    }});
                    clearFilterBtnSum.addEventListener('mouseenter', function() {{ this.style.color = '#333'; }});
                    clearFilterBtnSum.addEventListener('mouseleave', function() {{ this.style.color = '#999'; }});
                }}
            }}

            // Pattern filter functionality for Average panel
            const patternFilterInputAvg = document.getElementById('patternFilterInputAvg');
            const clearFilterBtnAvg = document.getElementById('clearFilterBtnAvg');

            if (patternFilterInputAvg) {{
                const filterPatternsAvg = function() {{
                    const filterText = patternFilterInputAvg.value.trim();
                    const patternItems = document.querySelectorAll('.pattern-item-avg');

                    if (clearFilterBtnAvg) {{
                        clearFilterBtnAvg.style.display = filterText ? 'block' : 'none';
                    }}

                    if (!filterText) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                        return;
                    }}

                    try {{
                        const regex = new RegExp(filterText, 'i');
                        patternItems.forEach(item => {{
                            const pattern = item.getAttribute('data-pattern') || '';
                            item.style.display = regex.test(pattern) ? '' : 'none';
                        }});
                    }} catch (e) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                    }}
                }};

                patternFilterInputAvg.addEventListener('input', filterPatternsAvg);
                patternFilterInputAvg.addEventListener('keyup', filterPatternsAvg);

                if (clearFilterBtnAvg) {{
                    clearFilterBtnAvg.addEventListener('click', function() {{
                        patternFilterInputAvg.value = '';
                        filterPatternsAvg();
                        patternFilterInputAvg.focus();
                    }});
                    clearFilterBtnAvg.addEventListener('mouseenter', function() {{ this.style.color = '#333'; }});
                    clearFilterBtnAvg.addEventListener('mouseleave', function() {{ this.style.color = '#999'; }});
                }}
            }}
        }}

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', () => setTimeout(initCheckboxes, 300));
        }} else {{
            setTimeout(initCheckboxes, 300);
        }}
    }})();
    </script>
    '''

    # Insert checkbox HTML, hover text display, and JavaScript before closing body tag
    if '</body>' in html_content:
        html_content = html_content.rsplit('</body>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_sum_html + checkbox_avg_html + hover_text_html + js_code + '</body>' + html_content[1]
    elif '</html>' in html_content:
        html_content = html_content.rsplit('</html>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_sum_html + checkbox_avg_html + hover_text_html + js_code + '</html>' + html_content[1]
    else:
        html_content += checkbox_sum_html + checkbox_avg_html + hover_text_html + js_code

    # Write modified HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Received bytes visualization saved to {output_file}")

    return {
        'filePath': str(output_file.resolve()),
        'totalTransactions': len(log_df),
        'topN': topN,
        'interval': interval,
        'patternsFile': patternsFile,
        'topNSum': top_patterns_sum,
        'topNAvg': top_patterns_avg
    }


# ============================================================================
# MCP Tool: generateSentBytesPerURI
# ============================================================================

def generateSentBytesPerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 10,
    interval: str = '10s',
    patternsFile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate Sent Bytes per URI time-series visualization with Sum and Average Top N.

    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        outputFormat (str): Output format ('html' only supported)
        topN (int): Number of top URI patterns to display (default: 10)
        interval (str): Time interval for aggregation (default: '10s').
                       Examples: '1s', '10s', '1min', '5min', '1h'
        patternsFile (str, optional): Path to JSON file containing URL patterns.
                                    If provided, uses these patterns for visualization.
                                    If not provided, extracts top N patterns and saves to file.

    Returns:
        dict: {
            'filePath': str (sentbytes_*.html),
            'totalTransactions': int,
            'patternsFile': str (path to saved patterns file),
            'topNSum': list (top N URIs by sum),
            'topNAvg': list (top N URIs by average)
        }
    """
    if outputFormat != 'html':
        raise ValidationError('outputFormat', "Only 'html' output format is currently supported")

    # Normalize interval parameter to pandas-compatible format
    interval = _normalize_interval(interval)

    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)

    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)

    if log_df.empty:
        raise ValueError("No data to visualize")

    # Get field mappings using FieldMapper
    time_field = FieldMapper.find_field(log_df, 'time', format_info)
    url_field = FieldMapper.find_field(log_df, 'url', format_info)

    # For bytes field, provide possible alternative names for SENT bytes
    possible_bytes_fields = ['sent_bytes', 'bytes_sent', 'body_bytes_sent',
                             'response_size', 'bytes', 'size']
    bytes_field = FieldMapper.find_field(log_df, 'sentBytes', format_info,
                                         possible_names=possible_bytes_fields)

    # Validate required fields
    if not time_field or time_field not in log_df.columns:
        raise ValueError(f"Time field not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    if not url_field or url_field not in log_df.columns:
        raise ValueError(f"URL field not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    if not bytes_field or bytes_field not in log_df.columns:
        raise ValueError(f"Sent bytes field not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")

    # Convert types
    log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    log_df[bytes_field] = pd.to_numeric(log_df[bytes_field], errors='coerce')
    log_df = log_df.dropna(subset=[time_field, bytes_field])

    # Determine input path for output file location
    input_path = Path(inputFile)

    # Load patterns from file if provided first (to use pattern rules for generalization)
    patterns_file_for_generalize = None
    top_patterns = None

    if patternsFile and os.path.exists(patternsFile):
        # Load patterns from file
        try:
            with open(patternsFile, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)

            # Extract pattern rules from file
            if isinstance(patterns_data, dict):
                if 'patternRules' in patterns_data and isinstance(patterns_data['patternRules'], list):
                    patterns_file_for_generalize = patternsFile
                    # Extract replacement values from patternRules as top_patterns
                    top_patterns = [rule.get('replacement', '') for rule in patterns_data['patternRules'] if isinstance(rule, dict) and 'replacement' in rule]
                    top_patterns = [p for p in top_patterns if p]  # Remove empty strings
                    logger.info(f"Using pattern rules from {patternsFile} for URL generalization")
                    logger.info(f"Loaded {len(top_patterns)} patterns from patternRules")
                else:
                    # Fallback for old format (backward compatibility)
                    if 'patterns' in patterns_data:
                        top_patterns = patterns_data['patterns']
                        patterns_file_for_generalize = patternsFile
                        logger.info(f"Using patterns from {patternsFile} (will be converted to rules)")
                    elif 'urls' in patterns_data:
                        top_patterns = patterns_data['urls']
                        patterns_file_for_generalize = patternsFile
                        logger.info(f"Using URLs from {patternsFile} (will be converted to rules)")
                    else:
                        raise ValueError(f"No patternRules, patterns, or urls found in {patternsFile}")
            else:
                raise ValueError(f"Unexpected patterns file format: {type(patterns_data)}")

            # Ensure patterns are strings and unique
            top_patterns = list(set([str(p) for p in top_patterns if p]))

        except Exception as e:
            logger.warning(f"Could not load patterns file {patternsFile}: {e}")
            logger.info(f"Falling back to extracting top {topN} patterns")
            patternsFile = None
            top_patterns = None

    # Generalize URLs (remove IDs) using pattern file if available
    from data_processor import _generalize_url
    log_df['url_pattern'] = log_df[url_field].apply(
        lambda x: _generalize_url(x, patterns_file_for_generalize) if pd.notna(x) else 'Unknown'
    )

    # Group by time interval and URL pattern
    log_df['time_bucket'] = log_df[time_field].dt.floor(interval)

    # Calculate sum and average for each time bucket and URL pattern
    bytes_stats = log_df.groupby(['time_bucket', 'url_pattern'])[bytes_field].agg(['sum', 'mean']).reset_index()
    bytes_stats.columns = ['time_bucket', 'url_pattern', 'sum_bytes', 'avg_bytes']

    # If patterns were not loaded from file, extract top N by sum
    if not patternsFile or not os.path.exists(patternsFile):
        # Get top N URL patterns by total sum of bytes
        pattern_total_sum = bytes_stats.groupby('url_pattern')['sum_bytes'].sum().sort_values(ascending=False)
        top_patterns = pattern_total_sum.head(topN).index.tolist()

        # Generate pattern rules from patterns
        pattern_rules = []
        for pattern in top_patterns:
            # Convert pattern with * wildcards to regex
            temp_pattern = pattern.replace('*', '__WILDCARD__')
            escaped_pattern = re.escape(temp_pattern)
            regex_pattern = escaped_pattern.replace('__WILDCARD__', '.*')

            pattern_rules.append({
                'pattern': f'^{regex_pattern}$',
                'replacement': pattern
            })

        # Save patterns to file with pattern rules only
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        patterns_file_path = input_path.parent / f"patterns_{timestamp}.json"

        patterns_data = {
            'patternRules': pattern_rules,
            'totalPatterns': len(top_patterns),
            'extractedAt': datetime.now().isoformat(),
            'sourceFile': str(inputFile),
            'topN': topN,
            'criteria': 'sum_sent_bytes'
        }

        with open(patterns_file_path, 'w', encoding='utf-8') as f:
            json.dump(patterns_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Extracted top {len(top_patterns)} patterns and saved to {patterns_file_path}")
        patternsFile = str(patterns_file_path)

    # Filter data to only include top patterns
    bytes_stats_filtered = bytes_stats[bytes_stats['url_pattern'].isin(top_patterns)].copy()

    # Get top N by sum
    pattern_sum = bytes_stats_filtered.groupby('url_pattern')['sum_bytes'].sum().sort_values(ascending=False)
    top_patterns_sum = pattern_sum.head(topN).index.tolist()

    # Get top N by average
    pattern_avg = bytes_stats_filtered.groupby('url_pattern')['avg_bytes'].mean().sort_values(ascending=False)
    top_patterns_avg = pattern_avg.head(topN).index.tolist()

    # Create pivot tables for sum and average
    pivot_sum = bytes_stats_filtered[bytes_stats_filtered['url_pattern'].isin(top_patterns_sum)].pivot_table(
        index='time_bucket',
        columns='url_pattern',
        values='sum_bytes',
        fill_value=0
    )

    pivot_avg = bytes_stats_filtered[bytes_stats_filtered['url_pattern'].isin(top_patterns_avg)].pivot_table(
        index='time_bucket',
        columns='url_pattern',
        values='avg_bytes',
        fill_value=0
    )

    # Sort columns by total sum/avg (descending)
    if len(pivot_sum.columns) > 0:
        pivot_sum = pivot_sum[pattern_sum.head(topN).index]
    if len(pivot_avg.columns) > 0:
        pivot_avg = pivot_avg[pattern_avg.head(topN).index]

    # Create subplots with two charts
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            f'Sent Bytes Sum per URI Pattern (Top {topN}, Interval: {interval})',
            f'Sent Bytes Average per URI Pattern (Top {topN}, Interval: {interval})'
        ),
        vertical_spacing=0.15
    )

    # Plotly's default color palette
    plotly_default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
    ]

    # Add Sum Top N traces
    for i, pattern in enumerate(pivot_sum.columns):
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        fig.add_trace(
            go.Scattergl(
                x=pivot_sum.index,
                y=pivot_sum[pattern],
                mode='lines+markers',
                name=pattern,
                line=dict(width=2, color=trace_color),
                marker=dict(size=4, color=trace_color),
                legendgroup='sum',
                showlegend=True,
                hovertemplate=f'Sum: %{{y:,.0f}} bytes<br>Pattern: {pattern}<extra></extra>'
            ),
            row=1, col=1
        )

    # Add Average Top N traces
    for i, pattern in enumerate(pivot_avg.columns):
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        fig.add_trace(
            go.Scattergl(
                x=pivot_avg.index,
                y=pivot_avg[pattern],
                mode='lines+markers',
                name=pattern,
                line=dict(width=2, color=trace_color),
                marker=dict(size=4, color=trace_color),
                legendgroup='avg',
                showlegend=True,
                hovertemplate=f'Avg: %{{y:,.0f}} bytes<br>Pattern: {pattern}<extra></extra>'
            ),
            row=2, col=1
        )

    # Update layout - hide legend since we use checkboxes
    fig.update_layout(
        height=900,
        showlegend=False,  # Hide legend, use checkboxes instead
        title_text=f"Sent Bytes per URI Pattern Analysis",
        hovermode='x unified',
        margin=dict(r=280),  # Add right margin for checkbox panels
        dragmode='zoom'  # Enable box select zoom (both horizontal and vertical)
    )

    # Update axes with vertical zoom enabled
    fig.update_xaxes(title_text='Time', row=2, col=1)
    fig.update_yaxes(title_text='Sum Bytes', row=1, col=1, fixedrange=False)  # Allow vertical zoom
    fig.update_yaxes(title_text='Average Bytes', row=2, col=1, fixedrange=False)  # Allow vertical zoom

    # Add range slider for time navigation on bottom chart
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1h", step="hour", stepmode="backward"),
                dict(count=6, label="6h", step="hour", stepmode="backward"),
                dict(count=12, label="12h", step="hour", stepmode="backward"),
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(step="all")
            ])
        ),
        row=2, col=1
    )

    # Generate output file
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"sentbytes_{timestamp}.html"

    # Save as HTML with specific div_id
    plotly_div_id = f'plotly-div-{timestamp}'
    fig.write_html(str(output_file), include_plotlyjs='cdn', div_id=plotly_div_id)

    # Add checkbox controls and JavaScript for filtering
    # Read the generated HTML
    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract the actual div ID from HTML
    div_id_match = re.search(r'<div id="([^"]+)"[^>]*class="[^"]*plotly[^"]*"', html_content)
    actual_div_id = div_id_match.group(1) if div_id_match else plotly_div_id

    # Create checkbox HTML for Sum chart (top)
    checkbox_sum_html = '<div id="filterCheckboxPanelSum" style="position: fixed; right: 20px; top: 80px; width: 250px; max-height: 350px; overflow-y: auto; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); color: #444; font-family: \'Open Sans\', verdana, arial, sans-serif;">'
    checkbox_sum_html += '<div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">Sum Top N:</div>'
    checkbox_sum_html += '<div style="margin-bottom: 8px; position: relative;"><input type="text" id="patternFilterInputSum" placeholder="Regex filter..." style="width: 100%; padding: 4px 24px 4px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 11px; box-sizing: border-box;"><span id="clearFilterBtnSum" style="position: absolute; right: 6px; top: 50%; transform: translateY(-50%); cursor: pointer; font-size: 14px; color: #999; display: none;" title="Clear filter">×</span></div>'
    checkbox_sum_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkAllSum" checked> <strong>All</strong></label></div>'
    checkbox_sum_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkNoneSum"> <strong>None</strong></label></div>'
    checkbox_sum_html += '<hr style="margin: 8px 0;">'

    for i, pattern in enumerate(pivot_sum.columns):
        pattern_id = f'pattern_sum_{i}'
        pattern_display = pattern[:50] + ('...' if len(pattern) > 50 else '')
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        checkbox_sum_html += f'<div class="pattern-item-sum" style="margin-bottom: 3px; font-size: 11px;" data-pattern="{pattern}"><label><input type="checkbox" class="pattern-checkbox-sum" id="{pattern_id}" data-index="{i}" checked> <span style="color: {trace_color}; font-weight: bold;">{pattern_display}</span></label></div>'

    checkbox_sum_html += '</div>'

    # Create checkbox HTML for Average chart (bottom)
    checkbox_avg_html = '<div id="filterCheckboxPanelAvg" style="position: fixed; right: 20px; top: 460px; width: 250px; max-height: 350px; overflow-y: auto; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); color: #444; font-family: \'Open Sans\', verdana, arial, sans-serif;">'
    checkbox_avg_html += '<div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">Average Top N:</div>'
    checkbox_avg_html += '<div style="margin-bottom: 8px; position: relative;"><input type="text" id="patternFilterInputAvg" placeholder="Regex filter..." style="width: 100%; padding: 4px 24px 4px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 11px; box-sizing: border-box;"><span id="clearFilterBtnAvg" style="position: absolute; right: 6px; top: 50%; transform: translateY(-50%); cursor: pointer; font-size: 14px; color: #999; display: none;" title="Clear filter">×</span></div>'
    checkbox_avg_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkAllAvg" checked> <strong>All</strong></label></div>'
    checkbox_avg_html += f'<div style="margin-bottom: 5px;"><label style="color: #444;"><input type="checkbox" id="checkNoneAvg"> <strong>None</strong></label></div>'
    checkbox_avg_html += '<hr style="margin: 8px 0;">'

    for i, pattern in enumerate(pivot_avg.columns):
        pattern_id = f'pattern_avg_{i}'
        pattern_display = pattern[:50] + ('...' if len(pattern) > 50 else '')
        trace_color = plotly_default_colors[i % len(plotly_default_colors)]
        checkbox_avg_html += f'<div class="pattern-item-avg" style="margin-bottom: 3px; font-size: 11px;" data-pattern="{pattern}"><label><input type="checkbox" class="pattern-checkbox-avg" id="{pattern_id}" data-index="{i + len(pivot_sum.columns)}" checked> <span style="color: {trace_color}; font-weight: bold;">{pattern_display}</span></label></div>'

    checkbox_avg_html += '</div>'

    # Add hover text display area
    hover_text_html = '''
    <div id="hoverTextDisplay" style="position: fixed; bottom: 20px; right: 20px; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 5px; max-width: 300px; max-height: 150px; overflow-y: auto; display: none; z-index: 2000; box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-size: 12px; color: #444; font-family: 'Open Sans', verdana, arial, sans-serif; cursor: pointer;">
        <div style="font-weight: bold; margin-bottom: 5px;">Hover Info (Click to copy):</div>
        <div id="hoverTextContent" style="white-space: pre-wrap; word-break: break-word;"></div>
        <div style="margin-top: 5px; font-size: 10px; color: #666;">Click or press Ctrl+C to copy</div>
    </div>
    '''

    # JavaScript for checkbox functionality and hover text copy
    js_code = f'''
    <script>
    (function() {{
        let lastHoverText = '';
        const sumTraceCount = {len(pivot_sum.columns)};
        const avgTraceCount = {len(pivot_avg.columns)};

        function copyToClipboard(text) {{
            const hoverTextContent = document.getElementById('hoverTextContent');
            if (!hoverTextContent) return;

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => {{
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{ hoverTextContent.innerHTML = originalContent; }}, 1000);
                }}).catch(() => {{ fallbackCopy(text); }});
            }} else {{
                fallbackCopy(text);
            }}
        }}

        function fallbackCopy(text) {{
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {{
                document.execCommand('copy');
                const hoverTextContent = document.getElementById('hoverTextContent');
                if (hoverTextContent) {{
                    const originalContent = hoverTextContent.innerHTML;
                    hoverTextContent.innerHTML = originalContent + '<br><span style="color: green;">✓ Copied!</span>';
                    setTimeout(() => {{ hoverTextContent.innerHTML = originalContent; }}, 1000);
                }}
            }} catch (err) {{ console.error('Copy failed:', err); }}
            document.body.removeChild(textArea);
        }}

        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'c' && lastHoverText) {{
                const hoverTextDisplay = document.getElementById('hoverTextDisplay');
                if (hoverTextDisplay && hoverTextDisplay.style.display !== 'none') {{
                    e.preventDefault();
                    copyToClipboard(lastHoverText);
                }}
            }}
        }});

        function initCheckboxes() {{
            const plotlyDiv = document.getElementById("{actual_div_id}") ||
                             document.querySelector('.js-plotly-plot') ||
                             document.querySelector('.plotly');

            if (!plotlyDiv || !window.Plotly) {{
                setTimeout(initCheckboxes, 100);
                return;
            }}

            // Setup hover event
            plotlyDiv.on('plotly_hover', function(data) {{
                if (data && data.points && data.points.length > 0) {{
                    const pointInfo = data.points.map(pt => {{
                        const count = pt.y !== undefined ? pt.y : 0;
                        const traceName = pt.data?.name || pt.fullData?.name || 'Unknown';
                        return {{ count: count, pattern: traceName }};
                    }});

                    pointInfo.sort((a, b) => b.count - a.count);

                    let displayText = '';
                    pointInfo.forEach((info, index) => {{
                        if (index > 0) displayText += '\\n';
                        displayText += `Count: ${{info.count.toLocaleString()}}, Pattern: ${{info.pattern}}`;
                    }});

                    lastHoverText = displayText;

                    const hoverTextContent = document.getElementById('hoverTextContent');
                    const hoverTextDisplay = document.getElementById('hoverTextDisplay');
                    if (hoverTextContent && hoverTextDisplay) {{
                        hoverTextContent.textContent = displayText;
                        hoverTextDisplay.style.display = 'block';
                    }}
                }}
            }});

            // Click to copy
            const hoverTextDisplay = document.getElementById('hoverTextDisplay');
            if (hoverTextDisplay) {{
                hoverTextDisplay.addEventListener('click', function() {{
                    if (lastHoverText) copyToClipboard(lastHoverText);
                }});
            }}

            // Checkbox handlers for Sum chart
            const checkAllSum = document.getElementById('checkAllSum');
            const checkNoneSum = document.getElementById('checkNoneSum');
            const checkboxesSum = document.querySelectorAll('.pattern-checkbox-sum');

            // Checkbox handlers for Average chart
            const checkAllAvg = document.getElementById('checkAllAvg');
            const checkNoneAvg = document.getElementById('checkNoneAvg');
            const checkboxesAvg = document.querySelectorAll('.pattern-checkbox-avg');

            function updateVisibility() {{
                const visible = [];

                // Sum traces
                checkboxesSum.forEach(cb => visible.push(cb.checked));
                // Average traces
                checkboxesAvg.forEach(cb => visible.push(cb.checked));

                try {{
                    Plotly.restyle(plotlyDiv, {{ visible: visible }},
                                  Array.from({{length: visible.length}}, (_, i) => i));
                }} catch (e) {{
                    console.error('Error updating visibility:', e);
                }}
            }}

            // Sum chart controls
            checkAllSum.addEventListener('change', function() {{
                if (this.checked) {{
                    checkNoneSum.checked = false;
                    // Only check visible items (filtered items)
                    checkboxesSum.forEach(cb => {{
                        const item = cb.closest('.pattern-item-sum');
                        if (item && item.style.display !== 'none') {{
                            cb.checked = true;
                        }}
                    }});
                    updateVisibility();
                }}
            }});

            checkNoneSum.addEventListener('change', function() {{
                if (this.checked) {{
                    checkAllSum.checked = false;
                    checkboxesSum.forEach(cb => cb.checked = false);
                    updateVisibility();
                }}
            }});

            checkboxesSum.forEach(cb => {{
                cb.addEventListener('change', function() {{
                    if (this.checked) checkNoneSum.checked = false;
                    // Check if all visible items are checked
                    const visibleCheckboxes = Array.from(checkboxesSum).filter(c => {{
                        const item = c.closest('.pattern-item-sum');
                        return item && item.style.display !== 'none';
                    }});
                    const allVisibleChecked = visibleCheckboxes.length > 0 && visibleCheckboxes.every(c => c.checked);
                    checkAllSum.checked = allVisibleChecked;
                    updateVisibility();
                }});
            }});

            // Average chart controls
            checkAllAvg.addEventListener('change', function() {{
                if (this.checked) {{
                    checkNoneAvg.checked = false;
                    // Only check visible items (filtered items)
                    checkboxesAvg.forEach(cb => {{
                        const item = cb.closest('.pattern-item-avg');
                        if (item && item.style.display !== 'none') {{
                            cb.checked = true;
                        }}
                    }});
                    updateVisibility();
                }}
            }});

            checkNoneAvg.addEventListener('change', function() {{
                if (this.checked) {{
                    checkAllAvg.checked = false;
                    checkboxesAvg.forEach(cb => cb.checked = false);
                    updateVisibility();
                }}
            }});

            checkboxesAvg.forEach(cb => {{
                cb.addEventListener('change', function() {{
                    if (this.checked) checkNoneAvg.checked = false;
                    // Check if all visible items are checked
                    const visibleCheckboxes = Array.from(checkboxesAvg).filter(c => {{
                        const item = c.closest('.pattern-item-avg');
                        return item && item.style.display !== 'none';
                    }});
                    const allVisibleChecked = visibleCheckboxes.length > 0 && visibleCheckboxes.every(c => c.checked);
                    checkAllAvg.checked = allVisibleChecked;
                    updateVisibility();
                }});
            }});

            // Pattern filter functionality for Sum panel
            const patternFilterInputSum = document.getElementById('patternFilterInputSum');
            const clearFilterBtnSum = document.getElementById('clearFilterBtnSum');

            if (patternFilterInputSum) {{
                const filterPatternsSum = function() {{
                    const filterText = patternFilterInputSum.value.trim();
                    const patternItems = document.querySelectorAll('.pattern-item-sum');

                    if (clearFilterBtnSum) {{
                        clearFilterBtnSum.style.display = filterText ? 'block' : 'none';
                    }}

                    if (!filterText) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                        return;
                    }}

                    try {{
                        const regex = new RegExp(filterText, 'i');
                        patternItems.forEach(item => {{
                            const pattern = item.getAttribute('data-pattern') || '';
                            item.style.display = regex.test(pattern) ? '' : 'none';
                        }});
                    }} catch (e) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                    }}
                }};

                patternFilterInputSum.addEventListener('input', filterPatternsSum);
                patternFilterInputSum.addEventListener('keyup', filterPatternsSum);

                if (clearFilterBtnSum) {{
                    clearFilterBtnSum.addEventListener('click', function() {{
                        patternFilterInputSum.value = '';
                        filterPatternsSum();
                        patternFilterInputSum.focus();
                    }});
                    clearFilterBtnSum.addEventListener('mouseenter', function() {{ this.style.color = '#333'; }});
                    clearFilterBtnSum.addEventListener('mouseleave', function() {{ this.style.color = '#999'; }});
                }}
            }}

            // Pattern filter functionality for Average panel
            const patternFilterInputAvg = document.getElementById('patternFilterInputAvg');
            const clearFilterBtnAvg = document.getElementById('clearFilterBtnAvg');

            if (patternFilterInputAvg) {{
                const filterPatternsAvg = function() {{
                    const filterText = patternFilterInputAvg.value.trim();
                    const patternItems = document.querySelectorAll('.pattern-item-avg');

                    if (clearFilterBtnAvg) {{
                        clearFilterBtnAvg.style.display = filterText ? 'block' : 'none';
                    }}

                    if (!filterText) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                        return;
                    }}

                    try {{
                        const regex = new RegExp(filterText, 'i');
                        patternItems.forEach(item => {{
                            const pattern = item.getAttribute('data-pattern') || '';
                            item.style.display = regex.test(pattern) ? '' : 'none';
                        }});
                    }} catch (e) {{
                        patternItems.forEach(item => {{ item.style.display = ''; }});
                    }}
                }};

                patternFilterInputAvg.addEventListener('input', filterPatternsAvg);
                patternFilterInputAvg.addEventListener('keyup', filterPatternsAvg);

                if (clearFilterBtnAvg) {{
                    clearFilterBtnAvg.addEventListener('click', function() {{
                        patternFilterInputAvg.value = '';
                        filterPatternsAvg();
                        patternFilterInputAvg.focus();
                    }});
                    clearFilterBtnAvg.addEventListener('mouseenter', function() {{ this.style.color = '#333'; }});
                    clearFilterBtnAvg.addEventListener('mouseleave', function() {{ this.style.color = '#999'; }});
                }}
            }}
        }}

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', () => setTimeout(initCheckboxes, 300));
        }} else {{
            setTimeout(initCheckboxes, 300);
        }}
    }})();
    </script>
    '''

    # Insert checkbox HTML, hover text display, and JavaScript before closing body tag
    if '</body>' in html_content:
        html_content = html_content.rsplit('</body>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_sum_html + checkbox_avg_html + hover_text_html + js_code + '</body>' + html_content[1]
    elif '</html>' in html_content:
        html_content = html_content.rsplit('</html>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_sum_html + checkbox_avg_html + hover_text_html + js_code + '</html>' + html_content[1]
    else:
        html_content += checkbox_sum_html + checkbox_avg_html + hover_text_html + js_code

    # Write modified HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Sent bytes visualization saved to {output_file}")

    return {
        'filePath': str(output_file.resolve()),
        'totalTransactions': len(log_df),
        'topN': topN,
        'interval': interval,
        'patternsFile': patternsFile,
        'topNSum': top_patterns_sum,
        'topNAvg': top_patterns_avg
    }


# ============================================================================
# Additional Visualization Functions
# ============================================================================

def generateMultiMetricDashboard(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html'
) -> Dict[str, Any]:
    """
    Generate a comprehensive dashboard with multiple metrics.
    
    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        outputFormat (str): Output format ('html' only supported)
        
    Returns:
        dict: {
            'filePath': str (dashboard_*.html),
            'totalTransactions': int
        }
    """
    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)
    
    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)
    
    if log_df.empty:
        raise ValueError("No data to visualize")
    
    # Get field mappings
    time_field = format_info['fieldMap'].get('timestamp', 'time')
    status_field = format_info['fieldMap'].get('status', 'elb_status_code')
    rt_field = format_info['fieldMap'].get('responseTime', 'target_processing_time')
    
    # Debug: Check available columns in DataFrame (for ALB parsing)
    if format_info.get('patternType') == 'ALB':
        available_columns = list(log_df.columns)
        print(f"  Available columns in DataFrame: {len(available_columns)} columns")
        
        # If fields are not found, try to find them
        if time_field not in available_columns:
            possible_time_fields = ['time', 'timestamp', '@timestamp', 'datetime']
            for field in possible_time_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as time field (instead of '{time_field}')")
                    time_field = field
                    break
        
        if status_field not in available_columns:
            possible_status_fields = ['elb_status_code', 'status_code', 'status', 'http_status']
            for field in possible_status_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as status field (instead of '{status_field}')")
                    status_field = field
                    break
        
        if rt_field not in available_columns:
            possible_rt_fields = ['target_processing_time', 'response_time', 'duration', 'elapsed']
            for field in possible_rt_fields:
                if field in available_columns:
                    print(f"  Using '{field}' as response time field (instead of '{rt_field}')")
                    rt_field = field
                    break
    
    # Check if required fields exist
    if time_field not in log_df.columns:
        raise ValueError(f"Time field '{time_field}' not found in DataFrame. Available columns: {list(log_df.columns)[:10]}...")
    
    # Convert types
    log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    log_df = log_df.dropna(subset=[time_field])
    
    if rt_field in log_df.columns:
        log_df[rt_field] = pd.to_numeric(log_df[rt_field], errors='coerce')
    else:
        print(f"  Warning: Response time field '{rt_field}' not found")
        rt_field = None
    
    if status_field in log_df.columns:
        log_df[status_field] = pd.to_numeric(log_df[status_field], errors='coerce')
    else:
        print(f"  Warning: Status field '{status_field}' not found")
        status_field = None
    
    # Convert response time to milliseconds if needed
    if rt_field and rt_field in log_df.columns:
        rt_unit = format_info.get('responseTimeUnit', 'ms')
    if rt_unit == 's':
        log_df[rt_field] = log_df[rt_field] * 1000
    elif rt_unit == 'us':
        log_df[rt_field] = log_df[rt_field] / 1000
    elif rt_unit == 'ns':
        log_df[rt_field] = log_df[rt_field] / 1000000
    
    # Group by minute
    log_df['time_bucket'] = log_df[time_field].dt.floor('1T')
    time_groups = log_df.groupby('time_bucket')
    
    # Aggregate metrics
    metrics = []
    for time_bucket, group in time_groups:
        metric = {
            'time': time_bucket,
            'request_count': len(group),
            'avg_response_time': group[rt_field].mean() if rt_field and rt_field in group.columns else 0,
            'error_count': (group[status_field] >= 400).sum() if status_field and status_field in group.columns else 0,
            'error_rate': (group[status_field] >= 400).mean() * 100 if status_field and status_field in group.columns else 0
        }
        metrics.append(metric)
    
    metrics_df = pd.DataFrame(metrics)
    
    # Create subplot dashboard
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Request Count per Minute', 'Average Response Time', 'Error Rate (%)'),
        vertical_spacing=0.1
    )
    
    # Request count (use Scattergl for better performance)
    fig.add_trace(
        go.Scattergl(x=metrics_df['time'], y=metrics_df['request_count'], 
                     mode='lines', name='Request Count', line=dict(color='blue', width=2)),
        row=1, col=1
    )
    
    # Response time
    fig.add_trace(
        go.Scattergl(x=metrics_df['time'], y=metrics_df['avg_response_time'], 
                     mode='lines', name='Avg Response Time (ms)', line=dict(color='orange', width=2)),
        row=2, col=1
    )
    
    # Error rate
    fig.add_trace(
        go.Scattergl(x=metrics_df['time'], y=metrics_df['error_rate'], 
                     mode='lines', name='Error Rate (%)', line=dict(color='red', width=2)),
        row=3, col=1
    )
    
    # Update layout with vertical zoom support
    fig.update_layout(
        height=900,
        showlegend=True,
        title_text="Access Log Dashboard",
        legend=dict(
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            orientation="v"
        ),
        dragmode='zoom'  # Enable box select zoom (both horizontal and vertical)
    )

    # Enable vertical zoom for all y-axes
    fig.update_yaxes(fixedrange=False, row=1, col=1)
    fig.update_yaxes(fixedrange=False, row=2, col=1)
    fig.update_yaxes(fixedrange=False, row=3, col=1)

    # Generate output file
    input_path = Path(inputFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"dashboard_{timestamp}.html"

    # Save as HTML
    fig.write_html(str(output_file), include_plotlyjs='cdn')

    return {
        'filePath': str(output_file.resolve()),
        'totalTransactions': len(log_df)
    }


# ============================================================================
# Legacy Function: visualize_data (for main.py)
# ============================================================================

def visualize_data(time_series_data):
    """
    Visualize aggregated time-series data (legacy function for main.py).
    
    Args:
        time_series_data (pandas.DataFrame): Aggregated time-series DataFrame
    """
    if time_series_data.empty:
        print("No data to visualize")
        return
    
    # Create subplot dashboard
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Request Count per Minute', 'Average Response Time (ms)', 'Error Rate (%)'),
        vertical_spacing=0.1
    )
    
    # Request count
    if 'time' in time_series_data.columns and 'request_count' in time_series_data.columns:
        fig.add_trace(
            go.Scattergl(
                x=time_series_data['time'],
                y=time_series_data['request_count'],
                mode='lines',
                name='Request Count',
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )
    
    # Response time
    if 'time' in time_series_data.columns and 'avg_response_time' in time_series_data.columns:
        fig.add_trace(
            go.Scattergl(
                x=time_series_data['time'],
                y=time_series_data['avg_response_time'],
                mode='lines',
                name='Avg Response Time (ms)',
                line=dict(color='orange', width=2)
            ),
            row=2, col=1
        )
    
    # Error rate
    if 'time' in time_series_data.columns and 'error_rate' in time_series_data.columns:
        fig.add_trace(
            go.Scattergl(
                x=time_series_data['time'],
                y=time_series_data['error_rate'],
                mode='lines',
                name='Error Rate (%)',
                line=dict(color='red', width=2)
            ),
            row=3, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=900,
        showlegend=True,
        title_text="Access Log Dashboard",
        legend=dict(
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            orientation="v"
        )
    )
    
    # Update axes labels
    fig.update_xaxes(title_text="Time", row=3, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Response Time (ms)", row=2, col=1)
    fig.update_yaxes(title_text="Error Rate (%)", row=3, col=1)
    
    # Generate output file
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = f"dashboard_{timestamp}.html"
    
    # Save as HTML
    fig.write_html(output_file, include_plotlyjs='cdn')
    print(f"Dashboard saved to {output_file}")


# ============================================================================
# Pivot Visualization Functions
# ============================================================================

def generate_pivot_chart(
    pivot_df: pd.DataFrame,
    output_file: Path,
    chart_type: str,
    title: str = "Pivot Analysis",
    row_field: str = "row",
    column_field: str = "column",
    value_field: str = "value",
    agg_func: str = "count"
) -> None:
    """
    Generate interactive pivot chart visualization.

    Args:
        pivot_df: Pivot table DataFrame (rows x columns)
        output_file: Output file path
        chart_type: Chart type ('line', 'bar', 'heatmap', 'area', 'stacked_bar', 'stacked_area', 'facet')
        title: Chart title
        row_field: Row field name (for display)
        column_field: Column field name (for display)
        value_field: Value field name (for display)
        agg_func: Aggregation function name (for display)
    """
    logger.info(f"Generating {chart_type} chart for pivot data: {len(pivot_df)} rows x {len(pivot_df.columns)} columns")

    if chart_type == 'line':
        fig = _create_pivot_line_chart(pivot_df, title, row_field, column_field, value_field, agg_func)
    elif chart_type == 'bar':
        fig = _create_pivot_bar_chart(pivot_df, title, row_field, column_field, value_field, agg_func)
    elif chart_type == 'heatmap':
        fig = _create_pivot_heatmap(pivot_df, title, row_field, column_field, value_field, agg_func)
    elif chart_type == 'area':
        fig = _create_pivot_area_chart(pivot_df, title, row_field, column_field, value_field, agg_func)
    elif chart_type == 'stacked_bar':
        fig = _create_pivot_stacked_bar_chart(pivot_df, title, row_field, column_field, value_field, agg_func)
    elif chart_type == 'stacked_area':
        fig = _create_pivot_stacked_area_chart(pivot_df, title, row_field, column_field, value_field, agg_func)
    elif chart_type == 'facet':
        fig = _create_pivot_facet_chart(pivot_df, title, row_field, column_field, value_field, agg_func)
    else:
        raise ValueError(f"Unknown chart type: {chart_type}")

    # Save as HTML with CDN
    fig.write_html(str(output_file), include_plotlyjs='cdn')
    logger.info(f"Pivot chart saved to {output_file}")


def _create_pivot_line_chart(pivot_df, title, row_field, column_field, value_field, agg_func):
    """Create line chart from pivot table"""
    fig = go.Figure()

    # Each row becomes a line
    for idx, row in pivot_df.iterrows():
        fig.add_trace(go.Scatter(
            x=pivot_df.columns,
            y=row.values,
            mode='lines+markers',
            name=str(idx),
            hovertemplate=f'{row_field}: {idx}<br>{column_field}: %{{x}}<br>{agg_func}({value_field}): %{{y}}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title=column_field,
        yaxis_title=f'{agg_func}({value_field})',
        hovermode='x unified',
        height=600,
        showlegend=True
    )

    return fig


def _create_pivot_bar_chart(pivot_df, title, row_field, column_field, value_field, agg_func):
    """Create bar chart from pivot table"""
    fig = go.Figure()

    # Each row becomes a bar group
    for idx, row in pivot_df.iterrows():
        fig.add_trace(go.Bar(
            x=pivot_df.columns,
            y=row.values,
            name=str(idx),
            hovertemplate=f'{row_field}: {idx}<br>{column_field}: %{{x}}<br>{agg_func}({value_field}): %{{y}}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title=column_field,
        yaxis_title=f'{agg_func}({value_field})',
        barmode='group',
        height=600,
        showlegend=True
    )

    return fig


def _create_pivot_heatmap(pivot_df, title, row_field, column_field, value_field, agg_func):
    """Create heatmap from pivot table"""
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='Viridis',
        hovertemplate=f'{row_field}: %{{y}}<br>{column_field}: %{{x}}<br>{agg_func}({value_field}): %{{z}}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        xaxis_title=column_field,
        yaxis_title=row_field,
        height=max(600, len(pivot_df) * 20),  # Dynamic height based on rows
        showlegend=False
    )

    return fig


def _create_pivot_area_chart(pivot_df, title, row_field, column_field, value_field, agg_func):
    """Create area chart from pivot table"""
    fig = go.Figure()

    # Each row becomes an area
    for idx, row in pivot_df.iterrows():
        fig.add_trace(go.Scatter(
            x=pivot_df.columns,
            y=row.values,
            mode='lines',
            name=str(idx),
            fill='tonexty',
            hovertemplate=f'{row_field}: {idx}<br>{column_field}: %{{x}}<br>{agg_func}({value_field}): %{{y}}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title=column_field,
        yaxis_title=f'{agg_func}({value_field})',
        hovermode='x unified',
        height=600,
        showlegend=True
    )

    return fig


def _create_pivot_stacked_bar_chart(pivot_df, title, row_field, column_field, value_field, agg_func):
    """Create stacked bar chart from pivot table"""
    fig = go.Figure()

    # Each row becomes a stacked bar
    for idx, row in pivot_df.iterrows():
        fig.add_trace(go.Bar(
            x=pivot_df.columns,
            y=row.values,
            name=str(idx),
            hovertemplate=f'{row_field}: {idx}<br>{column_field}: %{{x}}<br>{agg_func}({value_field}): %{{y}}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title=column_field,
        yaxis_title=f'{agg_func}({value_field})',
        barmode='stack',
        height=600,
        showlegend=True
    )

    return fig


def _create_pivot_stacked_area_chart(pivot_df, title, row_field, column_field, value_field, agg_func):
    """Create stacked area chart from pivot table"""
    fig = go.Figure()

    # Each row becomes a stacked area
    for idx, row in pivot_df.iterrows():
        fig.add_trace(go.Scatter(
            x=pivot_df.columns,
            y=row.values,
            mode='lines',
            name=str(idx),
            stackgroup='one',
            hovertemplate=f'{row_field}: {idx}<br>{column_field}: %{{x}}<br>{agg_func}({value_field}): %{{y}}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title=column_field,
        yaxis_title=f'{agg_func}({value_field})',
        hovermode='x unified',
        height=600,
        showlegend=True
    )

    return fig


def _create_pivot_facet_chart(pivot_df, title, row_field, column_field, value_field, agg_func):
    """Create facet chart (small multiples) from pivot table"""
    # Calculate grid dimensions
    n_rows = len(pivot_df)
    n_cols = min(3, n_rows)  # Max 3 columns
    n_row_grid = (n_rows + n_cols - 1) // n_cols

    # Create subplots
    fig = make_subplots(
        rows=n_row_grid,
        cols=n_cols,
        subplot_titles=[str(idx) for idx in pivot_df.index],
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )

    # Add trace for each row
    for i, (idx, row) in enumerate(pivot_df.iterrows()):
        row_num = i // n_cols + 1
        col_num = i % n_cols + 1

        fig.add_trace(
            go.Scatter(
                x=pivot_df.columns,
                y=row.values,
                mode='lines+markers',
                name=str(idx),
                showlegend=False,
                hovertemplate=f'{column_field}: %{{x}}<br>{agg_func}({value_field}): %{{y}}<extra></extra>'
            ),
            row=row_num,
            col=col_num
        )

    fig.update_layout(
        title_text=title,
        height=300 * n_row_grid,
        showlegend=False
    )

    # Update all xaxes and yaxes
    for i in range(1, n_row_grid + 1):
        for j in range(1, n_cols + 1):
            fig.update_xaxes(title_text=column_field if i == n_row_grid else "", row=i, col=j)
            fig.update_yaxes(title_text=f'{agg_func}({value_field})' if j == 1 else "", row=i, col=j)

    return fig


# ============================================================================
# MCP Tool: generateProcessingTimePerURI
# ============================================================================

def generateProcessingTimePerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    processingTimeField: str = 'target_processing_time',
    metric: str = 'avg',
    topN: int = 10,
    interval: str = '1min',
    patternsFile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate Processing Time per URI time-series visualization.

    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        outputFormat (str): Output format ('html' only supported)
        processingTimeField (str): Processing time field to analyze
            - 'request_processing_time'
            - 'target_processing_time' (default)
            - 'response_processing_time'
        metric (str): Metric to calculate (default: 'avg')
            - 'avg': Average processing time
            - 'median': Median processing time
            - 'p95': 95th percentile
            - 'p99': 99th percentile
            - 'max': Maximum processing time
        topN (int): Number of top URI patterns to display (default: 10)
        interval (str): Time interval for aggregation (default: '1min').
                       Examples: '1s', '10s', '1min', '5min', '1h'
        patternsFile (str, optional): Path to JSON file containing URL patterns.
                                    If provided, uses these patterns for visualization.
                                    If not provided, extracts top N patterns by processing time.

    Returns:
        dict: {
            'filePath': str (proctime_*.html),
            'totalTransactions': int,
            'patternsFile': str (path to saved patterns file),
            'processingTimeField': str,
            'metric': str
        }
    """
    if outputFormat != 'html':
        raise ValueError("Only 'html' output format is currently supported")

    # Validate metric
    valid_metrics = ['avg', 'median', 'p95', 'p99', 'max']
    if metric not in valid_metrics:
        raise ValidationError('metric', f"Invalid metric: {metric}. Must be one of: {valid_metrics}")

    # Normalize interval parameter to pandas-compatible format
    interval = _normalize_interval(interval)

    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)

    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)

    if log_df.empty:
        raise ValueError("No data to visualize")

    # Get field mappings
    time_field = format_info['fieldMap'].get('timestamp', 'time')
    url_field = format_info['fieldMap'].get('url', 'request_url')

    # Check if processing time field exists
    if processingTimeField not in log_df.columns:
        raise ValueError(f"Processing time field '{processingTimeField}' not found in DataFrame. Available columns: {list(log_df.columns)[:20]}...")

    # Convert types
    log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    log_df[processingTimeField] = pd.to_numeric(log_df[processingTimeField], errors='coerce')
    log_df = log_df.dropna(subset=[time_field, processingTimeField])

    logger.info(f"Loaded {len(log_df)} records with valid {processingTimeField}")

    # Determine input path for output file location
    input_path = Path(inputFile)

    # Load patterns from file if provided
    patterns_file_for_generalize = None
    top_patterns = None

    if patternsFile and os.path.exists(patternsFile):
        # Load patterns from file
        try:
            with open(patternsFile, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)

            # Extract pattern rules from file
            if isinstance(patterns_data, dict):
                if 'patternRules' in patterns_data and isinstance(patterns_data['patternRules'], list):
                    patterns_file_for_generalize = patternsFile
                    # Extract replacement values from patternRules as top_patterns
                    top_patterns = [rule.get('replacement', '') for rule in patterns_data['patternRules'] if isinstance(rule, dict) and 'replacement' in rule]
                    top_patterns = [p for p in top_patterns if p]  # Remove empty strings
                    logger.info(f"Using pattern rules from {patternsFile} for URL generalization")
                    logger.info(f"Loaded {len(top_patterns)} patterns from patternRules")
                else:
                    # Fallback for old format
                    if 'patterns' in patterns_data:
                        top_patterns = patterns_data['patterns']
                        patterns_file_for_generalize = patternsFile
                    elif 'urls' in patterns_data:
                        top_patterns = patterns_data['urls']
                        patterns_file_for_generalize = patternsFile

            # Ensure patterns are strings and unique
            if top_patterns:
                top_patterns = list(set([str(p) for p in top_patterns if p]))

        except Exception as e:
            logger.warning(f"Could not load patterns file {patternsFile}: {e}")
            logger.warning(f"Falling back to extracting top {topN} patterns")
            patternsFile = None
            top_patterns = None

    # Generalize URLs
    from data_processor import _generalize_url
    log_df['url_pattern'] = log_df[url_field].apply(
        lambda x: _generalize_url(x, patterns_file_for_generalize) if pd.notna(x) else 'Unknown'
    )

    # Group by time interval and URL pattern
    log_df['time_bucket'] = log_df[time_field].dt.floor(interval)

    # If patterns were not loaded from file, extract top N by processing time
    if not patternsFile or not os.path.exists(patternsFile):
        # Get top N URL patterns by total processing time (sum)
        pattern_totals = log_df.groupby('url_pattern')[processingTimeField].sum().sort_values(ascending=False)
        top_patterns = pattern_totals.head(topN).index.tolist()

        logger.info(f"Extracted top {len(top_patterns)} patterns by {processingTimeField} sum")

        # Mark patterns not in top_patterns as "Others"
        log_df.loc[~log_df['url_pattern'].isin(top_patterns) & (log_df['url_pattern'] != 'Unknown'), 'url_pattern'] = 'Others'

        # Generate pattern rules from patterns
        pattern_rules = []
        for pattern in top_patterns:
            # Convert pattern with * wildcards to regex
            temp_pattern = pattern.replace('*', '__WILDCARD__')
            escaped_pattern = re.escape(temp_pattern)
            regex_pattern = escaped_pattern.replace('__WILDCARD__', '.*')

            pattern_rules.append({
                'pattern': f'^{regex_pattern}$',
                'replacement': pattern
            })

        # Save patterns to file
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        patterns_file_path = input_path.parent / f"patterns_proctime_{timestamp}.json"

        patterns_data = {
            'patternRules': pattern_rules,
            'totalPatterns': len(top_patterns),
            'extractedAt': datetime.now().isoformat(),
            'sourceFile': str(inputFile),
            'topN': topN,
            'sortedBy': f'{processingTimeField}_sum'
        }

        with open(patterns_file_path, 'w', encoding='utf-8') as f:
            json.dump(patterns_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved patterns to {patterns_file_path}")
        patternsFile = str(patterns_file_path)
    else:
        # Mark patterns not in top_patterns as "Others"
        if top_patterns:
            if patterns_file_for_generalize:
                generalized_top_patterns = [
                    _generalize_url(pattern, patterns_file_for_generalize)
                    for pattern in top_patterns
                ]
                top_patterns = list(set(generalized_top_patterns))

            log_df.loc[~log_df['url_pattern'].isin(top_patterns) & (log_df['url_pattern'] != 'Unknown'), 'url_pattern'] = 'Others'

    # Calculate metric for each time bucket and URL pattern
    if metric == 'avg':
        pivot = log_df.groupby(['time_bucket', 'url_pattern'])[processingTimeField].mean().unstack(fill_value=0)
        metric_label = 'Average'
    elif metric == 'median':
        pivot = log_df.groupby(['time_bucket', 'url_pattern'])[processingTimeField].median().unstack(fill_value=0)
        metric_label = 'Median'
    elif metric == 'p95':
        pivot = log_df.groupby(['time_bucket', 'url_pattern'])[processingTimeField].quantile(0.95).unstack(fill_value=0)
        metric_label = '95th Percentile'
    elif metric == 'p99':
        pivot = log_df.groupby(['time_bucket', 'url_pattern'])[processingTimeField].quantile(0.99).unstack(fill_value=0)
        metric_label = '99th Percentile'
    elif metric == 'max':
        pivot = log_df.groupby(['time_bucket', 'url_pattern'])[processingTimeField].max().unstack(fill_value=0)
        metric_label = 'Maximum'
    else:
        raise ValueError(f"Unknown metric: {metric}")

    # Create interactive line chart
    fig = go.Figure()

    # Plotly's default color palette
    plotly_default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
    ]

    # Get actual patterns from pivot (sorted by total, excluding "Others")
    pattern_totals = pivot.sum().sort_values(ascending=False)
    actual_patterns = [p for p in pattern_totals.index if p != 'Others'][:topN]

    # Add top patterns first
    for i, pattern in enumerate(actual_patterns):
        if pattern in pivot.columns:
            trace_color = plotly_default_colors[i % len(plotly_default_colors)]
            trace = go.Scattergl(
                x=pivot.index,
                y=pivot[pattern],
                mode='lines+markers',
                name=pattern,
                line=dict(width=2, color=trace_color),
                marker=dict(size=4, color=trace_color),
                hovertemplate=f'{metric_label}: %{{y:.4f}}s, Pattern: {pattern}<extra></extra>',
                visible=True
            )
            fig.add_trace(trace)

    # Add "Others" trace if it exists
    if 'Others' in pivot.columns:
        others_color = '#808080'  # Gray color for Others
        others_trace = go.Scattergl(
            x=pivot.index,
            y=pivot['Others'],
            mode='lines+markers',
            name='Others',
            line=dict(width=2, color=others_color),
            marker=dict(size=4, color=others_color),
            hovertemplate=f'{metric_label}: %{{y:.4f}}s, Pattern: Others<extra></extra>',
            visible=True
        )
        fig.add_trace(others_trace)

    # Collect trace names and colors for checkbox filter
    trace_names = []
    trace_colors = []
    for trace in fig.data:
        trace_names.append(trace.name)
        trace_colors.append(trace.line.color)

    # Update layout with checkbox filter enhancements
    field_display_name = processingTimeField.replace('_', ' ').title()
    fig.update_layout(
        title=f'{metric_label} {field_display_name} per URI Pattern (Top {topN}, Interval: {interval})',
        xaxis_title='Time',
        yaxis_title=f'{metric_label} {field_display_name} (seconds)',
        hovermode='x unified',
        height=600,
        showlegend=False,  # Use checkbox filter instead
        margin=dict(r=250),  # Add right margin for checkbox panel
        dragmode='zoom'  # Enable box select zoom (both horizontal and vertical)
    )

    # Add range slider for time navigation
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1h", step="hour", stepmode="backward"),
                dict(count=6, label="6h", step="hour", stepmode="backward"),
                dict(count=12, label="12h", step="hour", stepmode="backward"),
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(step="all")
            ])
        )
    )

    # Enable y-axis autorange and vertical zoom
    fig.update_yaxes(
        autorange=True,
        fixedrange=False  # Allow manual zoom on y-axis
    )

    # Generate output file
    timestamp_output = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"proctime_{processingTimeField}_{metric}_{timestamp_output}.html"

    # Save to HTML with plotly div ID
    plotly_div_id = f'plotly-div-{timestamp_output}'
    fig.write_html(
        str(output_file),
        include_plotlyjs='cdn',
        div_id=plotly_div_id,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'proctime_{processingTimeField}_{metric}',
                'height': 600,
                'width': 1200,
                'scale': 2
            }
        }
    )

    # Generate interactive enhancements (checkbox filter, hover text, vertical zoom)
    checkbox_html, hover_text_html, js_code = _generate_interactive_enhancements(
        patterns=trace_names,
        colors=trace_colors,
        div_id=plotly_div_id,
        filter_label="Filter URI Patterns:",
        hover_format="processing_time"
    )

    # Read the generated HTML and insert enhancements
    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract the actual div ID from HTML (Plotly may modify it)
    div_id_match = re.search(r'<div id="([^"]+)"[^>]*class="[^"]*plotly[^"]*"', html_content)
    actual_div_id = div_id_match.group(1) if div_id_match else plotly_div_id

    # Update js_code with actual div ID
    js_code = js_code.replace(f'"{plotly_div_id}"', f'"{actual_div_id}"')

    # Insert checkbox HTML, hover text display, and JavaScript before closing body tag
    inserted = False
    if '</body>' in html_content:
        html_content = html_content.rsplit('</body>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_html + hover_text_html + js_code + '</body>' + html_content[1]
            inserted = True

    # Fallback: Insert before </html>
    if not inserted and '</html>' in html_content:
        html_content = html_content.rsplit('</html>', 1)
        if len(html_content) == 2:
            html_content = html_content[0] + checkbox_html + hover_text_html + js_code + '</html>' + html_content[1]
            inserted = True

    # Fallback: Append at the end
    if not inserted:
        html_content += checkbox_html + hover_text_html + js_code

    # Write modified HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Processing time visualization saved to {output_file}")
    logger.info(f"  ✓ filterCheckboxPanel inserted for Processing Time chart")
    logger.info(f"  ✓ hoverTextDisplay inserted for Processing Time chart")

    # Return result
    return {
        'filePath': str(output_file.resolve()),
        'totalTransactions': len(log_df),
        'patternsFile': patternsFile,
        'patternsDisplayed': len(actual_patterns),
        'processingTimeField': processingTimeField,
        'metric': metric,
        'interval': interval,
        'topN': topN
    }


# Main function for testing
if __name__ == "__main__":
    print("Data Visualizer Module - MCP Tools")
    print("Available tools:")
    print("  - generateXlog(inputFile, logFormatFile, outputFormat)")
    print("  - generateRequestPerURI(inputFile, logFormatFile, outputFormat)")
    print("  - generateMultiMetricDashboard(inputFile, logFormatFile, outputFormat)")
    print("  - generateProcessingTimePerURI(inputFile, logFormatFile, outputFormat, ...)")
    print("  - generate_pivot_chart(pivot_df, output_file, chart_type, ...)")