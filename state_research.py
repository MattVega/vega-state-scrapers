"""
Research and scrape contractor license data for all remaining states
Priority: states with bulk download CSVs
"""
import requests, csv, re, time, os, json
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# Known bulk download URLs for contractor data
STATE_SOURCES = {
    # State: (url, format, notes)
    'IL': 'https://data.illinois.gov/api/views/xkcr-r83s/rows.csv?accessType=DOWNLOAD',
    'MI': 'https://michigancontractors.lara.michigan.gov/Contractors/DownloadContractors',  
    'IN': 'https://mylicense.in.gov/EGov/Custom/BulkDownload.aspx',
    'WI': 'https://licensesearch.wi.gov/api/Download/GetContractors',
    'PA': 'https://www.dos.pa.gov/ProfessionalLicensing/BoardsCommissions/HomeImprovement',
    'NC': 'https://www.nclbgc.org/licensee-search/',
    'GA': 'https://verify.sos.ga.gov/verification/',
    'TN': 'https://www.tn.gov/content/dam/tn/commerce/documents/regboards/contractors/Roster_Unlimited_License.xls',
}

# Actually let me check the most reliable state open data portals
print("Checking state open data portals...")
