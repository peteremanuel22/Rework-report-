import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os

# ======================================================
# Arabic helper (RTL safe everywhere)
# ======================================================
def ar(text):
    return get_display(reshape(str(text)))

# ======================================================
# Font config (DEPLOYMENT SAFE)
# ======================================================
FONT_PATH = "fonts/DejaVuSans.ttf"

font_box   = ImageFont.truetype(FONT_PATH, 44)
font_title = ImageFont.truetype(FONT_PATH, 40)
font_hdr   = ImageFont.truetype(FONT_PATH, 34)
font_cell  = ImageFont.truetype(FONT_PATH, 32)

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
# Read SAP-style Excel
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
prod_df   = read_sap(production_file)

# ======================================================
# Date handling
# ======================================================
rework_df["Date"] = pd.to_datetime(rework_df.iloc[:, 0], errors="coerce").dt.date
prod_df["Date"]   = pd.to_datetime(prod_df.iloc[:, 0], errors="coerce").dt.date
rework_df.dropna(subset=["Date"], inplace=True)
prod_df.dropna(subset=["Date"], inplace=True)

# ======================================================
# Problem column
# ======================================================
rework_df["Problem"] = (
    rework_df.iloc[:, 7].astype(str) + " " +
    rework_df.iloc[:, 8].astype(str)
)

# ======================================================
# Calculations
# ======================================================
daily_rework = rework_df.groupby("Date").size()
daily_prod   = prod_df.groupby("Date").size()

daily = pd.concat([daily_rework, daily_prod], axis=1)
daily.columns = ["Rework", "Production"]
daily["Rework %"] = daily["Rework"] / daily["Production"] * 100

total_rework     = int(daily["Rework"].sum())
total_production = int(daily["Production"].sum())
monthly_ratio    = total_rework / total_production * 100

selected_day = st.selectbox("Select Day", daily.index, index=len(daily) - 1)
daily_ratio = daily.loc[selected_day, "Rework %"]

# ======================================================
# KPI UI
# ======================================================
k1, k2, k3 = st.columns(3)
k1.metric("Total Rework", total_rework)
k2.metric("Total Production", total_production)
k3.metric("Monthly Rework / Production", f"{monthly_ratio:.2f}%")

k4, k5 = st.columns(2)
k4.metric("Selected Day", selected_day.strftime("%Y-%m-%d"))
k5.metric("Daily Rework / Production", f"{daily_ratio:.2f}%")

# ======================================================
# Daily trend chart
# ======================================================
fig_trend, ax = plt.subplots(figsize=(13, 5))
ax.plot(daily.index, daily["Rework %"], marker="o")

for x, y in zip(daily.index, daily["Rework %"]):
    ax.annotate(
        f"{y:.1f}%",
        (x, y),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        fontsize=10
    )

ax.set_title(ar("الاتجاه اليومي لنسبة إعادة التشغيل"))
ax.set_xlabel(ar("التاريخ"))
ax.set_ylabel(ar("نسبة إعادة التشغيل %"))
plt.xticks(rotation=45)
plt.tight_layout()
st.pyplot(fig_trend)

# ======================================================
# Pareto chart
# ======================================================
pareto = rework_df["Problem"].value_counts()
cum_pct = pareto.cumsum() / pareto.sum() * 100
cutoff_index = list(pareto.index).index(cum_pct[cum_pct >= 80].index[0])

fig_pareto, ax2 = plt.subplots(figsize=(14, 6))
ax2.bar(range(len(pareto)), pareto.values, width=0.6)
ax2.set_xlabel(ar("سبب إعادة التشغيل"))
ax2.set_ylabel(ar("عدد الحالات"))
ax2.set_xticks(range(len(pareto)))
ax2.set_xticklabels(
    [ar(x) for x in pareto.index],
    rotation=45,
    ha="right",
    fontsize=9
)
ax2.invert_xaxis()
ax2.axvline(cutoff_index, linestyle="--", linewidth=2)

ax3 = ax2.twinx()
ax3.plot(range(len(pareto)), cum_pct.values, color="red", marker="o")
ax3.set_ylabel(ar("النسبة التراكمية %"))

plt.subplots_adjust(bottom=0.35)
plt.tight_layout()
st.pyplot(fig_pareto)

# ======================================================
# Tables (UI)
# ======================================================
month_tbl = rework_df["Problem"].value_counts().head(10).reset_index()
month_tbl.columns = ["Problem", "Value"]
month_tbl["Percentage"] = (month_tbl["Value"] / total_rework * 100).round(2)

