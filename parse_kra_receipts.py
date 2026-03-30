import os
import re
import pandas as pd
from pathlib import Path

def parse_receipt_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    data = {'filename': os.path.basename(file_path)}

    # File timestamp (from header)
    ts = re.search(r'\[(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})\]', content)
    if ts:
        data['file_timestamp'] = ts.group(1)

    # Order number
    order = re.search(r'Order #: (\d+) DINE IN', content)
    if order:
        data['order_number'] = order.group(1)

    # Full Receipt ID (the key evidence)
    receipt = re.search(r'####RECEIPT ID: (.*?);', content, re.DOTALL)
    if receipt:
        data['receipt_id'] = receipt.group(1).strip()

    # Financials
    total = re.search(r'TOTAL:\s*(\d+\.\d{2})', content)
    if total:
        data['total'] = float(total.group(1))

    vat = re.search(r'VAT/Levy COLLECTED (\d+\.\d{2})', content)
    if vat:
        data['vat'] = float(vat.group(1))

    subtotal = re.search(r'Food Subtotal: (\d+\.\d{2})', content)
    if subtotal:
        data['subtotal'] = float(subtotal.group(1))

    cash = re.search(r'Cash Tendered: (\d+\.\d{2})', content)
    if cash:
        data['cash_tendered'] = float(cash.group(1))

    change = re.search(r'CHANGE:\s*(\d+\.\d{2})', content)
    if change:
        data['change'] = float(change.group(1))

    # Timestamps (Kenya DD/MM/YYYY format)
    created = re.search(r'Created: ([\d/]+ \d{1,2}:\d{2}:\d{2} [AP]M)', content)
    if created:
        data['created'] = created.group(1)

    settled = re.search(r'SETTLED: ([\d/]+ \d{1,2}:\d{2}:\d{2} [AP]M)', content)
    if settled:
        data['settled'] = settled.group(1)

    # Server / Table / Guests
    server = re.search(r'Server: (.*?) Station:', content)
    if server:
        data['server'] = server.group(1).strip()

    table = re.search(r'Table: (\d+)  Guests: (\d+)', content)
    if table:
        data['table'] = table.group(1)
        data['guests'] = table.group(2)

    # Items (all R_TRP lines)
    items = re.findall(r'R_TRP "(.*?)"', content)
    data['items'] = ' | '.join(items) if items else ''

    return data


def main():
    directory = r"C:\Users\Lenovo\Desktop\midrift kra case\roastoast out\out"   # ← CHANGE THIS TO YOUR FOLDER
    files = list(Path(directory).glob("*.txt"))
    print(f"Found {len(files)} TXT files")

    data_list = []
    for f in files:
        try:
            data_list.append(parse_receipt_file(f))
        except Exception as e:
            print(f"Error on {f.name}: {e}")

    df = pd.DataFrame(data_list)

    # Sort chronologically (filename starts with YYYYMMDDHHMMSS)
    df = df.sort_values(by='filename')

    # Save full audit trail
    df.to_csv('all_receipts_parsed.csv', index=False)
    print("✅ Full data saved → all_receipts_parsed.csv")

    # === DUPLICATE ANALYSIS ===
    if 'order_number' in df.columns and 'total' in df.columns:
        dup_summary = df.groupby('order_number').agg(
            num_receipts=('receipt_id', 'count'),
            total=('total', 'first'),
            created=('created', 'first'),
            receipt_ids=('receipt_id', lambda x: ' | '.join(x)),
            filenames=('filename', lambda x: ' | '.join(x))
        ).reset_index()

        duplicates = dup_summary[dup_summary['num_receipts'] > 1]
        duplicates.to_csv('duplicate_orders_summary.csv', index=False)

        print(f"🚨 Found {len(duplicates)} orders with multiple invoices (duplicates/reprints)")

        # Financial impact
        recorded = df['total'].sum()
        actual = df.drop_duplicates(subset=['order_number'])['total'].sum()
        overstatement = recorded - actual

        print(f"Recorded in KRA:  KSh {recorded:,.2f}")
        print(f"Actual sales:     KSh {actual:,.2f}")
        print(f"Overstatement:    KSh {overstatement:,.2f} ({len(duplicates)} fake entries)")

    print("\n🎯 Done! Open the two CSVs in Excel for your evidence package.")

if __name__ == "__main__":
    main()