from fastapi import FastAPI
from parser.models import ParseRequest, ParsedReceipt
from parser.receipt_parser import parse_receipt

app = FastAPI(title="Billit Receipt Parser", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse", response_model=ParsedReceipt)
def parse(request: ParseRequest) -> ParsedReceipt:
    return parse_receipt(request)
