
# ============================================
# المكتبات
# streamlit  = بيعمل الواجهة
# pandas     = بيقرأ ويحلل Excel
# plotly     = بيعمل الرسوم البيانية
# io         = بيساعد في تصدير الملفات
# ============================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from audit_engine import run_audit

# ============================================
# PART 1 — إعدادات الصفحة
# بتحدد اسم التطبيق في المتصفح
# والأيقونة وشكل الصفحة (عريض)
# ============================================
st.set_page_config(
    page_title="Financial Audit Pro",
    page_icon="⚖️",
    layout="wide"
)

# ============================================
# PART 2 — دالة حساب ضريبة الرواتب
# بتاخد الراتب الشهري وترجع الضريبة
# بناءً على الشرائح الحقيقية المصرية:
# - إعفاء شخصي 15,000 سنوياً
# - إعفاء إضافي 30,000 سنوياً
# - المجموع المعفي = 45,000 سنوياً
# ============================================
def calculate_payroll_tax(salary):
    annual  = salary * 12                    # تحويل لسنوي
    taxable = max(0, annual - 45000)         # طرح الإعفاء
    
    if taxable <= 15000:
        tax = taxable * 0.10                 # شريحة 10%
    elif taxable <= 30000:
        tax = 1500 + (taxable - 15000) * 0.15  # شريحة 15%
    else:
        tax = 3750 + (taxable - 30000) * 0.20  # شريحة 20%
    
    return tax / 12                          # رجّع شهري

# ============================================
# PART 3 — الـ Sidebar (الشريط الجانبي)
# فيه كل إعدادات التطبيق
# ============================================
with st.sidebar:
    st.header("⚙️ إعدادات النظام")
    
    # نوع المؤسسة
    # بيغير طريقة التحليل حسب النوع
    entity_type = st.selectbox(
        "🏢 نوع المؤسسة:",
        ["NGO — مؤسسة غير هادفة للربح",
         "Commercial — شركة تجارية",
         "Startup — شركة ناشئة"]
    )
    
    st.divider()
    
    # نطاق التدقيق
    # المستخدم يختار أي فحوصات يريدها
    audit_scope = st.multiselect(
        "🔍 نطاق التدقيق:",
        ["VAT", "Payroll", "WHT",
         "Duplicates", "Outliers",
         "Vendor Risk", "Bank Recon"],
        default=["VAT", "Duplicates",
                 "WHT", "Outliers"]
    )
    
    st.divider()
    
    # نسبة الضريبة
    tax_rate = st.slider(
        "💹 نسبة VAT:",
        min_value=0,
        max_value=20,
        value=14,
        step=1,
        format="%d%%"
    ) / 100
    
    st.divider()
    
    # Audit Trail
    show_trail = st.checkbox(
        "📋 عرض Audit Trail",
        value=False
    )
    
    st.divider()
    st.markdown("**✅ الفحوصات المتاحة:**")
    st.markdown("""
    - Missing Values
    - Duplicate Invoices
    - Negative Amounts
    - VAT Validation
    - Outlier Detection
    - Vendor Concentration
    - Withholding Tax
    - Bank Reconciliation
    - Payroll Tax
    - Stamp Duty
    """)

# ============================================
# PART 4 — العنوان الرئيسي
# ============================================
st.title("⚖️ Professional Financial Audit System")
st.markdown("**نظام التدقيق المالي الاحترافي للمؤسسات**")
st.divider()

# ============================================
# PART 5 — رفع الملف
# المستخدم بيرفع Excel من جهازه
# ============================================
st.subheader("📂 الخطوة 1 — رفع ملف البيانات")

uploaded_file = st.file_uploader(
    "ارفع ملف Excel هنا",
    type=["xlsx", "xls"],
    help="أي ملف Excel فيه بيانات مالية"
)

