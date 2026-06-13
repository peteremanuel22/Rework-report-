import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile
import os
from PIL import Image


# ======================================================
# ✅ Page Config
# ======================================================
st.set_page_config(layout="wide", page_title="Rework Dashboard")
st.title("📊 Rework Analysis Dashboard")

# ======================================================
# ✅ Upload Files
# ======================================================
c1, c2 = st.columns(2)

with c1:
    rework_file = st.file_uploader("📂 Rework File (Excel)", type=["xlsx"])

with c2:
    production_file = st.file_uploader("📂 Production File (Excel)", type=["xlsx"])

if not rework_file or not production_file:
    st.stop()

# ======================================================
# ✅ Read Excel (SAP style)
# ======================================================
def read_sap(file):
    raw = pd.read_excel(file, header=None)
    header_row = raw.apply(
        lambda r: r.astype(str).str.contains("Qty", case=False).any(), axis=1
    ).idxmax()
    df = pd.read_excel(file, header=header_row)
    df.columns = df.columns.str.strip()
    return df

rework_df = read_sap(rework_file)
prod_df = read_sap(production_file)

# ======================================================
# ✅ Date Handling
# ======================================================
rework_df["Date"] = pd.to_datetime(rework_df.iloc[:, 0], errors="coerce").dt.date
prod_df["Date"] = pd.to_datetime(prod_df.iloc[:, 0], errors="coerce").dt.date

rework_df.dropna(subset=["Date"], inplace=True)
prod_df.dropna(subset=["Date"], inplace=True)

# ======================================================
# ✅ Problem Column
# ======================================================
rework_df["Problem"] = (
    rework_df.iloc[:, 7].astype(str) + " " +
    rework_df.iloc[:, 8].astype(str)
)

# ======================================================
# ✅ Calculations
# ======================================================
daily_rework = rework_df.groupby("Date").size()
daily_prod = prod_df.groupby("Date").size()

daily = pd.concat([daily_rework, daily_prod], axis=1)
daily.columns = ["Rework", "Production"]

daily["Rework %"] = daily["Rework"] / daily["Production"] * 100

total_rework = int(daily["Rework"].sum())
total_production = int(daily["Production"].sum())
monthly_ratio = total_rework / total_production * 100

selected_day = st.selectbox("Select Day", daily.index, index=len(daily) - 1)
daily_ratio = daily.loc[selected_day, "Rework %"]

# ======================================================
# ✅ KPI
# ======================================================
k1, k2, k3 = st.columns(3)
k1.metric("Total Rework", total_rework)
k2.metric("Total Production", total_production)
k3.metric("Monthly %", f"{monthly_ratio:.2f}%")

k4, k5 = st.columns(2)
k4.metric("Selected Day", selected_day.strftime("%Y-%m-%d"))
k5.metric("Daily %", f"{daily_ratio:.2f}%")

# ======================================================
# ✅ TREND CHART (Plotly — Arabic works automatically)
# ======================================================
trend_data = daily.reset_index()

fig_trend = px.line(
    trend_data,
    x="Date",
    y="Rework %",
    markers=True,
    title="الاتجاه اليومي لنسبة إعادة التشغيل"
)

fig_trend.update_layout(
    xaxis_title="التاريخ",
    yaxis_title="نسبة إعادة التشغيل %",
)

st.plotly_chart(fig_trend, use_container_width=True)

# ======================================================
# ✅ PARETO CHART (Plotly — FIXED Arabic + NO overlap)
# ======================================================
pareto = rework_df["Problem"].value_counts().head(10).reset_index()
pareto.columns = ["Problem", "Count"]

pareto["Cum %"] = pareto["Count"].cumsum() / pareto["Count"].sum() * 100

fig_pareto = px.bar(
    pareto,
    x="Count",
    y="Problem",
    orientation="h",
    text="Count",
    title="تحليل باريتو لأسباب إعادة التشغيل"
)

# cumulative line
fig_pareto.add_scatter(
    x=pareto["Cum %"],
    y=pareto["Problem"],
    mode="lines+markers",
    name="النسبة التراكمية %",
    xaxis="x2"
)

fig_pareto.update_layout(
    xaxis=dict(title="عدد الحالات"),
    xaxis2=dict(title="النسبة التراكمية %", overlaying="x", side="top"),
    yaxis=dict(title="سبب إعادة التشغيل"),
    height=600
)

st.plotly_chart(fig_pareto, use_container_width=True)

# ======================================================
# ✅ Tables (Arabic works naturally — no fix needed)
# ======================================================
month_tbl = rework_df["Problem"].value_counts().head(10).reset_index()
month_tbl.columns = ["Problem", "Value"]
month_tbl["Percentage"] = (month_tbl["Value"] / total_rework * 100).round(2)

day_df = rework_df[rework_df["Date"] == selected_day]
day_tbl = day_df["Problem"].value_counts().head(10).reset_index()
day_tbl.columns = ["Problem", "Value"]
day_tbl["Percentage"] = (day_tbl["Value"] / len(day_df) * 100).round(2)

st.subheader("Top Rework Problems")

c1, c2 = st.columns(2)

with c1:
    st.markdown("### Top 10 – Whole Month")
    st.dataframe(month_tbl, use_container_width=True)

with c2:
    st.markdown("### Top 10 – Selected Day")
    st.dataframe(day_tbl, use_container_width=True)
# ======================================================
# ✅ EXPORT SECTION (SAFE VERSION — NO KALEIDO)
# ======================================================
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.subheader("⬇️ Download Reports")

with tempfile.TemporaryDirectory() as tmp:

    pdf_path = tmp + "/report.pdf"

    # Create PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 14)
    c.drawString(180, height - 40, "Rework Analysis Report")

    # KPIs
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 80, f"Total Rework: {total_rework}")
    c.drawString(50, height - 100, f"Total Production: {total_production}")
    c.drawString(50, height - 120, f"Monthly %: {monthly_ratio:.2f}%")

    c.drawString(50, height - 150, "Open app to view full interactive charts")

    c.save()

    # Download PDF
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 Download PDF Report",
            f,
            file_name="Rework_Report.pdf",
            mime="application/pdf"
        )
