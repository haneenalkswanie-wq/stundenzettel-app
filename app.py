from datetime import datetime, timedelta
import io
import json
import os
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import streamlit as st
from supabase import create_client, Client


# إعدادات الصفحة
st.set_page_config(
    page_title="Clean & Care - Stundenzettel", page_icon="📋", layout="wide"
)

# ---------------------------------------------------------
# إعدادات الاتصال بـ Supabase
# ---------------------------------------------------------
SUPABASE_URL = "https://knzrtbjwqqhxghtfasvy.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()


# ---------------------------------------------------------
# قاعدة البيانات السحابية Supabase (إضافة جدول المدن وربط العمال)
# ---------------------------------------------------------
def init_db_supabase():
  try:
    # التحقق من العمال
    res = supabase.table("employees").select("name").execute()
    if not res.data or len(res.data) == 0:
      for emp in ["Sakleh Alsoudi", "Alaa Edin Ibrahim"]:
        supabase.table("employees").upsert({"name": emp}).execute()
        
    # التحقق من الأماكن
    res_p = supabase.table("places").select("name").execute()
    if not res_p.data or len(res_p.data) == 0:
      for place in ["Limehome Salzburg", "Nespresso Store", "IKEA Wals", "Villach Hauptplatz"]:
        supabase.table("places").upsert({"name": place}).execute()

    # التحقق من المدن (Cities)
    res_c = supabase.table("cities").select("name").execute()
    if not res_c.data or len(res_c.data) == 0:
      for city in ["Salzburg", "Villach", "Klagenfurt", "Bregenz"]:
        supabase.table("cities").upsert({"name": city}).execute()

    # التحقق من جدول ربط العمال بالمدن (employee_cities)
    res_ec = supabase.table("employee_cities").select("*").execute()
    if not res_ec.data or len(res_ec.data) == 0:
      default_mappings = [
          {"employee": "Sakleh Alsoudi", "city": "Salzburg"},
          {"employee": "Alaa Edin Ibrahim", "city": "Salzburg"}
      ]
      for m in default_mappings:
        supabase.table("employee_cities").upsert(m).execute()
  except Exception as e:
    st.sidebar.warning(f"ملاحظة اتصال قاعدة البيانات: {e}")

init_db_supabase()


def load_employees():
  try:
    res = supabase.table("employees").select("name").execute()
    if res.data:
      return sorted([row["name"] for row in res.data])
  except:
    pass
  return ["Sakleh Alsoudi", "Alaa Edin Ibrahim"]


def save_employees(emp_list):
  try:
    existing = supabase.table("employees").select("name").execute()
    if existing.data:
      for row in existing.data:
        supabase.table("employees").delete().eq("name", row["name"]).execute()
    for emp in emp_list:
      supabase.table("employees").upsert({"name": emp}).execute()
  except Exception as e:
    st.error(f"خطأ في حفظ العمال: {e}")


def load_places():
  try:
    res = supabase.table("places").select("name").execute()
    if res.data:
      return sorted([row["name"] for row in res.data])
  except:
    pass
  return ["Limehome Salzburg", "Nespresso Store", "IKEA Wals", "Villach Hauptplatz"]


def save_places(places_list):
  try:
    existing = supabase.table("places").select("name").execute()
    if existing.data:
      for row in existing.data:
        supabase.table("places").delete().eq("name", row["name"]).execute()
    for place in places_list:
      supabase.table("places").upsert({"name": place}).execute()
  except Exception as e:
    st.error(f"خطأ في حفظ الأماكن: {e}")


# دوال إدارة المدن والربط
def load_cities():
  try:
    res = supabase.table("cities").select("name").execute()
    if res.data:
      return sorted([row["name"] for row in res.data])
  except:
    pass
  return ["Salzburg", "Villach", "Klagenfurt", "Bregenz"]


def save_cities(cities_list):
  try:
    existing = supabase.table("cities").select("name").execute()
    if existing.data:
      for row in existing.data:
        supabase.table("cities").delete().eq("name", row["name"]).execute()
    for city in cities_list:
      supabase.table("cities").upsert({"name": city}).execute()
  except Exception as e:
    st.error(f"خطأ في حفظ المدن: {e}")


def get_employee_city(emp_name):
  try:
    res = supabase.table("employee_cities").select("city").eq("employee", emp_name).execute()
    if res.data and len(res.data) > 0:
      return res.data[0]["city"]
  except:
    pass
  return "Salzburg"


def set_employee_city(emp_name, city_name):
  try:
    supabase.table("employee_cities").upsert({"employee": emp_name, "city": city_name}).execute()
  except Exception as e:
    st.error(f"خطأ في ربط العامل بالمدينة: {e}")


def get_employees_by_city(city_name):
  all_emps = load_employees()
  if city_name == "Alle Städte" or not city_name:
    return all_emps
  filtered = []
  for emp in all_emps:
    if get_employee_city(emp) == city_name:
      filtered.append(emp)
  return filtered if filtered else all_emps


def load_employee_month_hours(emp_name, month_str, year_val):
  try:
    res = supabase.table("monthly_hours").select("content").eq("emp", emp_name).eq("month", month_str).eq("year", int(year_val)).execute()
    if res.data and len(res.data) > 0:
      data = json.loads(res.data[0]["content"])
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
  try:
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("monthly_hours").upsert({
        "emp": emp_name,
        "month": month_str,
        "year": int(year_val),
        "content": content
    }).execute()
  except Exception as e:
    st.error(f"خطأ في الحفظ الشهري: {e}")


