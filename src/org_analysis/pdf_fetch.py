#!/usr/bin/env python3
"""Fetch a paper PDF's bytes: authenticated OpenReview (v2 + v1), or open PMLR /
nips.cc.

OpenReview ran two incompatible APIs and conferences migrated at different times:
  - v2 (api2.openreview.net): ICLR 2024+, NeurIPS 2023+, ICML 2024+
  - v1 (api.openreview.net):  ICLR <=2023, NeurIPS 2021-2022 (legacy
    Blind_Submission ids the v2 client cannot resolve)
So we try the v2 client first and fall back to the v1 client. PMLR (ICML
2019-2022) and papers.nips.cc (NeurIPS 2019-2020) are plain authenticated-free
HTTP.
"""

import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0 Safari/537.36"


def get_pdf_bytes(row, orclient=None, orclient_v1=None) -> tuple[bytes | None, str]:
    """Return (pdf_bytes, source) or (None, reason). `row` needs id + pdf_url.

    orclient    — authenticated v2 client (openreview.api.OpenReviewClient)
    orclient_v1 — authenticated v1 client (openreview.Client) for legacy papers
    Either may be None; an OpenReview URL with neither client returns no_auth.
    """
    url = str(row.get("pdf_url") or "")
    if "openreview.net" in url:
        if orclient is None and orclient_v1 is None:
            return None, "no_auth"
        err = ""
        if orclient is not None:  # v2 first (current conferences)
            try:
                return orclient.get_attachment("pdf", id=row["id"]), "openreview_v2"
            except Exception as e:
                err = f"v2:{str(e)[:30]}"
        if orclient_v1 is not None:  # v1 fallback (Blind_Submission era)
            try:
                return orclient_v1.get_pdf(row["id"]), "openreview_v1"
            except Exception as e:
                err += f" v1:{str(e)[:30]}"
        return None, f"openreview_err:{err.strip()}"
    if "mlr.press" in url or "nips.cc" in url:
        src = "pmlr" if "mlr.press" in url else "nips.cc"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read(), src
        except Exception as e:
            return None, f"{src}_err:{str(e)[:40]}"
    return None, "no_pdf_url"
