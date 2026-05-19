"""Test a comprehensive list of state contractor license download URLs"""
import requests, time

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

# Comprehensive list of state contractor license data sources
URLS = {
    # Direct CSV/Excel downloads
    'IL_IDFPR': 'https://www.idfpr.com/LicenseLookup/LicenseesByLicenseType/Electrical_ContractingLicensee.CSV',
    'IL_IDFPR2': 'https://www.idfpr.com/LicenseLookup/LicenseesByLicenseType/PlumbingContractorLicensee.CSV',
    'IL_IDFPR3': 'https://www.idfpr.com/LicenseLookup/ActiveLicensees.csv',
    
    'MI_BPL': 'https://www.michigan.gov/-/media/Project/Websites/lara/bpl/license-lists/master-contractors.csv',
    'MI_BPL2': 'https://miplus.lara.michigan.gov/api/licensees/download?type=contractor&format=csv',
    
    'TN_TDCI': 'https://tnmap.tn.gov/webservices/tdci/contractors/export.csv',
    'TN_TDCI2': 'https://apps.tn.gov/tdci-licensees/contractors.csv',
    
    'GA_SOS': 'https://verify.sos.ga.gov/verification/DownloadAllContractors.csv',
    'GA_SOS2': 'https://verify.sos.ga.gov/verification/export?type=contractor',
    
    'NC_LBGC': 'https://portal.nclbgc.org/Public/ExportLicensees.csv',
    'NC_LBGC2': 'https://www.nclbgc.org/download/licensees.csv',
    
    'MO_AGO': 'https://pr.mo.gov/contractors-download.asp',
    'MO_DOLIR': 'https://labor.mo.gov/data/contractor-list.csv',
    
    'KY_DOCEP': 'https://www.docep.ky.gov/contractors/download/active.csv',
    'KY_SOS': 'https://secure.kentucky.gov/farmersmarket/api/contractors/download',
    
    'LA_SLBC': 'https://lslbc.louisiana.gov/wp-content/uploads/contractor-list.csv',
    'LA_LSBCL': 'https://www.lslbc.louisiana.gov/downloads/contractor_roster.csv',
    
    'AL_ALBLC': 'https://genconbd.alabama.gov/pages/verify.aspx?export=csv',
    'AL_ALBLC2': 'https://www.genconbd.alabama.gov/download/active_contractors.csv',
    
    'SC_LLR': 'https://www.llronline.com/download/contractors.csv',
    'SC_LLR2': 'https://verify.llronline.com/LicLookup/export?type=contractor',
    
    'AR_ACLB': 'https://www.aclb.arkansas.gov/download/licensees.csv',
    'AR_ACLB2': 'https://aclb.arkansas.gov/export/contractors.csv',
    
    'MS_MSBOC': 'https://www.msboc.us/download/contractors.csv',
    
    'CT_DCP': 'https://www.elicense.ct.gov/Lookup/ContractorExport.csv',
    'CT_DCP2': 'https://www.ctdcp.com/Home/DownloadLicensees?type=contractor',
    
    'MA_OCABR': 'https://elicensing.state.ma.us/download/contractors.csv',
    'MA_OCABR2': 'https://www.mass.gov/download/contractor-list',
    
    'NH_OPLC': 'https://www.oplc.nh.gov/download/contractors.csv',
    
    'ME_DPFM': 'https://www.maine.gov/pfr/ins/download/contractors.csv',
    
    'VT_SOS': 'https://www.sec.state.vt.us/download/contractors.csv',
    
    'RI_CRMC': 'https://www.crmc.ri.gov/download/contractors.csv',
    'RI_DOL': 'https://dol.ri.gov/download/contractors.csv',
    
    'DE_DLLR': 'https://dllr.delaware.gov/download/contractors.csv',
    
    'NJ_DCA': 'https://newjersey.gov/download/contractors.csv',
    'NJ_DCA2': 'https://www.njconsumeraffairs.gov/hic/download.aspx',
    
    'PA_DOS': 'https://www.dos.pa.gov/ProfessionalLicensing/BoardsCommissions/HomeImprovement/download.aspx',
    'PA_HICPA': 'https://www.hicpa.org/download/contractors.csv',
    
    'WI_DSPS': 'https://dsps.wi.gov/Pages/SelfService/OrderListofLicensees.aspx?type=contractor&format=csv',
    
    'MN_DLI': 'https://www.dli.mn.gov/business/codes-and-licensing/contractor-licensing/download',
    'MN_DLI2': 'https://apps.dli.mn.gov/download/contractors.csv',
    
    'IA_IDPH': 'https://mydata.iowa.gov/api/views/contractors/rows.csv?accessType=DOWNLOAD',
    'IA_IDPH2': 'https://data.iowa.gov/api/views/contractors/rows.csv?accessType=DOWNLOAD',
    
    'KS_KBOC': 'https://kboc.ks.gov/download/contractors.csv',
    
    'NE_DHHS': 'https://dhhs.ne.gov/Pages/download-contractors.aspx',
    
    'NM_RLD': 'https://www.rld.nm.gov/construction-industries/download/active-licensees.csv',
    'NM_CID': 'https://www.rld.nm.gov/content/uploads/contractor-list.csv',
    
    'ID_PWB': 'https://dbs.idaho.gov/download/contractors.csv',
    'ID_IPWB': 'https://www.ipwb.idaho.gov/download/contractors.csv',
    
    'UT_DOPL': 'https://dopl.utah.gov/download/contractors.csv',
    'UT_DOPL2': 'https://secure.utah.gov/dopl-contractors/download.html',
}

working = {}
print(f"Testing {len(URLS)} URLs...")
for key, url in URLS.items():
    try:
        r = s.head(url, timeout=8, allow_redirects=True)
        ct = r.headers.get('content-type','')
        cl = r.headers.get('content-length','0')
        if r.status_code == 200:
            print(f"  ✓ {key}: {r.status_code} {ct[:30]} {cl} bytes")
            working[key] = url
        elif r.status_code in [302, 301]:
            loc = r.headers.get('location','')
            print(f"  → {key}: {r.status_code} -> {loc[:60]}")
    except Exception as e:
        pass
    time.sleep(0.1)

print(f"\nWorking: {len(working)}")
for k,v in working.items():
    print(f"  {k}: {v}")