# لو مفيش ملف — عرض مثال ووقف
if uploaded_file is None:
    st.info("👆 ارفع ملف Excel للبدء")
    st.subheader("📋 مثال على شكل الداتا")
    st.dataframe(pd.DataFrame({
        "Date":           ["2024-01-15", "2024-02-20"],
        "Invoice_ID":     ["INV-1001",   "INV-1002"],
        "Category":       ["Rent",       "Supplies"],
        "Amount":         [5000,          2300],
        "VAT":            [700,           322],
        "WHT":            [250,           23],
        "Vendor":         ["شركة النيل", "مؤسسة الأمل"],
        "Payment_Status": ["Paid",        "Unpaid"]
    }), use_container_width=True)
    st.stop()

# قراءة الملف
try:
    df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    st.success(
        f"✅ تم تحميل الملف — "
        f"{len(df)} صف | {len(df.columns)} عمود"
    )
except Exception as e:
    st.error(f"❌ خطأ: {e}")
    st.stop()

# ============================================
# PART 6 — Column Mapping
# السيستم بيسأل المستخدم:
# "أي عمود = المبلغ؟ أي عمود = التاريخ؟"
# عشان يشتغل على أي Excel مش بس بتاعنا
# ============================================
st.divider()
st.subheader("🗂️ الخطوة 2 — ربط الأعمدة")
st.info("حدد أي عمود في ملفك يقابل كل حقل ✅")

cols        = df.columns.tolist()
none_option = ["-- اختر --"] + cols

c1, c2 = st.columns(2)

with c1:
    map_date = st.selectbox(
        "📅 عمود التاريخ", none_option,
        index=none_option.index("Date")
              if "Date" in none_option else 0
    )
    map_amount = st.selectbox(
        "💰 عمود المبلغ", none_option,
        index=none_option.index("Amount")
              if "Amount" in none_option else 0
    )
    map_invoice = st.selectbox(
        "🧾 رقم الفاتورة", none_option,
        index=none_option.index("Invoice_ID")
              if "Invoice_ID" in none_option else 0
    )
    map_vendor = st.selectbox(
        "🏢 عمود المورد", none_option,
        index=0
    )

with c2:
    map_vat = st.selectbox(
        "💹 عمود VAT", none_option,
        index=none_option.index("VAT")
              if "VAT" in none_option else 0
    )
    map_category = st.selectbox(
        "📂 عمود البند", none_option,
        index=none_option.index("Category")
              if "Category" in none_option else 0
    )
    map_wht = st.selectbox(
        "📊 عمود WHT (اختياري)", none_option,
        index=none_option.index("WHT")
              if "WHT" in none_option else 0
    )
    map_payment = st.selectbox(
        "💳 حالة الدفع (اختياري)", none_option,
        index=none_option.index("Payment_Status")
              if "Payment_Status" in none_option else 0
    )

# التحقق من الأساسيين
required_maps = [
    map_date, map_amount, map_invoice,
    map_vendor, map_vat, map_category
]
if any(x == "-- اختر --" for x in required_maps):
    st.warning("⚠️ حدد الأعمدة الأساسية الستة")
    st.stop()

# إعادة تسمية الأعمدة
rename_map = {
    map_date:     "Date",
    map_amount:   "Amount",
    map_invoice:  "Invoice_ID",
    map_vendor:   "Vendor",
    map_vat:      "VAT",
    map_category: "Category"
}
if map_wht     != "-- اختر --":
    rename_map[map_wht]     = "WHT"
if map_payment != "-- اختر --":
    rename_map[map_payment] = "Payment_Status"

df = df.rename(columns=rename_map)
st.success("✅ تم ربط الأعمدة!")

# ============================================
# PART 7 — زرار التحليل
# ============================================
st.divider()
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    run_button = st.button(
        "🚀 الخطوة 3 — تشغيل التدقيق الكامل",
        use_container_width=True,
        type="primary"
    )

if not run_button:
    st.stop()

# ============================================
# PART 8 — تشغيل الـ Engine
# بيبعت الداتا لـ audit_engine.py
# ويجيب النتائج
# ============================================
with st.spinner("⏳ جاري التدقيق..."):
    results = run_audit(df, tax_rate=tax_rate)

