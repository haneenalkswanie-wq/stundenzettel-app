from datetime import datetime
import io
import json
import os
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="Clean & Care - Stundenzettel", page_icon="📋", layout="wide"
)

# ملفات الحفظ المحلي
EMPLOYEES_FILE = "employees_data.json"
PLACES_FILE = "places_list.json"
LOCATIONS_FILE = "locations_data.json"


# دوال التحميل والحفظ العامة
def load_json_file(filename, default_val):
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return default_val


def save_json_file(filename, data):
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def load_employees():
  emp_list = load_json_file(EMPLOYEES_FILE, ["Sakleh Alsoudi", "Alaa Edin Ibrahim", "Neuer Mitarbeiter"])
  return sorted(emp_list)


def save_employees(emp_list):
  save_json_file(EMPLOYEES_FILE, sorted(emp_list))


def load_places():
  places_list = load_json_file(PLACES_FILE, ["Limehome Salzburg", "Nespresso Store", "IKEA Wals"])
  return sorted(places_list)


def save_places(places_list):
  save_json_file(PLACES_FILE, sorted(places_list))


# دوال حفظ وتحميل ساعات الموظفين الشهرية (الصفحة الأولى)
def get_employee_month_file(emp_name, month_str, year_val):
  safe_emp = "".join(c for c in emp_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  safe_month = "".join(c for c in month_str if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  return f"emp_{safe_emp}_{safe_month}_{year_val}.json"


def load_employee_month_hours(emp_name, month_str, year_val):
  filename = get_employee_month_file(emp_name, month_str, year_val)
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return pd.DataFrame(data)
    except:
      pass
  
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
  return pd.DataFrame(days_data)


def save_employee_month_hours(emp_name, month_str, year_val, df):
  filename = get_employee_month_file(emp_name, month_str, year_val)
  save_json_file(filename, df.to_dict(orient="list"))


# دوال الساعات اليومية للعامل المحدد
def get_daily_emp_file(emp_name, month_str, year_val):
  safe_emp = "".join(c for c in emp_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  safe_month = "".join(c for c in month_str if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  return f"daily_emp_{safe_emp}_{safe_month}_{year_val}.json"


def load_daily_emp_hours(emp_name, month_str, year_val):
  filename = get_daily_emp_file(emp_name, month_str, year_val)
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return pd.DataFrame(data)
    except:
      pass
  
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
  return pd.DataFrame(days_data)


def save_daily_emp_hours(emp_name, month_str, year_val, df):
  filename = get_daily_emp_file(emp_name, month_str, year_val)
  save_json_file(filename, df.to_dict(orient="list"))


# دوال ساعات الأماكن
def load_locations():
  if os.path.exists(LOCATIONS_FILE):
    try:
      with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return pd.DataFrame(data)
    except:
      pass
  init_data = {
      "Objekt": [
          "Limehome Salzburg",
          "Nespresso Store",
          "IKEA Wals",
      ]
  }
  for day in range(1, 32):
    init_data[str(day)] = [0.0, 0.0, 0.0]
  return pd.DataFrame(init_data)


def save_locations(df):
  data = df.to_dict(orient="list")
  with open(LOCATIONS_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


# دوال ساعات الأماكن الفردية
def get_place_hours_file(place_name, month_str, year_val):
  safe_place = "".join(c for c in place_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  safe_month = "".join(c for c in month_str if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  return f"place_{safe_place}_{safe_month}_{year_val}.json"


def load_place_hours(place_name, month_str, year_val, selected_employees):
  filename = get_place_hours_file(place_name, month_str, year_val)
  existing_data = {}
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        df_old = pd.DataFrame(data)
        for _, row in df_old.iterrows():
          existing_data[row["Mitarbeiter"]] = row["Stunden"]
    except:
      pass
  
  df_data = []
  for emp in selected_employees:
    hrs = existing_data.get(emp, 0.0)
    df_data.append({"Mitarbeiter": emp, "Stunden": hrs})
  return pd.DataFrame(df_data)


def save_place_hours(place_name, month_str, year_val, df):
  filename = get_place_hours_file(place_name, month_str, year_val)
  save_json_file(filename, df.to_dict(orient="list"))


# القوائم الثابتة
months_list_de = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]
months_list_ar = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
]
years_list = [2024, 2025, 2026, 2027, 2028, 2029, 2030]


# ---------------------------------------------------------
# نظام لغة الواجهة
# ---------------------------------------------------------
st.sidebar.title("⚙️ Einstellungen")
lang_choice = st.sidebar.radio("Sprache / اللغة:", ["Deutsch", "العربية"])

is_arabic = (lang_choice == "العربية")

if not is_arabic:
    t = {
        "menu": "📌 Hauptmenü",
        "p1": "📋 Mitarbeiter Stundenzettel",
        "p2": "📝 Tägliche Stunden",
        "p3": "🏢 Objekt-Stundenübersicht",
        "p4": "🏢 Orte & Mitarbeiter-Stunden",
        "p5": "👥 Mitarbeiterverwaltung",
        "p6": "📅 Monatsübersicht",
        "emp_label": "Mitarbeiter wählen:",
        "month_label": "Monat auswählen:",
        "year_label": "Jahr auswählen:",
        "save_btn": "💾 Speichern",
        "success_msg": "Erfolgreich gespeichert!",
        "pdf_btn": "📥 PDF herunterladen",
        "sum_label": "Summe:",
        "add_emp": "Neuen Mitarbeiter hinzufügen",
        "del_emp": "Mitarbeiter löschen",
        "add_btn": "Hinzufügen",
        "del_btn": "Löschen",
        "place_label": "Ort / Platz auswählen:",
        "add_place": "Neuen Ort hinzufügen",
    }
else:
    t = {
        "menu": "📌 القائمة الرئيسية",
        "p1": "📋 استمارة ساعات العمال",
        "p2": "📝 الساعات اليومية",
        "p3": "🏢 ملخص ساعات المواقع (عرض)",
        "p4": "🏢 الأماكن وساعات العمال",
        "p5": "👥 إدارة العمال",
        "p6": "📅 ملخص الأشهر",
        "emp_label": "اختر اسم الموظف:",
        "month_label": "اختر الشهر:",
        "year_label": "اختر السنة:",
        "save_btn": "💾 حفظ",
        "success_msg": "تم الحفظ بنجاح!",
        "pdf_btn": "📥 تحميل ملف PDF",
        "sum_label": "المجموع:",
        "add_emp": "إضافة موظف جديد",
        "del_emp": "حذف موظف",
        "add_btn": "إضافة",
        "del_btn": "حذف",
        "place_label": "اختر اسم المكان:",
        "add_place": "إضافة مكان جديد",
    }

page = st.sidebar.radio(
    t["menu"],
    [
        t["p1"],
        t["p2"],
        t["p3"],
        t["p4"],
        t["p5"],
        t["p6"],
    ],
)


# ---------------------------------------------------------
# دوال طباعة PDF الجميلة
# ---------------------------------------------------------

def generate_employee_pdf(emp_name, month_str, year_val, df, total_hours):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor("#111111"))
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 15))
  elements.append(Paragraph(f"<b>Mitarbeiter:</b> {emp_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Monat:</b> {month_str} {year_val}", styles['Normal']))
  elements.append(Spacer(1, 15))
  
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
  table_data.append(["Summe:", "", "", "", "", f"{total_hours:.2f} St."])
  
  t_pdf = Table(table_data, colWidths=[50, 100, 70, 70, 70, 180])
  t_pdf.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
      ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#666666")),
      ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
      ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
      ('GRID', (0, -1), (-1, -1), 1, colors.HexColor("#000000")),
  ]))
  elements.append(t_pdf)
  elements.append(Spacer(1, 40))
  
  sig_data = [
      ["__________________________________", "__________________________________"],
      ["Unterschrift Arbeitnehmer", "Unterschrift Arbeitgeber / GF"],
      ["Datum: ______________", "Datum: ______________"]
  ]
  sig_table = Table(sig_data, colWidths=[250, 250])
  sig_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
  elements.append(sig_table)
  
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


