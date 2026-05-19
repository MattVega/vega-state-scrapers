# Vega State Scrapers
State contractor license scrapers for all 48 US states — part of the Vega Estimating AI lead generation pipeline.

## What it does
- Scrapes contractor license databases across 48 US states (excl. FL & TX)
- Pulls contact info: company name, phone, address, trade, license number
- Supports Yelp Fusion API, YellowPages, state DPOR/L&I portals, and Socrata APIs
- Daily automation feeds new contacts into master Excel workbook

## States covered
WA, OR, CA, NV, AZ, CO, UT, ID, MT, WY, ND, SD, NE, KS, MN, IA, MO, WI, MI, IL, IN, OH, KY, TN, VA, NC, SC, GA, AL, MS, AR, LA, OK, NM, AK, HI, ME, VT, NH, MA, RI, CT, NY, NJ, PA, MD, DE, WV

## Setup
```bash
pip install requests pandas openpyxl beautifulsoup4
```
Set your `YELP_API_KEY` environment variable before running Yelp-based scrapers.
