import re
from typing import Optional
from .models import ParsedItem, ParsedReceipt, ParseRequest, Confidence, ValidationStatus

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Price at end of line: optional $, digits, dot or comma, exactly 2 decimal places
PRICE_RE        = re.compile(r'\$?\s*(\d{1,6}[.,]\d{2})\s*$')

# Leading quantity prefix: "2x", "3 X", "2×"
QTY_PREFIX_RE   = re.compile(r'^(\d+)\s*[xX×]\s*')

# Keywords — all case-insensitive
SUBTOTAL_RE     = re.compile(r'sub\s*[-–]?\s*total', re.I)
TAX_RE          = re.compile(r'\b(tax|hst|gst|pst|vat|sales\s+tax)\b', re.I)
TIP_RE          = re.compile(r'\b(tip|gratuity|service\s+charge)\b', re.I)
TOTAL_RE        = re.compile(r'\b(grand\s+total|total\s+due|amount\s+due|balance\s+due|total)\b', re.I)

# Lines that are pure noise: dashes, equals, asterisks
NOISE_RE        = re.compile(r'^[-=*#\s]+$')

# Trailing price pattern used to strip price from name
TRAILING_PRICE_RE = re.compile(r'\$?\s*\d+[.,]\d{2}\s*$')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_price(text: str) -> Optional[float]:
    m = PRICE_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(',', '.')
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def match_item(text: str) -> Optional[ParsedItem]:
    if NOISE_RE.match(text):
        return None

    price = extract_price(text)
    if price is None:
        return None

    # Strip trailing price to isolate name
    name_text = TRAILING_PRICE_RE.sub('', text).strip()

    # Extract and strip leading quantity prefix
    quantity = 1
    qty_match = QTY_PREFIX_RE.match(name_text)
    if qty_match:
        quantity = int(qty_match.group(1))
        name_text = name_text[qty_match.end():].strip()

    name = name_text.strip()
    if len(name) < 2:
        return None

    unit_price = round(price / quantity, 2)
    confidence = Confidence.low if len(name) < 4 else Confidence.high

    return ParsedItem(
        name=name,
        unit_price=unit_price,
        quantity=quantity,
        line_total=price,
        confidence=confidence,
        raw_text=text,
    )


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_receipt(request: ParseRequest) -> ParsedReceipt:
    lines = request.lines

    merchant: Optional[str] = None
    items: list[ParsedItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: Optional[float] = None

    for i, raw in enumerate(lines):
        text = raw.strip()
        if not text:
            continue

        # First few non-price lines are likely the merchant header
        if merchant is None and i < 4 and extract_price(text) is None:
            merchant = text
            continue

        # Subtotal must be checked before total (subtotal contains "total" too)
        if SUBTOTAL_RE.search(text):
            subtotal = extract_price(text)

        elif TAX_RE.search(text):
            val = extract_price(text)
            if val is not None:
                tax = round((tax or 0) + val, 2)

        elif TIP_RE.search(text):
            tip = extract_price(text)

        elif TOTAL_RE.search(text) and not SUBTOTAL_RE.search(text):
            total = extract_price(text)

        else:
            item = match_item(text)
            if item:
                items.append(item)

    # Validation
    item_sum = round(sum(it.line_total for it in items), 2)

    if subtotal is not None:
        diff = abs(item_sum - subtotal)
        if diff <= 0.02:
            status = ValidationStatus.valid
            mismatch_item_sum = None
            mismatch_claimed = None
        else:
            status = ValidationStatus.mismatch
            mismatch_item_sum = item_sum
            mismatch_claimed = subtotal
    else:
        status = ValidationStatus.incomplete
        mismatch_item_sum = None
        mismatch_claimed = None

    return ParsedReceipt(
        merchant=merchant,
        items=items,
        subtotal=subtotal,
        tax=tax,
        tip=tip,
        total=total,
        validation_status=status,
        mismatch_item_sum=mismatch_item_sum,
        mismatch_claimed_subtotal=mismatch_claimed,
    )
