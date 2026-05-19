#!/usr/bin/env python3
"""
Daily subcontractor scraper automation.
Pulls new contacts from Yelp API, dedupes against master, and emails daily list to Neiva.
"""

import os
import json
import sys
from datetime import datetime, timedelta
import requests
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import csv
import time
import random

# Load environment
YELP_API_KEY = os.getenv('YELP_API_KEY')
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')

if not YELP_API_KEY:
    print("ERROR: YELP_API_KEY not found in environment")
    sys.exit(1)

# Configuration
MASTER_FILE = "subcontractor_master_v2.xlsx"
DAILY_OUTPUT = "daily_export.xlsx"
TODAY = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = f"daily_scraper_{TODAY}.log"

STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
    "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
    "TN", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

TRADES = [
    "drywall",
    "painting",
    "flooring",
    "electrical",
    "plumbing",
    "HVAC",
    "roofing",
    "concrete",
    "carpentry"
]

def log(msg):
    """Log to file and stdout"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    with open(LOG_FILE, "a") as f:
        f.write(log_msg + "\n")

def normalize_phone(phone):
    """Normalize phone to digits only"""
    if not phone:
        return ""
    return ''.join(c for c in str(phone) if c.isdigit())

def normalize_email(email):
    """Normalize email"""
    if not email:
        return ""
    return email.strip().lower()

def load_master_contacts():
    """Load all existing contacts from master file for deduplication"""
    log("Loading master contact list...")
    master_contacts = set()
    
    if not os.path.exists(MASTER_FILE):
        log(f"WARNING: Master file not found at {MASTER_FILE}")
        return master_contacts
    
    try:
        wb = openpyxl.load_workbook(MASTER_FILE, data_only=True)
        if "All Contacts" not in wb.sheetnames:
            log("ERROR: 'All Contacts' sheet not found in master file")
            return master_contacts
        
        ws = wb["All Contacts"]
        header = [cell.value for cell in ws[1]]
        
        # Find column indices
        try:
            phone_idx = header.index("Phone") + 1
            email_idx = header.index("Email") + 1
        except ValueError as e:
            log(f"ERROR: Required column not found: {e}")
            return master_contacts
        
        # Load all phone/email combos
        for row_num in range(2, ws.max_row + 1):
            phone = normalize_phone(ws.cell(row_num, phone_idx).value)
            email = normalize_email(ws.cell(row_num, email_idx).value)
            
            if phone:
                master_contacts.add(("phone", phone))
            if email:
                master_contacts.add(("email", email))
        
        log(f"Loaded {len(master_contacts)} contact identifiers from master (phones + emails)")
        return master_contacts
        
    except Exception as e:
        log(f"ERROR loading master: {e}")
        return master_contacts

def scrape_yelp(state, trade):
    """Scrape contacts from Yelp API for a state/trade combo"""
    url = "https://api.yelp.com/v3/businesses/search"
    headers = {
        "Authorization": f"Bearer {YELP_API_KEY}"
    }
    
    params = {
        "term": f"{trade} contractors",
        "location": state,
        "limit": 50,
        "offset": 0
    }
    
    all_businesses = []
    
    try:
        # Fetch first page
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            log(f"WARNING: Yelp API error for {state}/{trade}: {response.status_code}")
            return []
        
        data = response.json()
        if "businesses" not in data:
            return []
        
        all_businesses.extend(data["businesses"])
        
        # Check if there are more results
        total = data.get("total", 0)
        fetched = len(all_businesses)
        
        while fetched < min(total, 500):  # Limit to 500 per state/trade to avoid rate limits
            params["offset"] = fetched
            time.sleep(0.2)  # Rate limiting
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                break
            
            data = response.json()
            if "businesses" not in data or not data["businesses"]:
                break
            
            all_businesses.extend(data["businesses"])
            fetched = len(all_businesses)
        
        return all_businesses
        
    except Exception as e:
        log(f"ERROR scraping Yelp {state}/{trade}: {e}")
        return []

def extract_contact_info(business):
    """Extract contact info from Yelp business record"""
    contact = {
        "company_name": business.get("name", ""),
        "phone": business.get("phone", ""),
        "city": business.get("location", {}).get("city", ""),
        "state": business.get("location", {}).get("state", ""),
        "address": " ".join([
            business.get("location", {}).get("address1", ""),
            business.get("location", {}).get("address2", ""),
            business.get("location", {}).get("city", ""),
            business.get("location", {}).get("state", ""),
            business.get("location", {}).get("zip_code", "")
        ]).strip(),
        "website": business.get("url", ""),
        "email": "",  # Yelp doesn't provide email
    }
    
    return contact

def run_daily_scrape():
    """Run daily scrape across all states/trades"""
    log("="*60)
    log("STARTING DAILY SUBCONTRACTOR SCRAPE")
    log("="*60)
    
    # Load existing contacts for dedup
    master_contacts = load_master_contacts()
    
    # Scrape new contacts
    new_contacts = []
    total_scraped = 0
    
    for state in STATES:
        for trade in TRADES:
            log(f"Scraping {state} / {trade}...")
            businesses = scrape_yelp(state, trade)
            
            if not businesses:
                continue
            
            for business in businesses:
                contact = extract_contact_info(business)
                phone_normalized = normalize_phone(contact["phone"])
                email_normalized = normalize_email(contact["email"])
                
                # Check if this contact already exists in master
                is_duplicate = False
                if phone_normalized:
                    is_duplicate = ("phone", phone_normalized) in master_contacts
                if email_normalized and not is_duplicate:
                    is_duplicate = ("email", email_normalized) in master_contacts
                
                if not is_duplicate:
                    # Check for duplicates within today's scraped batch
                    batch_key = (phone_normalized or email_normalized,)
                    is_batch_dup = any(
                        normalize_phone(c.get("phone")) == phone_normalized
                        for c in new_contacts
                        if phone_normalized
                    )
                    
                    if not is_batch_dup:
                        new_contacts.append(contact)
            
            total_scraped += len(businesses)
            time.sleep(1)  # Rate limiting between state/trade combos
    
    log(f"Total records scraped: {total_scraped}")
    log(f"New unique contacts found: {len(new_contacts)}")
    
    return new_contacts

def create_daily_excel(contacts):
    """Create Excel file with today's new contacts only"""
    log(f"Creating daily Excel file with {len(contacts)} contacts...")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = TODAY
    
    # Header row
    header = ["Company Name", "Contact Name", "Trade", "State", "City", "Address", "Phone", "Email", "Website", "Notes"]
    ws.append(header)
    
    # Style header
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Add data rows
    for contact in contacts:
        ws.append([
            contact.get("company_name", ""),
            "",  # Contact Name
            "",  # Trade
            contact.get("state", ""),
            contact.get("city", ""),
            contact.get("address", ""),
            contact.get("phone", ""),
            contact.get("email", ""),
            contact.get("website", ""),
            ""   # Notes
        ])
    
    # Auto-adjust column widths
    for col_num, column_title in enumerate(header, 1):
        column_letter = get_column_letter(col_num)
        ws.column_dimensions[column_letter].width = 20
    
    # Save
    wb.save(DAILY_OUTPUT)
    log(f"Daily Excel file saved to {DAILY_OUTPUT}")
    return True