def load_daily_emp_hours(emp_name, month_str, year_val):
  try:
    res = supabase.table("daily_hours").select("content").eq("emp", emp_name).eq("month", month_str).eq("year", int(year_val)).execute()
    if res.data and len(res.data) > 0:
      data = json.loads(res.data[0]["content"])
      df = pd.DataFrame(data)
      for i in range(1, 4):
        if f"Hrs{i}" not in df.columns:
          df[f"Hrs{i}"] = ""
      return df
  except:
    pass
  
  days_data = []
  for day in range(1, 32):
    days_data.append(
        {
            "Datum": str(day),
            "Ort 1": "", "Beginn 1": "", "Ende 1": "", "Hrs1": "",
            "Ort 2": "", "Beginn 2": "", "Ende 2": "", "Hrs2": "",
            "Ort 3": "", "Beginn 3": "", "Ende 3": "", "Hrs3": "",
            "Pause": "",
            "Gesamtstunden": 0.0,
        }
    )
  return pd.DataFrame(days_data)


def save_daily_emp_hours(emp_name, month_str, year_val, df):
  try:
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("daily_hours").upsert({
        "emp": emp_name,
        "month": month_str,
        "year": int(year_val),
        "content": content
    }).execute()
  except Exception as e:
    st.error(f"خطأ في حفظ الساعات اليومية: {e}")


def load_tickets_data(month_str, year_val):
  try:
    res = supabase.table("tickets_data").select("content").eq("month", month_str).eq("year", int(year_val)).execute()
    if res.data and len(res.data) > 0:
      data = json.loads(res.data[0]["content"])
      return pd.DataFrame(data)
  except:
    pass
  
  tickets_rows = []
  month_map = {
      "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
      "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
  }
  m_num = month_map.get(month_str, 10)
  days_in_m = pd.Period(f"{year_val}-{m_num}").days_in_month
  
  for day in range(1, days_in_m + 1):
    tickets_rows.append({
        "Datum": str(day),
        "Ort": "",
        "Ticket-Nummer": "",
        "Beginn": "",
        "Ende": "",
        "Bemerkung": "",
        "Netto-Stunden": 0.0
    })
  return pd.DataFrame(tickets_rows)


def save_tickets_data(month_str, year_val, df):
  try:
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("tickets_data").upsert({
        "month": month_str,
        "year": int(year_val),
        "content": content
    }).execute()
  except Exception as e:
    st.error(f"خطأ في حفظ التذاكر: {e}")


months_list_de = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]
years_list = [2024, 2025, 2026, 2027, 2028, 2029, 2030]

now = datetime.now()
current_year_val = now.year
current_month_de = months_list_de[now.month - 1]

default_year_index = years_list.index(current_year_val) if current_year_val in years_list else 2
default_month_index = months_list_de.index(current_month_de)


# ---------------------------------------------------------
# نظام لغة القائمة الجانبية
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
        "p7": "🎫 Einsatz-Tickets",
        "p8": "🚆 Zug-Fahrten (Züge)",
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
        "del_place": "Ort löschen",
        "city_label": "Stadt wählen (المدينة):",
        "all_cities": "Alle Städte",
    }
else:
    t = {
        "menu": "📌 القائمة الرئيسية (Hauptmenü)",
        "p1": "📋 استمارة ساعات العمال (Mitarbeiter Stundenzettel)",
        "p2": "📝 الساعات اليومية (Tägliche Stunden)",
        "p3": "🏢 ملخص ساعات المواقع (Objekt-Stundenübersicht)",
        "p4": "🏢 الأماكن وساعات العمال (Orte & Mitarbeiter)",
        "p5": "👥 إدارة العمال والمدن (Mitarbeiter & Städte)",
        "p6": "📅 ملخص الأشهر (Monatsübersicht)",
        "p7": "🎫 تذاكر المهام (Einsatz-Tickets)",
        "p8": "🚆 جدول القطارات (Zug-Fahrten)",
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
        "del_place": "Ort löschen",
        "city_label": "Stadt wählen (المدينة):",
        "all_cities": "Alle Städte (كل المدن)",
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
        t["p7"],
        t["p8"],
    ],
)


# ---------------------------------------------------------
# دوال طباعة PDF باللغة الألمانية حصراً
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
  for _, row in df.iterrows():
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


def generate_daily_pdf(emp_name, month_str, year_val, df, total_hours):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=13, leading=16, textColor=colors.HexColor("#111111"))
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH - Tägliche Arbeitszeiten</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 10))
  elements.append(Paragraph(f"<b>Mitarbeiter:</b> {emp_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Monat:</b> {month_str} {year_val}", styles['Normal']))
  elements.append(Spacer(1, 10))
  
  # أعمدة الجدول المحدثة لتشمل الاستراحة لكل مكان
  table_data = [["Tag", "Ort 1", "Std 1", "Pause 1", "Ort 2", "Std 2", "Pause 2", "Ort 3", "Std 3", "Pause 3", "Gesamt"]]
  for _, row in df.iterrows():
    table_data.append([
        str(row["Datum"]),
        str(row["Ort 1"] if pd.notna(row["Ort 1"]) else ""), str(row.get("Hrs1", "")), str(row.get("Pause 1", "")),
        str(row["Ort 2"] if pd.notna(row["Ort 2"]) else ""), str(row.get("Hrs2", "")), str(row.get("Pause 2", "")),
        str(row["Ort 3"] if pd.notna(row["Ort 3"]) else ""), str(row.get("Hrs3", "")), str(row.get("Pause 3", "")),
        str(row["Gesamtstunden"])
    ])
  table_data.append(["Summe:", "", "", "", "", "", "", "", "", "", f"{total_hours:.2f} St."])
  
  t_pdf = Table(table_data, colWidths=[25, 75, 35, 45, 75, 35, 45, 75, 35, 45, 55])
  t_pdf.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, -1), 7),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
      ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#666666")),
      ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
      ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
      ('GRID', (0, -1), (-1, -1), 1, colors.HexColor("#000000")),
  ]))
  elements.append(t_pdf)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()