day_df = rework_df[rework_df["Date"] == selected_day]
day_tbl = day_df["Problem"].value_counts().head(10).reset_index()
day_tbl.columns = ["Problem", "Value"]
day_tbl["Percentage"] = (day_tbl["Value"] / len(day_df) * 100).round(2)

st.subheader("Top Rework Problems")
u1, u2 = st.columns(2)
with u1:
    st.markdown("### Top 10 – Whole Month")
    st.dataframe(month_tbl, height=350, use_container_width=True)
with u2:
    st.markdown("### Top 10 – Selected Day")
    st.dataframe(day_tbl, height=350, use_container_width=True)

# ======================================================
# EXPORT – FULL REPORT (CHARTS + BIG TABLES)
# ======================================================
st.subheader("⬇️ Download Full Report")

with tempfile.TemporaryDirectory() as tmp:
    trend_img = os.path.join(tmp, "trend.png")
    pareto_img = os.path.join(tmp, "pareto.png")

    fig_trend.savefig(trend_img, dpi=300)
    fig_pareto.savefig(pareto_img, dpi=300)

    img_trend = Image.open(trend_img)
    img_pareto = Image.open(pareto_img)

    W = max(img_trend.width, img_pareto.width)
    H = img_trend.height + img_pareto.height + 1800
    report = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(report)

    y = 30
    box_h = 100

    def draw_box(text, y):
        draw.rectangle((30, y, W - 30, y + box_h), outline="black", width=3)
        tb = draw.textbbox((0, 0), text, font=font_box)
        draw.text(
            ((W - (tb[2] - tb[0])) // 2,
             y + (box_h - (tb[3] - tb[1])) // 2),
            text, fill="black", font=font_box
        )

    draw_box(f"Total Rework: {total_rework}", y); y += box_h + 10
    draw_box(f"Total Production: {total_production}", y); y += box_h + 10
    draw_box(f"Monthly Rework / Production: {monthly_ratio:.2f}%", y); y += box_h + 10
    draw_box(f"Selected Day: {selected_day}", y); y += box_h + 10
    draw_box(f"Daily Rework / Production: {daily_ratio:.2f}%", y); y += box_h + 40

    report.paste(img_trend, (0, y))
    y += img_trend.height + 30
    report.paste(img_pareto, (0, y))
    y += img_pareto.height + 60

    # ===== TABLES =====
    left_x = 40
    right_x = W // 2 + 20
    row_h = 60
    header_color = (220, 230, 245)

    draw.line([(W // 2, y - 20), (W // 2, y + 11 * row_h)],
              fill="black", width=3)

    def draw_table(x, y, title, df):
        draw.text((x, y), title, fill="black", font=font_title)
        y += 60

        col_titles = ["Problem", "Value", "Percentage"]
        col_widths = [700, 180, 220]

        cx = x
        for i, h in enumerate(col_titles):
            draw.rectangle(
                (cx, y, cx + col_widths[i], y + row_h),
                fill=header_color,
                outline="black", width=3
            )
            hb = draw.textbbox((0, 0), h, font=font_hdr)
            draw.text(
                (cx + (col_widths[i] - (hb[2] - hb[0])) // 2,
                 y + (row_h - (hb[3] - hb[1])) // 2),
                h, fill="black", font=font_hdr
            )
            cx += col_widths[i]

        y += row_h

        for _, r in df.iterrows():
            cx = x
            values = [ar(r["Problem"]), str(r["Value"]), f'{r["Percentage"]}%']
            for i, v in enumerate(values):
                draw.rectangle(
                    (cx, y, cx + col_widths[i], y + row_h),
                    outline="black", width=2
                )
                vb = draw.textbbox((0, 0), v, font=font_cell)
                draw.text(
                    (cx + (col_widths[i] - (vb[2] - vb[0])) // 2,
                     y + (row_h - (vb[3] - vb[1])) // 2),
                    v, fill="black", font=font_cell
                )
                cx += col_widths[i]
            y += row_h

    draw_table(left_x, y, "Top 10 – Whole Month", month_tbl)
    draw_table(right_x, y, "Top 10 – Selected Day", day_tbl)

    jpg_path = os.path.join(tmp, "rework_report.jpg")
    pdf_path = os.path.join(tmp, "rework_report.pdf")

    report.save(jpg_path)
    report.save(pdf_path, "PDF")

    with open(jpg_path, "rb") as f:
        st.download_button("Download Report (JPG)", f, "rework_report.jpg")
    with open(pdf_path, "rb") as f:
        st.download_button("Download Report (PDF)", f, "rework_report.pdf")
