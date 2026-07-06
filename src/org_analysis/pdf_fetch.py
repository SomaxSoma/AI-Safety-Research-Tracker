#!/usr/bin/env python3
"""Fetch a paper PDF's bytes: authenticated OpenReview, or open PMLR / nips.cc."""

import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0 Safari/537.36"


def get_pdf_bytes(row, orclient) -> tuple[bytes | None, str]:
    """Return (pdf_bytes, source) or (None, reason). `row` needs id + pdf_url;
    `orclient` is an authenticated OpenReviewClient (or None to skip gated PDFs)."""
    url = str(row.get("pdf_url") or "")
    if "openreview.net" in url:
        if orclient is None:
            return None, "no_auth"
        try:
            return orclient.get_attachment("pdf", id=row["id"]), "openreview"
        except Exception as e:
            return None, f"openreview_err:{str(e)[:40]}"
    if "mlr.press" in url or "nips.cc" in url:
        src = "pmlr" if "mlr.press" in url else "nips.cc"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read(), src
        except Exception as e:
            return None, f"{src}_err:{str(e)[:40]}"
    return None, "no_pdf_url"
