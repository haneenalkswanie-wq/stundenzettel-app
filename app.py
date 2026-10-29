import streamlit as st
import pandas as pd
from datetime import datetime
import io
import json
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="Stundenzettel - Clean & Care GmbH", layout="wide")

st.title("📋 نظام تسجيل و إدارة ساعات العمال (Stundenzettel)")
st.write("CLEAN & CARE GmbH - Am Messezentrum 6, 5020 Salzburg")

st.divider()

# ملف الحفظ المحلي للعمال
DB_FILE = "workers_timesheets.json"

def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_database(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

db_data = load_database()

# قسم اختيار أو البحث عن عامل محفوظ مسبقاً
st.subheader("🔍 البحث عن عامل محفوظ")
saved_workers = list(db_data.keys())

col_search1, col_search2 = st.columns([2, 1])
with col_search1:
    selected_worker_lookup = st.selectbox(
        "اختر عاملاً من القائمة لاستعراض ورقته فوراً:",
        options=["-- اختر عاملاً أو اتركها لإدخال جديد --"] + saved_workers
    )

# تهيئة بيانات الجدول الافتراضية
initial_data = []
for day in range(1, 32):
    initial_data.append({
        "Datum": day,
        "Ort": "",
        "Beginn": "",
        "Ende": "",
        "Pause": 0.5,
        "Arbeitszeit": 0.0
    })

loaded_name = ""
loaded_month = "10/2026"
loaded_df_rows = initial_data

if selected_worker_lookup != "-- اختر عاملاً أو اتركها لإدخال جديد --":
    worker_info = db_data[selected_worker_lookup]
    loaded_name = selected_worker_lookup
    loaded_month = worker_info.get("month", "10/2026")
    loaded_df_rows = worker_info.get("rows", initial_data)

st.divider()

col1, col2 = st.columns(2)
with col1:
    worker_name = st.text_input("اسم العامل (Name):", value=loaded_name, placeholder="أدخل اسم العامل هنا")
with col2:
    stundenzettel_month = st.text_input("شهر العمل (Stundenzettel Monat):", value=loaded_month)

st.subheader("📊 جدول الأيام (من 1 إلى 31)")
st.write("قم بتعبئة الموقع، البداية، والنهاية (مثال: 08:00 و 16:00)، وسيتم حساب الساعات تلقائياً:")

df_to_load = pd.DataFrame(loaded_df_rows)
edited_df = st.data_editor(
    df_to_load,
    num_rows="fixed",
    hide_index=True,
    column_config={
        "Datum": st.column_config.NumberColumn("التاريخ (Datum)", disabled=True),
        "Ort": st.column_config.TextColumn("الموقع (Ort)"),
        "Beginn": st.column_config.TextColumn("البداية (Beginn) [مثال: 08:00]"),
        "Ende": st.column_config.TextColumn("الانصراف (Ende) [مثال: 16:30]"),
        "Pause": st.column_config.NumberColumn("الاستراحة (Pause - ساعات)", min_value=0.0, max_value=5.0, step=0.25),
        "Arbeitszeit": st.column_config.NumberColumn("صافي الساعات (Arbeitszeit)", disabled=True)
    },
    width='stretch',
    key="grid_editor"
)

# حساب الساعات فوراً
total_sum_hours = 0.0
for index, row in edited_df.iterrows():
    b_str = str(row["Beginn"]).strip()
    e_str = str(row["Ende"]).strip()
    p_val = float(row["Pause"]) if row["Pause"] else 0.0
    
    hrs = 0.0
    if b_str and e_str and b_str != "nan" and e_str != "nan":
        for fmt in ("%H:%M", "%H.%M", "%H"):
            try:
                t1 = datetime.strptime(b_str.replace('.', ':'), fmt)
                t2 = datetime.strptime(e_str.replace('.', ':'), fmt)
                delta = (t2 - t1).total_seconds() / 3600
                if delta > 0:
                    hrs = max(0.0, delta - p_val)
                break
            except ValueError:
                continue
                
    edited_df.at[index, "Arbeitszeit"] = round(hrs, 2)
    total_sum_hours += hrs

st.divider()
col_res1, col_res2, col_res3 = st.columns([2, 1, 1])
col_res1.metric("إجمالي ساعات الشهر (Summe)", f"{total_sum_hours:.2f} ساعة")

with col_res2:
    if st.button("💾 حفظ بيانات العامل", type="secondary"):
        if not worker_name.strip():
            st.warning("يرجى كتابة اسم العامل قبل الحفظ!")
        else:
            db_data[worker_name.strip()] = {
                "month": stundenzettel_month,
                "rows": edited_df.to_dict(orient="records")
            }
            save_database(db_data)
            st.success(f"تم حفظ بيانات العامل ({worker_name}) بنجاح!")

def generate_pdf(name, month, df_data, total_hours):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CompanyHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14)
    sub_style = ParagraphStyle('CompanySub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12)

    header_data = [
        [
            Paragraph("<b>CLEAN & CARE GmbH</b><br/>Am Messezentrum 6<br/>5020 Salzburg", title_style),
            Paragraph("<font size=14><b>WIR KÜMMERN UNS</b></font>", ParagraphStyle('LogoTxt', alignment=2, fontName='Helvetica-Bold'))
        ]
    ]
    header_table = Table(header_data, colWidths=[300, 235])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    
    info_data = [
        [Paragraph(f"<b>Name:</b> {name}", sub_style), Paragraph(f"<b>Stundenzettel Monat:</b> {month}", sub_style)]
    ]
    info_table = Table(info_data, colWidths=[300, 235])
    info_table.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))
    
    table_content = [["Datum", "Ort", "Beginn", "Ende", "Pause", "Arbeitszeit\n(abzgl. Pause)"]]
    
    for _, r in df_data.iterrows():
        table_content.append([
            str(r["Datum"]),
            str(r["Ort"]) if str(r["Ort"]) != "nan" else "",
            str(r["Beginn"]) if str(r["Beginn"]) != "nan" else "",
            str(r["Ende"]) if str(r["Ende"]) != "nan" else "",
            str(r["Pause"]) if float(r["Pause"]) > 0 else "",
            str(r["Arbeitszeit"]) if float(r["Arbeitszeit"]) > 0 else ""
        ])
        
    table_content.append(["", "", "", "", "Summe:", f"{total_hours:.2f}"])
    
    col_widths = [45, 130, 75, 75, 75, 135]
    t = Table(table_content, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('SPAN', (0,-1), (3,-1)),
        ('ALIGN', (4,-1), (4,-1), 'RIGHT'),
        ('FONTNAME', (4,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (4,-1), (-1,-1), 1, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 25))
    
    sig_data = [
        [
            Paragraph("___________________________________<br/>Unterschrift Arbeitnehmer<br/>Datum: _____________", sub_style),
            Paragraph("___________________________________<br/>Unterschrift Arbeitgeber / GF<br/>Datum: _____________", sub_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[265, 270])
    sig_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    elements.append(sig_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

with col_res3:
    if worker_name.strip():
        pdf_file = generate_pdf(worker_name.strip(), stundenzettel_month, edited_df, total_sum_hours)
        st.download_button(
            label="📥 تنزيل ملف PDF",
            data=pdf_file,
            file_name=f"Stundenzettel_{worker_name.strip()}_{stundenzettel_month.replace('/', '-')}.pdf",
            mime="application/pdf",
            type="primary"
        )