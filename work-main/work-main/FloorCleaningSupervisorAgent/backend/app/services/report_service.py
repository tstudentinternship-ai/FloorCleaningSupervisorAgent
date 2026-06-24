from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException, Response

from app.core.database import (
    alerts_container,
    reports_container,
    rounds_container,
    scan_container,
    tags_container,
)
from app.services.alert_service import list_alerts
from app.services.scan_service import get_scan_history


def _now() -> str:
    return datetime.utcnow().isoformat()


def get_report(report_id: str):
    try:
        items = list(
            reports_container.query_items(
                query="SELECT * FROM c WHERE c.id=@report_id",
                parameters=[{"name": "@report_id", "value": report_id}],
                enable_cross_partition_query=True,
            )
        )
        return items[0] if items else None
    except Exception:
        return None


def generate_report(data):
    report_id = str(uuid.uuid4())
    summary: Dict[str, Any] = {}

    # 1. Fetch raw data based on store scope
    if data.store_id:
        all_scans = get_scan_history(data.store_id)
        all_alerts = list_alerts(store_id=data.store_id)
        all_rounds = list(
            rounds_container.query_items(
                query="SELECT * FROM c WHERE c.store_id=@store_id",
                parameters=[{"name": "@store_id", "value": data.store_id}],
                enable_cross_partition_query=True,
            )
        )
        store_tags = list(
            tags_container.query_items(
                query="SELECT * FROM c WHERE c.store_id=@store_id",
                parameters=[{"name": "@store_id", "value": data.store_id}],
                enable_cross_partition_query=True,
            )
        )
    else:
        all_scans = list(scan_container.read_all_items())
        all_alerts = list_alerts()
        all_rounds = list(rounds_container.read_all_items())
        store_tags = list(tags_container.read_all_items())

    # 2. Filter historical data strictly by chosen date range (comparing YYYY-MM-DD strings)
    filtered_scans = [
        s for s in all_scans
        if data.start_date <= (s.get("shift_date") or s.get("server_timestamp") or "")[:10] <= data.end_date
    ]
    filtered_alerts = [
        a for a in all_alerts
        if data.start_date <= (a.get("time") or a.get("created_at") or "")[:10] <= data.end_date
    ]
    filtered_rounds = [
        r for r in all_rounds
        if data.start_date <= (r.get("shift_date") or r.get("time") or "")[:10] <= data.end_date
    ]

    # 3. Compile report sections corresponding to requested report_types
    report_types = data.report_types or []

    if "Compliance Summary" in report_types:
        total_scans = len(filtered_scans)
        verified_scans = len([s for s in filtered_scans if s.get("scan_status") == "verified"])
        duplicate_scans = len([s for s in filtered_scans if s.get("compliance_status") == "duplicate_scan"])
        fraud_scans = len([s for s in filtered_scans if s.get("compliance_status") == "gps_mismatch"])
        avg_compliance = 0
        if filtered_rounds:
            avg_compliance = round(sum(r.get("compliance", 0) for r in filtered_rounds) / len(filtered_rounds))
        elif total_scans > 0:
            avg_compliance = round((verified_scans / total_scans) * 100)

        summary["compliance_summary"] = {
            "total_scans": total_scans,
            "verified_scans": verified_scans,
            "duplicate_scans": duplicate_scans,
            "fraud_scans": fraud_scans,
            "avg_compliance": avg_compliance,
        }

    if "Alert History" in report_types:
        summary["alerts"] = filtered_alerts

    if "NFC Tag Status" in report_types:
        summary["tags"] = store_tags

    if "Staff Performance" in report_types:
        staff_performance = {}
        for scan in filtered_scans:
            staff_id = scan.get("employee_id") or "unassigned"
            staff_name = scan.get("employee_name") or "Unknown Staff"
            if staff_id not in staff_performance:
                staff_performance[staff_id] = {
                    "name": staff_name,
                    "total_scans": 0,
                    "verified_scans": 0,
                    "compliance": 0,
                }
            staff_performance[staff_id]["total_scans"] += 1
            if scan.get("scan_status") == "verified":
                staff_performance[staff_id]["verified_scans"] += 1
        for staff_id, stats in staff_performance.items():
            if stats["total_scans"] > 0:
                stats["compliance"] = round((stats["verified_scans"] / stats["total_scans"]) * 100)
        summary["staff_performance"] = staff_performance

    if "Round Details" in report_types:
        summary["rounds"] = filtered_rounds

    report = {
        "id": report_id,
        "title": data.title,
        "context": data.context,
        "format": data.format,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "report_types": data.report_types,
        "store_id": data.store_id,
        "generated_at": _now(),
        "download_url": f"/reports/{report_id}/download",
        "summary": summary,
    }
    reports_container.create_item(report)
    return report


