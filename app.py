import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os

# ======================================================
# Font Configuration (CLOUD FIX)
# ======================================================
FONT_FILENAME = "NotoSansArabic-Regular.ttf"
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), FONT_FILENAME)

if not os.path.exists(FONT_PATH):
    st.error(f"Error: '{FONT_FILENAME}' not found in the repository. Please upload it.")
    st.stop()

# Register font for Matplotlib
fm.fontManager.addfont(FONT_PATH)
prop = fm.FontProperties(fname=FONT_PATH)
plt.rcParams['font.family'] = prop.get_name()

# ======================================================
# Arabic Helper (RTL safe)
# ======================================================
def ar(text):
    """Reshapes and forces Right-To-Left base direction."""
    if pd.isna(text) or not str(text).strip():
        return ""
    # Force base_dir='R' for mixed English/Arabic/Numbers
    return get_display(arabic_reshaper.reshape(str(text)), base_dir='R')

# ======================================================
# Page config
# ======================================================
st.set_page_config(layout="wide", page_title="Rework Analysis Dashboard")
st.title("📊 Rework Analysis Dashboard")

# ======================================================
# Upload files
# ======================================================
c1, c2 = st.columns(2)
with c1:
    rework_file = st.file_uploader("📂 Rework File (Excel)", type=["xlsx"])
with c2:
    production_file = st.file_uploader("📂 Production File (Excel)", type=["xlsx"])

if not rework_file or not production_file:
    st.stop()

# ======================================================
# Data Processing
# ======================================================
def read_sap(file):
    raw = pd.read_excel(file, header=None)
    header_row = raw.apply(lambda r: r.astype(str).str.contains("Qty", case=False).any(), axis=1).idxmax()
    df = pd.read_excel(file, header=header_row)
    df.columns = df.columns.str.strip()
    return df

rework_df = read_sap(rework_file)
prod_df = read_sap(production_file)

rework_df["Date"] = pd.to_datetime(rework_df.iloc[:, 0], errors="coerce").dt.date
prod_df["Date"] = pd.to_datetime(prod_df.iloc[:, 0], errors="coerce").dt.date
rework_df.dropna(subset=["Date"], inplace=True)
prod_df.dropna(subset=["Date"], inplace=True)
rework_df["Problem"] = rework_df.iloc[:, 7].astype(str) + " " + rework_df.iloc[:, 8].astype(str)

# ======================================================
# Calculations
# ======================================================
daily = pd.concat([rework_df.groupby("Date").size(), prod_df.groupby("Date").size()], axis=1)
daily.columns = ["Rework", "Production"]
daily["Rework %"] = daily["Rework"] / daily["Production"] * 100
total_rework = int(daily["Rework"].sum())
total_production = int(daily["Production"].sum())
monthly_ratio = total_rework / total_production * 100

selected_day = st.selectbox("Select Day", daily.index, index=len(daily) - 1)
daily_ratio = daily.loc[selected_day, "Rework %"]

# ======================================================
# Charts
# ======================================================
fig_trend, ax = plt.subplots(figsize=(13, 5))
ax.plot(daily.index, daily["Rework %"], marker="o")
ax.set_title(ar("الاتجاه اليومي لنسبة إعادة التشغيل"), fontproperties=prop)
ax.set_xlabel(ar("التاريخ"), fontproperties=prop)
ax.set_ylabel(ar("نسبة إعادة التشغيل %"), fontproperties=prop)
plt.xticks(rotation=45)
st.pyplot(fig_trend)

# ======================================================
# Export Logic (Updated with NotoSansArabic)
# ======================================================
st.subheader("⬇️ Download Full Report")
with tempfile.TemporaryDirectory() as tmp:
    trend_img = os.path.join(tmp, "trend.png")
    fig_trend.savefig(trend_img, dpi=300)
    
    report = Image.new("RGB", (1600, 1200), "white")
    draw = ImageDraw.Draw(report)
    font = ImageFont.truetype(FONT_PATH, 32)
    
    # Use ar() function for all labels
    draw.text((50, 50), ar("تقرير إعادة التشغيل"), fill="black", font=font)
    
    # ... Continue with your drawing logic using 'font' and 'ar()' for text ...
    
    jpg_path = os.path.join(tmp, "report.jpg")
    report.save(jpg_path)
    with open(jpg_path, "rb") as f:
        st.download_button("Download Report (JPG)", f, "report.jpg")
