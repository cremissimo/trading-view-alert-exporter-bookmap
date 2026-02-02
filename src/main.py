from email.policy import default
import imaplib
import email
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file

load_dotenv(".env")

# Get configuration from environment variables
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
CSV_PATH = os.getenv("CSV_PATH")

DELETE_PROCESSED_EMAILS = os.getenv("DELETE_PROCESSED_EMAILS", "False").strip().lower()
if not DELETE_PROCESSED_EMAILS:
    DELETE_PROCESSED_EMAILS = False
else:
    DELETE_PROCESSED_EMAILS = DELETE_PROCESSED_EMAILS in ["1", "true", "yes", "on"]


READ_EMAIL_SINCE_MINUTES = int(os.getenv("READ_EMAIL_SINCE_MINUTES", 6))
# Parse comma-separated symbols from env
INCLUDE_SYMBOLS = [
    symbol.strip() 
    for symbol in os.getenv("INCLUDE_SYMBOLS", "").split(",") 
    if symbol.strip()
]

def recent_alerts(minutes=5):
    """Get all alerts from the last N minutes."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select("inbox")

    # Calculate date for IMAP search (5 minutes ago)
    since_date = (datetime.now() - timedelta(minutes=minutes)).strftime("%d-%b-%Y")
    
    # Search for TradingView alerts from the last period
    # IMAP SINCE is date-only, so we'll filter by time in Python
    _, messages = mail.search(None, f'(SUBJECT "Alert: AMT Levels" SINCE {since_date})')
    email_ids = messages[0].split()

    if not email_ids:
        mail.logout()
        return []

    alerts = []
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    emails_to_delete = []
    
    for email_id in email_ids:
        _, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        # Parse email date
        date_str = msg.get("Date")
        email_date = email.utils.parsedate_to_datetime(date_str)
        
        # Only include emails from the last N minutes
        if email_date < cutoff_time:
            continue
        
        # Extract HTML content
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode()
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator="\n").strip()
                alerts.append({"date": email_date, "content": text})
                emails_to_delete.append(email_id)
                break

    # Delete processed emails
    if emails_to_delete and DELETE_PROCESSED_EMAILS:
        print(f"Marking {len(emails_to_delete)} email(s) for deletion...")
        for email_id in emails_to_delete:
            mail.store(email_id, '+FLAGS', '\\Deleted')
        mail.expunge()
        print(f"Deleted {len(emails_to_delete)} processed email(s)")
    else:
        print(f"Skipping deletion of {len(emails_to_delete)} processed email(s)")


    mail.logout()
    return alerts

def extract_bookmap_notes(msg):
    lines_of_interest = []
    for line in msg.splitlines():
        if not any(k.lower() in line.lower() for k in INCLUDE_SYMBOLS):
            continue
        lines_of_interest.append(line.replace('"', '').split(","))
    return lines_of_interest

def main():
    print(f"Checking emails from the last {READ_EMAIL_SINCE_MINUTES} minutes... [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    
    alerts = recent_alerts(minutes=READ_EMAIL_SINCE_MINUTES)
    
    if not alerts:
        print(f"No alerts found in the last {READ_EMAIL_SINCE_MINUTES} minutes.")
        exit(0)
    
    print(f"Found {len(alerts)} alert(s) to process")
    
    for idx, alert_data in enumerate(alerts, 1):
        alert = alert_data['content']
        alert_time = alert_data['date'].strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\nProcessing alert #{idx} from {alert_time}")
        
        lines = extract_bookmap_notes(alert)
        if not lines:
            print(f"  No relevant symbols found in alert #{idx}")
            continue
        
        print(f"Latest AMT Level alert: Symbol {alert.splitlines()[0].split(',')[0]}")
        symbol_name = lines[0][0].upper()
        file_name = symbol_name + "_STF.csv"
        path = CSV_PATH + file_name
        
        with open(path, 'w', newline='') as f:
            print(f"  Writing {len(lines)} lines to {path}")
            f.write("Symbol,Price Level,Note,Foreground Color,Background Color,Text Alignment,DIAMETER,DRAW_NOTE_PRICE_HORIZONTAL_LINE\n")
            writer = csv.writer(f)
            writer.writerows([line for line in lines])


