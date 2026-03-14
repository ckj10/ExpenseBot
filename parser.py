import re

patterns=[

# GXBank / transfer
re.compile(r"RM([\d\.]+)\s+to\s+(.+?)\s+(?:is|was)\s+successful\.?", re.I),

# generic payments
re.compile(r"RM([\d\.]+)\s+spent at\s+(.+)",re.I),
re.compile(r"RM([\d\.]+)\s+paid to\s+(.+)",re.I),
re.compile(r"paid\s+rm([\d\.]+)\s+for\s+(.+)",re.I),
re.compile(r"You have paid RM([\d\.]+)\s+for\s+(.+)",re.I),

# CIMB card charge
re.compile(r"RM([\d\.]+)\s+is charged from your card .* to\s+(.+?)\.",re.I),

# alternative CIMB format
re.compile(r"RM([\d\.]+)\s+charged to your card .* at\s+(.+)",re.I),

# another possible variant
re.compile(r"RM([\d\.]+)\s+was charged .* to\s+(.+)",re.I),

# TNG ewallet
re.compile(r"RM([\d\.]+)\s+payment to\s+(.+)",re.I),

# payment received (no merchant)
re.compile(r"Payment of RM([\d\.]+)\s+is received", re.I),
re.compile(r"RM([\d\.]+).*(?:to|at|for)\s+(.+)",re.I)
]


def detect_transfer(text):

    text=text.lower()

    keywords=[
    "transfer",
    "duitnow",
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
