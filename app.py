from datetime import datetime
import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="Clean & Care - Stundenzettel", page_icon="📋", layout="wide"
)

# القائمة الجانبية للتنقل بين الصفحات
st.sidebar.title("📌 القائمة الرئيسية")
page = st.sidebar.radio(
    "اختر الصفحة:",
    [
        "📋 إدارة ساعات الموظفين (Stundenzettel)",
        "👥 إدارة العمال (Mitarbeiter)",
        "🏢 متابعة ساعات المواقع (Objekte)",
    ],
)

# ---------------------------------------------------------
# دالة توليد PDF لتقرير ساعات الموظف (مطابق للنموذج الورقي)
# ---------------------------------------------------------
def generate_employee_pdf(emp_name, month_str, df, total_hours):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
  elements = []
  
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle(
      'TitleStyle',
      parent=styles['Heading1'],
      fontSize=14,
      leading=18,
      alignment=0,
      textColor=colors.HexColor("#111111")
  )
  
  # رأس الشركة
  elements.append(Paragraph("<b>CLEAN & CARE GmbH</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 15))
  
  # معلومات الموظف
  info_text = f"<b>Name (اسم الموظف):</b> {emp_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Stundenzettel Monat:</b> {month_str}"
  elements.append(Paragraph(info_text, styles['Normal']))
  elements.append(Spacer(1, 15))
  
  # جدول البيانات
  table_data = [["Datum", "Ort", "Beginn", "Ende", "Pause", "Arbeitszeit (abzgl. Pause)"]]
  
  for index, row in df.iterrows():
    table_data.append([
        str(row["Datum"]),
        str(row["Ort"] if pd.notna(row["Ort"]) else ""),
        str(row["Beginn"] if pd.notna(row["Beginn"]) else ""),
        str(row["Ende"] if pd.notna(row["Ende"]) else ""),
        str(row["Pause"] if pd.notna(row["Pause"]) else ""),
        str(row["Arbeitszeit (abzgl. Pause)"])
    ])
    
  # صف المجموع
  table_data.append(["Summe:", "", "", "", "", f"{total_hours:.2f} h"])
  
  t = Table(table_data, colWidths=[50, 100, 70, 70, 70, 180])
  t.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
      ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#666666")),
      ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
      ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
      ('GRID', (0, -1), (-1, -1), 1, colors.HexColor("#000000")),
  ]))
  
  elements.append(t)
  elements.append(Spacer(1, 30))
  
  # التوقيعات في الأسفل
  sig_data = [
      ["__________________________________", "__________________________________"],
      ["Unterschrift Arbeitnehmer (توقيع الموظف)", "Unterschrift Arbeitgeber / GF (توقيع الإدارة)"],
      ["Datum: ______________", "Datum: ______________"]
  ]
  sig_table = Table(sig_data, colWidths=[250, 250])
  sig_table.setStyle(TableStyle([
      ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
      ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
  ]))
  elements.append(sig_table)
  
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


# ---------------------------------------------------------
# دالة توليد PDF لتقرير ساعات المواقع (Objekte)
# ---------------------------------------------------------
def generate_location_pdf(month_name, year_val, df):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
  elements = []
  
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle(
      'TitleStyle',
      parent=styles['Heading1'],
      fontSize=14,
      leading=18,
      alignment=0,
      textColor=colors.HexColor("#111111")
  )
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH - تقرير ساعات المواقع (Objekte)</b>", title_style))
  elements.append(Paragraph(f"الشهر: {month_name} / {year_val}", styles['Normal']))
  elements.append(Spacer(1, 15))
  
  # تجهيز أعمدة الجدول للمواقع
  columns = list(df.columns)
  table_data = [[str(col) for col in columns]]
  
  for index, row in df.iterrows():
    row_data = [str(row[col]) if pd.notna(row[col]) else "" for col in columns]
    table_data.append(row_data)
    
  t = Table(table_data, repeatRows=1)
  t.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d0d0d0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, -1), 8),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
      ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
  ]))
  
  elements.append(t)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


