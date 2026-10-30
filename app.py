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


# دوال إدارة العمال والموظفين
def load_employees():
  if os.path.exists(EMPLOYEES_FILE):
    try:
      with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return ["Sakleh Alsoudi", "Alaa Edin Ibrahim", "Neuer Mitarbeiter"]


def save_employees(emp_list):
  with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
    json.dump(emp_list, f, ensure_ascii=False, indent=4)


# دوال حفظ وتحميل ساعات كل موظف مع دعم حفظ الأشهر
def get_employee_file(emp_name):
  safe_name = "".join(c for c in emp_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
  return f"emp_hours_{safe_name}.json"


def load_employee_hours(emp_name):
  filename = get_employee_file(emp_name)
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


def save_employee_hours(emp_name, df):
  filename = get_employee_file(emp_name)
  data = df.to_dict(orient="list")
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


# دوال للمواقع
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


# القائمة الجانبية باللغة الألمانية مع الصفحة الجديدة
st.sidebar.title("📌 Hauptmenü")
page = st.sidebar.radio(
    "Navigation wählen:",
    [
        "📋 Mitarbeiter Stundenzettel",
        "👥 Mitarbeiterverwaltung",
        "🏢 Objekt-Stundenübersicht",
        "📅 Monatsübersicht (ملخص الأشهر)",
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
  
  sig_data = [
      ["__________________________________", "__________________________________"],
      ["Unterschrift Arbeitnehmer", "Unterschrift Arbeitgeber / GF"],
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
# دالة توليد PDF لتقرير ساعات المواقع بالعرض
# ---------------------------------------------------------
def generate_location_pdf(month_name, year_val, df, days_count):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
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
  
  t = Table(table_data, colWidths=col_widths, repeatRows=1)
  t.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d0d0d0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, -1), 7),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
      ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
  ]))
  
  elements.append(t)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


# ---------------------------------------------------------
# صفحة إدارة العمال (Mitarbeiterverwaltung)
# ---------------------------------------------------------
if page == "👥 Mitarbeiterverwaltung":
  st.title("👥 Clean & Care GmbH - Mitarbeiterverwaltung")
  st.write("Mitarbeiter hinzufügen oder löschen:")

  if "employees_list" not in st.session_state:
    st.session_state.employees_list = load_employees()

  st.subheader("➕ Neuen Mitarbeiter hinzufügen")
  new_emp_name = st.text_input("Name des Mitarbeiters:")
  
  if st.button("Hinzufügen"):
    if new_emp_name and new_emp_name not in st.session_state.employees_list:
      st.session_state.employees_list.append(new_emp_name)
      save_employees(st.session_state.employees_list)
      save_employee_hours(new_emp_name, load_employee_hours(new_emp_name))
      st.success(f"Mitarbeiter ({new_emp_name}) erfolgreich hinzugefügt und gespeichert!")
      st.rerun()
    elif not new_emp_name:
      st.warning("Bitte geben Sie einen Namen ein.")
    else:
      st.info("Dieser Mitarbeiter existiert bereits.")

  st.markdown("---")
  st.subheader("🗑️ Mitarbeiter löschen")
  if len(st.session_state.employees_list) > 0:
    emp_to_delete = st.selectbox("Mitarbeiter auswählen:", st.session_state.employees_list)
    if st.button("Ausählten Mitarbeiter löschen"):
      if len(st.session_state.employees_list) > 1:
        st.session_state.employees_list.remove(emp_to_delete)
        save_employees(st.session_state.employees_list)
        st.success(f"Mitarbeiter ({emp_to_delete}) wurde gelöscht!")
        st.rerun()
      else:
        st.warning("Es muss mindestens ein Mitarbeiter erhalten bleiben.")

  st.markdown("---")
  st.subheader("📋 Aktuelle Mitarbeiterliste:")
  for idx, emp in enumerate(st.session_state.employees_list, 1):
    st.write(f"{idx}. {emp}")

