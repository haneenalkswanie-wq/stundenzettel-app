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
LOCATIONS_FILE = "locations_data.json"
PLACES_FILE = "places_list.json"


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
  return load_json_file(EMPLOYEES_FILE, ["Sakleh Alsoudi", "Alaa Edin Ibrahim", "Neuer Mitarbeiter"])


def save_employees(emp_list):
  save_json_file(EMPLOYEES_FILE, emp_list)


def load_places():
  return load_json_file(PLACES_FILE, ["Limehome Salzburg", "Nespresso Store", "IKEA Wals"])


def save_places(places_list):
  save_json_file(PLACES_FILE, places_list)


# دوال حفظ وتحميل ساعات الموظفين الشهرية
def get_employee_month_file(emp_name, month_str):
  safe_emp = "".join(c for c in emp_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  safe_month = "".join(c for c in month_str if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  return f"emp_{safe_emp}_{safe_month}.json"


def load_employee_month_hours(emp_name, month_str):
  filename = get_employee_month_file(emp_name, month_str)
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


def save_employee_month_hours(emp_name, month_str, df):
  filename = get_employee_month_file(emp_name, month_str)
  save_json_file(filename, df.to_dict(orient="list"))


# دوال الساعات اليومية المستقلة (الصفحة الجديدة الثانية)
def get_daily_hours_file(month_str):
  safe_month = "".join(c for c in month_str if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  return f"daily_hours_{safe_month}.json"


def load_daily_hours(month_str):
  filename = get_daily_hours_file(month_str)
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return pd.DataFrame(data)
    except:
      pass
  
  # جدول افتراضي للساعات اليومية
  return pd.DataFrame(columns=["Datum", "Mitarbeiter", "Ort / Platz", "Stunden"])


def save_daily_hours(month_str, df):
  filename = get_daily_hours_file(month_str)
  save_json_file(filename, df.to_dict(orient="list"))


# دوال ساعات الأماكن (ربط الأماكن بالعمال)
def get_place_hours_file(place_name, month_str):
  safe_place = "".join(c for c in place_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  safe_month = "".join(c for c in month_str if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  return f"place_{safe_place}_{safe_month}.json"


def load_place_hours(place_name, month_str, employees):
  filename = get_place_hours_file(place_name, month_str)
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return pd.DataFrame(data)
    except:
      pass
  
  # إنشاء جدول افتراضي لكل موظف وساعاته في هذا المكان
  df_data = []
  for emp in employees:
    df_data.append({"Mitarbeiter": emp, "Stunden": 0.0})
  return pd.DataFrame(df_data)


def save_place_hours(place_name, month_str, df):
  filename = get_place_hours_file(place_name, month_str)
  save_json_file(filename, df.to_dict(orient="list"))


# ---------------------------------------------------------
# نظام لغة الواجهة (عربي / ألماني)
# ---------------------------------------------------------
st.sidebar.title("⚙️ Einstellungen / الإعدادات")
lang_choice = st.sidebar.radio("Sprache / اللغة:", ["Deutsch (ألماني)", "العربية (Arabic)"])

is_arabic = "العربية" in lang_choice

# نصوص مترجمة ديناميكية
t = {
    "menu": "📌 Hauptmenü" if not is_arabic else "📌 القائمة الرئيسية",
    "p1": "📋 Mitarbeiter Stundenzettel (PDF)" if not is_arabic else "📋 استمارة ساعات العمال (مع طباعة PDF)",
    "p2": "📝 Tägliche Stunden (ساعات يومية جديدة)" if not is_arabic else "📝 الساعات اليومية (صفحة كتابة جديدة)",
    "p3": "🏢 Orte & Stunden (ساعات الأماكن)" if not is_arabic else "🏢 الأماكن وساعات العمال",
    "p4": "👥 Mitarbeiterverwaltung" if not is_arabic else "👥 إدارة العمال",
    "p5": "📅 Monatsübersicht" if not is_arabic else "📅 ملخص الأشهر",
}

page = st.sidebar.radio(
    t["menu"],
    [
        t["p1"],
        t["p2"],
        t["p3"],
        t["p4"],
        t["p5"],
    ],
)


# ---------------------------------------------------------
# دالة توليد PDF لتقرير ساعات الموظف
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
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 15))
  
  info_text = f"<b>Name:</b> {emp_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Stundenzettel Monat:</b> {month_str}"
  elements.append(Paragraph(info_text, styles['Normal']))
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
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


# ---------------------------------------------------------
# الصفحة الأولى: استمارة ساعات العمال (مع طباعة PDF)
# ---------------------------------------------------------
if page == t["p1"]:
  st.title("📋 Clean & Care GmbH - Stundenzettel")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  employees_list = load_employees()
  
  col1, col2 = st.columns(2)
  with col1:
    selected_employee = st.selectbox("Mitarbeiter / اسم الموظف:", employees_list, key="p1_emp")
  with col2:
    stundenzettel_monat = st.text_input("Monat / الشهر:", value="Oktober 2026", key="p1_month")

  st.subheader(f"Arbeitszeiterfassung für: {selected_employee} ({stundenzettel_monat})")

  current_emp_df = load_employee_month_hours(selected_employee, stundenzettel_monat)

  edited_df = st.data_editor(
      current_emp_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"p1_table_{selected_employee}_{stundenzettel_monat}",
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
            else:
              if gross_hours <= 4.5:
                break_val = 0.0
              elif 5.0 <= gross_hours <= 8.0:
                break_val = 0.5
              else:
                break_val = 1.0
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
    pdf_data = generate_employee_pdf(selected_employee, stundenzettel_monat, edited_df, total_sum_hours)
    st.download_button("📥 PDF herunterladen", pdf_data, f"Stundenzettel_{selected_employee}.pdf", "application/pdf")
  with c2:
    st.metric("Summe:", f"{total_sum_hours:.2f} St.")
  with c3:
    if st.button("💾 Speichern"):
      save_employee_month_hours(selected_employee, stundenzettel_monat, edited_df)
      st.success("Erfolgreich gespeichert!")


# ---------------------------------------------------------
# الصفحة الثانية: الساعات اليومية الجديدة (بدون PDF، مع زر حفظ)
# ---------------------------------------------------------
elif page == t["p2"]:
  st.title("📝 Clean & Care GmbH - Tägliche Stunden (ساعات يومية)")
  
  employees_list = load_employees()
  places_list = load_places()

  col1, col2 = st.columns(2)
  with col1:
    daily_month = st.text_input("Monat / الشهر:", value="Oktober 2026", key="daily_month_input")
  with col2:
    st.write("")

  daily_df = load_daily_hours(daily_month)

  st.subheader("Tabelle der täglichen Stunden (جدول الساعات اليومية)")
  
  edited_daily_df = st.data_editor(
      daily_df,
      num_rows="dynamic",
      use_container_width=True,
      key="daily_hours_editor",
      column_config={
          "Mitarbeiter": st.column_config.SelectboxColumn("Mitarbeiter", options=employees_list),
          "Ort / Platz": st.column_config.SelectboxColumn("Ort / Platz", options=places_list),
      }
  )

  if st.button("💾 Tägliche Stunden speichern (حفظ الساعات اليومية)"):
    save_daily_hours(daily_month, edited_daily_df)
    st.success("Tägliche Stunden erfolgreich gespeichert! (تم حفظ الساعات اليومية بنجاح)")


# ---------------------------------------------------------
# الصفحة الثالثة: الأماكن وساعات العمال (قائمة منسدلة بالأماكن)
# ---------------------------------------------------------
elif page == t["p3"]:
  st.title("🏢 Clean & Care GmbH - Orte & Mitarbeiter-Stunden (الأماكن والعمال)")

  places_list = load_places()
  employees_list = load_employees()

  col1, col2 = st.columns(2)
  with col1:
    selected_place = st.selectbox("Ort / Platz auswählen (اختر المكان):", places_list)
  with col2:
    place_month = st.text_input("Monat / الشهر:", value="Oktober 2026", key="place_month_input")

  st.subheader(f"Mitarbeiter-Stunden für Ort: {selected_place} ({place_month})")

  # تحميل ساعات هذا المكان للعمال
  place_df = load_place_hours(selected_place, place_month, employees_list)

  edited_place_df = st.data_editor(
      place_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"place_editor_{selected_place}_{place_month}",
  )

  if st.button(f"💾 Stunden für {selected_place} speichern (حفظ ساعات المكان)"):
    save_place_hours(selected_place, place_month, edited_place_df)
    st.success(f"Stunden für {selected_place} erfolgreich gespeichert!")

  total_place_hours = edited_place_df["Stunden"].astype(float).sum()
  st.metric(label=f"Gesamtstunden für {selected_place}:", value=f"{total_place_hours:.2f} St.")

  st.markdown("---")
  st.subheader("➕ Neuen Ort hinzufügen (إضافة مكان جديد)")
  new_place_name = st.text_input("Name des neuen Ortes:")
  if st.button("Ort hinzufügen"):
    if new_place_name and new_place_name not in places_list:
      places_list.append(new_place_name)
      save_places(places_list)
      st.success(f"Ort ({new_place_name}) erfolgreich hinzugefügt!")
      st.rerun()


# ---------------------------------------------------------
# الصفحة الرابعة: إدارة العمال (Mitarbeiterverwaltung)
# ---------------------------------------------------------
elif page == t["p4"]:
  st.title("👥 Clean & Care GmbH - Mitarbeiterverwaltung")
  
  employees_list = load_employees()

  st.subheader("➕ Neuen Mitarbeiter hinzufügen")
  new_emp_name = st.text_input("Name des Mitarbeiters:")
  if st.button("Hinzufügen"):
    if new_emp_name and new_emp_name not in employees_list:
      employees_list.append(new_emp_name)
      save_employees(employees_list)
      st.success(f"Mitarbeiter ({new_emp_name}) hinzugefügt!")
      st.rerun()

  st.markdown("---")
  st.subheader("🗑️ Mitarbeiter löschen")
  if len(employees_list) > 0:
    emp_to_delete = st.selectbox("Mitarbeiter:", employees_list)
    if st.button("Löschen"):
      if len(employees_list) > 1:
        employees_list.remove(emp_to_delete)
        save_employees(employees_list)
        st.success("Mitarbeiter gelöscht!")
        st.rerun()
      else:
        st.warning("Es muss mindestens ein Mitarbeiter bleiben.")


# ---------------------------------------------------------
# الصفحة الخامسة: ملخص الأشهر (Monatsübersicht)
# ---------------------------------------------------------
elif page == t["p5"]:
  st.title("📅 Clean & Care GmbH - Monatsübersicht")
  
  selected_summary_month = st.text_input("Monat eingeben (z.B. Oktober 2026):", value="Oktober 2026")
  employees_list = load_employees()

  st.subheader(f"📊 Gesamtstunden für Monat: {selected_summary_month}")

  summary_data = []
  total_company_hours = 0.0

  for emp in employees_list:
    emp_df = load_employee_month_hours(emp, selected_summary_month)
    emp_total = emp_df["Arbeitszeit (abzgl. Pause)"].astype(float).sum() if "Arbeitszeit (abzgl. Pause)" in emp_df.columns else 0.0
    summary_data.append({
        "Mitarbeiter": emp,
        "Gesamtstunden": f"{emp_total:.2f} St."
    })
    total_company_hours += emp_total

  st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
  st.metric("Gesamtsumme aller Mitarbeiter:", f"{total_company_hours:.2f} St.")