# ---------------------------------------------------------
# صفحة إدارة العمال
# ---------------------------------------------------------
if page == "👥 إدارة العمال (Mitarbeiter)":
  st.title("👥 Clean & Care GmbH - إدارة العمال والموظفين")
  st.write("إضافة أو حذف أسماء العمال لتظهر تلقائياً في قائمة إدخال الساعات:")

  if "employees_list" not in st.session_state:
    st.session_state.employees_list = [
        "Sakleh Alsoudi",
        "Alaa Edin Ibrahim",
        "موظف جديد",
    ]

  st.subheader("➕ إضافة موظف جديد")
  new_emp_name = st.text_input("اسم الموظف الجديد:")
  if st.button("إضافة الموظف"):
    if new_emp_name and new_emp_name not in st.session_state.employees_list:
      st.session_state.employees_list.append(new_emp_name)
      st.success(f"تمت إضافة الموظف ({new_emp_name}) بنجاح!")
    elif not new_emp_name:
      st.warning("الرجاء كتابة اسم الموظف أولاً.")
    else:
      st.info("هذا الاسم موجود مسبقاً في القائمة.")

  st.markdown("---")
  st.subheader("🗑️ حذف موظف من القائمة")
  if len(st.session_state.employees_list) > 0:
    emp_to_delete = st.selectbox(
        "اختر الموظف المراد حذفه:", st.session_state.employees_list
    )
    if st.button("❌ حذف الموظف المحدد"):
      if len(st.session_state.employees_list) > 1:
        st.session_state.employees_list.remove(emp_to_delete)
        st.success(f"تم حذف الموظف ({emp_to_delete}) بنجاح!")
        st.rerun()
      else:
        st.warning("لا يمكن حذف جميع العمال، يجب أن يبقى موظف واحد على الأقل.")

  st.markdown("---")
  st.subheader("📋 قائمة العمال الحاليين:")
  for idx, emp in enumerate(st.session_state.employees_list, 1):
    st.write(f"{idx}. {emp}")

# ---------------------------------------------------------
# الصفحة الأولى: إدارة ساعات الموظفين (Stundenzettel)
# ---------------------------------------------------------
elif page == "📋 إدارة ساعات الموظفين (Stundenzettel)":
  st.title("📋 Clean & Care GmbH - Stundenzettel")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  if "employees_list" not in st.session_state:
    st.session_state.employees_list = [
        "Sakleh Alsoudi",
        "Alaa Edin Ibrahim",
        "موظف جديد",
    ]

  if "emp_meta" not in st.session_state:
    st.session_state.emp_meta = {"month_str": "Oktober 2026"}

  col1, col2 = st.columns(2)
  with col1:
    selected_employee = st.selectbox(
        "Name (اسم الموظف):", st.session_state.employees_list
    )
  with col2:
    stundenzettel_monat = st.text_input(
        "Stundenzettel Monat (الشهر):",
        value=st.session_state.emp_meta["month_str"],
        key="input_month_str",
    )
    st.session_state.emp_meta["month_str"] = stundenzettel_monat

  st.subheader(f"تسجيل الدوام اليومي للموظف: {selected_employee}")

  if "employee_df" not in st.session_state:
    days_data = []
    for day in range(1, 32):
      days_data.append(
          {
              "Datum": str(day),
              "Ort": "",
              "Beginn": "",
              "Ende": "",
              "Pause": "",
              "Arbeitszeit (abzgl. Pause)": 0.0,
          }
      )
    st.session_state.employee_df = pd.DataFrame(days_data)

  edited_df = st.data_editor(
      st.session_state.employee_df,
      num_rows="fixed",
      use_container_width=True,
      key="emp_table_editor",
  )
  st.session_state.employee_df = edited_df

  total_sum_hours = 0.0

  for index, row in edited_df.iterrows():
    b_str = str(row["Beginn"]).strip()
    e_str = str(row["Ende"]).strip()
    p_input = str(row["Pause"]).strip()

    hrs = 0.0
    if b_str and e_str and b_str != "nan" and e_str != "nan":
      for fmt in ("%H:%M", "%H.%M", "%H"):
        try:
          t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
          t2 = datetime.strptime(e_str.replace(".", ":"), fmt)

          gross_hours = (t2 - t1).total_seconds() / 3600

          if gross_hours > 0:
            if p_input and p_input != "nan" and p_input != "":
              try:
                break_val = float(p_input.replace(",", "."))
              except ValueError:
                break_val = 0.0
            else:
              if gross_hours <= 4.5:
                break_val = 0.0
              elif 5.0 <= gross_hours <= 8.0:
                break_val = 0.5
              else:
                break_val = 1.0

            hrs = max(0.0, gross_hours - break_val)
          break
        except ValueError:
          continue

    edited_df.at[index, "Arbeitszeit (abzgl. Pause)"] = round(hrs, 2)
    total_sum_hours += hrs

  st.markdown("---")
  col_res1, col_res2 = st.columns([2, 1])
  with col_res1:
    # زر تحميل ملف PDF للموظف مباشرة
    pdf_data = generate_employee_pdf(selected_employee, stundenzettel_monat, edited_df, total_sum_hours)
    st.download_button(
        label="📥 تحميل تقرير Stundenzettel (PDF)",
        data=pdf_data,
        file_name=f"Stundenzettel_{selected_employee}.pdf",
        mime="application/pdf",
    )
  with col_res2:
    st.metric(label="Summe (إجمالي الساعات):", value=f"{total_sum_hours:.2f} h")

  st.markdown("---")
  sig_col1, sig_col2 = st.columns(2)
  with sig_col1:
    st.text("__________________________________")
    st.text("Unterschrift Arbeitnehmer (توقيع الموظف)")
    st.text("Datum: ______________")
  with sig_col2:
    st.text("__________________________________")
    st.text("Unterschrift Arbeitgeber / GF (توقيع الإدارة)")
    st.text("Datum: ______________")

