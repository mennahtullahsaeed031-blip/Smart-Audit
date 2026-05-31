import streamlit as st
import pandas as pd
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Audit Dashboard", layout="wide")

# 2. قاعدة بيانات الضرائب (إضافة خيارات مرنة لكل الشركات)
TAX_OPTIONS = {
    "VAT (Standard 14%)": 0.14,
    "WHT Goods (1%)": 0.01,
    "WHT Services/Professional (5%)": 0.05,
    "Payroll Tax (Manual Entry)": "manual", # المستخدم هيدخل الرقم
    "Stamp Duty": 0.001,
    "Custom Tax %": "custom" # المستخدم يحدد النسبة
}

st.title("⚖️ Smart Financial Audit & Dashboard")

# 3. القائمة الجانبية (Sidebar)
st.sidebar.header("Configuration")
selected_taxes = st.sidebar.multiselect("Select Taxes to Audit:", list(TAX_OPTIONS.keys()))

# تحديد النسب يدوياً للضرائب المختارة
tax_rates = {}
for tax in selected_taxes:
    if TAX_OPTIONS[tax] == "manual":
        st.sidebar.info(f"ℹ️ {tax}: System will check against your Excel entries.")
        tax_rates[tax] = "manual"
    elif TAX_OPTIONS[tax] == "custom":
        tax_rates[tax] = st.sidebar.number_input(f"Enter Rate for {tax}:", value=0.10, format="%.3f")
    else:
        tax_rates[tax] = TAX_OPTIONS[tax]

file = st.sidebar.file_uploader("Upload Transaction File", type=["xlsx"])

if not file:
    st.info("💡 Please upload an Excel file to see the Dashboard.")
    st.stop()

# 4. معالجة البيانات
df = pd.read_excel(file)
df.columns = [str(c).strip() for c in df.columns] # تنظيف أسماء الأعمدة

# التأكد من وجود الأعمدة المطلوبة
amount_col = 'Amount' if 'Amount' in df.columns else df.columns[2] # محاولة تخمين العمود لو مش موجود
df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
df["Actual_VAT"] = pd.to_numeric(df.get("VAT", 0), errors="coerce").fillna(0)

# حساب الأخطاء
alert_cols = []
for tax, rate in tax_rates.items():
    col_name = f"{tax}_Alert"
    if rate == "manual":
        # في حالة كسب العمل اليدوي، بنشوف لو الخانة فاضية أو فيها فرق ضخم
        df[col_name] = df["Actual_VAT"] == 0
    else:
        expected = df[amount_col] * rate
        df[col_name] = abs(df["Actual_VAT"] - expected) > 1
    alert_cols.append(col_name)

df["Is_Duplicate"] = df.duplicated(subset=['Invoice_ID'], keep=False) if 'Invoice_ID' in df.columns else False

# --- 5. الداشبورد (رجعت تاني وبقوة) ---
st.subheader("📊 Executive Summary")
d1, d2, d3, d4 = st.columns(4)
d1.metric("Total Expenditure", f"{df[amount_col].sum():,.2f}")
d2.metric("Tax Issues", int(df[alert_cols].any(axis=1).sum() if alert_cols else 0))
d3.metric("Duplicates", int(df["Is_Duplicate"].sum()))
d4.metric("Audited Records", len(df))

st.divider()

# --- 6. الجدول (حل مشكلة applymap) ---
st.subheader("📋 Audit Detail Table")

def style_rows(row):
    has_issue = (any(row[col] for col in alert_cols) if alert_cols else False) or row["Is_Duplicate"]
    if has_issue:
        return ['background-color: #fff2f2; color: black'] * len(row)
    return [''] * len(row)

# استخدام apply بدلاً من applymap لمنع الـ AttributeError
st.dataframe(df.style.apply(style_rows, axis=1), use_container_width=True)

# 7. التصدير
output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False)
st.sidebar.download_button("📥 Download Audit Report", data=output.getvalue(), file_name="Final_Audit.xlsx")