def generate_single_location_pdf(place_name, month_str, year_val, df, total_hours):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor("#111111"))
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH - Objekt-Stundenbericht</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 15))
  elements.append(Paragraph(f"<b>Objekt / Ort:</b> {place_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Monat:</b> {month_str} {year_val}", styles['Normal']))
  elements.append(Spacer(1, 15))
  
  table_data = [["Tag (Datum)", "Stunden"]]
  for _, row in df.iterrows():
    table_data.append([str(row["Tag"]), str(row["Stunden"])])
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
  for _, row in df.iterrows():
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
  for _, row in df.iterrows():
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


def generate_tickets_pdf(month_str, year_val, df, total_hours):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor("#111111"))
  
  elements.append(Paragraph("<b>CLEAN & CARE GmbH - Einsatz-Tickets Bericht</b>", title_style))
  elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
  elements.append(Spacer(1, 15))
  elements.append(Paragraph(f"<b>Monat:</b> {month_str} {year_val}", styles['Normal']))
  elements.append(Spacer(1, 15))
  
  table_data = [["Datum", "Ort", "Ticket", "Beginn", "Ende", "Bemerkung", "Stunden"]]
  for _, row in df.iterrows():
    table_data.append([
        str(row["Datum"]),
        str(row["Ort"] if pd.notna(row["Ort"]) else ""),
        str(row["Ticket-Nummer"] if pd.notna(row["Ticket-Nummer"]) else ""),
        str(row["Beginn"] if pd.notna(row["Beginn"]) else ""),
        str(row["Ende"] if pd.notna(row["Ende"]) else ""),
        str(row["Bemerkung"] if pd.notna(row["Bemerkung"]) else ""),
        str(row["Netto-Stunden"])
    ])
  table_data.append(["Summe:", "", "", "", "", "", f"{total_hours:.2f} St."])
  
  t_pdf = Table(table_data, colWidths=[40, 90, 70, 60, 60, 110, 70])
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
# الصفحة الأولى: استمارة ساعات العمال (Mitarbeiter Stundenzettel)
# (تبقى مستقلة كما طلبت)
# ---------------------------------------------------------
if page == t["p1"]:
  st.title("📋 Clean & Care GmbH - Stundenzettel")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  employees_list = load_employees()
  places_list = [""] + load_places()
  
  col1, col2, col3 = st.columns(3)
  with col1:
    selected_employee = st.selectbox(t["emp_label"], employees_list, key="p1_emp")
  with col2:
    selected_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="p1_month")
  with col3:
    selected_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="p1_year")

  st.subheader(f"Arbeitszeiterfassung für: {selected_employee} ({selected_month} {selected_year})")

  current_emp_df = load_employee_month_hours(selected_employee, selected_month, selected_year)

  edited_df = st.data_editor(
      current_emp_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"p1_table_{selected_employee}_{selected_month}_{selected_year}",
      column_config={
          "Ort": st.column_config.SelectboxColumn("Ort", options=places_list),
      }
  )

  edited_df = edited_df.astype(object)

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
          if t2 < t1:
              t2 += timedelta(days=1)

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
# الصفحة الثانية: الساعات اليومية (Tägliche Stunden) - استراحة لكل مكان على حدة
# ---------------------------------------------------------
elif page == t["p2"]:
  st.title("📝 Clean & Care GmbH - Tägliche Stunden")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  cities_list = load_cities()
  places_list = [""] + load_places()

  col_c, col_m, col_y = st.columns(3)
  with col_c:
    selected_city = st.selectbox(t["city_label"], cities_list, key="p2_city_select")
  with col_m:
    daily_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="daily_month_select")
  with col_y:
    daily_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="daily_year_select")

  city_employees = get_employees_by_city(selected_city)

  col1, col2 = st.columns(2)
  with col1:
    daily_emp = st.selectbox(t["emp_label"], city_employees, key="daily_emp_select") if city_employees else st.warning("Keine Mitarbeiter in dieser Stadt")

  if city_employees:
    st.subheader(f"Tägliche Stunden für: {daily_emp} ({daily_month} {daily_year})")

    # تحديث هيكل البيانات اليومية ليشمل استراحة خاصة بكل مكان
    def load_custom_daily_hours(emp_name, month_str, year_val):
      try:
        res = supabase.table("daily_hours").select("content").eq("emp", emp_name).eq("month", month_str).eq("year", int(year_val)).execute()
        if res.data and len(res.data) > 0:
          data = json.loads(res.data[0]["content"])
          df = pd.DataFrame(data)
          
          # 1. أولاً: نقل قيم استراحة العمود القديم (Pause) إلى Pause 1 إن وجدت
          if "Pause" in df.columns:
            for idx, val in enumerate(df["Pause"]):
              if pd.notna(val) and str(val).strip() != "" and str(val).strip() != "nan":
                if "Pause 1" not in df.columns or pd.isna(df.loc[idx, "Pause 1"]) or str(df.loc[idx, "Pause 1"]).strip() in ["", "nan"]:
                  df.loc[idx, "Pause 1"] = val
            # 2. ثانياً: حذف العمود القديم نهائياً لكي لا يظهر أبداً
            df = df.drop(columns=["Pause"])

          # التأكد من وجود كافة الأعمدة الجديدة
          for i in range(1, 4):
            if f"Pause {i}" not in df.columns:
              df[f"Pause {i}"] = ""
            if f"Hrs{i}" not in df.columns:
              df[f"Hrs{i}"] = ""
              
          # ترتيب الأعمدة بشكل منظم وجميل بجانب بعضها
          cols_order = [
              "Datum", 
              "Ort 1", "Beginn 1", "Ende 1", "Pause 1", "Hrs1",
              "Ort 2", "Beginn 2", "Ende 2", "Pause 2", "Hrs2",
              "Ort 3", "Beginn 3", "Ende 3", "Pause 3", "Hrs3",
              "Gesamtstunden"
          ]
          existing_cols = [c for c in cols_order if c in df.columns]
          other_cols = [c for c in df.columns if c not in existing_cols]
          df = df[existing_cols + other_cols]
          
          return df
      except:
        pass
      
      days_data = []
      for day in range(1, 32):
        days_data.append(
            {
                "Datum": str(day),
                "Ort 1": "", "Beginn 1": "", "Ende 1": "", "Pause 1": "", "Hrs1": "",
                "Ort 2": "", "Beginn 2": "", "Ende 2": "", "Pause 2": "", "Hrs2": "",
                "Ort 3": "", "Beginn 3": "", "Ende 3": "", "Pause 3": "", "Hrs3": "",
                "Gesamtstunden": 0.0,
            }
        )
      return pd.DataFrame(days_data)

    daily_df = load_custom_daily_hours(daily_emp, daily_month, daily_year)

    edited_daily_df = st.data_editor(
        daily_df,
        num_rows="fixed",
        use_container_width=True,
        key=f"daily_table_{daily_emp}_{daily_month}_{daily_year}",
        column_config={
            "Ort 1": st.column_config.SelectboxColumn("Ort 1", options=places_list),
            "Ort 2": st.column_config.SelectboxColumn("Ort 2", options=places_list),
            "Ort 3": st.column_config.SelectboxColumn("Ort 3", options=places_list),
        }
    )

    edited_daily_df = edited_daily_df.astype(object)

    total_daily_sum = 0.0
    for index, row in edited_daily_df.iterrows():
      net_day_total = 0.0
      
      for i in range(1, 4):
        b_str = str(row.get(f"Beginn {i}", "")).strip()
        e_str = str(row.get(f"Ende {i}", "")).strip()
        p_str = str(row.get(f"Pause {i}", "")).strip()
        
        hrs = 0.0
        break_val = 0.0

        if b_str and e_str and b_str != "nan" and e_str != "nan":
          for fmt in ("%H:%M", "%H.%M", "%H"):
            try:
              t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
              t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
              if t2 < t1:
                t2 += timedelta(days=1)

              gh = (t2 - t1).total_seconds() / 3600
              if gh > 0:
                # حساب استراحة هذا المكان بالذات
                if p_str and p_str != "nan" and p_str != "":
                  try:
                    break_val = float(p_str.replace(",", "."))
                  except:
                    break_val = 0.0
                hrs = max(0.0, gh - break_val)
              break
            except:
              continue

        if break_val > 0:
          edited_daily_df.at[index, f"Pause {i}"] = str(break_val)
        else:
          if not p_str or p_str == "nan":
            edited_daily_df.at[index, f"Pause {i}"] = ""

        edited_daily_df.at[index, f"Hrs{i}"] = round(hrs, 2) if hrs > 0 else ""
        net_day_total += hrs

      edited_daily_df.at[index, "Gesamtstunden"] = round(net_day_total, 2)
      total_daily_sum += net_day_total

    st.markdown("---")
    col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
    with col_d1:
      # دالة الطباعة المحدثة إذا احتجت لتعديل شكل PDF لاحقاً
      pdf_daily_data = generate_daily_pdf(daily_emp, daily_month, daily_year, edited_daily_df, total_daily_sum)
      st.download_button(t["pdf_btn"], pdf_daily_data, f"Tägliche_Stunden_{daily_emp}_{daily_month}_{daily_year}.pdf", "application/pdf", key="p2_pdf")
    with col_d2:
      if st.button(t["save_btn"], key="p2_save"):
        save_daily_emp_hours(daily_emp, daily_month, daily_year, edited_daily_df)
        st.success(t["success_msg"])
    with col_d3:
      st.metric(t["sum_label"], f"{total_daily_sum:.2f} St.")

