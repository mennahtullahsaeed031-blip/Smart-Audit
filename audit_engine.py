import pandas as pd
import numpy as np

def calculate_payroll_tax(annual_salary):
    if annual_salary <= 600:
        return 0
    elif annual_salary <= 50000:
        return annual_salary * 0.10
    elif annual_salary <= 250000:
        return annual_salary * 0.15
    else:
        return annual_salary * 0.20

def run_audit(df, tax_rate=0.14):

    errors = []

    # ---- تنظيف الداتا ----
    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["VAT"]    = pd.to_numeric(df["VAT"], errors="coerce")

    # ================================
    # CHECK 1: Missing Values
    # ================================
    missing = df[
        df["Amount"].isna() |
        df["VAT"].isna() |
        df["Invoice_ID"].isna()
    ]
    for _, row in missing.iterrows():
        errors.append({
            "Invoice_ID": row["Invoice_ID"],
            "Issue": "Missing Value",
            "Details": "عمود Amount أو VAT أو Invoice_ID فارغ",
            "Severity": "🔴 High"
        })

    # ================================
    # CHECK 2: Duplicate Invoices
    # ================================
    duplicates = df[df.duplicated(subset=["Invoice_ID"], keep=False)]
    for _, row in duplicates.iterrows():
        errors.append({
            "Invoice_ID": row["Invoice_ID"],
            "Issue": "Duplicate Invoice",
            "Details": "الفاتورة دي اتكررت أكتر من مرة",
            "Severity": "🔴 High"
        })

    # ================================
    # CHECK 3: Negative Amounts
    # ================================
    negatives = df[df["Amount"] < 0]
    for _, row in negatives.iterrows():
        errors.append({
            "Invoice_ID": row["Invoice_ID"],
            "Issue": "Negative Amount",
            "Details": f"المبلغ = {row['Amount']} — مبلغ سالب غير صحيح",
            "Severity": "🔴 High"
        })

    # ================================
    # CHECK 4: VAT Validation
    # ================================
    df_valid     = df.dropna(subset=["Amount", "VAT"])
    expected_vat = (df_valid["Amount"] * tax_rate).round(2)
    actual_vat   = df_valid["VAT"].round(2)
    tax_errors   = df_valid[abs(expected_vat - actual_vat) > 1]

    for _, row in tax_errors.iterrows():
        expected = round(row["Amount"] * tax_rate, 2)
        errors.append({
            "Invoice_ID": row["Invoice_ID"],
            "Issue": "VAT Inconsistency",
            "Details": f"VAT الفعلي = {row['VAT']} | المفروض = {expected}",
            "Severity": "🟡 Medium"
        })

    # ================================
    # CHECK 5: Outliers
    # ================================
    Q1          = df["Amount"].quantile(0.25)
    Q3          = df["Amount"].quantile(0.75)
    IQR         = Q3 - Q1
    upper_bound = Q3 + (3 * IQR)

    outliers = df[df["Amount"] > upper_bound]
    for _, row in outliers.iterrows():
        errors.append({
            "Invoice_ID": row["Invoice_ID"],
            "Issue": "Outlier Amount",
            "Details": f"المبلغ = {row['Amount']:,.0f} — أعلى من الحد الطبيعي ({upper_bound:,.0f})",
            "Severity": "🟡 Medium"
        })

    # ================================
    # CHECK 6: Vendor Concentration
    # ================================
    vendor_totals      = df.groupby("Vendor")["Amount"].sum()
    total_spend        = vendor_totals.sum()
    vendor_pct         = (vendor_totals / total_spend * 100).round(1)
    high_concentration = vendor_pct[vendor_pct > 30]

    for vendor, pct in high_concentration.items():
        errors.append({
            "Invoice_ID": "N/A",
            "Issue": "Vendor Concentration",
            "Details": f"{vendor} بياخد {pct}% من إجمالي المصروفات",
            "Severity": "🟠 Warning"
        })

    # ================================
    # CHECK 7: Withholding Tax (ضريبة المورد)
    # ================================
    WITHHOLDING_RATES = {
        "Consulting":      0.05,
        "Maintenance":     0.02,
        "Supplies":        0.01,
        "Rent":            0.05,
        "Food & Beverage": 0.01
    }

    if "WHT" in df.columns:
        df["WHT"] = pd.to_numeric(df["WHT"], errors="coerce")
        for _, row in df.dropna(subset=["Amount", "WHT"]).iterrows():
            rate         = WITHHOLDING_RATES.get(row["Category"], 0)
            expected_wht = round(row["Amount"] * rate, 2)
            actual_wht   = round(row["WHT"], 2)

            if abs(expected_wht - actual_wht) > 1:
                errors.append({
                    "Invoice_ID": row["Invoice_ID"],
                    "Issue": "Withholding Tax Error",
                    "Details": (
                        f"WHT المفروض = {expected_wht} | "
                        f"الفعلي = {actual_wht} | "
                        f"النشاط = {row['Category']}"
                    ),
                    "Severity": "🔴 High"
                })

    # ================================
    # CHECK 8: Bank Reconciliation
    # ================================
    if "Payment_Status" in df.columns:
        today      = pd.Timestamp.now()
        old_unpaid = df[
            (df["Payment_Status"] == "Unpaid") &
            ((today - df["Date"]).dt.days > 30)
        ]
        for _, row in old_unpaid.iterrows():
            days = (today - row["Date"]).days
            errors.append({
                "Invoice_ID": row["Invoice_ID"],
                "Issue": "Overdue Payment",
                "Details": f"فاتورة غير مدفوعة منذ {days} يوم | المبلغ = {row['Amount']:,.0f}",
                "Severity": "🔴 High"
            })

        partial = df[df["Payment_Status"] == "Partial"]
        for _, row in partial.iterrows():
            errors.append({
                "Invoice_ID": row["Invoice_ID"],
                "Issue": "Partial Payment",
                "Details": f"دفع جزئي فقط | المبلغ الكلي = {row['Amount']:,.0f}",
                "Severity": "🟡 Medium"
            })

    # ================================
    # CHECK 9: Payroll Tax (ضريبة الموظفين)
    # ================================
    if "Salary" in df.columns:
        df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")
        for _, row in df.dropna(subset=["Salary"]).iterrows():
            annual_salary = row["Salary"] * 12
            expected_tax  = calculate_payroll_tax(annual_salary)

            if "Payroll_Tax" in df.columns:
                actual_tax = pd.to_numeric(row.get("Payroll_Tax", 0), errors="coerce")
                if abs(expected_tax - actual_tax) > 1:
                    errors.append({
                        "Invoice_ID": row.get("Employee_ID", "N/A"),
                        "Issue": "Payroll Tax Error",
                        "Details": (
                            f"ضريبة الراتب المفروضة = {expected_tax:,.0f} | "
                            f"الفعلية = {actual_tax:,.0f}"
                        ),
                        "Severity": "🔴 High"
                    })

    # ================================
    # CHECK 10: Stamp Duty (ضريبة الدمغة)
    # ================================
    STAMP_DUTY_RATES = {
        "Consulting": 0.009,
        "Rent":       0.003,
        "Supplies":   0.003,
        "Maintenance": 0.003,
        "Food & Beverage": 0.003
    }

    if "Stamp_Duty" in df.columns:
        df["Stamp_Duty"] = pd.to_numeric(df["Stamp_Duty"], errors="coerce")
        for _, row in df.dropna(subset=["Amount", "Stamp_Duty"]).iterrows():
            rate          = STAMP_DUTY_RATES.get(row["Category"], 0.003)
            expected_stamp = round(row["Amount"] * rate, 2)
            actual_stamp   = round(row["Stamp_Duty"], 2)

            if abs(expected_stamp - actual_stamp) > 1:
                errors.append({
                    "Invoice_ID": row["Invoice_ID"],
                    "Issue": "Stamp Duty Error",
                    "Details": (
                        f"ضريبة الدمغة المفروضة = {expected_stamp} | "
                        f"الفعلية = {actual_stamp}"
                    ),
                    "Severity": "🟡 Medium"
                })

    # ================================
    # AUDIT TRAIL
    # ================================
    audit_trail = []
    for _, row in df.iterrows():
        row_errors = [
            e["Issue"] for e in errors
            if e["Invoice_ID"] == row["Invoice_ID"]
        ]
        status = "❌ Has Issues" if row_errors else "✅ Clean"
        audit_trail.append({
            "Invoice_ID":   row["Invoice_ID"],
            "Date":         row["Date"],
            "Vendor":       row["Vendor"],
            "Amount":       row["Amount"],
            "Status":       status,
            "Issues Found": ", ".join(row_errors) if row_errors else "None"
        })

    # ================================
    # SUMMARY
    # ================================
    summary = {
        "total_expenses":        df["Amount"].sum(),
        "total_invoices":        len(df),
        "total_errors":          len(errors),
        "top_category":          df.groupby("Category")["Amount"].sum().idxmax(),
        "top_vendor":            vendor_totals.idxmax(),
        "vendor_distribution":   vendor_pct.to_dict(),
        "category_distribution": df.groupby("Category")["Amount"].sum().to_dict()
    }

    # ================================
    # INSIGHTS
    # ================================
    insights = []

    dup_count = sum(1 for e in errors if e["Issue"] == "Duplicate Invoice")
    if dup_count > 0:
        insights.append(f"⚠️ تم اكتشاف {dup_count} فاتورة مكررة — خطر دفع مزدوج")

    if len(high_concentration) > 0:
        insights.append("⚠️ اعتماد عالي على مورد واحد — يُنصح بتوزيع الموردين")

    vat_count = sum(1 for e in errors if e["Issue"] == "VAT Inconsistency")
    if vat_count > 0:
        insights.append(f"⚠️ {vat_count} فاتورة فيها تناقض في VAT")

    wht_count = sum(1 for e in errors if e["Issue"] == "Withholding Tax Error")
    if wht_count > 0:
        insights.append(f"⚠️ {wht_count} فاتورة فيها خطأ في Withholding Tax")

    overdue_count = sum(1 for e in errors if e["Issue"] == "Overdue Payment")
    if overdue_count > 0:
        insights.append(f"⚠️ {overdue_count} فاتورة متأخرة الدفع — خطر مالي")

    outlier_count = sum(1 for e in errors if e["Issue"] == "Outlier Amount")
    if outlier_count > 0:
        insights.append(f"⚠️ {outlier_count} مصروف غير طبيعي — يحتاج تفسير")

    payroll_count = sum(1 for e in errors if e["Issue"] == "Payroll Tax Error")
    if payroll_count > 0:
        insights.append(f"⚠️ {payroll_count} خطأ في ضريبة الرواتب")

    stamp_count = sum(1 for e in errors if e["Issue"] == "Stamp Duty Error")
    if stamp_count > 0:
        insights.append(f"⚠️ {stamp_count} خطأ في ضريبة الدمغة")

    if len(errors) == 0:
        insights.append("✅ لم يتم اكتشاف أي مشاكل — الداتا نظيفة")

    return {
        "errors":      pd.DataFrame(errors),
        "summary":     summary,
        "insights":    insights,
        "audit_trail": pd.DataFrame(audit_trail)
    }

# ---- اختبار ----
if __name__ == "__main__":
    df      = pd.read_excel("financial_data.xlsx")
    results = run_audit(df)

    print("=== الأخطاء ===")
    print(results["errors"])
    print("\n=== Insights ===")
    for i in results["insights"]:
        print(i)