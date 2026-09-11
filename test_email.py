from mmf_engine.engine import analyze_ticker
from mailer.email_engine import get_email_language_preference, send_email_report
language=get_email_language_preference()
print(send_email_report(analyze_ticker("SOXL", mode="live"), lang=language))
