import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# Clear old cache
st.cache_data.clear()

st.set_page_config(page_title="KRA Roastoast Auditor", layout="wide", page_icon="🧾")
st.title("🧾 KRA Fiscal Receipt Auditor — Roastoast")
st.markdown("**Transparent • Visually informative • 100% evidence-ready**  \n"
            "Only real receipts • Every reprint highlighted • Full audit trail")

# Load & clean data
@st.cache_data
def load_data():
    df = pd.read_csv('clean_receipts.csv')
    
    # Parse dates
    df['created_dt'] = pd.to_datetime(df['created'], format='%d/%m/%Y %I:%M:%S %p', errors='coerce')
    df['settled_dt'] = pd.to_datetime(df['settled'], format='%d/%m/%Y %I:%M:%S %p', errors='coerce')
    
    # Strict cleaning
    original = len(df)
    df = df.dropna(subset=['created_dt', 'order_number', 'receipt_id']).copy()
    df['date'] = df['created_dt'].dt.date
    
    # Force clean strings
    df['receipt_id'] = df['receipt_id'].astype(str)
    df['server'] = df['server'].fillna('Unknown').astype(str)
    df['table'] = df['table'].fillna('Unknown').astype(str)
    df['items'] = df['items'].fillna('').astype(str)
    
    # Bulletproof date filter
    df = df[df['date'].apply(lambda x: isinstance(x, datetime.date))].copy()
    
    st.sidebar.success(f"✅ Loaded {len(df):,} clean real receipts "
                       f"(dropped {original - len(df):,} invalid rows)")
    
    if len(df) == 0:
        st.error("No valid receipts found. Please re-run fix_csv.py first.")
        st.stop()
    
    return df

df = load_data()

# SIDEBAR FILTERS
st.sidebar.header("🔎 Filters")
valid_dates = [d for d in df['date'] if isinstance(d, datetime.date)]
min_date = min(valid_dates) if valid_dates else datetime.date(2026, 3, 1)
max_date = max(valid_dates) if valid_dates else datetime.date(2026, 3, 31)

date_range = st.sidebar.date_input("Date range", value=[min_date, max_date], format="DD/MM/YYYY")
server_filter = st.sidebar.multiselect("Server", options=sorted(df['server'].unique()))
table_filter = st.sidebar.multiselect("Table", options=sorted(df['table'].unique()))

# Apply filters
mask = (df['date'] >= date_range[0]) & (df['date'] <= date_range[1])
if server_filter: mask &= df['server'].isin(server_filter)
if table_filter:  mask &= df['table'].isin(table_filter)
filtered = df[mask].copy()

# TOP METRICS
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📄 Total Prints (KRA recorded)", f"{len(filtered):,}")
col2.metric("✅ Unique Orders (Real Sales)", f"{filtered['order_number'].nunique():,}")
col3.metric("🔴 Duplicate / Reprint Receipts", f"{len(filtered[filtered.duplicated(subset=['order_number'], keep=False)]):,}")
col4.metric("💰 Recorded Total", f"KSh {filtered['total'].sum():,.0f}")

real_total = filtered.drop_duplicates(subset=['order_number'])['total'].sum()
over = filtered['total'].sum() - real_total
col5.metric("🔴 OVERSTATEMENT to KRA", f"KSh {over:,.0f}", 
            delta=f"{(over / filtered['total'].sum() * 100):.1f}% over" if filtered['total'].sum() > 0 else None)

st.divider()

# TABS
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Duplicates (Evidence)", "📈 Timeline", "📋 Full Raw Data"])

with tab1:
    st.subheader("Sales Overview")
    colA, colB = st.columns(2)
    with colA:
        fig_pie = px.pie(filtered.drop_duplicates('order_number'), values='total', names='server', title="Real Sales by Server")
        st.plotly_chart(fig_pie, use_container_width=True)
    with colB:
        daily = filtered.groupby('date')['total'].sum().reset_index()
        daily_real = filtered.drop_duplicates('order_number').groupby('date')['total'].sum().reset_index()
        fig_line = px.line(daily, x='date', y='total', title="Daily Recorded vs Real Sales")
        fig_line.add_scatter(x=daily_real['date'], y=daily_real['total'], mode='lines', name='Real Sales', line=dict(dash='dash'))
        st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    st.subheader("🔴 Duplicate / Reprint Orders — These are the fake KRA sales")
    dup = filtered.groupby('order_number').agg(
        num_receipts=('receipt_id', 'count'),
        total=('total', 'first'),
        created=('created', 'first'),
        settled=('settled', 'first'),
        receipt_ids=('receipt_id', lambda x: ' | '.join(x.dropna().astype(str))),
        servers=('server', lambda x: ', '.join(x.dropna().astype(str))),
        tables=('table', lambda x: ', '.join(x.dropna().astype(str)))
    ).reset_index()
    
    dups_only = dup[dup['num_receipts'] > 1].sort_values('num_receipts', ascending=False)
    
    # FIXED: changed 'Reds_3' → 'Reds'
    st.dataframe(
        dups_only.style.background_gradient(subset=['num_receipts'], cmap='Reds'),
        use_container_width=True,
        hide_index=True
    )
    
    st.download_button("📥 Download Duplicate Evidence CSV (for KRA/lawyer)", 
                       dups_only.to_csv(index=False), 
                       "duplicate_orders_evidence.csv", mime="text/csv")

with tab3:
    st.subheader("Sales Timeline")
    daily_agg = filtered.groupby('date').agg(recorded=('total', 'sum'), real_orders=('order_number', 'nunique')).reset_index()
    real_daily = filtered.drop_duplicates('order_number').groupby('date')['total'].sum().reset_index()
    real_daily = real_daily.rename(columns={'total': 'real_total'})
    daily_agg = daily_agg.merge(real_daily, on='date', how='left').fillna(0)
    fig_bar = px.bar(daily_agg, x='date', y=['recorded', 'real_total'], barmode='group', title="Recorded vs Actual Daily Sales")
    st.plotly_chart(fig_bar, use_container_width=True)

with tab4:
    st.subheader("Full Raw Receipt Table")
    display_cols = ['filename', 'order_number', 'receipt_id', 'total', 'vat', 'created', 'settled', 'server', 'table', 'items']
    st.dataframe(filtered[display_cols], use_container_width=True, height=700)
    st.download_button("📥 Download Full Clean Evidence CSV", 
                       filtered.to_csv(index=False), 
                       "full_clean_receipts_evidence.csv", mime="text/csv")

st.caption("Built specifically for your Midrift KRA case • All numbers trace directly back to the original TXT files")