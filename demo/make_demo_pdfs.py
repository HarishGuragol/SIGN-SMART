"""Generates the demo agreements: demo/original_agreement.pdf and demo/revised_agreement.pdf.
Run: .venv_local/bin/python demo/make_demo_pdfs.py"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent
styles = getSampleStyleSheet()

HEAD = [
    "This Shop Rental Agreement is made at Bengaluru on 1 November 2026 between Mr. Ramesh Gowda "
    "(the \"Owner\") and Mr. Ravi Kumar, proprietor of Ravi General Stores (the \"Tenant\").",
]


def build(name, title, clauses):
    doc = SimpleDocTemplate(str(OUT / name), pagesize=A4, title=title)
    story = [Paragraph(title, styles["Title"])]
    for t in HEAD:
        story += [Paragraph(t, styles["BodyText"]), Spacer(1, 10)]
    for no, topic, text in clauses:
        story += [Paragraph(f"<b>Clause {no}. {topic}.</b> {text}", styles["BodyText"]), Spacer(1, 8)]
    story += [Spacer(1, 20), Paragraph("Signed: ____________ (Owner)      ____________ (Tenant)", styles["BodyText"])]
    doc.build(story)


ORIGINAL = [
    (1, "Premises", "The Owner lets the ground-floor shop No. 14, MG Road, Bengaluru, measuring 400 sq ft, to the Tenant for running a general store."),
    (2, "Term", "The tenancy is for a period of 36 months from 1 November 2026."),
    (3, "Rent", "The Tenant shall pay a monthly rent of Rs. 35,000 (Rupees Thirty Five Thousand only) on or before the 5th of every month."),
    (4, "Security Deposit", "The Tenant shall pay an interest-free security deposit of Rs. 3,00,000 (Rupees Three Lakh only). The deposit will be returned after the Owner is satisfied that the premises are in good condition. No time limit for refund is fixed."),
    (5, "Lock-in", "There is a lock-in period of 36 months. If the Tenant leaves before 36 months, the Tenant must pay the full rent for all remaining months."),
    (6, "Rent Increase", "The rent will not be increased during the term."),
    (7, "Late Payment", "If rent is paid after the 5th, a late fee of Rs. 500 per day will be charged. There is no maximum limit on the late fee."),
    (8, "Repairs", "Repairs and maintenance of the shop shall be carried out as mutually agreed from time to time."),
    (9, "Termination", "The Owner may terminate this agreement with 15 days' notice if the Tenant breaches any clause."),
]

REVISED = [
    (1, "Premises", "The Owner lets the ground-floor shop No. 14, MG Road, Bengaluru, measuring 400 sq ft, to the Tenant for running a general store."),
    (2, "Term", "The tenancy is for a period of 36 months from 1 November 2026."),
    (3, "Rent", "The Tenant shall pay a monthly rent of Rs. 35,000 (Rupees Thirty Five Thousand only) on or before the 5th of every month."),
    (4, "Security Deposit", "The Tenant shall pay an interest-free security deposit of Rs. 1,50,000 (Rupees One Lakh Fifty Thousand only). The deposit will be refunded within 30 days of the Tenant vacating the premises."),
    (5, "Lock-in", "There is a lock-in period of 12 months. If the Tenant leaves within the first 12 months, the Tenant must pay the full rent for the remaining months of the lock-in period."),
    (6, "Rent Increase", "The monthly rent shall increase by 15% at the end of every 12 months."),
    (7, "Late Payment", "If rent is paid after the 5th, a late fee of Rs. 500 per day will be charged. There is no maximum limit on the late fee."),
    (8, "Repairs", "Repairs and maintenance of the shop shall be carried out as mutually agreed from time to time."),
    (9, "Termination", "The Owner may terminate this agreement with 15 days' notice if the Tenant breaches any clause."),
]

build("original_agreement.pdf", "SHOP RENTAL AGREEMENT", ORIGINAL)
build("revised_agreement.pdf", "SHOP RENTAL AGREEMENT (REVISED)", REVISED)
print("created", OUT / "original_agreement.pdf", OUT / "revised_agreement.pdf")
