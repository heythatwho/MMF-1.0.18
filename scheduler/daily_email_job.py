from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mmf_engine.engine import analyze_ticker
from mailer.email_engine import get_email_language_preference, send_email_report
WATCHLIST=["SOXL"]
def main():
    now=datetime.now(ZoneInfo("America/Los_Angeles"))
    if now.weekday()>=5:
        print("Weekend: skip email."); return
    language=get_email_language_preference()
    for ticker in WATCHLIST:
        print(ticker, language, send_email_report(analyze_ticker(ticker, mode="snapshot"), lang=language))
if __name__=="__main__": main()