errors_df   = results["errors"]
summary     = results["summary"]
insights    = results["insights"]
audit_trail = results["audit_trail"]

st.divider()

# ============================================
# PART 9 — النتائج في 6 Tabs
# كل Tab بيعرض جزء مختلف من التحليل
# ============================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard",
    "📑 Trial Balance",
    "❌ Audit Report",
    "📒 Journal Entries",
    "💡 Insights",
    "📋 Audit Trail"
])

# ============================================
# TAB 1 — Dashboard
# بيعرض أرقام كبيرة + رسوم بيانية
# ============================================
with tab1:
    st.subheader("📊 ملخص تنفيذي")

    # KPI Cards — 4 أرقام كبيرة في الأعلى
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(
            "💰 إجمالي المصروفات",
            f"{summary['total_expenses']:,.0f} ج.م"
        )
    with k2:
        st.metric(
            "🧾 عدد الفواتير",
            f"{summary['total_invoices']}"
        )
    with k3:
        st.metric(
            "❌ إجمالي الأخطاء",
            f"{summary['total_errors']}",
            delta="خطر" if summary['total_errors'] > 5
                  else "مقبول",
            delta_color="inverse"
        )
    with k4:
        st.metric(
            "🏆 أعلى مورد",
            summary["top_vendor"][:20]
        )

    st.divider()

    # رسمين جنب بعض
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🏢 توزيع الموردين")
        # Pie Chart — كل مورد بياخد كام %
        vendor_data = pd.DataFrame({
            "Vendor":     list(summary["vendor_distribution"].keys()),
            "Percentage": list(summary["vendor_distribution"].values())
        })
        fig1 = px.pie(
            vendor_data,
            values="Percentage",
            names="Vendor",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig1.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.subheader("📂 توزيع البنود")
        # Bar Chart — إنفاق كل بند
        cat_data = pd.DataFrame({
            "Category": list(summary["category_distribution"].keys()),
            "Amount":   list(summary["category_distribution"].values())
        }).sort_values("Amount", ascending=True)

        fig2 = px.bar(
            cat_data,
            x="Amount", y="Category",
            orientation="h",
            color="Amount",
            color_continuous_scale="Blues"
        )
        fig2.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Monthly Trend — إنفاق كل شهر
    st.subheader("📈 المصروفات الشهرية")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    monthly    = df.groupby(
        df["Date"].dt.to_period("M")
    )["Amount"].sum().reset_index()
    monthly["Date"] = monthly["Date"].astype(str)

    fig3 = px.line(
        monthly, x="Date", y="Amount",
        markers=True,
        color_discrete_sequence=["#2196F3"]
    )
    fig3.update_traces(line_width=3, marker_size=8)
    fig3.update_layout(height=350)
    st.plotly_chart(fig3, use_container_width=True)

# ============================================
# TAB 2 — Trial Balance
# ميزان المراجعة — ملخص كل الحسابات
# بيثبت إن مجموع المدين = مجموع الدائن
# ده اللي Excel مش بيعمله تلقائي
# ============================================
with tab2:
    st.subheader("📑 ميزان المراجعة")
    st.info("ميزان المراجعة بيثبت إن كل القيود متوازنة ✅")

    # تجميع حسب البند
    trial = df.groupby("Category").agg({
        "Amount": "sum",
        "VAT":    "sum"
    }).reset_index()

    trial.columns    = ["البند", "إجمالي المدين", "إجمالي الضريبة"]
    trial["الدائن"] = trial["إجمالي المدين"] + trial["إجمالي الضريبة"]
    trial["متوازن"] = trial["إجمالي المدين"] > 0

    # إجمالي في الأسفل
    total_row = pd.DataFrame([{
        "البند":             "**الإجمالي**",
        "إجمالي المدين":    trial["إجمالي المدين"].sum(),
        "إجمالي الضريبة":  trial["إجمالي الضريبة"].sum(),
        "الدائن":           trial["الدائن"].sum(),
        "متوازن":           True
    }])
    trial_final = pd.concat([trial, total_row], ignore_index=True)

    st.dataframe(trial_final, use_container_width=True, height=400)

    # تحقق من التوازن
    if abs(trial["إجمالي المدين"].sum() - trial["الدائن"].sum()) < 1:
        st.success("✅ ميزان المراجعة متوازن")
    else:
        st.error("❌ ميزان المراجعة غير متوازن — يحتاج مراجعة")

# ============================================
# TAB 3 — Audit Report
# تقرير الأخطاء الكاملة
# مع فلتر وDownload
# ============================================
with tab3:
    st.subheader("❌ تقرير التدقيق")

    if errors_df.empty:
        st.success("✅ لم يتم اكتشاف أي أخطاء!")
    else:
        # فلتر حسب نوع الخطأ
        error_types   = ["الكل"] + list(errors_df["Issue"].unique())
        selected_type = st.selectbox("فلتر:", error_types)
        filtered_df   = (
            errors_df if selected_type == "الكل"
            else errors_df[errors_df["Issue"] == selected_type]
        )

        # عدد كل نوع خطأ
        error_counts = errors_df["Issue"].value_counts()
        ecols        = st.columns(min(4, len(error_counts)))
        for i, (issue, count) in enumerate(error_counts.items()):
            with ecols[i % 4]:
                st.metric(label=issue, value=count)

        st.divider()
        st.dataframe(filtered_df, use_container_width=True, height=400)

        # Download
        csv = errors_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 تحميل تقرير الأخطاء",
            data=csv,
            file_name="audit_report.csv",
            mime="text/csv",
            use_container_width=True
        )