def generate_location_pdf(month_name, year_val, df, days_count):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor("#111111"))
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH - Objekt-Stundenzettel</b>", title_style))
  elements.append(Paragraph(f"Monat: {month_name} {year_val}", styles['Normal']))
  elements.append(Spacer(1, 10))
  
  columns = ["Objekt"] + [str(d) for d in range(1, days_count + 1)] + ["Summe"]
  table_data = [[str(col) for col in columns]]
  
  for index, row in df.iterrows():
    row_data = [str(row["Objekt"])]
    for d in range(1, days_count + 1):
      val = row.get(str(d), 0.0)
      row_data.append(str(val) if pd.notna(val) else "0.0")
    row_data.append(str(row["Summe"]))
    table_data.append(row_data)
    
  col_widths = [110] + [18] * days_count + [55]
  t_pdf = Table(table_data, colWidths=col_widths, repeatRows=1)
  t_pdf.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d0d0d0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, -1), 7),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
      ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
  ]))
  elements.append(t_pdf)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


def generate_place_pdf(place_name, month_str, year_val, df, total_hours):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor("#111111"))
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH - Ort-Stundenbericht</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 15))
  elements.append(Paragraph(f"<b>Ort:</b> {place_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Monat:</b> {month_str} {year_val}", styles['Normal']))
  elements.append(Spacer(1, 15))
  
  table_data = [["Mitarbeiter", "Stunden"]]
  for index, row in df.iterrows():
    table_data.append([str(row["Mitarbeiter"]), str(row["Stunden"])])
  table_data.append(["Gesamtsumme:", f"{total_hours:.2f} St."])
  
  t_pdf = Table(table_data, colWidths=[250, 200])
  t_pdf.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
      ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#666666")),
      ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
      ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
      ('GRID', (0, -1), (-1, -1), 1, colors.HexColor("#000000")),
  ]))
  elements.append(t_pdf)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


