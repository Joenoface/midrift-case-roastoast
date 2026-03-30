import pandas as pd

print("🔧 Fixing and cleaning your CSV...")

df = pd.read_csv('all_receipts_parsed.csv')

# === STRICT FILTER: Only real receipts ===
original_count = len(df)
df = df.dropna(subset=['receipt_id', 'order_number']).copy()
df['receipt_id'] = df['receipt_id'].astype(str)

print(f"✅ Kept {len(df):,} real receipts (removed {original_count - len(df):,} non-receipt logs)")

# === Safe duplicate analysis ===
dup_summary = df.groupby('order_number').agg(
    num_receipts=('receipt_id', 'count'),
    total=('total', 'first'),
    created=('created', 'first'),
    settled=('settled', 'first'),
    server=('server', 'first'),
    table=('table', 'first'),
    receipt_ids=('receipt_id', lambda x: ' | '.join(x)),
    filenames=('filename', lambda x: ' | '.join(x))
).reset_index()

duplicates = dup_summary[dup_summary['num_receipts'] > 1].copy()

# Save clean files
df.to_csv('clean_receipts.csv', index=False)
duplicates.to_csv('duplicate_orders_summary.csv', index=False)

# Financial impact
recorded = df['total'].sum()
actual = df.drop_duplicates(subset=['order_number'])['total'].sum()
overstatement = recorded - actual

print(f"\n📊 SUMMARY")
print(f"Real sales (unique orders) : {df['order_number'].nunique():,}")
print(f"Total prints recorded by KRA: {len(df):,}")
print(f"Duplicate / fake entries     : {len(duplicates):,}")
print(f"Recorded total               : KSh {recorded:,.2f}")
print(f"Actual total                 : KSh {actual:,.2f}")
print(f"🔴 OVERSTATEMENT             : KSh {overstatement:,.2f}")

print("\n🎉 Files ready:")
print("   → clean_receipts.csv")
print("   → duplicate_orders_summary.csv")