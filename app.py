import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# === CONFIGURATION ===
st.set_page_config(page_title="Manukora Dashboard", layout="wide")
bg_color = "#FFF5EB"  # light beige color

# === CUSTOM STYLE ===
st.markdown(f"""
    <style>
        .stApp {{
            background-color: {bg_color};
        }}
        .block-container {{
            padding-top: 0rem;
        }}
        .title-bar {{
            background-color: #F26522;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 2rem;
        }}
        .title-bar h1 {{
            color: black;
            font-size: 32px;
            font-weight: 900;
            margin: 0;
        }}
        .chart-box {{
            background-color: white;
            border-radius: 12px;
            padding: 1.2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
            margin-bottom: 1rem;
        }}
    </style>
""", unsafe_allow_html=True)

# === TITLE ===
st.markdown("""
    <div class="title-bar">
        <h1>Manukora Business Performance Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

# === LOAD DATA ===
df_a = pd.read_csv("data/final_dataset_a.csv")
df_b = pd.read_csv("data/final_dataset_b.csv")
df_a['created_at'] = pd.to_datetime(df_a['created_at'], errors='coerce')
df_a = df_a.dropna(subset=['created_at'])
df_a['month'] = df_a['created_at'].dt.to_period("M").astype(str)
df_b['month'] = pd.to_datetime(df_b['date'], errors='coerce').dt.to_period("M").astype(str)

# === KPIs ===
monthly_rev = df_a.groupby("month")["total_price"].sum().reset_index()
monthly_orders = df_a.groupby("month")["order_id"].count().reset_index(name="orders")
monthly_new = df_a[df_a["order_rank"] == 1].groupby("month")["customer_id"].nunique().reset_index(name="new_customers")
summary = monthly_rev.merge(monthly_orders, on="month").merge(monthly_new, on="month")
summary["month"] = pd.to_datetime(summary["month"])

latest, prev = summary.iloc[-1], summary.iloc[-2]
delta_rev = (latest["total_price"] - prev["total_price"]) / prev["total_price"]
delta_orders = (latest["orders"] - prev["orders"]) / prev["orders"]
delta_newcust = (latest["new_customers"] - prev["new_customers"]) / prev["new_customers"]

# === METRICS ===
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Revenue", f"${latest['total_price']:,.0f}", f"{delta_rev:.1%}")
with col2:
    st.metric("New Customers", f"{latest['new_customers']:,.0f}", f"{delta_newcust:.1%}")
with col3:
    st.metric("Orders", f"{latest['orders']:,.0f}", f"{delta_orders:.1%}")

# === DATA TRANSFORMATIONS ===
first_orders = df_a[df_a["order_rank"] == 1]
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

# === DISCOUNTS ===
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

# === RETURNING VS NEW ===
df_a["customer_type"] = df_a["order_rank"].apply(lambda x: "New" if x == 1 else "Returning")
revenue_summary = df_a.groupby("customer_type").agg(
    order_count=("order_id", "count"),
    total_revenue=("total_price", "sum"),
    avg_order_value=("total_price", "mean")
).reset_index()

# === SEGMENTATION ===
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

# === ROW 1 ===
col4, col5, col6 = st.columns(3)
with col4:
    with st.container():
        fig1 = px.line(roas_data, x="month", y="ROAS", color="attributed_channel", title="ROAS Trend by Channel")
        fig1.update_layout(paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig1, use_container_width=True)

with col5:
    with st.container():
        fig2 = px.line(roas_data, x="month", y="CAC", color="attributed_channel", title="Customer Acquisition Cost (CAC)")
        fig2.update_layout(paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig2, use_container_width=True)

with col6:
    with st.container():
        fig3 = px.pie(segment_counts, names="Customer Type", values="Count", hole=0.4, title="Customer Segmentation")
        fig3.update_layout(paper_bgcolor="white")
        st.plotly_chart(fig3, use_container_width=True)

# === ROW 2 ===
col7, col8, col9 = st.columns(3)
with col7:
    fig4 = px.bar(first_orders.groupby("attributed_channel")["customer_id"].nunique().reset_index(name="new_customers"),
                  x="attributed_channel", y="new_customers", title="New Customers by Channel", text_auto=".2s",
                  color_discrete_sequence=["#FFC300"])
    fig4.update_layout(paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig4, use_container_width=True)

with col8:
    fig5 = px.bar(discount_impact, x="discount_status", y="avg_order_value", title="Average Order Value by Discount", text_auto=".2f",
                  color_discrete_sequence=["#581845"])
    fig5.update_layout(paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig5, use_container_width=True)

with col9:
    fig6 = px.bar(revenue_summary, x="customer_type", y="total_revenue", title="Revenue: New vs. Returning", text_auto=".2s",
                  color_discrete_sequence=["#F26522"])
    fig6.update_layout(paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig6, use_container_width=True)

# === ROW 3: Combined Monthly Trends ===
fig = go.Figure()
fig.add_trace(go.Bar(x=summary['month'], y=summary['total_price'], name='Revenue', marker_color='#F26522', yaxis='y'))
fig.add_trace(go.Scatter(x=summary['month'], y=summary['orders'], mode='lines+markers', name='Orders', marker=dict(color='#2E86AB'), yaxis='y2'))
fig.add_trace(go.Scatter(x=summary['month'], y=summary['new_customers'], mode='lines+markers', name='New Customers', marker=dict(color='#D7263D'), yaxis='y2'))
fig.update_layout(
    title='📈 Monthly Revenue, Orders, and New Customers',
    xaxis=dict(title='Month'),
    yaxis=dict(title='Revenue (USD)', showgrid=False),
    yaxis2=dict(title='Orders / Customers', overlaying='y', side='right', showgrid=False),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=500,
    legend=dict(title='Metric', x=1.05, y=1)
)
st.plotly_chart(fig, use_container_width=True)

# === FOOTER ===
st.markdown("---")
st.caption("Made by Ashhab K • Case Study: Manukora BI Analyst • Built with ❤️ using Streamlit")
