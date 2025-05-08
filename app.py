import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ✅ 1. Page Config (must be first)
st.set_page_config(page_title="Manukora Dashboard", layout="wide")

# ✅ 2. Load Data
df_a = pd.read_csv('dataset_a.csv')
df_b = pd.read_csv('dataset_b.csv')

df_a['created_at'] = pd.to_datetime(df_a['created_at'])
df_a['month'] = df_a['created_at'].dt.to_period('M').astype(str)
df_b['date'] = pd.to_datetime(df_b['date'])
df_b['month'] = df_b['date'].dt.to_period('M').astype(str)

# Cleaned for discount logic
df_a['discount_status'] = df_a.apply(
    lambda row: "Free Gift" if row['total_price'] == 0 and row['discount_amount'] > 0 else (
        "Discount Applied" if row['discount_amount'] > 0 else (
            "No Discount" if row['discount_amount'] == 0 else "Other"
        )
    ), axis=1
)

# ✅ 3. KPI METRICS
monthly_df = df_a.groupby('month').agg(
    revenue=('total_price', 'sum'),
    new_customers=('customer_id', lambda x: x[df_a.loc[x.index, 'order_rank'] == 1].nunique()),
    orders=('order_id', 'count')
).reset_index()

current_month = monthly_df['month'].max()
prev_month = monthly_df['month'].sort_values().iloc[-2]

latest_metrics = monthly_df[monthly_df['month'] == current_month].iloc[0]
prev_metrics = monthly_df[monthly_df['month'] == prev_month].iloc[0]

def calc_change(curr, prev):
    return (curr - prev) / prev if prev else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("This Month's Revenue", f"${latest_metrics.revenue:,.2f}", f"{calc_change(latest_metrics.revenue, prev_metrics.revenue)*100:.1f}%")
with col2:
    st.metric("New Customers This Month", f"{latest_metrics.new_customers:,}", f"{calc_change(latest_metrics.new_customers, prev_metrics.new_customers)*100:.1f}%")
with col3:
    st.metric("Total Orders This Month", f"{latest_metrics.orders:,}", f"{calc_change(latest_metrics.orders, prev_metrics.orders)*100:.1f}%")

st.markdown("## ")

# ✅ 4. ROW 1: Monthly Trends
rev_fig = px.bar(monthly_df, x='month', y='revenue', title="Monthly Revenue", text_auto=True)
cust_fig = px.line(monthly_df, x='month', y='new_customers', title="Monthly New Customers", markers=True)
ord_fig = px.line(monthly_df, x='month', y='orders', title="Monthly Orders", markers=True)

st.plotly_chart(rev_fig, use_container_width=True)
st.plotly_chart(cust_fig, use_container_width=True)
st.plotly_chart(ord_fig, use_container_width=True)

# ✅ 5. ROW 2: ROAS & CAC
first_orders = df_a[df_a['order_rank'] == 1]
acq = first_orders.groupby(['month', 'attributed_channel']).agg(
    new_customers=('customer_id', 'nunique'),
    revenue=('total_price', 'sum')
).reset_index()
spend = df_b.groupby(['month', 'channel']).agg(spend=('spend', 'sum')).reset_index()
merged = pd.merge(acq, spend, left_on=['month', 'attributed_channel'], right_on=['month', 'channel'], how='inner')
merged['CAC'] = merged['spend'] / merged['new_customers']
merged['ROAS'] = merged['revenue'] / merged['spend']

roas_fig = px.line(merged, x='month', y='ROAS', color='attributed_channel', title="ROAS Trend by Channel", markers=True)
cac_fig = px.line(merged, x='month', y='CAC', color='attributed_channel', title="Customer Acquisition Cost (CAC)", markers=True)

st.plotly_chart(roas_fig, use_container_width=True)
st.plotly_chart(cac_fig, use_container_width=True)

# ✅ 6. ROW 3: Other Insights

# First Order Attribution
ch_summary = first_orders.groupby('attributed_channel').agg(
    new_customers=('customer_id', 'nunique'),
    revenue=('total_price', 'sum')
).reset_index().sort_values('new_customers', ascending=False)

# Discount Impact
discount_impact = df_a.groupby('discount_status').agg(
    order_count=('order_id', 'count'),
    total_revenue=('total_price', 'sum'),
    avg_order_value=('total_price', 'mean')
).reset_index()

# Revenue New vs Returning
rev_split = df_a.copy()
rev_split['customer_type'] = rev_split['order_rank'].apply(lambda x: "New" if x == 1 else "Returning")
rev_summary = rev_split.groupby('customer_type').agg(
    order_count=('order_id', 'count'),
    total_revenue=('total_price', 'sum'),
    avg_order_value=('total_price', 'mean')
).reset_index()

# Segmentation Pie
customer_avg = df_a.groupby('customer_id')['created_at'].agg(['min', 'count']).reset_index()
order_counts = df_a.groupby('customer_id')['order_id'].count().reset_index(name='order_count')
customer_avg = customer_avg.merge(order_counts, on='customer_id')
customer_avg['cluster_label'] = pd.cut(
    customer_avg['order_count'],
    bins=[0,1,2,4,12,100],
    labels=['One-Timer','Infrequent Buyer','Bi-Weekly Buyer','Monthly Buyer','Weekly Buyer']
)
seg_pie = customer_avg['cluster_label'].value_counts().reset_index()
seg_pie.columns = ['Segment', 'Count']
pie_fig = px.pie(seg_pie, names='Segment', values='Count', title='Customer Segmentation', hole=0.5)

col4, col5, col6 = st.columns(3)
with col4:
    st.dataframe(ch_summary, use_container_width=True)
with col5:
    st.dataframe(discount_impact, use_container_width=True)
with col6:
    st.dataframe(rev_summary, use_container_width=True)

st.plotly_chart(pie_fig, use_container_width=True)

st.markdown("---")
st.caption("Made with ❤️ using Streamlit | Case Study: Manukora BI Analyst")