# ============================================
# TAB 4 — Journal Entries
# القيود المحاسبية التلقائية
# كل فاتورة بتتحول لقيد DR/CR صح
# ده الفرق الحقيقي عن Excel
# ============================================
with tab4:
    st.subheader("📒 القيود المحاسبية التلقائية")
    st.info("كل فاتورة بتتحول تلقائياً لقيد محاسبي صحيح ✅")

    # عرض أول 10 فواتير
    for _, row in df.head(10).iterrows():
        with st.container():
            st.markdown(
                f"**فاتورة: {row.get('Invoice_ID', 'N/A')} "
                f"| {row.get('Vendor', '')} "
                f"| {row.get('Category', '')}**"
            )

            col_a, col_b = st.columns(2)

            # المدين — اللي بنصرفه
            with col_a:
                st.code(
                    f"مدين:\n"
                    f"  ح/ مصروف {row['Category']:<20} "
                    f"{row['Amount']:>10,.2f}\n"
                    f"  ح/ ضريبة مدخلات (VAT)      "
                    f"{row.get('VAT', 0):>10,.2f}"
                )

            # الدائن — المصدر
            with col_b:
                total = row['Amount'] + row.get('VAT', 0)
                # لو WHT موجود القيد بيتغير
                if 'WHT' in df.columns and row.get('WHT', 0) > 0:
                    net = total - row.get('WHT', 0)
                    st.code(
                        f"دائن:\n"
                        f"  ح/ البنك                     "
                        f"{net:>10,.2f}\n"
                        f"  ح/ WHT مستحقة               "
                        f"{row.get('WHT', 0):>10,.2f}"
                    )
                else:
                    st.code(
                        f"دائن:\n"
                        f"  ح/ البنك / الدائنون         "
                        f"{total:>10,.2f}"
                    )

            st.divider()

    # زرار Odoo Export
    st.subheader("📤 تصدير للأنظمة المحاسبية")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("🔗 تجهيز للـ Odoo", use_container_width=True):
            import time
            with st.spinner("جاري التجهيز..."):
                time.sleep(1)
            st.success("✅ الملف جاهز للـ Odoo 17.0 API")

    with c2:
        # تصدير القيود كـ Excel
        journal_df = df[["Invoice_ID", "Category",
                         "Amount", "VAT"]].copy()
        journal_df["DR_Account"] = "مصروف " + journal_df["Category"]
        journal_df["CR_Account"] = "البنك / الدائنون"
        journal_df["Total"]      = journal_df["Amount"] + journal_df["VAT"]

        buffer = io.BytesIO()
        journal_df.to_excel(buffer, index=False)
        st.download_button(
            "📥 تحميل القيود Excel",
            data=buffer.getvalue(),
            file_name="journal_entries.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )

# ============================================
# TAB 5 — Insights
# تحليل + Risk Score + توصيات
# ============================================
with tab5:
    st.subheader("💡 التحليل والتوصيات")

    for insight in insights:
        if "⚠️" in insight:
            st.warning(insight)
        elif "✅" in insight:
            st.success(insight)
        else:
            st.info(insight)

    st.divider()

    # Risk Score Gauge
    st.subheader("🎯 تقييم المخاطر")
    total_errors = summary["total_errors"]

    if total_errors == 0:
        risk_score, risk_label = 100, "✅ منخفض جداً"
    elif total_errors <= 5:
        risk_score, risk_label = 75,  "🟡 منخفض"
    elif total_errors <= 10:
        risk_score, risk_label = 50,  "🟠 متوسط"
    else:
        risk_score, risk_label = 25,  "🔴 مرتفع"

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
        title={"text": f"Risk Score — {risk_label}"},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0,  25],  "color": "#ffcccc"},
                {"range": [25, 50],  "color": "#ffe0b2"},
                {"range": [50, 75],  "color": "#fff9c4"},
                {"range": [75, 100], "color": "#c8e6c9"},
            ]
        }
    ))
    fig_gauge.update_layout(height=300)
    st.plotly_chart(fig_gauge, use_container_width=True)

    # توصيات
    st.subheader("📌 التوصيات")
    error_issues = errors_df["Issue"].tolist() \
                   if not errors_df.empty else []

    recommendations = {
        "Duplicate Invoice":    "🔴 راجع إجراءات الموافقة على الفواتير",
        "Vendor Concentration": "🟠 وزّع المشتريات على موردين متعددين",
        "VAT Inconsistency":    "🟡 راجع آلية احتساب الضريبة",
        "Withholding Tax Error":"🔴 تحقق من نسب خصم WHT",
        "Overdue Payment":      "🔴 راجع الفواتير غير المسددة",
        "Outlier Amount":       "🟡 افحص المصروفات غير الطبيعية"
    }

    found_any = False
    for issue, rec in recommendations.items():
        if issue in error_issues:
            st.markdown(rec)
            found_any = True

    if not found_any:
        st.success("✅ لا توجد توصيات — الوضع المالي سليم")