# ---------------------------------------------------------
# الصفحة الثالثة: متابعة ساعات المواقع (Objekte)
# ---------------------------------------------------------
elif page == "🏢 متابعة ساعات المواقع (Objekte)":
  st.title("🏢 Clean & Care GmbH - متابعة ساعات المواقع والمنشآت")

  col1, col2 = st.columns(2)
  with col1:
    loc_month = st.selectbox(
        "اختر الشهر للمواقع:",
        [
            "يناير",
            "فبراير",
            "مارس",
            "أبريل",
            "مايو",
            "يونيو",
            "يوليو",
            "أغسطس",
            "سبتمبر",
            "أكتوبر",
            "نوفمبر",
            "ديسمبر",
        ],
        index=9,
    )
  with col2:
    loc_year = st.number_input("السنة للمواقع:", min_value=2024, max_value=2030, value=2026)

  # تحديد عدد الأيام بالشهر بناءً على اسم الشهر
  month_map = {
      "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "مايو": 5, "يونيو": 6,
      "يوليو": 7, "أغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12
  }
  m_num = month_map[loc_month]
  days_in_month = pd.Period(f"{loc_year}-{m_num}").days_in_month

  # تثبيت بيانات جدول المواقع لعدم الحذف أثناء الكتابة
  if "locations_data" not in st.session_state:
    init_data = {
        "اسم المكان (Objekt)": [
            "Limehome Salzburg",
            "Nespresso Store",
            "IKEA Wals",
        ]
    }
    for day in range(1, 32):
      init_data[f"يوم {day}"] = [0.0] * 3
    st.session_state.locations_data = pd.DataFrame(init_data)

  st.subheader("📝 جدول الساعات الشهرية للمواقع")
  edited_locations_df = st.data_editor(
      st.session_state.locations_data,
      num_rows="dynamic",
      use_container_width=True,
      key="loc_table_editor",
  )
  st.session_state.locations_data = edited_locations_df

  # حساب المجموع لكل موقع للأيام الفعلية للشهر
  active_day_cols = [f"يوم {d}" for d in range(1, days_in_month + 1)]
  existing_cols = [c for c in active_day_cols if c in edited_locations_df.columns]
  
  edited_locations_df["المجموع الكلي (Summe)"] = edited_locations_df[existing_cols].sum(axis=1)

  st.markdown("---")
  st.subheader("📊 ملخص ساعات المواقع لهذا الشهر")
  summary_df = edited_locations_df[
      ["اسم المكان (Objekt)", "المجموع الكلي (Summe)"]
  ]
  st.dataframe(summary_df, use_container_width=True)

  total_all_locations = summary_df["المجموع الكلي (Summe)"].sum()
  st.metric(
      label="إجمالي كافة الساعات لجميع المواقع:",
      value=f"{total_all_locations:.2f} ساعة",
  )

  st.markdown("---")
  # زر تحميل تقرير المواقع PDF
  loc_pdf_data = generate_location_pdf(loc_month, loc_year, edited_locations_df)
  st.download_button(
      label="📥 تحميل تقرير ساعات المواقع (PDF)",
      data=loc_pdf_data,
      file_name=f"Objekte_Report_{loc_month}_{loc_year}.pdf",
      mime="application/pdf",
  )