# ---------------------------------------------------------
# الصفحة الثالثة: ملخص ساعات المواقع (Objekt-Stundenübersicht)
# ---------------------------------------------------------
elif page == t["p3"]:
  st.title("🏢 Clean & Care GmbH - Objekt-Stundenübersicht")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  places_list = load_places()

  col1, col2, col3 = st.columns(3)
  with col1:
    selected_loc_place = st.selectbox(t["place_label"], places_list, key="loc_place_select") if places_list else st.warning("Kein Ort vorhanden")
  with col2:
    loc_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="loc_month_select")
  with col3:
    loc_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="loc_year_select")

  month_map = {
      "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
      "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
  }
  m_num = month_map.get(loc_month, 10)
  days_in_month = pd.Period(f"{loc_year}-{m_num}").days_in_month

  if places_list:
    st.subheader(f"Objekt: {selected_loc_place} ({loc_month} {loc_year})")

    try:
      res_rows = supabase.table("daily_hours").select("content").eq("month", loc_month).eq("year", int(loc_year)).execute()
      rows = res_rows.data if res_rows.data else []
    except:
      rows = []
    
    loc_days_data = []
    for d in range(1, days_in_month + 1):
      day_sum = 0.0
      for row in rows:
        try:
          emp_data = json.loads(row["content"])
          df_emp = pd.DataFrame(emp_data)
          for _, r in df_emp.iterrows():
            if str(r.get("Datum")) == str(d):
              day_gross = 0.0
              locs_in_day = []
              for i in range(1, 4):
                loc_name = str(r.get(f"Ort {i}")).strip()
                b_str = str(r.get(f"Beginn {i}", "")).strip()
                e_str = str(r.get(f"Ende {i}", "")).strip()
                loc_hrs = 0.0
                if b_str and e_str and b_str != "nan" and e_str != "nan":
                  for fmt in ("%H:%M", "%H.%M", "%H"):
                    try:
                      t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
                      t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
                      gh = (t2 - t1).total_seconds() / 3600
                      if gh > 0:
                        loc_hrs = gh
                      break
                    except:
                      continue
                day_gross += loc_hrs
                locs_in_day.append((loc_name, loc_hrs))

              p_input = str(r.get("Pause", "")).strip()
              break_val = float(p_input.replace(",", ".")) if p_input and p_input != "nan" and p_input != "" else 0.0

              for loc_name, loc_hrs in locs_in_day:
                if loc_name.lower() == selected_loc_place.strip().lower() and loc_hrs > 0:
                  ratio = (loc_hrs / day_gross) if day_gross > 0 else 0
                  net_loc_hrs = max(0.0, loc_hrs - (break_val * ratio))
                  day_sum += net_loc_hrs
        except:
          pass
      loc_days_data.append({"Tag": str(d), "Stunden": round(day_sum, 2)})

    loc_df = pd.DataFrame(loc_days_data)
    st.dataframe(loc_df, use_container_width=True)

    total_loc_sum = loc_df["Stunden"].astype(float).sum()

    st.markdown("---")
    col_l1, col_l2 = st.columns([2, 1])
    with col_l1:
      loc_pdf_data = generate_single_location_pdf(selected_loc_place, loc_month, loc_year, loc_df, total_loc_sum)
      st.download_button(t["pdf_btn"], loc_pdf_data, f"Objekt_{selected_loc_place}_{loc_month}_{loc_year}.pdf", "application/pdf", key="p3_pdf")
    with col_l2:
      st.metric(t["sum_label"], f"{total_loc_sum:.2f} St.")

  st.markdown("---")
  add_col, del_col = st.columns(2)
  with add_col:
    st.subheader(t["add_place"])
    new_place_name = st.text_input("Name des neuen Ortes:", key="p3_new_place")
    if st.button(t["add_btn"], key="p3_add_btn"):
      if new_place_name and new_place_name not in places_list:
        places_list.append(new_place_name)
        save_places(places_list)
        st.success(t["success_msg"])
        st.rerun()
  with del_col:
    st.subheader(t["del_place"])
    if len(places_list) > 0:
      place_to_delete = st.selectbox("Ort löschen:", places_list, key="p3_del_select")
      if st.button(t["del_btn"], key="p3_del_btn"):
        if len(places_list) > 1:
          places_list.remove(place_to_delete)
          save_places(places_list)
          st.success(t["success_msg"])
          st.rerun()
        else:
          st.warning("Es muss mindestens ein Ort bleiben.")