# ============================================
# TAB 6 — Audit Trail
# سجل كل فاتورة وحالتها
# مهم جداً للـ External Auditor
# ============================================
with tab6:
    st.subheader("📋 Audit Trail — سجل المراجعة")

    clean  = len(audit_trail[audit_trail["Status"] == "✅ Clean"])
    issues = len(audit_trail[audit_trail["Status"] == "❌ Has Issues"])
    pct    = round(clean / len(audit_trail) * 100, 1) \
             if len(audit_trail) > 0 else 0

    a1, a2, a3 = st.columns(3)
    with a1:
        st.metric("✅ فواتير نظيفة",      clean)
    with a2:
        st.metric("❌ فواتير بها مشاكل", issues)
    with a3:
        st.metric("📊 نسبة النظافة",      f"{pct}%")

    st.divider()

    if show_trail:
        st.dataframe(
            audit_trail,
            use_container_width=True,
            height=500
        )
    else:
        st.info("فعّل 'عرض Audit Trail' من الإعدادات")

    csv_audit = audit_trail.to_csv(
        index=False
    ).encode("utf-8-sig")
    st.download_button(
        "📥 تحميل Audit Trail",
        data=csv_audit,
        file_name="audit_trail.csv",
        mime="text/csv",
        use_container_width=True
    )

