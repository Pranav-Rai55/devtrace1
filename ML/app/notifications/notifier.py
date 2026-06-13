"""
Phase 4 — Slack & Teams Notification Service
Sends rich formatted messages on analysis completion or HIGH severity findings
"""

import json
import logging
import urllib.request
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Notifier:

    def send_analysis_complete(self, webhook_url: str, platform: str, report: Dict[str, Any]):
        """Send a rich analysis-complete notification."""
        if not webhook_url:
            return
        quality = _val(report.get("quality_score", {}))
        security = _val(report.get("security_risks", {}))
        debt = _val(report.get("estimated_tech_debt_hours", {}))
        maint = _val(report.get("maintainability", {}))
        repo = report.get("repo_name", "Unknown")
        critical = report.get("critical_issues_count", 0)
        vuln_deps = report.get("vulnerable_dependencies", 0)

        if platform == "slack":
            payload = self._slack_payload(repo, quality, security, debt, maint, critical, vuln_deps)
        else:
            payload = self._teams_payload(repo, quality, security, debt, maint, critical, vuln_deps)

        self._post(webhook_url, payload)

    def send_high_severity_alert(self, webhook_url: str, platform: str,
                                  repo: str, issue_title: str, file_path: str):
        """Send an immediate HIGH severity alert."""
        if not webhook_url:
            return
        if platform == "slack":
            payload = {
                "text": f"🚨 *HIGH Severity Issue Detected in `{repo}`*",
                "attachments": [{
                    "color": "#ff4d6a",
                    "fields": [
                        {"title": "Issue", "value": issue_title, "short": False},
                        {"title": "File", "value": file_path, "short": True},
                    ]
                }]
            }
        else:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "ff4d6a",
                "summary": f"HIGH Severity in {repo}",
                "sections": [{
                    "activityTitle": f"🚨 HIGH Severity in `{repo}`",
                    "facts": [
                        {"name": "Issue", "value": issue_title},
                        {"name": "File", "value": file_path},
                    ]
                }]
            }
        self._post(webhook_url, payload)

    def _slack_payload(self, repo, quality, security, debt, maint, critical, vuln_deps):
        q_emoji = "🟢" if float(quality or 0) >= 75 else "🟡" if float(quality or 0) >= 50 else "🔴"
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"✅ DevTrace Analysis Complete"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Repository:* `{repo}`"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"{q_emoji} *Quality Score*\n{quality}/100"},
                        {"type": "mrkdwn", "text": f"🛡️ *Security Risks*\n{security} high"},
                        {"type": "mrkdwn", "text": f"⚙️ *Maintainability*\n{maint}"},
                        {"type": "mrkdwn", "text": f"⏱️ *Tech Debt*\n{debt}"},
                    ]
                },
                *([] if not critical else [{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"⚠️ *{critical} critical issue(s)* require immediate attention."}
                }]),
                *([] if not vuln_deps else [{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"🔴 *{vuln_deps} vulnerable dependenc{'y' if vuln_deps==1 else 'ies'}* detected."}
                }]),
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": "Powered by *DevTrace* — AI Code Intelligence"}]
                }
            ]
        }

    def _teams_payload(self, repo, quality, security, debt, maint, critical, vuln_deps):
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "6c63ff",
            "summary": f"DevTrace Analysis: {repo}",
            "sections": [{
                "activityTitle": f"✅ DevTrace Analysis Complete — `{repo}`",
                "facts": [
                    {"name": "Quality Score", "value": f"{quality}/100"},
                    {"name": "Security Risks", "value": f"{security} high severity"},
                    {"name": "Maintainability", "value": str(maint)},
                    {"name": "Tech Debt", "value": str(debt)},
                    {"name": "Critical Issues", "value": str(critical)},
                    {"name": "Vulnerable Dependencies", "value": str(vuln_deps)},
                ],
                "markdown": True,
            }]
        }

    def _post(self, url: str, payload: dict):
        try:
            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=8)
        except Exception as e:
            logger.warning("[Notifier] Failed to send notification: %s", e)


def _val(card):
    if isinstance(card, dict):
        return card.get("value", "—")
    return str(card)


notifier = Notifier()