# ---------------------------------------------------------
# الصفحة الرابعة: الأماكن وساعات العمال (Orte & Mitarbeiter-Stunden)
# ---------------------------------------------------------
elif page == t["p4"]:
  st.title("🏢 Clean & Care GmbH - Orte & Mitarbeiter-Stunden")

  places_list = load_places()

  col1, col2, col3 = st.columns(3)
  with col1:
    selected_place = st.selectbox(t["place_label"], places_list, key="p4_place_select") if places_list else st.warning("Kein Ort vorhanden")
  with col2:
    place_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="place_month_select")
  with col3:
    place_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="place_year_select")

  if places_list:
    st.subheader(f"Mitarbeiter-Stunden für Ort: {selected_place} ({place_month} {place_year})")

    try:
      res_rows = supabase.table("daily_hours").select("emp, content").eq("month", place_month).eq("year", int(place_year)).execute()
      rows = res_rows.data if res_rows.data else []
    except:
      rows = []

    place_data_rows = []
    for row in rows:
      emp = row["emp"]
      try:
        emp_data = json.loads(row["content"])
        emp_daily_df = pd.DataFrame(emp_data)
        emp_place_hours = 0.0
        for _, r in emp_daily_df.iterrows():
          day_gross = 0.0
          locs_in_day = []
          for i in range(1, 4):
            loc_name = str(r.get(f"Ort {i}")).strip()
            b_str = str(r.get(f"Beginn {i}", "")).strip()
            e_str = str(r.get(f"Ende {i}", "")).strip()
            loc_hrs = 0.0
            if b_str and e_str and b_str != "nan" and e_str != "nan":
              for fmt in ("%H:%M", "%H.%M", "%H"):
                try:
                  t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
                  t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
                  gh = (t2 - t1).total_seconds() / 3600
                  if gh > 0:
                    loc_hrs = gh
                  break
                except:
                  continue
            day_gross += loc_hrs
            locs_in_day.append((loc_name, loc_hrs))

          p_input = str(r.get("Pause", "")).strip()
          break_val = float(p_input.replace(",", ".")) if p_input and p_input != "nan" and p_input != "" else 0.0

          for loc_name, loc_hrs in locs_in_day:
            if loc_name.lower() == selected_place.strip().lower() and loc_hrs > 0:
              ratio = (loc_hrs / day_gross) if day_gross > 0 else 0
              net_loc_hrs = max(0.0, loc_hrs - (break_val * ratio))
              emp_place_hours += net_loc_hrs
        
        if emp_place_hours > 0:
          clean_emp_name = emp.strip()
          existing_row = next((r for r in place_data_rows if r["Mitarbeiter"].strip().lower() == clean_emp_name.lower()), None)
          if existing_row:
            existing_row["Stunden"] = round(existing_row["Stunden"] + emp_place_hours, 2)
          else:
            place_data_rows.append({"Mitarbeiter": clean_emp_name, "Stunden": round(emp_place_hours, 2)})
      except:
        pass

    if not place_data_rows:
      place_df = pd.DataFrame([{"Mitarbeiter": "Keine Stunden erfasst", "Stunden": 0.0}])
    else:
      place_df = pd.DataFrame(place_data_rows)

    st.dataframe(place_df, use_container_width=True)

    total_place_hours = place_df["Stunden"].astype(float).sum() if not place_df.empty else 0.0

    st.markdown("---")
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
      pdf_place_data = generate_place_pdf(selected_place, place_month, place_year, place_df, total_place_hours)
      st.download_button(t["pdf_btn"], pdf_place_data, f"Ort_Report_{selected_place}_{place_month}_{place_year}.pdf", "application/pdf", key="p4_pdf")
    with col_p2:
      st.metric(t["sum_label"], f"{total_place_hours:.2f} St.")