# ---------------------------------------------------------
# الصفحة الأولى: تسجيل ساعات الموظفين (Stundenzettel لكل موظف مستقل)
# ---------------------------------------------------------
elif page == "📋 Mitarbeiter Stundenzettel":
  st.title("📋 Clean & Care GmbH - Stundenzettel")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  if "employees_list" not in st.session_state:
    st.session_state.employees_list = load_employees()

  if "emp_meta" not in st.session_state:
    st.session_state.emp_meta = {"month_str": "Oktober 2026"}

  col1, col2 = st.columns(2)
  with col1:
    selected_employee = st.selectbox("Name (Mitarbeiter wählen):", st.session_state.employees_list, key="selected_emp_dropdown")
  with col2:
    stundenzettel_monat = st.text_input(
        "Stundenzettel Monat:",
        value=st.session_state.emp_meta["month_str"],
        key="input_month_str",
    )
    st.session_state.emp_meta["month_str"] = stundenzettel_monat

  st.subheader(f"Arbeitszeiterfassung für: {selected_employee}")

  current_emp_df = load_employee_hours(selected_employee)

  edited_df = st.data_editor(
      current_emp_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"emp_table_editor_{selected_employee}",
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

    if break_val > 0:
      edited_df.at[index, "Pause"] = str(break_val)
    else:
      if not p_input or p_input == "nan":
        edited_df.at[index, "Pause"] = ""

    edited_df.at[index, "Arbeitszeit (abzgl. Pause)"] = round(hrs, 2)
    total_sum_hours += hrs

  st.markdown("---")
  col_res1, col_res2, col_res3 = st.columns([2, 1, 1])
  with col_res1:
    pdf_data = generate_employee_pdf(selected_employee, stundenzettel_monat, edited_df, total_sum_hours)
    st.download_button(
        label="📥 Stundenzettel PDF herunterladen",
        data=pdf_data,
        file_name=f"Stundenzettel_{selected_employee}.pdf",
        mime="application/pdf",
    )
  with col_res2:
    st.metric(label="Summe:", value=f"{total_sum_hours:.2f} St.")
  with col_res3:
    if st.button(f"💾 {selected_employee} Stunden speichern"):
      save_employee_hours(selected_employee, edited_df)
      st.success(f"Stunden für {selected_employee} erfolgreich gespeichert!")

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
# الصفحة الثالثة: متابعة ساعات المواقع (Objekt-Stundenübersicht)
# ---------------------------------------------------------
elif page == "🏢 Objekt-Stundenübersicht":
  st.title("🏢 Clean & Care GmbH - Objekt-Stundenübersicht")

  col1, col2 = st.columns(2)
  with col1:
    loc_month = st.selectbox(
        "Monat auswählen:",
        [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ],
        index=9,
        key="loc_month_select"
    )
  with col2:
    loc_year = st.number_input("Jahr:", min_value=2024, max_value=2030, value=2026, key="loc_year_input")

  month_map = {
      "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
      "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
  }
  m_num = month_map[loc_month]
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
  
  if st.button("💾 Objekt-Stunden speichern"):
    save_locations(edited_locations_df)
    st.success("Alle Objekt-Stunden wurden erfolgreich gespeichert!")

  st.subheader("📊 Zusammenfassung")
  summary_df = edited_locations_df[["Objekt", "Summe"]]
  st.dataframe(summary_df, use_container_width=True)

  total_all_locations = summary_df["Summe"].sum()
  st.metric(
      label="Gesamtstunden aller Objekte:",
      value=f"{total_all_locations:.2f} St.",
  )

  st.markdown("---")
  loc_pdf_data = generate_location_pdf(loc_month, loc_year, edited_locations_df, days_in_month)
  st.download_button(
      label="📥 Objekt-Bericht PDF herunterladen (Querformat)",
      data=loc_pdf_data,
      file_name=f"Objekte_Report_{loc_month}_{loc_year}.pdf",
      mime="application/pdf",
  )

# ---------------------------------------------------------
# الصفحة الرابعة: ملخص الأشهر (Monatsübersicht) لعرض أسماء العمال وساعاتهم الكلية للشهر المختار
# ---------------------------------------------------------
elif page == "📅 Monatsübersicht (ملخص الأشهر)":
  st.title("📅 Clean & Care GmbH - Monatsübersicht")
  st.write("Wählen Sie einen Monat, um die Gesamtstunden aller Mitarbeiter zu sehen:")

  selected_summary_month = st.selectbox(
      "Monat wählen:",
      [
          "Januar", "Februar", "März", "April", "Mai", "Juni",
          "Juli", "August", "September", "Oktober", "November", "Dezember",
          "Oktober 2026"  # دعم للشهر الافتراضي المكتوب
      ],
      index=9,
      key="summary_month_dropdown"
  )

  if "employees_list" not in st.session_state:
    st.session_state.employees_list = load_employees()

  st.subheader(f"📊 Gesamtstunden der Mitarbeiter für: {selected_summary_month}")

  summary_data = []
  total_company_hours = 0.0

  for emp in st.session_state.employees_list:
    emp_df = load_employee_hours(emp)
    # جمع الساعات الكلية المسجلة بجدول هذا الموظف
    if "Arbeitszeit (abzgl. Pause)" in emp_df.columns:
      emp_total = emp_df["Arbeitszeit (abzgl. Pause)"].astype(float).sum()
    else:
      emp_total = 0.0
    
    summary_data.append({
        "Mitarbeiter (اسم الموظف)": emp,
        "Gesamtstunden (إجمالي الساعات)": f"{emp_total:.2f} St."
    })
    total_company_hours += emp_total

  summary_table_df = pd.DataFrame(summary_data)
  
  st.dataframe(summary_table_df, use_container_width=True)

  st.markdown("---")
  st.metric(
      label="Gesamtsumme aller Mitarbeiter (إجمالي ساعات كل العمال):",
      value=f"{total_company_hours:.2f} St."
  )