import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
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
acq = first_orders.groupby(["month", "attributed_channel"]).agg(
    new_customers=("customer_id", "nunique"),
    revenue=("total_price", "sum")
).reset_index()

spend = df_b.groupby(["month", "channel"]).agg(spend=("spend", "sum")).reset_index()
roas_data = pd.merge(acq, spend, left_on=["month", "attributed_channel"], right_on=["month", "channel"], how="inner")
roas_data["CAC"] = roas_data["spend"] / roas_data["new_customers"]
roas_data["ROAS"] = roas_data["revenue"] / roas_data["spend"]

# === DASHBOARD ===
st.title("📊 Business Performance Dashboard — Marketing, Revenue & Customer Insights")

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
    fig4 = px.bar(first_order_channel, x="attributed_channel", y="new_customers", title="New Customers by Channel", text_auto=".2s")
    st.plotly_chart(fig4, use_container_width=True)
with col8:
    fig5 = px.bar(discount_impact, x="discount_status", y="avg_order_value", title="Average Order Value by Discount", text_auto=".2f")
    st.plotly_chart(fig5, use_container_width=True)
with col9:
    fig6 = px.bar(revenue_summary, x="customer_type", y="total_revenue", title="Revenue: New vs. Returning", text_auto=".2s")
    st.plotly_chart(fig6, use_container_width=True)

# --- Row 3: Trends Monthly ---
col10, col11, col12 = st.columns(3)
with col10:
    fig7 = px.bar(summary, x="month", y="total_price", title="Monthly Revenue")
    st.plotly_chart(fig7, use_container_width=True)
with col11:
    fig8 = px.bar(summary, x="month", y="new_customers", title="Monthly New Customers")
    st.plotly_chart(fig8, use_container_width=True)
with col12:
    fig9 = px.bar(summary, x="month", y="orders", title="Monthly Orders")
    st.plotly_chart(fig9, use_container_width=True)

st.markdown("---")
st.caption("Made by Ashhab K • Case Study: Manukora BI Analyst • Built with ❤️ using Streamlit")
''')
