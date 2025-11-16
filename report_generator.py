"""Report generation in multiple formats (text, JSON, CSV, HTML)."""
import csv
import json
from datetime import datetime, timezone
from typing import List, Any, Dict
import aiofiles
from jinja2 import Template


async def generate_text_report(results: List[Any], filename: str) -> None:
    """Generate text-based report."""
    report = "Ollama Monitor Report\n"
    report += "=====================\n"
    report += f"Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}\n\n"

    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            report += f"Endpoint {idx + 1}: An error occurred - {str(result)}\n"
        elif isinstance(result, tuple):
            response_time, status_code = result
            report += f"Endpoint {idx + 1}:\n"
            report += f"  Status Code: {status_code}\n"
            report += f"  Response Time: {response_time:.2f} seconds\n\n"
        else:
            report += f"Endpoint {idx + 1}: Unexpected result format\n"

    async with aiofiles.open(filename, mode="w") as f:
        await f.write(report)


async def generate_json_report(results: List[Any], endpoints: Dict[str, Any], filename: str) -> None:
    """Generate JSON report."""
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "summary": {
            "total_endpoints": len(results),
            "successful": sum(1 for r in results if isinstance(r, tuple) and r[1] == 200),
            "failed": sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, tuple) and r[1] != 200))
        },
        "endpoints": []
    }

    endpoint_names = list(endpoints.keys())
    for idx, result in enumerate(results):
        endpoint_name = endpoint_names[idx] if idx < len(endpoint_names) else f"endpoint_{idx + 1}"

        if isinstance(result, Exception):
            endpoint_data = {
                "name": endpoint_name,
                "status": "error",
                "error": str(result)
            }
        elif isinstance(result, tuple):
            response_time, status_code = result
            endpoint_data = {
                "name": endpoint_name,
                "status": "success" if status_code == 200 else "failed",
                "status_code": status_code,
                "response_time_seconds": round(response_time, 3)
            }
        else:
            endpoint_data = {
                "name": endpoint_name,
                "status": "unknown",
                "error": "Unexpected result format"
            }

        report_data["endpoints"].append(endpoint_data)

    async with aiofiles.open(filename, mode="w") as f:
        await f.write(json.dumps(report_data, indent=2))


async def generate_csv_report(results: List[Any], endpoints: Dict[str, Any], filename: str) -> None:
    """Generate CSV report."""
    endpoint_names = list(endpoints.keys())

    # Prepare data
    rows = []
    rows.append(["Endpoint", "Status", "Status Code", "Response Time (s)", "Error"])

    for idx, result in enumerate(results):
        endpoint_name = endpoint_names[idx] if idx < len(endpoint_names) else f"endpoint_{idx + 1}"

        if isinstance(result, Exception):
            rows.append([endpoint_name, "error", "-", "-", str(result)])
        elif isinstance(result, tuple):
            response_time, status_code = result
            status = "success" if status_code == 200 else "failed"
            rows.append([endpoint_name, status, status_code, f"{response_time:.3f}", "-"])
        else:
            rows.append([endpoint_name, "unknown", "-", "-", "Unexpected result format"])

    # Write CSV
    async with aiofiles.open(filename, mode="w", newline='') as f:
        content = ""
        for row in rows:
            content += ",".join(str(cell) for cell in row) + "\n"
        await f.write(content)


async def generate_html_report(results: List[Any], endpoints: Dict[str, Any], filename: str) -> None:
    """Generate HTML report with styling."""
    endpoint_names = list(endpoints.keys())

    # Prepare endpoint data
    endpoint_data = []
    successful = 0
    failed = 0

    for idx, result in enumerate(results):
        endpoint_name = endpoint_names[idx] if idx < len(endpoint_names) else f"endpoint_{idx + 1}"

        if isinstance(result, Exception):
            endpoint_data.append({
                "name": endpoint_name,
                "status": "error",
                "status_code": "-",
                "response_time": "-",
                "error": str(result),
                "status_class": "error"
            })
            failed += 1
        elif isinstance(result, tuple):
            response_time, status_code = result
            is_success = status_code == 200
            if is_success:
                successful += 1
            else:
                failed += 1

            endpoint_data.append({
                "name": endpoint_name,
                "status": "success" if is_success else "failed",
                "status_code": status_code,
                "response_time": f"{response_time:.3f}s",
                "error": "-",
                "status_class": "success" if is_success else "failed"
            })
        else:
            endpoint_data.append({
                "name": endpoint_name,
                "status": "unknown",
                "status_code": "-",
                "response_time": "-",
                "error": "Unexpected result format",
                "status_class": "error"
            })
            failed += 1

    # HTML template
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ollama Monitor Report</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 30px;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
            }
            .timestamp {
                color: #666;
                font-size: 14px;
                margin-bottom: 30px;
            }
            .summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .summary-card {
                padding: 20px;
                border-radius: 6px;
                background: #f9f9f9;
                border-left: 4px solid #0066cc;
            }
            .summary-card h3 {
                color: #666;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 5px;
            }
            .summary-card .value {
                font-size: 32px;
                font-weight: 600;
                color: #333;
            }
            .summary-card.success { border-left-color: #28a745; }
            .summary-card.failed { border-left-color: #dc3545; }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th {
                background: #f9f9f9;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                color: #333;
                border-bottom: 2px solid #e0e0e0;
            }
            td {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            tr:hover {
                background: #f9f9f9;
            }
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .status-badge.success {
                background: #d4edda;
                color: #155724;
            }
            .status-badge.failed {
                background: #f8d7da;
                color: #721c24;
            }
            .status-badge.error {
                background: #fff3cd;
                color: #856404;
            }
            .error-text {
                color: #dc3545;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Ollama Monitor Report</h1>
            <div class="timestamp">Generated: {{ timestamp }}</div>

            <div class="summary">
                <div class="summary-card">
                    <h3>Total Endpoints</h3>
                    <div class="value">{{ total }}</div>
                </div>
                <div class="summary-card success">
                    <h3>Successful</h3>
                    <div class="value">{{ successful }}</div>
                </div>
                <div class="summary-card failed">
                    <h3>Failed</h3>
                    <div class="value">{{ failed }}</div>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Status</th>
                        <th>Status Code</th>
                        <th>Response Time</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
                    {% for endpoint in endpoints %}
                    <tr>
                        <td><strong>{{ endpoint.name }}</strong></td>
                        <td><span class="status-badge {{ endpoint.status_class }}">{{ endpoint.status }}</span></td>
                        <td>{{ endpoint.status_code }}</td>
                        <td>{{ endpoint.response_time }}</td>
                        <td>{% if endpoint.error != '-' %}<span class="error-text">{{ endpoint.error }}</span>{% else %}-{% endif %}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    template = Template(html_template)
    html_content = template.render(
        timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        total=len(results),
        successful=successful,
        failed=failed,
        endpoints=endpoint_data
    )

    async with aiofiles.open(filename, mode="w") as f:
        await f.write(html_content)


async def generate_report(
    results: List[Any],
    endpoints: Dict[str, Any],
    filename: str,
    format: str = "text"
) -> None:
    """
    Generate report in specified format.

    Args:
        results: List of endpoint check results
        endpoints: Dictionary of endpoint configurations
        filename: Output filename
        format: Report format (text, json, csv, html)
    """
    if format == "json":
        await generate_json_report(results, endpoints, filename)
    elif format == "csv":
        await generate_csv_report(results, endpoints, filename)
    elif format == "html":
        await generate_html_report(results, endpoints, filename)
    else:
        await generate_text_report(results, filename)