def generate_summary_pdf(month_str, year_val, df, total_hours):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor("#111111"))
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH - Monatsübersicht</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 15))
  elements.append(Paragraph(f"<b>Monat:</b> {month_str} {year_val}", styles['Normal']))
  elements.append(Spacer(1, 15))
  
  table_data = [["Mitarbeiter", "Gesamtstunden"]]
  for index, row in df.iterrows():
    table_data.append([str(row["Mitarbeiter"]), str(row["Gesamtstunden"])])
  table_data.append(["Gesamtsumme:", f"{total_hours:.2f} St."])
  
  t_pdf = Table(table_data, colWidths=[250, 200])
  t_pdf.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
      ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#666666")),
      ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
      ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
      ('GRID', (0, -1), (-1, -1), 1, colors.HexColor("#000000")),
  ]))
  elements.append(t_pdf)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


# ---------------------------------------------------------
# الصفحة الأولى: استمارة ساعات العمال
# ---------------------------------------------------------
if page == t["p1"]:
  st.title("📋 Clean & Care GmbH - Stundenzettel")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  employees_list = load_employees()
  
  col1, col2, col3 = st.columns(3)
  with col1:
    selected_employee = st.selectbox(t["emp_label"], employees_list, key="p1_emp")
  with col2:
    selected_month = st.selectbox(t["month_label"], months_list_de if not is_arabic else months_list_ar, index=9, key="p1_month")
  with col3:
    selected_year = st.selectbox(t["year_label"], years_list, index=2, key="p1_year")

  st.subheader(f"Arbeitszeiterfassung für: {selected_employee} ({selected_month} {selected_year})")

  current_emp_df = load_employee_month_hours(selected_employee, selected_month, selected_year)

  edited_df = st.data_editor(
      current_emp_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"p1_table_{selected_employee}_{selected_month}_{selected_year}",
  )

  total_sum_hours = 0.0
  for index, row in edited_df.iterrows():
    b_str = str(row["Beginn"]).strip()
    e_str = str(row["Ende"]).strip()
    p_input = str(row["Pause"]).strip()

    hrs = 0.0
    break_val = 0.0

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
              except:
                break_val = 0.0
            hrs = max(0.0, gross_hours - break_val)
          break
        except:
          continue

    if break_val > 0:
      edited_df.at[index, "Pause"] = str(break_val)
    else:
      if not p_input or p_input == "nan":
        edited_df.at[index, "Pause"] = ""

    edited_df.at[index, "Arbeitszeit (abzgl. Pause)"] = round(hrs, 2)
    total_sum_hours += hrs

  st.markdown("---")
  c1, c2, c3 = st.columns([2, 1, 1])
  with c1:
    pdf_data = generate_employee_pdf(selected_employee, selected_month, selected_year, edited_df, total_sum_hours)
    st.download_button(t["pdf_btn"], pdf_data, f"Stundenzettel_{selected_employee}_{selected_month}_{selected_year}.pdf", "application/pdf")
  with c2:
    st.metric(t["sum_label"], f"{total_sum_hours:.2f} St.")
  with c3:
    if st.button(t["save_btn"], key="p1_save"):
      save_employee_month_hours(selected_employee, selected_month, selected_year, edited_df)
      st.success(t["success_msg"])

  st.markdown("---")
  sig_col1, sig_col2 = st.columns(2)
  with sig_col1:
    st.text("__________________________________")
    st.text("Unterschrift Arbeitnehmer")
    st.text("Datum: ______________")
  with sig_col2:
    st.text("__________________________________")
    st.text("Unterschrift Arbeitgeber / GF")
    st.text("Datum: ______________")


