import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page setup
st.set_page_config(page_title="Manukora BI Dashboard", layout="wide")
st.title("📊 Manukora Marketing & Customer Dashboard")

# Load data
df_a = pd.read_csv("data/final_dataset_a.csv")

# Explicitly convert `created_at` to datetime, handle errors safely
df_a['created_at'] = pd.to_datetime(df_a['created_at'], errors='coerce')

# Drop rows where date conversion failed (optional, depending on your use case)
df_a = df_a.dropna(subset=['created_at'])

# Now continue
df_a['month'] = df_a['created_at'].dt.to_period('M').astype(str)
df_b = pd.read_csv("data/final_dataset_b.csv")

# === Preprocessing ===
df_a['month'] = df_a['created_at'].dt.to_period('M').astype(str)
df_b['month'] = pd.to_datetime(df_b['date']).dt.to_period('M').astype(str)

# == KPIs ==
monthly_rev = df_a.groupby('month')['total_price'].sum().reset_index()
monthly_orders = df_a.groupby('month')['order_id'].count().reset_index(name='orders')
monthly_new_cust = df_a[df_a['order_rank'] == 1].groupby('month')['customer_id'].nunique().reset_index(name='new_customers')

merged = monthly_rev.merge(monthly_orders, on='month').merge(monthly_new_cust, on='month')
merged['month'] = pd.to_datetime(merged['month'])

latest = merged.sort_values('month').iloc[-1]
prev = merged.sort_values('month').iloc[-2]

delta_rev = (latest['total_price'] - prev['total_price']) / prev['total_price']
delta_orders = (latest['orders'] - prev['orders']) / prev['orders']
delta_newcust = (latest['new_customers'] - prev['new_customers']) / prev['new_customers']

# == Channel Attribution (First Orders) ==
first_orders = df_a[df_a['order_rank'] == 1]
first_order_channel = first_orders.groupby('attributed_channel').agg(
    new_customers=('customer_id', 'nunique'),
    revenue=('total_price', 'sum')
).reset_index()

# == Discount Impact ==
def classify_discount(row):
    if row['total_price'] == 0 and row['discount_amount'] > 0:
        return "Free Gift"
    elif row['discount_amount'] > 0:
        return "Discount Applied"
    elif row['discount_amount'] == 0 and row['total_price'] > 0:
        return "No Discount"
    else:
        return "Other"

df_a['discount_status'] = df_a.apply(classify_discount, axis=1)
discount_impact = df_a.groupby('discount_status').agg(
    order_count=('order_id', 'count'),
    total_revenue=('total_price', 'sum'),
    avg_order_value=('total_price', 'mean')
).reset_index()

# == Revenue Split ==
revenue_split = df_a.copy()
revenue_split['customer_type'] = revenue_split['order_rank'].apply(lambda x: 'New' if x == 1 else 'Returning')
revenue_summary = revenue_split.groupby('customer_type').agg(
    order_count=('order_id', 'count'),
    total_revenue=('total_price', 'sum'),
    avg_order_value=('total_price', 'mean')
).reset_index()

# == Customer Segmentation ==
from datetime import timedelta
cust_orders = df_a.sort_values(['customer_id', 'created_at'])
cust_orders['days_since_last'] = cust_orders.groupby('customer_id')['created_at'].diff().dt.days
avg_days = cust_orders.groupby('customer_id').agg(
    order_count=('order_id', 'count'),
    avg_days_between_orders=('days_since_last', 'mean')
).reset_index()

def label_segment(row):
    if row['order_count'] == 1:
        return "One-Timer"
    elif row['avg_days_between_orders'] <= 15:
        return "Weekly Buyer"
    elif row['avg_days_between_orders'] <= 31:
        return "Bi-Weekly Buyer"
    elif row['avg_days_between_orders'] > 31:
        return "Infrequent Buyer"
    else:
        return "Monthly Buyer"

avg_days['cluster_label'] = avg_days.apply(label_segment, axis=1)
seg_counts = avg_days['cluster_label'].value_counts().reset_index()
seg_counts.columns = ['Customer Type', 'Count']

# === Streamlit App ===
st.set_page_config(layout='wide', page_title="Manukora Dashboard")

st.markdown("## 📊 Manukora Marketing & Customer Dashboard")

# === Scorecards ===
col1, col2, col3 = st.columns(3)
col1.metric("Revenue", f"${latest['total_price']:,.2f}", f"{delta_rev:.1%}")
col2.metric("Orders", f"{latest['orders']:,}", f"{delta_orders:.1%}")
col3.metric("New Customers", f"{latest['new_customers']:,}", f"{delta_newcust:.1%}")

# === Line Charts ===
st.markdown("### 📈 Monthly Trends")
fig = go.Figure()
fig.add_trace(go.Scatter(x=merged['month'], y=merged['total_price'], name="Revenue", mode='lines+markers'))
fig.add_trace(go.Scatter(x=merged['month'], y=merged['orders'], name="Orders", mode='lines+markers'))
fig.add_trace(go.Scatter(x=merged['month'], y=merged['new_customers'], name="New Customers", mode='lines+markers'))
fig.update_layout(template='plotly_dark', height=400)
st.plotly_chart(fig, use_container_width=True)

# === Grid Visuals ===
col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("#### 📌 Attribution Breakdown")
    st.dataframe(first_order_channel)

with col5:
    st.markdown("#### 💸 Discount Impact")
    st.dataframe(discount_impact)

with col6:
    st.markdown("#### 🔁 Revenue: New vs Returning")
    st.dataframe(revenue_summary)

# === Pie Chart ===
st.markdown("### 🧬 Customer Segmentation")
pie = go.Figure(go.Pie(labels=seg_counts['Customer Type'], values=seg_counts['Count'], hole=0.4))
pie.update_layout(showlegend=True, template='plotly_dark')
st.plotly_chart(pie, use_container_width=True)

# === Footer ===
st.markdown("---")
st.caption("Made by Ashhab K using Streamlit | Case Study: Manukora BI Analyst")
