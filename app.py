
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Manukora BI Dashboard", layout="wide")
st.title("📊 Manukora Marketing & Customer Dashboard")

df_a = pd.read_csv("data/final_dataset_a.csv")
df_b = pd.read_csv("data/final_dataset_b.csv")

df_a['created_at'] = pd.to_datetime(df_a['created_at'])
df_a['month'] = df_a['created_at'].dt.to_period('M').astype(str)
df_b['date'] = pd.to_datetime(df_b['date'])
df_b['month'] = df_b['date'].dt.to_period('M').astype(str)

monthly_summary = df_a.groupby('month').agg(
    revenue=('total_price', 'sum'),
    orders=('order_id', 'count'),
    new_customers=('customer_id', 'nunique')
).reset_index()

st.subheader("📌 Monthly KPIs")
col1, col2, col3 = st.columns(3)
if len(monthly_summary) > 1:
    current = monthly_summary.iloc[-1]
    previous = monthly_summary.iloc[-2]
    def growth(val, prev):
        if prev == 0: return "N/A"
        return f"{((val - prev) / prev) * 100:.1f}%"
    col1.metric("Revenue", f"${current['revenue']:,.2f}", growth(current['revenue'], previous['revenue']))
    col2.metric("Orders", f"{current['orders']:,}", growth(current['orders'], previous['orders']))
    col3.metric("New Customers", f"{current['new_customers']:,}", growth(current['new_customers'], previous['new_customers']))

st.subheader("📈 Monthly Trends")
fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly_summary['month'], y=monthly_summary['revenue'], mode='lines+markers', name='Revenue'))
fig.add_trace(go.Scatter(x=monthly_summary['month'], y=monthly_summary['orders'], mode='lines+markers', name='Orders'))
fig.add_trace(go.Scatter(x=monthly_summary['month'], y=monthly_summary['new_customers'], mode='lines+markers', name='New Customers'))
fig.update_layout(height=450, template='plotly_white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

st.subheader("📤 Attribution Breakdown (First Orders)")
first_orders = df_a[df_a['order_rank'] == 1]
channel_summary = first_orders.groupby('attributed_channel').agg(
    new_customers=('customer_id', 'nunique'),
    revenue=('total_price', 'sum')
).reset_index().sort_values(by='new_customers', ascending=False)
st.dataframe(channel_summary)

st.markdown("Made with ❤️ using Streamlit | Case Study: Manukora BI Analyst")
