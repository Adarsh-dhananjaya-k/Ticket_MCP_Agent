import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_approval_email(manager_email, ticket_id, priority, description, agent_email):
    """
    Sends an approval email to the manager with links to approve or reject.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SMTP_FROM_EMAIL")
    base_url = os.getenv("BASE_URL", "http://localhost:3978")

    if not all([smtp_server, smtp_user, smtp_password, sender_email]):
        print("⚠️ SMTP credentials not fully configured. Email not sent.")
        return False

    subject = f"ACTION REQUIRED: Approval Needed for P1 Ticket {ticket_id}"
    
    approve_link = f"{base_url}/approve?ticket_id={ticket_id}&agent_email={agent_email}"
    reject_link = f"{base_url}/reject?ticket_id={ticket_id}"

    html = f"""
    <html>
    <body>
        <h2>Ticket Approval Request</h2>
        <p>A high-priority (P1) ticket has been created and needs your approval before assignment.</p>
        <p><b>Ticket ID:</b> {ticket_id}</p>
        <p><b>Priority:</b> {priority}</p>
        <p><b>Description:</b> {description}</p>
        <p><b>Proposed Assignee:</b> {agent_email}</p>
        <br>
        <p>
            <a href="{approve_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">APPROVE & ASSIGN</a>
            &nbsp;&nbsp;
            <a href="{reject_link}" style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">REJECT</a>
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = manager_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, manager_email, msg.as_string())
        print(f"✅ Approval email sent to {manager_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