# ---------------------------------------------------------
# الصفحة الخامسة: إدارة العمال والمدن (Mitarbeiterverwaltung & Städte)
# ---------------------------------------------------------
elif page == t["p5"]:
  st.title("👥 Clean & Care GmbH - Mitarbeiter- & Städtederverwaltung")
  
  employees_list = load_employees()
  cities_list = load_cities()

  tab1, tab2 = st.tabs(["إدارة العمال وتعيين المدن", "إدارة المدن (Städte verwalten)"])

  with tab1:
    st.subheader("تعيين المدينة للعامل / Mitarbeiter-Stadtzuweisung")
    if employees_list and cities_list:
      selected_emp_to_assign = st.selectbox("اختر العامل:", employees_list, key="assign_emp")
      current_city = get_employee_city(selected_emp_to_assign)
      current_city_index = cities_list.index(current_city) if current_city in cities_list else 0
      
      assigned_city = st.selectbox("اختر المدينة:", cities_list, index=current_city_index, key="assign_city")
      if st.button("حفظ ربط العامل بالمدينة"):
        set_employee_city(selected_emp_to_assign, assigned_city)
        st.success(f"تم ربط العامل {selected_emp_to_assign} بمدينة {assigned_city} بنجاح!")

    st.markdown("---")
    st.subheader(t["add_emp"])
    new_emp_name = st.text_input("Name des Mitarbeiters:")
    default_emp_city = st.selectbox("المدينة الأساسية للعامل الجديد:", cities_list, key="new_emp_city")
    if st.button(t["add_btn"], key="add_emp_btn"):
      if new_emp_name and new_emp_name not in employees_list:
        employees_list.append(new_emp_name)
        save_employees(employees_list)
        set_employee_city(new_emp_name, default_emp_city)
        st.success(t["success_msg"])
        st.rerun()

    st.markdown("---")
    st.subheader(t["del_emp"])
    if len(employees_list) > 0:
      emp_to_delete = st.selectbox("Mitarbeiter löschen:", employees_list, key="del_emp_select")
      if st.button(t["del_btn"], key="del_emp_btn"):
        if len(employees_list) > 1:
          employees_list.remove(emp_to_delete)
          save_employees(employees_list)
          st.success("Mitarbeiter erfolgreich gelöscht!")
          st.rerun()
        else:
          st.warning("Es muss mindestens ein Mitarbeiter bleiben.")

  with tab2:
    st.subheader("إضافة وحذف المدن / Städte hinzufügen & löschen")
    new_city_name = st.text_input("اسم المدينة الجديدة (Neue Stadt):")
    if st.button("إضافة المدينة", key="add_city_btn"):
      if new_city_name and new_city_name not in cities_list:
        cities_list.append(new_city_name)
        save_cities(cities_list)
        st.success(t["success_msg"])
        st.rerun()

    st.markdown("---")
    if len(cities_list) > 0:
      city_to_delete = st.selectbox("حذف مدينة (Stadt löschen):", cities_list, key="del_city_select")
      if st.button("حذف المدينة المحددة", key="del_city_btn"):
        if len(cities_list) > 1:
          cities_list.remove(city_to_delete)
          save_cities(cities_list)
          st.success("Stadt erfolgreich gelöscht!")
          st.rerun()
        else:
          st.warning("Es muss mindestens eine Stadt bleiben.")


