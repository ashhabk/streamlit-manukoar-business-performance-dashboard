import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
# ✅ THIS MUST COME BEFORE ANYTHING ELSE
st.set_page_config(page_title="Manukora Dashboard", layout="wide")

# Then inject your custom CSS
# Custom styling
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #f9f9f9, #f0f0f0);
            font-family: 'Segoe UI', sans-serif;
        }

        h1, h2, h3 {
            color: #f26522 !important;
            font-weight: 700;
        }

        .block-container {
            padding: 2rem 3rem;
        }

        .css-1kyxreq, .css-1v0mbdj {
            background-color: #ffffff !important;
            border-radius: 10px;
            padding: 1.2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }

        .metric-container {
            background-color: #fff8f2;
            border-radius: 8px;
            padding: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATA LOAD ---
df_a = pd.read_csv("data/final_dataset_a.csv")
df_b = pd.read_csv("data/final_dataset_b.csv")

df_a['created_at'] = pd.to_datetime(df_a['created_at'], errors='coerce')
df_a = df_a.dropna(subset=['created_at'])
df_a['month'] = df_a['created_at'].dt.to_period("M").astype(str)
df_b['month'] = pd.to_datetime(df_b['date'], errors='coerce').dt.to_period("M").astype(str)

# --- ETL ---
monthly_rev = df_a.groupby("month")["total_price"].sum().reset_index()
monthly_orders = df_a.groupby("month")["order_id"].count().reset_index(name="orders")
monthly_new_cust = df_a[df_a["order_rank"] == 1].groupby("month")["customer_id"].nunique().reset_index(name="new_customers")
summary = monthly_rev.merge(monthly_orders, on="month").merge(monthly_new_cust, on="month")
summary["month"] = pd.to_datetime(summary["month"])

latest = summary.iloc[-1]
prev = summary.iloc[-2]

delta_rev = (latest["total_price"] - prev["total_price"]) / prev["total_price"]
delta_orders = (latest["orders"] - prev["orders"]) / prev["orders"]
delta_newcust = (latest["new_customers"] - prev["new_customers"]) / prev["new_customers"]

# --- First Order Attribution ---
first_orders = df_a[df_a["order_rank"] == 1]
first_order_channel = first_orders.groupby("attributed_channel").agg(
    new_customers=("customer_id", "nunique"),
    revenue=("total_price", "sum")
).reset_index()

# --- Discount Categorization ---
def classify_discount(row):
    if row["total_price"] == 0 and row["discount_amount"] > 0:
        return "Free Gift"
    elif row["discount_amount"] > 0:
        return "Discount Applied"
    elif row["discount_amount"] == 0 and row["total_price"] > 0:
        return "No Discount"
    else:
        return "Other"

df_a["discount_status"] = df_a.apply(classify_discount, axis=1)
discount_impact = df_a.groupby("discount_status").agg(
    order_count=("order_id", "count"),
    total_revenue=("total_price", "sum"),
    avg_order_value=("total_price", "mean")
).reset_index()

# --- New vs Returning ---
df_a["customer_type"] = df_a["order_rank"].apply(lambda x: "New" if x == 1 else "Returning")
revenue_summary = df_a.groupby("customer_type").agg(
    order_count=("order_id", "count"),
    total_revenue=("total_price", "sum"),
    avg_order_value=("total_price", "mean")
).reset_index()

# --- Customer Segmentation ---
df_a = df_a.sort_values(["customer_id", "created_at"])
df_a["days_since_last"] = df_a.groupby("customer_id")["created_at"].diff().dt.days
cust_summary = df_a.groupby("customer_id").agg(
    order_count=("order_id", "count"),
    avg_days_between_orders=("days_since_last", "mean")
).reset_index()

def label_segment(row):
    if row["order_count"] == 1:
        return "One-Timer"
    elif row["avg_days_between_orders"] <= 15:
        return "Weekly Buyer"
    elif row["avg_days_between_orders"] <= 31:
        return "Bi-Weekly Buyer"
    elif row["avg_days_between_orders"] > 31:
        return "Infrequent Buyer"
    else:
        return "Monthly Buyer"

cust_summary["cluster_label"] = cust_summary.apply(label_segment, axis=1)
segment_counts = cust_summary["cluster_label"].value_counts().reset_index()
segment_counts.columns = ["Customer Type", "Count"]

# --- ROAS and CAC ---
xyz_orders = df_a[df_a['attributed_channel'] == 'XYZ media']
xyz_commission = xyz_orders.groupby('month')['total_price'].sum().reset_index()
xyz_commission['commission_spend'] = xyz_commission['total_price'] * 0.10

xyz_commission['flat_fee'] = 3000
xyz_commission['spend'] = xyz_commission['commission_spend'] + xyz_commission['flat_fee']
xyz_commission['channel'] = 'XYZ media'

xyz_spend = xyz_commission[['month', 'channel', 'spend']]
df_b_updated = pd.concat([df_b, xyz_spend], ignore_index=True)

acq = first_orders.groupby(["month", "attributed_channel"]).agg(
    new_customers=("customer_id", "nunique"),
    revenue=("total_price", "sum")
).reset_index()

spend = df_b_updated.groupby(["month", "channel"]).agg(spend=("spend", "sum")).reset_index()
roas_data = pd.merge(acq, spend, left_on=['month', 'attributed_channel'], right_on=['month', 'channel'], how='inner')
roas_data['CAC'] = roas_data['spend'] / roas_data['new_customers']
roas_data['ROAS'] = roas_data['revenue'] / roas_data['spend']

# === DASHBOARD ===
st.title("📊 Manukora Business Performance Dashboard")

# Scorecards
st.markdown("### 📌 Monthly KPIs")
col1, col2, col3 = st.columns(3)
col1.metric("This Month's Revenue", f"${latest['total_price']:,.0f}", f"{delta_rev:.1%}")
col2.metric("New Customers This Month", f"{latest['new_customers']:,.0f}", f"{delta_newcust:.1%}")
col3.metric("Total Orders This Month", f"{latest['orders']:,.0f}", f"{delta_orders:.1%}")

# --- Row 1 ---
col4, col5, col6 = st.columns(3)
with col4:
    fig1 = px.line(roas_data, x="month", y="ROAS", color="attributed_channel", title="ROAS Trend by Channel")
    st.plotly_chart(fig1, use_container_width=True)
with col5:
    fig2 = px.line(roas_data, x="month", y="CAC", color="attributed_channel", title="Customer Acquisition Cost (CAC)")
    st.plotly_chart(fig2, use_container_width=True)
with col6:
    fig3 = px.pie(segment_counts, names="Customer Type", values="Count", hole=0.4, title="Customer Segmentation")
    st.plotly_chart(fig3, use_container_width=True)

# --- Row 2 ---
col7, col8, col9 = st.columns(3)
with col7:
    fig4 = px.bar(first_order_channel, x="attributed_channel", y="new_customers", title="New Customers by Channel", text_auto=".2s", color_discrete_sequence=['#FF7F0E'])
    st.plotly_chart(fig4, use_container_width=True)
with col8:
    fig5 = px.bar(discount_impact, x="discount_status", y="avg_order_value", title="Average Order Value by Discount", text_auto=".2f", color_discrete_sequence=['#008080'])
    st.plotly_chart(fig5, use_container_width=True)
with col9:
    fig6 = px.bar(revenue_summary, x="customer_type", y="total_revenue", title="Revenue: New vs. Returning", text_auto=".2s")
    st.plotly_chart(fig6, use_container_width=True)

# --- Row 3: Trends Monthly ---
fig = go.Figure()

# Revenue (bar)
fig.add_trace(go.Bar(
    x=summary['month'],
    y=summary['total_price'],
    name='Revenue',
    marker_color='#2ECC71',  # Emerald Green
    yaxis='y'
))

# Orders (line)
fig.add_trace(go.Scatter(
    x=summary['month'],
    y=summary['orders'],
    mode='lines+markers',
    name='Orders',
    marker=dict(color='#5D3FD3'),  # Indigo
    yaxis='y2'
))

# New Customers (line)
fig.add_trace(go.Scatter(
    x=summary['month'],
    y=summary['new_customers'],
    mode='lines+markers',
    name='New Customers',
    marker=dict(color='#E74C3C'),  # Crimson Rose
    yaxis='y2'
))

# Layout
fig.update_layout(
    title='📈 Monthly Revenue, Orders, and Customer Growth',
    xaxis=dict(title='Month'),
    yaxis=dict(title='Revenue (USD)', showgrid=False),
    yaxis2=dict(title='Orders / New Customers', overlaying='y', side='right', showgrid=False),
    template='plotly_white',
    height=500,
    legend=dict(
        title='Metric',
        orientation='v',
        x=1.05,   # move legend to the right outside chart
        y=1,
        xanchor='left',
        yanchor='top',
        bgcolor='rgba(255,255,255,0)',
        borderwidth=0
    )
)
st.plotly_chart(fig, use_container_width=True)


st.markdown("---")
st.caption("Made by Ashhab K • Case Study: Manukora BI Analyst • Built with ❤️ using Streamlit")