# ---------------------------------------------------------
# الصفحة الثانية: الساعات اليومية (مع قائمة منسدلة لاختيار العامل وطباعة ورقته الخاصة)
# ---------------------------------------------------------
elif page == t["p2"]:
  st.title("📝 Clean & Care GmbH - Tägliche Stunden")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  employees_list = load_employees()

  col1, col2, col3 = st.columns(3)
  with col1:
    daily_emp = st.selectbox(t["emp_label"], employees_list, key="daily_emp_select")
  with col2:
    daily_month = st.selectbox(t["month_label"], months_list_de if not is_arabic else months_list_ar, index=9, key="daily_month_select")
  with col3:
    daily_year = st.selectbox(t["year_label"], years_list, index=2, key="daily_year_select")

  st.subheader(f"Tägliche Stunden für: {daily_emp} ({daily_month} {daily_year})")

  daily_df = load_daily_emp_hours(daily_emp, daily_month, daily_year)

  edited_daily_df = st.data_editor(
      daily_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"daily_table_{daily_emp}_{daily_month}_{daily_year}",
  )

  total_daily_sum = 0.0
  for index, row in edited_daily_df.iterrows():
    b_str = str(row["Beginn"]).strip()
    e_str = str(row["Ende"]).strip()
    p_input = str(row["Pause"]).strip()

    hrs = 0.0
    break_val = 0.0

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
              except:
                break_val = 0.0
            hrs = max(0.0, gross_hours - break_val)
          break
        except:
          continue

    if break_val > 0:
      edited_daily_df.at[index, "Pause"] = str(break_val)
    else:
      if not p_input or p_input == "nan":
        edited_daily_df.at[index, "Pause"] = ""

    edited_daily_df.at[index, "Arbeitszeit (abzgl. Pause)"] = round(hrs, 2)
    total_daily_sum += hrs

  st.markdown("---")
  col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
  with col_d1:
    pdf_daily_data = generate_employee_pdf(daily_emp, daily_month, daily_year, edited_daily_df, total_daily_sum)
    st.download_button(t["pdf_btn"], pdf_daily_data, f"Tägliche_Stunden_{daily_emp}_{daily_month}_{daily_year}.pdf", "application/pdf", key="p2_pdf")
  with col_d2:
    if st.button(t["save_btn"], key="p2_save"):
      save_daily_emp_hours(daily_emp, daily_month, daily_year, edited_daily_df)
      st.success(t["success_msg"])
  with col_d3:
    st.metric(t["sum_label"], f"{total_daily_sum:.2f} St.")


