import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Manukora Dashboard")

# === THEME STYLING ===
st.markdown("""
    <style>
        .stApp {
            background-color: #FFF7ED;
        }
        .main-title {
            background-color: #F26522;
            color: black;
            padding: 1rem;
            text-align: center;
            font-size: 30px;
            font-weight: 900;
            margin-bottom: 10px;
            border-radius: 5px;
        }
        .block-container {
            padding-top: 0rem;
            padding-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# === HEADER ===
st.markdown("<div class='main-title'>Manukora Business Performance Dashboard</div>", unsafe_allow_html=True)

# === LOAD DATA ===
df_a = pd.read_csv("data/final_dataset_a.csv")
df_b = pd.read_csv("data/final_dataset_b.csv")
df_a['created_at'] = pd.to_datetime(df_a['created_at'], errors='coerce')
df_a = df_a.dropna(subset=['created_at'])
df_a['month'] = df_a['created_at'].dt.to_period("M").astype(str)
df_b['month'] = pd.to_datetime(df_b['date'], errors='coerce').dt.to_period("M").astype(str)

# === SUMMARY DATA ===
monthly_rev = df_a.groupby("month")["total_price"].sum().reset_index()
monthly_orders = df_a.groupby("month")["order_id"].count().reset_index(name="orders")
monthly_new = df_a[df_a["order_rank"] == 1].groupby("month")["customer_id"].nunique().reset_index(name="new_customers")
summary = monthly_rev.merge(monthly_orders, on="month").merge(monthly_new, on="month")
summary["month"] = pd.to_datetime(summary["month"])
latest, prev = summary.iloc[-1], summary.iloc[-2]
delta_rev = (latest["total_price"] - prev["total_price"]) / prev["total_price"]
delta_orders = (latest["orders"] - prev["orders"]) / prev["orders"]
delta_newcust = (latest["new_customers"] - prev["new_customers"]) / prev["new_customers"]

# === FIRST ORDER ATTRIBUTION & XYZ MEDIA ===
first_orders = df_a[df_a["order_rank"] == 1]
xyz_orders = df_a[df_a['attributed_channel'] == 'XYZ media']
xyz_commission = xyz_orders.groupby('month')['total_price'].sum().reset_index()
xyz_commission['commission_spend'] = xyz_commission['total_price'] * 0.10
xyz_commission['flat_fee'] = 3000
xyz_commission['spend'] = xyz_commission['commission_spend'] + xyz_commission['flat_fee']
xyz_commission['channel'] = 'XYZ media'
df_b_updated = pd.concat([df_b, xyz_commission[['month', 'channel', 'spend']]], ignore_index=True)

# === ROAS / CAC ===
acq = first_orders.groupby(["month", "attributed_channel"]).agg(
    new_customers=("customer_id", "nunique"),
    revenue=("total_price", "sum")
).reset_index()
spend = df_b_updated.groupby(["month", "channel"]).agg(spend=("spend", "sum")).reset_index()
roas_data = pd.merge(acq, spend, left_on=['month', 'attributed_channel'], right_on=['month', 'channel'], how='inner')
roas_data['CAC'] = roas_data['spend'] / roas_data['new_customers']
roas_data['ROAS'] = roas_data['revenue'] / roas_data['spend']

# === DISCOUNT IMPACT ===
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

# === CUSTOMER SEGMENT ===
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

# === METRICS ===
col1, col2, col3 = st.columns(3)
col1.metric("Revenue", f"${latest['total_price']:,.0f}", f"{delta_rev:.1%}")
col2.metric("New Customers", f"{latest['new_customers']:,.0f}", f"{delta_newcust:.1%}")
col3.metric("Orders", f"{latest['orders']:,.0f}", f"{delta_orders:.1%}")

# === CHART ROW 1 ===
col4, col5, col6 = st.columns(3)
with col4:
    fig1 = px.line(roas_data, x="month", y="ROAS", color="attributed_channel", title="ROAS Trend by Channel")
    fig1.update_layout(height=350)
    st.plotly_chart(fig1, use_container_width=True)

with col5:
    fig2 = px.line(roas_data, x="month", y="CAC", color="attributed_channel", title="Customer Acquisition Cost (CAC)")
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)

with col6:
    fig3 = px.pie(segment_counts, names="Customer Type", values="Count", hole=0.4, title="Customer Segmentation")
    fig3.update_layout(height=350)
    st.plotly_chart(fig3, use_container_width=True)

# === CHART ROW 2 ===
col7, col8, col9 = st.columns(3)
with col7:
    fig4 = px.bar(first_orders.groupby("attributed_channel")["customer_id"].nunique().reset_index(name="new_customers"),
                  x="attributed_channel", y="new_customers", title="New Customers by Channel",
                  color_discrete_sequence=["#F26522"])
    fig4.update_layout(height=350)
    st.plotly_chart(fig4, use_container_width=True)

with col8:
    fig5 = px.bar(discount_impact, x="discount_status", y="avg_order_value", title="Average Order Value by Discount",
                  color_discrete_sequence=["#D35400"])
    fig5.update_layout(height=350)
    st.plotly_chart(fig5, use_container_width=True)

with col9:
    fig6 = px.bar(revenue_summary, x="customer_type", y="total_revenue", title="Revenue: New vs. Returning",
                  color_discrete_sequence=["#BA4A00"])
    fig6.update_layout(height=350)
    st.plotly_chart(fig6, use_container_width=True)

# === CHART ROW 3 ===
fig = go.Figure()
fig.add_trace(go.Bar(x=summary['month'], y=summary['total_price'], name='Revenue', marker_color='#F26522', yaxis='y'))
fig.add_trace(go.Scatter(x=summary['month'], y=summary['orders'], name='Orders', mode='lines+markers', yaxis='y2'))
fig.add_trace(go.Scatter(x=summary['month'], y=summary['new_customers'], name='New Customers', mode='lines+markers', yaxis='y2'))

fig.update_layout(
    title="📈 Monthly Revenue, Orders, and New Customers",
    xaxis=dict(title='Month'),
    yaxis=dict(title='Revenue (USD)', showgrid=False),
    yaxis2=dict(title='Orders / Customers', overlaying='y', side='right', showgrid=False),
    height=350
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Built with ❤️ by Ashhab – Manukora BI Analyst Case Study")
