"""Ingestion (bronze layer): pull raw data from each source into data/raw.

Source access models differ, which is the single most important operational
fact about this project:

* FCC complaints (Socrata) ...... open, no auth required.
* Census ACS .................... free API key required.
* FCC Broadband Map (BDC) ....... FCC account + generated API token, OR a
                                  one-time bulk CSV download.
* Data centers (PNNL / LBNL) .... file downloads (no live API).
* Water (USGS) .................. file download (best-effort).
"""