# ---------------------------------------------------------
# الصفحة الثالثة: ملخص ساعات المواقع (عرض - Landscape)
# ---------------------------------------------------------
elif page == t["p3"]:
  st.title("🏢 Clean & Care GmbH - Objekt-Stundenübersicht")

  col1, col2 = st.columns(2)
  with col1:
    loc_month = st.selectbox(t["month_label"], months_list_de if not is_arabic else months_list_ar, index=9, key="loc_month_select")
  with col2:
    loc_year = st.selectbox(t["year_label"], years_list, index=2, key="loc_year_input")

  month_map = {
      "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
      "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
      "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "مايو": 5, "يونيو": 6,
      "يوليو": 7, "أغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12
  }
  m_num = month_map.get(loc_month, 10)
  days_in_month = pd.Period(f"{loc_year}-{m_num}").days_in_month

  if "locations_data" not in st.session_state:
    st.session_state.locations_data = load_locations()

  st.subheader("📝 Monatliche Objekt-Stunden")
  
  edited_locations_df = st.data_editor(
      st.session_state.locations_data,
      num_rows="dynamic",
      use_container_width=True,
      key="stable_loc_table_editor",
  )
  st.session_state.locations_data = edited_locations_df

  active_day_cols = [str(d) for d in range(1, days_in_month + 1)]
  existing_cols = [c for c in active_day_cols if c in edited_locations_df.columns]

  try:
      edited_locations_df["Summe"] = edited_locations_df[existing_cols].astype(float).sum(axis=1)
  except:
      edited_locations_df["Summe"] = 0.0

  st.markdown("---")
  col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
  with col_l1:
    loc_pdf_data = generate_location_pdf(loc_month, loc_year, edited_locations_df, days_in_month)
    st.download_button(t["pdf_btn"], loc_pdf_data, f"Objekte_Report_{loc_month}_{loc_year}.pdf", "application/pdf", key="p3_pdf")
  with col_l2:
    if st.button(t["save_btn"], key="p3_save"):
      save_locations(edited_locations_df)
      st.success(t["success_msg"])
  with col_l3:
    total_all_locations = edited_locations_df["Summe"].sum()
    st.metric(t["sum_label"], f"{total_all_locations:.2f} St.")


# ---------------------------------------------------------
# الصفحة الرابعة: الأماكن وساعات العمال (مع تصميم شيك وأنيق لاختيار العمال)
# ---------------------------------------------------------
elif page == t["p4"]:
  st.title("🏢 Clean & Care GmbH - Orte & Mitarbeiter-Stunden")

  places_list = load_places()
  employees_list = load_employees()

  col1, col2, col3 = st.columns(3)
  with col1:
    selected_place = st.selectbox(t["place_label"], places_list)
  with col2:
    place_month = st.selectbox(t["month_label"], months_list_de if not is_arabic else months_list_ar, index=9, key="place_month_select")
  with col3:
    place_year = st.selectbox(t["year_label"], years_list, index=2, key="place_year_select")

  st.subheader(f"Mitarbeiter-Stunden für Ort: {selected_place} ({place_month} {place_year})")

  # اختيار العمال بطريقة أجمل باستخدام Expander و Checkboxes منسقة
  with st.expander("⚙️ Mitarbeiter für diesen Ort auswählen / اختيار العمال لهذا المكان", expanded=False):
    selected_emps_for_place = []
    cols_chk = st.columns(3)
    for idx, emp in enumerate(employees_list):
      with cols_chk[idx % 3]:
        if st.checkbox(emp, value=True, key=f"chk_emp_{selected_place}_{emp}"):
          selected_emps_for_place.append(emp)

  place_df = load_place_hours(selected_place, place_month, place_year, selected_emps_for_place)

  edited_place_df = st.data_editor(
      place_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"place_editor_{selected_place}_{place_month}_{place_year}",
  )

  total_place_hours = edited_place_df["Stunden"].astype(float).sum()

  st.markdown("---")
  col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
  with col_p1:
    pdf_place_data = generate_place_pdf(selected_place, place_month, place_year, edited_place_df, total_place_hours)
    st.download_button(t["pdf_btn"], pdf_place_data, f"Ort_Report_{selected_place}_{place_month}_{place_year}.pdf", "application/pdf", key="p4_pdf")
  with col_p2:
    if st.button(t["save_btn"], key="p4_save"):
      save_place_hours(selected_place, place_month, place_year, edited_place_df)
      st.success(t["success_msg"])
  with col_p3:
    st.metric(t["sum_label"], f"{total_place_hours:.2f} St.")

  st.markdown("---")
  st.subheader(t["add_place"])
  new_place_name = st.text_input("Name des neuen Ortes:")
  if st.button(t["add_btn"], key="add_place_btn"):
    if new_place_name and new_place_name not in places_list:
      places_list.append(new_place_name)
      save_places(places_list)
      st.success(t["success_msg"])
      st.rerun()


