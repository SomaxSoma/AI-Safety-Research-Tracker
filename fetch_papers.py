#!/usr/bin/env python3
"""Fetch all non-rejected, non-withdrawn ICLR 2026 papers from OpenReview."""

import openreview
import pandas as pd

client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")
print("Fetching ICLR 2026 papers...")

submissions = client.get_all_notes(invitation="ICLR.cc/2026/Conference/-/Submission")

papers = []
for paper in submissions:
    venue = paper.content.get("venueid", {}).get("value", "")
    if "Rejected" in venue or "Withdrawn" in venue or venue == "":
        continue
    papers.append({
        "id":           paper.id,
        "title":        paper.content.get("title", {}).get("value", ""),
        "authors":      "; ".join(paper.content.get("authors", {}).get("value", [])),
        "author_ids":   "; ".join(paper.content.get("authorids", {}).get("value", [])),
        "abstract":     paper.content.get("abstract", {}).get("value", ""),
        "keywords":     paper.content.get("keywords", {}).get("value", ""),
        "primary_area": paper.content.get("primary_area", {}).get("value", ""),
        "venue":        paper.content.get("venue", {}).get("value", ""),
        "tldr":         paper.content.get("TLDR", {}).get("value", ""),
        "url":          f"https://openreview.net/forum?id={paper.id}",
        "pdf_url":      f"https://openreview.net/pdf?id={paper.id}",
    })

print(f"Fetched {len(papers)} papers")

df = pd.DataFrame(papers)
df.to_csv("iclr2026_papers.csv", index=False)
print(f"Saved to iclr2026_papers.csv ({len(df.columns)} columns)")
