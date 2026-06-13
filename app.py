import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import arabic_reshaper
from bidi.algorithm import get_display
import os

# ======================================================
# ✅ Arabic Fix (ONLY FOR CHARTS)
# ======================================================
def fix_arabic(text):
    if not text:
        return ""

    text = str(text)

    # reshape letters correctly
    reshaped = arabic_reshaper.reshape(text)

    # fix direction (RTL)
    bidi_text = get_display(reshaped)

    return bidi_text


# ======================================================
# ✅ Font Setup
# ======================================================
FONT_PATH = "NotoSansArabic-Regular.ttf"

if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    arabic_font = fm.FontProperties(fname=FONT_PATH)
else:
    arabic_font = None
    st.warning("Font not found")

plt.rcParams["axes.unicode_minus"] = False

# ======================================================
# ✅ PAGE RTL FIX (IMPORTANT)
# ======================================================
st.markdown(
    """
    <style>
    body {
        direction: RTL;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ======================================================
# ✅ Page
# ======================================================
st.set_page_config(layout="wide", page_title="Rework Dashboard")
st.title("📊 Rework Analysis Dashboard")

# ======================================================
# ✅ Upload
# ======================================================
c1, c2 = st.columns(2)

with c1:
    rework_file = st.file_uploader("📂 Rework File (Excel)", type=["xlsx"])

with c2:
    production_file = st.file_uploader("📂 Production File (Excel)", type=["xlsx"])

if not rework_file or not production_file:
    st.stop()

# ======================================================
# ✅ Read Excel
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
# ✅ Date
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
# ✅ Trend Chart (FIXED Arabic)
# ======================================================
fig_trend, ax = plt.subplots(figsize=(13, 5))

ax.plot(daily.index, daily["Rework %"], marker="o")

for x, y in zip(daily.index, daily["Rework %"]):
    ax.annotate(f"{y:.1f}%", (x, y), xytext=(0, 8),
                textcoords="offset points", ha="center", fontsize=9)

ax.set_title(fix_arabic("الاتجاه اليومي لنسبة إعادة التشغيل"),
             fontproperties=arabic_font)

ax.set_xlabel(fix_arabic("التاريخ"),
              fontproperties=arabic_font)

ax.set_ylabel(fix_arabic("نسبة إعادة التشغيل %"),
              fontproperties=arabic_font)

plt.xticks(rotation=45)

if arabic_font:
    for label in ax.get_xticklabels():
        label.set_fontproperties(arabic_font)
    for label in ax.get_yticklabels():
        label.set_fontproperties(arabic_font)

plt.tight_layout()
st.pyplot(fig_trend)

# ======================================================
# ✅ Pareto Chart (FIXED overlap + Arabic)
# ======================================================
pareto = rework_df["Problem"].value_counts().head(10)

# ✅ FIX DIRECTION
pareto = pareto.iloc[::-1]

cum_pct = pareto.cumsum() / pareto.sum() * 100

fig_pareto, ax2 = plt.subplots(figsize=(14, 6))

ax2.barh(range(len(pareto)), pareto.values)

labels = [fix_arabic(x) for x in pareto.index]

ax2.set_yticks(range(len(labels)))
ax2.set_yticklabels(labels,
                    fontsize=10,
                    fontproperties=arabic_font)

ax2.set_xlabel(fix_arabic("عدد الحالات"),
               fontproperties=arabic_font)

ax2.set_ylabel(fix_arabic("سبب إعادة التشغيل"),
               fontproperties=arabic_font)

# cumulative line
ax3 = ax2.twiny()
ax3.plot(cum_pct.values, range(len(pareto)),
         color="red", marker="o")

ax3.set_xlabel(fix_arabic("النسبة التراكمية %"),
               fontproperties=arabic_font)

plt.tight_layout()
st.pyplot(fig_pareto)
# ======================================================
# ✅ Tables (NO Arabic fix here!)
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