# ---------------------------------------------------------
# الصفحة السادسة: ملخص الأشهر (Monatsübersicht) - مع خيار "جميع المدن"
# ---------------------------------------------------------
elif page == t["p6"]:
    st.title("📅 Clean & Care GmbH - Monatsübersicht")
    
    cities_list = [t["all_cities"]] + load_cities()

    col_c, col1, col2 = st.columns(3)
    with col_c:
        summary_city = st.selectbox(t["city_label"], cities_list, key="summary_city_select")
    with col1:
        summary_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="summary_month_select")
    with col2:
        summary_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="summary_year_select")

    allowed_emps = get_employees_by_city(summary_city)

    rows = []
    try:
        res_rows = supabase.table("daily_hours").select("emp, content").eq("month", summary_month).eq("year", int(summary_year)).execute()
        rows = res_rows.data if res_rows.data else []
    except Exception:
        rows = []

    zug_hours_per_emp = {}
    try:
        zug_res = supabase.table("trains_data").select("emp, content").eq("month", summary_month).eq("year", int(summary_year)).execute()
        zug_rows = zug_res.data if zug_res.data else []
        for z_row in zug_rows:
            z_emp = z_row.get("emp")
            if z_emp and z_row.get("content"):
                try:
                    z_df = pd.DataFrame(json.loads(z_row["content"]))
                    if "Gesamtstunden" in z_df.columns:
                        z_sum = z_df["Gesamtstunden"].astype(float).sum()
                        zug_hours_per_emp[z_emp.strip()] = z_sum
                except Exception:
                    pass
    except Exception:
        zug_hours_per_emp = {}

    summary_data = []
    total_company_hours = 0.0
    processed_emps = set()

    for row in rows:
        emp = row.get("emp")
        if not emp:
            continue
        clean_emp_name = emp.strip()
        
        if clean_emp_name not in allowed_emps:
            continue
          
        try:
            emp_data = json.loads(row["content"])
            emp_daily_df = pd.DataFrame(emp_data)
            emp_daily_total = emp_daily_df["Gesamtstunden"].astype(float).sum() if "Gesamtstunden" in emp_daily_df.columns else 0.0
        except Exception:
            emp_daily_total = 0.0

        emp_zug_total = zug_hours_per_emp.get(clean_emp_name, 0.0)
        total_emp_combined = emp_daily_total + emp_zug_total

        if total_emp_combined > 0 and clean_emp_name not in processed_emps:
            processed_emps.add(clean_emp_name)
            summary_data.append({
                "Mitarbeiter": clean_emp_name,
                "Gesamtstunden": f"{total_emp_combined:.2f} St."
            })
            total_company_hours += total_emp_combined

    for emp_name, zug_hrs in zug_hours_per_emp.items():
        if emp_name and emp_name.strip() not in processed_emps and zug_hrs > 0:
            clean_name = emp_name.strip()
            if clean_name in allowed_emps:
                processed_emps.add(clean_name)
                summary_data.append({
                    "Mitarbeiter": clean_name,
                    "Gesamtstunden": f"{zug_hrs:.2f} St."
                })
                total_company_hours += zug_hrs

    if not summary_data:
        summary_df = pd.DataFrame([{"Mitarbeiter": "Keine Stunden erfasst", "Gesamtstunden": "0.00 St."}])
    else:
        summary_df = pd.DataFrame(summary_data)

    st.dataframe(summary_df, use_container_width=True)
    st.markdown("---")
    
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        pdf_summary_data = generate_summary_pdf(summary_month, summary_year, summary_df, total_company_hours)
        st.download_button(t["pdf_btn"], pdf_summary_data, f"Monatsübersicht_{summary_month}_{summary_year}.pdf", "application/pdf", key="p6_pdf")
    with col_s2:
        st.metric("Gesamtsumme:", f"{total_company_hours:.2f} St.")


# ---------------------------------------------------------
# الصفحة السابعة: تذاكر المهام (Einsatz-Tickets)
# ---------------------------------------------------------
elif page == t["p7"]:
  st.title("🎫 Clean & Care GmbH - Einsatz-Tickets")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  places_list = [""] + load_places()

  col1, col2 = st.columns(2)
  with col1:
    ticket_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="ticket_month_select")
  with col2:
    ticket_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="ticket_year_select")

  st.subheader(f"Monats-Tickets ({ticket_month} {ticket_year})")

  tickets_df = load_tickets_data(ticket_month, ticket_year)

  edited_tickets_df = st.data_editor(
      tickets_df,
      num_rows="fixed",
      use_container_width=True,
      key=f"tickets_table_{ticket_month}_{ticket_year}",
      column_config={
          "Ort": st.column_config.SelectboxColumn("Ort", options=places_list),
      }
  )

  edited_tickets_df = edited_tickets_df.astype(object)

  total_tickets_sum = 0.0
  for index, row in edited_tickets_df.iterrows():
    b_str = str(row.get("Beginn", "")).strip()
    e_str = str(row.get("Ende", "")).strip()
    net_hrs = 0.0

    if b_str and e_str and b_str != "nan" and e_str != "nan":
      for fmt in ("%H:%M", "%H.%M", "%H"):
        try:
          t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
          t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
          gh = (t2 - t1).total_seconds() / 3600
          if gh > 0:
            net_hrs = gh
          break
        except:
          continue

    edited_tickets_df.at[index, "Netto-Stunden"] = round(net_hrs, 2)
    total_tickets_sum += net_hrs

  st.markdown("---")
  col_t1, col_t2 = st.columns([2, 1])
  with col_t1:
    pdf_tickets_data = generate_tickets_pdf(ticket_month, ticket_year, edited_tickets_df, total_tickets_sum)
    st.download_button(t["pdf_btn"], pdf_tickets_data, f"Tickets_{ticket_month}_{ticket_year}.pdf", "application/pdf", key="p7_pdf_btn")
    if st.button("💾 Speichern / حفظ", key="tickets_save_btn"):
      save_tickets_data(ticket_month, ticket_year, edited_tickets_df)
      st.success("Erfolgreich gespeichert! / تم الحفظ بنجاح")
  with col_t2:
    st.metric("Gesamtsumme:", f"{total_tickets_sum:.2f} St.")


