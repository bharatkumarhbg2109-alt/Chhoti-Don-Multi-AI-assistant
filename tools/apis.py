"""
Chhoti Don - API Manager
Advanced API integration hub with email, SMS, webhooks,
HTTP requests, and notification services.
Phase 2.2 - Full Upgrade
"""

import os
import json
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Type

class APIManager:
    """
    Advanced API Manager.
    Handles external API integrations with retry logic,
    rate limiting, and error handling.
    """

    def __init__(self):
        self.request_log = []
        self.rate_limits = {}
        self._session_headers = {
            "User-Agent": "ChhotiDon/2.2",
            "Content-Type": "application/json",
        }

    # ==================================================
    # 📧 EMAIL (PRESERVED + UPGRADED)
    # ==================================================

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: List[str] = None,
        attachments: List[str] = None,
    ) -> Dict:
        """
        Send email via SMTP or API.
        Preserved + upgraded.
        """
        # Try SendGrid if API key available
        sendgrid_key = os.getenv("SENDGRID_API_KEY")
        if sendgrid_key:
            return self._send_via_sendgrid(to, subject, body, sendgrid_key, html)

        # Try SMTP if configured
        smtp_host = os.getenv("SMTP_HOST")
        if smtp_host:
            return self._send_via_smtp(to, subject, body, html)

        # Simulation mode
        self._log_request("email", {"to": to, "subject": subject})
        return {
            "status": "simulated",
            "message": f"[Simulated Email Sent to {to}]",
            "subject": subject,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def _send_via_smtp(self, to: str, subject: str, body: str, html: bool) -> Dict:
        """SMTP email send karo."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_pass = os.getenv("SMTP_PASS", "")
            from_email = os.getenv("SMTP_FROM", smtp_user)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to

            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to], msg.as_string())

            return {
                "status": "success",
                "message": f"Email sent to {to}",
                "provider": "smtp",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _send_via_sendgrid(self, to: str, subject: str, body: str, api_key: str, html: bool) -> Dict:
        """SendGrid API se email send karo."""
        try:
            payload = json.dumps({
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": os.getenv("FROM_EMAIL", "noreply@chhotidon.ai")},
                "subject": subject,
                "content": [{"type": "text/html" if html else "text/plain", "value": body}],
            }).encode()

            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
            return {"status": "success", "provider": "sendgrid", "to": to}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================================================
    # 📱 SMS (PRESERVED + UPGRADED)
    # ==================================================

    def send_sms(
        self,
        number: str,
        message: str,
        provider: str = "auto",
    ) -> Dict:
        """
        Send SMS via Twilio or other providers.
        Preserved + upgraded.
        """
        # Try Twilio
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_from = os.getenv("TWILIO_FROM_NUMBER")

        if twilio_sid and twilio_token and twilio_from:
            return self._send_via_twilio(number, message, twilio_sid, twilio_token, twilio_from)

        # Simulation
        self._log_request("sms", {"to": number, "message": message[:50]})
        return {
            "status": "simulated",
            "message": f"[Simulated SMS Sent to {number}]",
            "content": message,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def _send_via_twilio(self, to: str, body: str, sid: str, token: str, from_num: str) -> Dict:
        """Twilio SMS send karo."""
        try:
            import base64
            payload = urllib.parse.urlencode({
                "To": to, "From": from_num, "Body": body
            }).encode()

            credentials = base64.b64encode(f"{sid}:{token}".encode()).decode()
            req = urllib.request.Request(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data=payload,
                headers={"Authorization": f"Basic {credentials}"},
                method="POST",
            )
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read())
            return {"status": "success", "sid": data.get("sid"), "provider": "twilio"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================================================
    # 🌐 HTTP REQUEST (NEW)
    # ==================================================

    def http_get(
        self,
        url: str,
        headers: Dict = None,
        params: Dict = None,
        timeout: int = 10,
    ) -> Dict:
        """HTTP GET request karo."""
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        req_headers = {**self._session_headers, **(headers or {})}
        req = urllib.request.Request(url, headers=req_headers)

        return self._execute_request(req, timeout)

    def http_post(
        self,
        url: str,
        data: Dict = None,
        headers: Dict = None,
        timeout: int = 10,
    ) -> Dict:
        """HTTP POST request karo."""
        payload = json.dumps(data or {}).encode()
        req_headers = {**self._session_headers, **(headers or {})}
        req = urllib.request.Request(url, data=payload, headers=req_headers, method="POST")

        return self._execute_request(req, timeout)

    def _execute_request(self, req, timeout: int, retry: int = 2) -> Dict:
        """HTTP request execute with retry."""
        last_error = None

        for attempt in range(retry + 1):
            try:
                start = time.time()
                response = urllib.request.urlopen(req, timeout=timeout)
                body = response.read().decode(errors="ignore")
                duration = round(time.time() - start, 3)

                self._log_request("http", {"url": req.full_url, "status": response.status})

                return {
                    "status": "success",
                    "status_code": response.status,
                    "body": body[:5000],
                    "headers": dict(response.headers),
                    "duration_sec": duration,
                }
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if e.code < 500:
                    break
            except Exception as e:
                last_error = str(e)
                if attempt < retry:
                    time.sleep(0.5 * (attempt + 1))

        return {"status": "error", "message": last_error}

    # ==================================================
    # 🔔 WEBHOOK (NEW)
    # ==================================================

    def send_webhook(
        self,
        url: str,
        payload: Dict,
        secret: str = None,
    ) -> Dict:
        """Webhook event send karo."""
        headers = {"Content-Type": "application/json"}

        if secret:
            import hmac
            import hashlib
            body = json.dumps(payload).encode()
            sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-Signature-256"] = f"sha256={sig}"

        return self.http_post(url, payload, headers)

    # ==================================================
    # 📣 SLACK NOTIFICATION (NEW)
    # ==================================================

    def send_slack(
        self,
        message: str,
        webhook_url: str = None,
        channel: str = None,
    ) -> Dict:
        """Slack notification send karo."""
        webhook = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

        if not webhook:
            return {
                "status": "simulated",
                "message": f"[Simulated Slack: {message[:50]}]",
            }

        payload = {
            "text": message,
            "username": "Chhoti Don",
        }
        if channel:
            payload["channel"] = channel

        return self.http_post(webhook, payload)

    # ==================================================
    # 📊 REQUEST LOG
    # ==================================================

    def _log_request(self, api_type: str, details: Dict) -> None:
        """Request log karo."""
        self.request_log.append({
            "type": api_type,
            "details": details,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        if len(self.request_log) > 200:
            self.request_log.pop(0)

    def get_request_log(self, last_n: int = 20) -> List[Dict]:
        """Recent API requests."""
        return self.request_log[-last_n:]

    def get_stats(self) -> Dict:
        """API usage stats."""
        by_type = {}
        for req in self.request_log:
            t = req["type"]
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_requests": len(self.request_log),
            "by_type": by_type,
        }
