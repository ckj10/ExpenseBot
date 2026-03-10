import re

patterns=[
re.compile(r"RM([\d\.]+)\s+to\s+(.+?)\s+is successful",re.I),
re.compile(r"RM([\d\.]+)\s+spent at\s+(.+)",re.I),
re.compile(r"RM([\d\.]+)\s+paid to\s+(.+)",re.I),
re.compile(r"paid\s+rm([\d\.]+)\s+for\s+(.+)",re.I),

# payment received (no merchant)
re.compile(r"Payment of RM([\d\.]+)\s+is received", re.I)
]


def detect_transfer(text):

    text=text.lower()

    keywords=[
    "transfer",
    "duitnow",
    " to ",
    "sent to"
    ]

    return any(k in text for k in keywords)


def parse_message(text):

    for p in patterns:

        m=p.search(text)

        if m:

            amount=float(m.group(1))

            # pattern with merchant
            if len(m.groups()) >= 2:
                merchant=m.group(2).strip()

            else:
                merchant=None

            tx_type="transfer" if detect_transfer(text) else "expense"

            return amount,merchant,tx_type

    return None,None,None