# ---------------------------------------------------------
# الصفحة الثامنة: جدول القطارات (Zug-Fahrten) - مربوطة بالمدن
# ---------------------------------------------------------
elif page == t["p8"]:
    st.title("🚆 Clean & Care GmbH - Zug-Fahrten")
    st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

    cities_list = load_cities()

    col_c, col_m, col_y = st.columns(3)
    with col_c:
        selected_city = st.selectbox(t["city_label"], cities_list, key="train_city_select")
    with col_m:
        train_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="train_month_select")
    with col_y:
        train_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="train_year_select")

    city_employees = get_employees_by_city(selected_city)

    if city_employees:
        train_emp = st.selectbox(t["emp_label"], city_employees, key="train_emp_select")
        st.subheader(f"Zug-Fahrten für: {train_emp} ({train_month} {train_year})")

        trains_options = ["", "Zug 1", "Zug 2", "Zug 3", "Zug 4", "Zug 5"]

        import calendar
        months_map_de = {
            "Januar": 1, "Februar": 2, "März": 3, "April": 4,
            "Mai": 5, "Juni": 6, "Juli": 7, "August": 8,
            "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
        }
        m_num = months_map_de.get(train_month, 10)
        try:
            days_count = calendar.monthrange(int(train_year), m_num)[1]
        except:
            days_count = 31

        existing_data = []
        try:
            res = supabase.table("trains_data")\
                .select("*")\
                .eq("emp", train_emp)\
                .eq("month", train_month)\
                .eq("year", int(train_year))\
                .execute()
            existing_data = res.data if res.data else []
        except Exception as e:
            st.warning(f"ملاحظة: {e}")

        saved_df = None
        if existing_data and "content" in existing_data[0]:
            try:
                content_json = json.loads(existing_data[0]["content"])
                saved_df = pd.DataFrame(content_json)
            except:
                pass

        if saved_df is not None and not saved_df.empty:
            default_trains_df = saved_df
            for i in range(1, 6):
                if f"Zug {i}" not in default_trains_df.columns:
                    default_trains_df[f"Zug {i}"] = ""
                if f"Verspätung {i}" not in default_trains_df.columns:
                    default_trains_df[f"Verspätung {i}"] = 0
        else:
            trains_rows = []
            for day in range(1, days_count + 1):
                row_data = {"Datum": str(day)}
                for i in range(1, 6):
                    row_data[f"Zug {i}"] = ""
                    row_data[f"Von {i}"] = ""
                    row_data[f"Bis {i}"] = ""
                row_data["Gesamtstunden"] = 0.0
                trains_rows.append(row_data)
            default_trains_df = pd.DataFrame(trains_rows)

        edited_trains_df = st.data_editor(
            default_trains_df,
            num_rows="fixed",
            use_container_width=True,
            key=f"trains_table_{train_emp}_{train_month}_{train_year}",
            column_config={
                "Zug 1": st.column_config.SelectboxColumn("Zug 1", options=trains_options),
                "Zug 2": st.column_config.SelectboxColumn("Zug 2", options=trains_options),
                "Zug 3": st.column_config.SelectboxColumn("Zug 3", options=trains_options),
                "Zug 4": st.column_config.SelectboxColumn("Zug 4", options=trains_options),
                "Zug 5": st.column_config.SelectboxColumn("Zug 5", options=trains_options),
            }
        )

        edited_trains_df = edited_trains_df.astype(object)

        total_trains_sum = 0.0
        for index, row in edited_trains_df.iterrows():
            day_total_hrs = 0.0
            for i in range(1, 6):
                v_str = str(row.get(f"Von {i}", "")).strip()
                b_str = str(row.get(f"Bis {i}", "")).strip()

                if v_str and b_str and v_str != "nan" and b_str != "nan":
                    for fmt in ("%H:%M", "%H.%M", "%H"):
                        try:
                            t1 = datetime.strptime(v_str.replace(".", ":"), fmt)
                            t2 = datetime.strptime(b_str.replace(".", ":"), fmt)
                            
                            if t2 < t1:
                                t2 += timedelta(days=1)

                            diff = (t2 - t1).total_seconds() / 3600.0
                            if diff > 0:
                                day_total_hrs += diff
                            break
                        except:
                            continue
            
            total_trains_sum += day_total_hrs
            edited_trains_df.at[index, "Gesamtstunden"] = round(day_total_hrs, 2)

        col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 1])
        
        with col_b1:
            if st.button("💾 Speichern / حفظ ساعات القطار", type="primary", key="save_trains_btn"):
                try:
                    content_str = json.dumps(edited_trains_df.to_dict(orient="list"), ensure_ascii=False)
                    supabase.table("trains_data").upsert({
                        "emp": train_emp,
                        "month": train_month,
                        "year": int(train_year),
                        "content": content_str
                    }).execute()
                    st.success("✅ تم حفظ ساعات القطار في جدول trains_data بنجاح!")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الحفظ: {e}")
        
        with col_b2:
            csv_data = edited_trains_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Zug-Stunden exportieren",
                data=csv_data,
                file_name=f"Zugstunden_{train_emp}_{train_month}_{train_year}.csv",
                mime="text/csv",
                key="export_trains_btn"
            )
        with col_b3:
            st.metric("Gesamtsumme:", f"{total_trains_sum:.2f} St.")
    else:
        st.warning("لا يوجد عمال مرتبطون بهذه المدينة حالياً.")