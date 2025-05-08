import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# === Load your data ===
df_a = pd.read_csv("data/dataset_a_clean.csv")
df_b = pd.read_csv("data/dataset_b_clean.csv")

# === Monthly aggregations ===
df_a['month'] = pd.to_datetime(df_a['created_at']).dt.to_period('M').astype(str)
monthly_summary = df_a.groupby('month').agg({
    'total_price': 'sum',
    'order_id': 'count',
    'customer_id': pd.Series.nunique
}).reset_index().rename(columns={
    'total_price': 'revenue',
    'order_id': 'orders',
    'customer_id': 'new_customers'
})

# === Current Month vs Previous ===
current = monthly_summary.iloc[-1]
previous = monthly_summary.iloc[-2]

def calc_change(current, previous):
    return round((current - previous) / previous * 100, 1)

revenue_change = calc_change(current.revenue, previous.revenue)
orders_change = calc_change(current.orders, previous.orders)
customers_change = calc_change(current.new_customers, previous.new_customers)

# === Dashboard ===
st.set_page_config(layout="wide")
st.title("📊 Manukora Marketing & Customer Dashboard")

# === Top KPIs ===
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Revenue", f"${current.revenue:,.2f}", f"{revenue_change}%")
with col2:
    st.metric("Orders", f"{current.orders:,}", f"{orders_change}%")
with col3:
    st.metric("New Customers", f"{current.new_customers:,}", f"{customers_change}%")

# === Trends ===
st.subheader("📈 Monthly Trends")
fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly_summary['month'], y=monthly_summary['revenue'], name='Revenue', mode='lines+markers'))
fig.add_trace(go.Scatter(x=monthly_summary['month'], y=monthly_summary['orders'], name='Orders', mode='lines+markers'))
fig.add_trace(go.Scatter(x=monthly_summary['month'], y=monthly_summary['new_customers'], name='New Customers', mode='lines+markers'))
fig.update_layout(height=400, template='plotly_white', legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True)

# === Attribution Breakdown ===
st.subheader("📌 Attribution Breakdown (First Orders)")
first_order = df_a[df_a['order_rank'] == 1]
channel_summary = first_order.groupby('attributed_channel').agg({
    'customer_id': 'nunique',
    'total_price': 'sum'
}).reset_index().rename(columns={'customer_id': 'new_customers', 'total_price': 'revenue'}).sort_values(by='revenue', ascending=False)
st.dataframe(channel_summary, use_container_width=True)

st.caption("Made with ❤️ using Streamlit | Case Study: Manukora BI Analyst")
