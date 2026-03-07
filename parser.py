import re

patterns=[
re.compile(r"RM([\d\.]+)\s+to\s+(.+?)\s+is successful",re.I),
re.compile(r"RM([\d\.]+)\s+spent at\s+(.+)",re.I),
re.compile(r"RM([\d\.]+)\s+paid to\s+(.+)",re.I)
]

def detect_transfer(text):

    text=text.lower()

    keywords=[
    "transfer",
    "duitnow",
    " to ",
    "sent to",
    "received from"
    ]

    return any(k in text for k in keywords)


def parse_message(text):

    for p in patterns:

        m=p.search(text)

        if m:

            amount=float(m.group(1))
            merchant=m.group(2).strip()

            tx_type="transfer" if detect_transfer(text) else "expense"

            return amount,merchant,tx_type

    return None,None,None