def list_reports(store_id: str | None = None):
    if store_id:
        items = list(
            reports_container.query_items(
                query="SELECT * FROM c WHERE c.store_id=@store_id",
                parameters=[{"name": "@store_id", "value": store_id}],
                enable_cross_partition_query=True,
            )
        )
    else:
        items = list(reports_container.read_all_items())
    items.sort(key=lambda item: item.get("generated_at", ""), reverse=True)
    return items


def get_report_download(report_id: str) -> Response:
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    fmt = report.get("format", "pdf")
    title = report.get("title", "Report")
    context = report.get("context", "")
    start_date = report.get("start_date")
    end_date = report.get("end_date")
    summary = report.get("summary", {})
    report_types = report.get("report_types", [])

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["REPORT TITLE", title])
        if context:
            writer.writerow(["CONTEXT", context])
        writer.writerow(["DATE RANGE", f"{start_date} to {end_date}"])
        writer.writerow(["GENERATED AT", report.get("generated_at", "")])
        writer.writerow([])

        # 1. Compliance Summary
        if "Compliance Summary" in report_types and "compliance_summary" in summary:
            writer.writerow(["=== COMPLIANCE SUMMARY ==="])
            cs = summary["compliance_summary"]
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Scans", cs.get("total_scans", 0)])
            writer.writerow(["Verified Scans", cs.get("verified_scans", 0)])
            writer.writerow(["Duplicate Scans", cs.get("duplicate_scans", 0)])
            writer.writerow(["Fraud Scans", cs.get("fraud_scans", 0)])
            writer.writerow(["Average Compliance", f"{cs.get('avg_compliance', 0)}%"])
            writer.writerow([])

        # 2. Alert History
        if "Alert History" in report_types and "alerts" in summary:
            writer.writerow(["=== ALERT HISTORY ==="])
            writer.writerow(["Title", "Category", "Severity", "Time", "Staff Involved", "Reviewed?"])
            for a in summary["alerts"]:
                writer.writerow([
                    a.get("title"),
                    a.get("category"),
                    a.get("type"),
                    a.get("time"),
                    a.get("staff", ""),
                    "Yes" if a.get("reviewed") else "No",
                ])
            writer.writerow([])

        # 3. NFC Tag Status
        if "NFC Tag Status" in report_types and "tags" in summary:
            writer.writerow(["=== NFC TAG STATUS ==="])
            writer.writerow(["Tag UID", "Location", "Area", "Zone", "Priority", "Status", "Total Scans"])
            for t in summary["tags"]:
                writer.writerow([
                    t.get("nfc_tag_uid"),
                    t.get("location"),
                    t.get("area", ""),
                    t.get("zone", ""),
                    t.get("priority", ""),
                    t.get("status"),
                    t.get("scan_count", 0),
                ])
            writer.writerow([])

        # 4. Staff Performance
        if "Staff Performance" in report_types and "staff_performance" in summary:
            writer.writerow(["=== STAFF PERFORMANCE ==="])
            writer.writerow(["Staff Name", "Staff ID", "Total Scans", "Verified Scans", "Compliance"])
            for s_id, s in summary["staff_performance"].items():
                writer.writerow([
                    s.get("name"),
                    s_id,
                    s.get("total_scans", 0),
                    s.get("verified_scans", 0),
                    f"{s.get('compliance', 0)}%",
                ])
            writer.writerow([])

        # 5. Round Details
        if "Round Details" in report_types and "rounds" in summary:
            writer.writerow(["=== ROUND DETAILS ==="])
            writer.writerow(["Round Name", "Date", "Staff Assigned", "Scans Completed", "Expected Scans", "Compliance", "Status"])
            for r in summary["rounds"]:
                writer.writerow([
                    r.get("name"),
                    r.get("shift_date"),
                    r.get("staff"),
                    r.get("completedScans"),
                    r.get("totalScans"),
                    f"{r.get('compliance', 0)}%",
                    r.get("status"),
                ])
            writer.writerow([])

        csv_content = output.getvalue()
        output.close()

        headers = {
            "Content-Disposition": f"attachment; filename={report_id}.csv"
        }
        return Response(content=csv_content, media_type="text/csv", headers=headers)

    else:
        # Generate beautifully styled print-ready HTML page (PDF format)
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #333;
            margin: 40px;
            font-size: 14px;
            line-height: 1.5;
        }}
        h1 {{
            color: #111;
            margin-bottom: 5px;
            font-size: 24px;
        }}
        h2 {{
            color: #222;
            border-bottom: 2px solid #eaeaea;
            padding-bottom: 5px;
            margin-top: 30px;
            font-size: 16px;
        }}
        .meta {{
            color: #666;
            font-size: 12px;
            margin-bottom: 25px;
        }}
        .meta span {{
            margin-right: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            margin-bottom: 20px;
        }}
        th, td {{
            text-align: left;
            padding: 8px 10px;
            border-bottom: 1px solid #eaeaea;
        }}
        th {{
            background-color: #f7f7f7;
            font-weight: 600;
            color: #444;
        }}
        .critical {{
            color: #dc2626;
            font-weight: 600;
        }}
        .warning {{
            color: #d97706;
            font-weight: 600;
        }}
        .fraud {{
            color: #7c3aed;
            font-weight: 600;
        }}
        .badge {{
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            display: inline-block;
        }}
        .badge-verified {{
            background-color: #d1fae5;
            color: #065f46;
        }}
        .badge-error {{
            background-color: #fee2e2;
            color: #991b1b;
        }}
        @media print {{
            body {{
                margin: 20px;
            }}
            button {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
            <h1>{title}</h1>
            <div class="meta">
                {f"<span><strong>Context:</strong> {context}</span>" if context else ""}
                <span><strong>Date Range:</strong> {start_date} to {end_date}</span>
                <span><strong>Generated:</strong> {report.get("generated_at", "")[:19].replace("T", " ")}</span>
            </div>
        </div>
        <button onclick="window.print()" style="padding: 8px 14px; background-color: #ea580c; border: none; color: white; font-weight: 600; border-radius: 8px; cursor: pointer;">Print / Save PDF</button>
    </div>
"""

        # 1. Compliance Summary
        if "Compliance Summary" in report_types and "compliance_summary" in summary:
            cs = summary["compliance_summary"]
            html += f"""
        <h2>Compliance Summary</h2>
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 25px;">
            <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Average Compliance</div>
                <div style="font-size: 20px; font-weight: bold; color: #ea580c; margin-top: 5px;">{cs.get("avg_compliance", 0)}%</div>
            </div>
            <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Total Scans</div>
                <div style="font-size: 20px; font-weight: bold; color: #111827; margin-top: 5px;">{cs.get("total_scans", 0)}</div>
            </div>
            <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Verified Scans</div>
                <div style="font-size: 20px; font-weight: bold; color: #10b981; margin-top: 5px;">{cs.get("verified_scans", 0)}</div>
            </div>
            <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Duplicate Scans</div>
                <div style="font-size: 20px; font-weight: bold; color: #f59e0b; margin-top: 5px;">{cs.get("duplicate_scans", 0)}</div>
            </div>
            <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Fraud Scans</div>
                <div style="font-size: 20px; font-weight: bold; color: #7c3aed; margin-top: 5px;">{cs.get("fraud_scans", 0)}</div>
            </div>
        </div>
"""

        # 2. Alert History
        if "Alert History" in report_types and "alerts" in summary:
            html += """
        <h2>Alert History</h2>
        <table>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Category</th>
                    <th>Severity</th>
                    <th>Time</th>
                    <th>Staff</th>
                    <th>Reviewed</th>
                </tr>
            </thead>
            <tbody>
"""
            for a in summary["alerts"]:
                reviewed_str = "Yes" if a.get("reviewed") else "No"
                severity_class = a.get("type", "")
                html += f"""
                <tr>
                    <td><strong>{a.get("title")}</strong><br><span style="font-size:11px; color:#666;">{a.get("description")}</span></td>
                    <td>{a.get("category")}</td>
                    <td class="{severity_class}">{a.get("type")}</td>
                    <td>{a.get("time")[:19].replace("T", " ")}</td>
                    <td>{a.get("staff") or "—"}</td>
                    <td>{reviewed_str}</td>
                </tr>
"""
            html += "</tbody></table>"

        # 3. NFC Tag Status
        if "NFC Tag Status" in report_types and "tags" in summary:
            html += """
        <h2>NFC Tag Status</h2>
        <table>
            <thead>
                <tr>
                    <th>Tag UID</th>
                    <th>Location</th>
                    <th>Area/Zone</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Total Scans</th>
                </tr>
            </thead>
            <tbody>
"""
            for t in summary["tags"]:
                html += f"""
                <tr>
                    <td style="font-family:monospace;">{t.get("nfc_tag_uid")}</td>
                    <td>{t.get("location")}</td>
                    <td>{f"{t.get('area') or ''} / {t.get('zone') or ''}"}</td>
                    <td>{t.get("priority") or "—"}</td>
                    <td><span class="badge badge-{"verified" if t.get("status") == "active" else "error"}">{t.get("status")}</span></td>
                    <td>{t.get("scan_count", 0)}</td>
                </tr>
"""
            html += "</tbody></table>"

        # 4. Staff Performance
        if "Staff Performance" in report_types and "staff_performance" in summary:
            html += """
        <h2>Staff Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Staff Name</th>
                    <th>Staff ID</th>
                    <th>Total Scans</th>
                    <th>Verified Scans</th>
                    <th>Compliance</th>
                </tr>
            </thead>
            <tbody>
"""
            for s_id, s in summary["staff_performance"].items():
                html += f"""
                <tr>
                    <td><strong>{s.get("name")}</strong></td>
                    <td style="font-family:monospace;">{s_id}</td>
                    <td>{s.get("total_scans", 0)}</td>
                    <td>{s.get("verified_scans", 0)}</td>
                    <td style="font-weight:bold; color:#ea580c;">{s.get("compliance", 0)}%</td>
                </tr>
"""
            html += "</tbody></table>"

        # 5. Round Details
        if "Round Details" in report_types and "rounds" in summary:
            html += """
        <h2>Round Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Round Name</th>
                    <th>Date</th>
                    <th>Staff Assigned</th>
                    <th>Completed Scans</th>
                    <th>Compliance</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""
            for r in summary["rounds"]:
                html += f"""
                <tr>
                    <td>{r.get("name")}</td>
                    <td>{r.get("shift_date")}</td>
                    <td>{r.get("staff")}</td>
                    <td>{r.get("completedScans")} / {r.get("totalScans")}</td>
                    <td style="font-weight:bold; color:#ea580c;">{r.get("compliance", 0)}%</td>
                    <td>{r.get("status")}</td>
                </tr>
"""
            html += "</tbody></table>"

        html += """
    <script>
        window.onload = function() {
            setTimeout(function() {
                window.print();
            }, 500);
        };
    </script>
</body>
</html>
"""
        return Response(content=html, media_type="text/html")


