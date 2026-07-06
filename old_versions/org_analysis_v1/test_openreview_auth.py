#!/usr/bin/env python3
"""
Test whether an authenticated OpenReview client can download a gated PDF.

Reads credentials from env vars so the password never lands in a script or the
transcript:
    OPENREVIEW_USERNAME   (your login email)
    OPENREVIEW_PASSWORD

Usage:
    source /home/emanuelr/my_env/bin/activate
    OPENREVIEW_USERNAME='you@example.com' OPENREVIEW_PASSWORD='...' \
        python3 src/test_openreview_auth.py
"""

import os
import sys

import fitz  # pymupdf
import openreview.api as orv2

sys.path.insert(0, ".")
from ai_safety_orgs import find_orgs

TEST_ID = "iEeiZlTbts"  # a NeurIPS 2024 paper that 403'd anonymously


def main():
    user = os.environ.get("OPENREVIEW_USERNAME")
    pw = os.environ.get("OPENREVIEW_PASSWORD")
    if not (user and pw):
        sys.exit("Set OPENREVIEW_USERNAME and OPENREVIEW_PASSWORD env vars first.")

    print(f"Logging in as {user} ...")
    try:
        client = orv2.OpenReviewClient(baseurl="https://api2.openreview.net",
                                       username=user, password=pw)
        print(f"  authenticated (token acquired: {bool(client.token)})")
    except Exception as e:
        sys.exit(f"Login FAILED: {e}")

    print(f"Downloading PDF for {TEST_ID} ...")
    try:
        pdf = client.get_attachment("pdf", id=TEST_ID)  # field_name first, then id=
    except Exception as e:
        sys.exit(f"PDF download FAILED (auth didn't bypass the gate): {str(e)[:200]}")

    doc = fitz.open(stream=pdf, filetype="pdf")
    text = "".join(p.get_text() for p in doc)
    npages = len(doc)
    doc.close()
    print(f"  OK: {len(pdf)/1e6:.1f} MB, {npages} pages, {len(text)} chars extracted")

    hits = find_orgs(text[:2500], affiliation_field=True)
    orgs = list(hits["safety_only"]) + list(hits["safety_adjacent"])
    print(f"  orgs found on first page: {orgs or '(none)'}")
    print("\nSUCCESS — authenticated download works. Safe to run the full job.")


if __name__ == "__main__":
    main()