def send_email_to_neiva(contact_count):
    """Send email to Neiva with today's new contacts"""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        log("WARNING: Gmail credentials not configured, skipping email")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = "neiva@vegaplans.com"
        msg['Subject'] = f"Daily Subcontractor Contacts - {TODAY} ({contact_count} new)"
        
        # Body
        body = f"""
Hello Neiva,

Today's daily subcontractor scrape has completed successfully.

Summary:
- Date: {TODAY}
- New contacts added: {contact_count}
- Attachment: daily_export.xlsx (TODAY'S NEW CONTACTS ONLY)

The attached file contains only the new contacts discovered today, deduplicated against the master list.

Best regards,
Scrapper Agent
"""
        
        msg.attach(MIMEText(body, "plain"))
        
        # Attach file
        if os.path.exists(DAILY_OUTPUT):
            with open(DAILY_OUTPUT, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(DAILY_OUTPUT)}")
                msg.attach(part)
        
        # Send via Gmail
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        log(f"Email sent successfully to neiva@vegaplans.com")
        return True
        
    except Exception as e:
        log(f"ERROR sending email: {e}")
        return False

def main():
    try:
        # Run scrape
        new_contacts = run_daily_scrape()
        
        if new_contacts:
            # Create Excel file
            create_daily_excel(new_contacts)
            
            # Send email
            send_email_to_neiva(len(new_contacts))
        else:
            log("No new contacts found today")
        
        log("="*60)
        log("DAILY SCRAPE COMPLETE")
        log("="*60)
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