# ---------------------------------------------------------
# الصفحة الخامسة: إدارة العمال (Mitarbeiterverwaltung)
# ---------------------------------------------------------
elif page == t["p5"]:
  st.title("👥 Clean & Care GmbH - Mitarbeiterverwaltung")
  
  employees_list = load_employees()

  st.subheader(t["add_emp"])
  new_emp_name = st.text_input("Name des Mitarbeiters:")
  if st.button(t["add_btn"], key="add_emp_btn"):
    if new_emp_name and new_emp_name not in employees_list:
      employees_list.append(new_emp_name)
      save_employees(employees_list)
      st.success(t["success_msg"])
      st.rerun()

  st.markdown("---")
  st.subheader(t["del_emp"])
  if len(employees_list) > 0:
    emp_to_delete = st.selectbox("Mitarbeiter:", employees_list)
    if st.button(t["del_btn"], key="del_emp_btn"):
      if len(employees_list) > 1:
        employees_list.remove(emp_to_delete)
        save_employees(employees_list)
        st.success(t["success_msg"])
        st.rerun()
      else:
        st.warning("Es muss mindestens ein Mitarbeiter bleiben.")


# ---------------------------------------------------------
# الصفحة السادسة: ملخص الأشهر (Monatsübersicht)
# ---------------------------------------------------------
elif page == t["p6"]:
  st.title("📅 Clean & Care GmbH - Monatsübersicht")
  
  col1, col2 = st.columns(2)
  with col1:
    summary_month = st.selectbox(t["month_label"], months_list_de if not is_arabic else months_list_ar, index=9, key="summary_month_select")
  with col2:
    summary_year = st.selectbox(t["year_label"], years_list, index=2, key="summary_year_select")

  employees_list = load_employees()

  st.subheader(f"📊 Gesamtstunden für: {summary_month} {summary_year}")

  summary_data = []
  total_company_hours = 0.0

  for emp in employees_list:
    emp_df = load_employee_month_hours(emp, summary_month, summary_year)
    emp_total = emp_df["Arbeitszeit (abzgl. Pause)"].astype(float).sum() if "Arbeitszeit (abzgl. Pause)" in emp_df.columns else 0.0
    summary_data.append({
        "Mitarbeiter": emp,
        "Gesamtstunden": f"{emp_total:.2f} St."
    })
    total_company_hours += emp_total

  summary_df = pd.DataFrame(summary_data)
  st.dataframe(summary_df, use_container_width=True)

  st.markdown("---")
  col_s1, col_s2 = st.columns([2, 1])
  with col_s1:
    pdf_summary_data = generate_summary_pdf(summary_month, summary_year, summary_df, total_company_hours)
    st.download_button(t["pdf_btn"], pdf_summary_data, f"Monatsübersicht_{summary_month}_{summary_year}.pdf", "application/pdf", key="p6_pdf")
  with col_s2:
    st.metric("Gesamtsumme:", f"{total_company_hours:.2f} St.")