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
from datetime import datetime

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



#login
#-----

def check_login():
    """
    دالة للتحقق من تسجيل الدخول:
    - تبقى مفعلة طوال اليوم.
    - تقفل الجلسة إذا تم إغلاق المتصفح (Session State).
    """
    # تهيئة حالة تسجيل الدخول في الذاكرة المؤقتة
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # إذا لم يتم تسجيل الدخول بعد
    if not st.session_state.authenticated:
        st.subheader("🔐 تسجيل الدخول إلى النظام")
        
        # حقل إدخال كلمة المرور (يمكنك تغيير كلمة المرور حسب رغبتك)
        password = st.text_input("أدخل كلمة المرور:", type="password", key="login_pass_input")
        
        if st.button("دخول"):
            # كلمة المرور الخاصة بكِ (يمكنك تعديلها هنا)
            if password == "1234":  # ضعِي كلمة المرور التي ترغبين بها هنا
                st.session_state.authenticated = True
                st.success("تم تسجيل الدخول بنجاح!")
                st.rerun()
            else:
                st.error("كلمة المرور غير صحيحة، يحاول مجدداً.")
        
        # إيقاف تنفيذ باقي الصفحة لحين تسجيل الدخول
        st.stop()

# استدعي هذه الدالة في بداية ملف الـ main أو في الصفحة الرئيسية لتطبيقك
check_login()




# ---------------------------------------------------------
# قاعدة البيانات السحابية Supabase (إضافة جدول المدن وربط العمال)
# ---------------------------------------------------------
def init_db_supabase():
  try:
    res = supabase.table("employees").select("name").execute()
    if not res.data or len(res.data) == 0:
      for emp in ["Sakleh Alsoudi", "Alaa Edin Ibrahim"]:
        supabase.table("employees").upsert({"name": emp}, on_conflict="name").execute()

    res_p = supabase.table("places").select("name").execute()
    if not res_p.data or len(res_p.data) == 0:
      for place in ["Limehome Salzburg", "Nespresso Store", "IKEA Wals", "Villach Hauptplatz"]:
        supabase.table("places").upsert({"name": place}, on_conflict="name").execute()

    res_c = supabase.table("cities").select("name").execute()
    if not res_c.data or len(res_c.data) == 0:
      for city in ["Salzburg", "Villach", "Klagenfurt", "Bregenz"]:
        supabase.table("cities").upsert({"name": city}, on_conflict="name").execute()

    res_ec = supabase.table("employee_cities").select("*").execute()
    if not res_ec.data or len(res_ec.data) == 0:
      default_mappings = [
          {"employee": "Sakleh Alsoudi", "city": "Salzburg"},
          {"employee": "Alaa Edin Ibrahim", "city": "Salzburg"},
      ]
      for m in default_mappings:
        supabase.table("employee_cities").upsert(m, on_conflict="employee").execute()
  except Exception as e:
    st.sidebar.warning(f"ملاحظة اتصال قاعدة البيانات: {e}")


init_db_supabase()


def load_employees():
  try:
    res = supabase.table("employees").select("name").execute()
    if res.data:
      return sorted([str(row["name"]).strip() for row in res.data if row.get("name")])
  except Exception:
    pass
  return ["Sakleh Alsoudi", "Alaa Edin Ibrahim"]


def save_employees(emp_list):
  try:
    clean_list = [str(e).strip() for e in emp_list if str(e).strip()]
    existing = supabase.table("employees").select("name").execute()
    existing_names = [str(row["name"]).strip() for row in (existing.data or []) if row.get("name")]

    # حذف العمال المحذوفين فقط دون مسح الجدول بالكامل أو المساس بـ max_hours
    for old_name in existing_names:
      if old_name not in clean_list:
        supabase.table("employees").delete().eq("name", old_name).execute()

    # إضافة العمال الجدد فقط دون لمس max_hours للعمال الحاليين
    new_rows = [{"name": emp} for emp in clean_list if emp not in existing_names]
    if new_rows:
      supabase.table("employees").upsert(new_rows, on_conflict="name").execute()
  except Exception as e:
    st.error(f"خطأ في حفظ العمال: {e}")


def load_places():
  try:
    res = supabase.table("places").select("name").execute()
    if res.data:
      return sorted([str(row["name"]).strip() for row in res.data if row.get("name")])
  except Exception:
    pass
  return ["Limehome Salzburg", "Nespresso Store", "IKEA Wals", "Villach Hauptplatz"]


def save_places(places_list):
  try:
    clean_places = [str(p).strip() for p in places_list if str(p).strip()]
    existing = supabase.table("places").select("name").execute()
    existing_places = [str(row["name"]).strip() for row in (existing.data or []) if row.get("name")]

    for old_p in existing_places:
      if old_p not in clean_places:
        supabase.table("places").delete().eq("name", old_p).execute()

    new_places = [{"name": p} for p in clean_places if p not in existing_places]
    if new_places:
      supabase.table("places").upsert(new_places, on_conflict="name").execute()
  except Exception as e:
    st.error(f"خطأ في حفظ الأماكن: {e}")


def load_cities():
  try:
    res = supabase.table("cities").select("name").execute()
    if res.data:
      return sorted([str(row["name"]).strip() for row in res.data if row.get("name")])
  except Exception:
    pass
  return ["Salzburg", "Villach", "Klagenfurt", "Bregenz"]


def save_cities(cities_list):
  try:
    clean_cities = [str(c).strip() for c in cities_list if str(c).strip()]
    existing = supabase.table("cities").select("name").execute()
    existing_cities = [str(row["name"]).strip() for row in (existing.data or []) if row.get("name")]

    for old_c in existing_cities:
      if old_c not in clean_cities:
        supabase.table("cities").delete().eq("name", old_c).execute()

    new_cities = [{"name": c} for c in clean_cities if c not in existing_cities]
    if new_cities:
      supabase.table("cities").upsert(new_cities, on_conflict="name").execute()
  except Exception as e:
    st.error(f"خطأ في حفظ المدن: {e}")


def get_employee_city(emp_name):
  clean_emp = str(emp_name).strip()
  try:
    res = supabase.table("employee_cities").select("city").eq("employee", clean_emp).limit(1).execute()
    if res.data and len(res.data) > 0:
      return res.data[0]["city"]
  except Exception:
    pass
  return "Salzburg"


def set_employee_city(emp_name, city_name):
  clean_emp = str(emp_name).strip()
  try:
    supabase.table("employee_cities").upsert(
        {"employee": clean_emp, "city": city_name}, on_conflict="employee"
    ).execute()
  except Exception as e:
    st.error(f"خطأ في ربط العامل بالمدينة: {e}")


def get_employees_by_city(city_name):
  all_emps = load_employees()
  if city_name == "Alle Städte" or not city_name:
    return all_emps

  city_map = {}
  try:
    res = supabase.table("employee_cities").select("employee, city").execute()
    if res.data:
      for row in res.data:
        emp_k = str(row.get("employee") or "").strip()
        city_v = str(row.get("city") or "").strip()
        if emp_k:
          city_map[emp_k] = city_v
  except Exception:
    pass

  filtered = [emp for emp in all_emps if city_map.get(emp, "Salzburg") == city_name]
  return filtered if filtered else all_emps


def load_employee_month_hours(emp_name, month_str, year_val):
  try:
    res = (
        supabase.table("monthly_hours")
        .select("content")
        .eq("emp", emp_name)
        .eq("month", month_str)
        .eq("year", int(year_val))
        .limit(1)
        .execute()
    )
    if res.data and len(res.data) > 0:
      data = json.loads(res.data[0]["content"])
      return pd.DataFrame(data)
  except Exception:
    pass

  days_data = [
      {
          "Datum": str(day),
          "Ort": "",
          "Beginn": "",
          "Ende": "",
          "Pause": "",
          "Arbeitszeit (abzgl. Pause)": 0.0,
      }
      for day in range(1, 32)
  ]
  return pd.DataFrame(days_data)


def save_employee_month_hours(emp_name, month_str, year_val, df):
  try:
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("monthly_hours").upsert(
        {
            "emp": emp_name,
            "month": month_str,
            "year": int(year_val),
            "content": content,
        }
    ).execute()
  except Exception as e:
    st.error(f"خطأ في الحفظ الشهري: {e}")


def load_daily_emp_hours(emp_name, month_str, year_val):
  try:
    res = (
        supabase.table("daily_hours")
        .select("content")
        .eq("emp", emp_name)
        .eq("month", month_str)
        .eq("year", int(year_val))
        .limit(1)
        .execute()
    )
    if res.data and len(res.data) > 0:
      data = json.loads(res.data[0]["content"])
      df = pd.DataFrame(data).fillna("")

      if "Pause" in df.columns:
        for idx, val in enumerate(df["Pause"]):
          if str(val).strip() not in ["", "None", "nan"]:
            if "Pause 1" not in df.columns or str(df.loc[idx, "Pause 1"]).strip() in ["", "None", "nan"]:
              df.loc[idx, "Pause 1"] = val
        df = df.drop(columns=["Pause"])

      for i in range(1, 4):
        for col_prefix in ["Pause ", "Hrs", "Ort ", "Beginn ", "Ende "]:
          col_name = f"{col_prefix}{i}" if col_prefix != "Hrs" else f"Hrs{i}"
          if col_name not in df.columns:
            df[col_name] = ""
        df[f"Ort {i}"] = df[f"Ort {i}"].replace(["None", "nan", None], "")

      cols_order = [
          "Datum",
          "Ort 1", "Beginn 1", "Ende 1", "Pause 1", "Hrs1",
          "Ort 2", "Beginn 2", "Ende 2", "Pause 2", "Hrs2",
          "Ort 3", "Beginn 3", "Ende 3", "Pause 3", "Hrs3",
          "Gesamtstunden",
      ]
      existing_cols = [c for c in cols_order if c in df.columns]
      other_cols = [c for c in df.columns if c not in existing_cols]
      return df[existing_cols + other_cols]
  except Exception:
    pass

  days_data = [
      {
          "Datum": str(day),
          "Ort 1": "", "Beginn 1": "", "Ende 1": "", "Pause 1": "", "Hrs1": "",
          "Ort 2": "", "Beginn 2": "", "Ende 2": "", "Pause 2": "", "Hrs2": "",
          "Ort 3": "", "Beginn 3": "", "Ende 3": "", "Pause 3": "", "Hrs3": "",
          "Gesamtstunden": 0.0,
      }
      for day in range(1, 32)
  ]
  return pd.DataFrame(days_data)


def save_daily_emp_hours(emp_name, month_str, year_val, df):
  try:
    clean_df = df.fillna("")
    content = json.dumps(clean_df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("daily_hours").upsert(
        {
            "emp": emp_name,
            "month": month_str,
            "year": int(year_val),
            "content": content,
        }
    ).execute()
  except Exception as e:
    st.error(f"خطأ في حفظ الساعات اليومية: {e}")


def load_tickets_data(month_str, year_val):
  try:
    res = (
        supabase.table("tickets_data")
        .select("content")
        .eq("month", month_str)
        .eq("year", int(year_val))
        .limit(1)
        .execute()
    )
    if res.data and len(res.data) > 0:
      data = json.loads(res.data[0]["content"])
      return pd.DataFrame(data)
  except Exception:
    pass

  tickets_rows = []
  month_map = {
      "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
      "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
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
        "Netto-Stunden": 0.0,
    })
  return pd.DataFrame(tickets_rows)


def save_tickets_data(month_str, year_val, df):
  try:
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("tickets_data").upsert(
        {
            "month": month_str,
            "year": int(year_val),
            "content": content,
        }
    ).execute()
  except Exception as e:
    st.error(f"خطأ في حفظ التذاكر: {e}")


months_list_de = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
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
        "p9": "📦 Lager & Material",
        "p10": "👕 Arbeitskleidung",
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
        "p7": "🎫 Einsatz-Tickets",
        "p8": "🚆 Zug-Fahrten (Züge)",
        "p9": "📦 Lager & Material",
        "p10": "👕 Arbeitskleidung",
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
        t["p9"],
        t["p10"],
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
  # إضافة مسافة وفراغ التوقيعات في نهاية الـ PDF
  elements.append(Spacer(1, 20))
  signature_data = [
      ["________________________________________", "________________________________________"],
      ["Unterschrift Arbeitnehmer", "Unterschrift Arbeitgeber / GF"],
      ["Datum: ___________________", "Datum: ___________________"]
  ]
  t_sig = Table(signature_data, colWidths=[250, 250])
  t_sig.setStyle(TableStyle([
      ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
      ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
      ('FONTSIZE', (0, 0), (-1, -1), 9),
      ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
  ]))
  elements.append(t_sig)
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
  
  # أعمدة الجدول المحدثة لتشمل المكان الرابع والاستراحة لكل مكان
  table_data = [["Tag", "Ort 1", "Std 1", "Pause 1", "Ort 2", "Std 2", "Pause 2", "Ort 3", "Std 3", "Pause 3", "Ort 4", "Std 4", "Pause 4", "Gesamt"]]
  for _, row in df.iterrows():
    table_data.append([
        str(row["Datum"]),
        str(row["Ort 1"] if pd.notna(row.get("Ort 1")) else ""), str(row.get("Hrs1", "")), str(row.get("Pause 1", "")),
        str(row["Ort 2"] if pd.notna(row.get("Ort 2")) else ""), str(row.get("Hrs2", "")), str(row.get("Pause 2", "")),
        str(row["Ort 3"] if pd.notna(row.get("Ort 3")) else ""), str(row.get("Hrs3", "")), str(row.get("Pause 3", "")),
        str(row["Ort 4"] if pd.notna(row.get("Ort 4")) else ""), str(row.get("Hrs4", "")), str(row.get("Pause 4", "")),
        str(row["Gesamtstunden"])
    ])
  table_data.append(["Summe:", "", "", "", "", "", "", "", "", "", "", "", "", f"{total_hours:.2f} St."])
  
  t_pdf = Table(table_data, colWidths=[22, 62, 28, 36, 62, 28, 36, 62, 28, 36, 62, 28, 36, 48])
  t_pdf.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, -1), 6.5),
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
  
  table_data = [["Nr.", "Ticket", "Beginn", "Ende", "Bemerkung", "Stunden"]]
  
  row_counter = 1
  for _, row in df.iterrows():
    for i in range(1, 5):
      b_str = str(row.get(f"T{i}_Beginn", "")).strip()
      e_str = str(row.get(f"T{i}_Ende", "")).strip()
      bem_str = str(row.get(f"T{i}_Bemerkung", "")).strip()
      
      if b_str and e_str and b_str != "nan" and e_str != "nan":
        net_h = 0.0
        for fmt in ("%H:%M", "%H.%M", "%H"):
          try:
            t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
            t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
            gh = (t2 - t1).total_seconds() / 3600
            if gh > 0:
              net_h = gh
            break
          except:
            continue
        
        table_data.append([
            str(row_counter),
            f"Ticket {i}",
            b_str,
            e_str,
            bem_str,
            f"{net_h:.2f} St."
        ])
        row_counter += 1

  table_data.append(["Summe:", "", "", "", "", f"{total_hours:.2f} St."])
  
  t_pdf = Table(table_data, colWidths=[35, 60, 65, 65, 175, 100])
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
#----------------------------------------------------------

elif page == t["p2"]:
  from datetime import date

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
    clean_emp_name = daily_emp.strip()

    month_num_map = {
        "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
        "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
    }
    weekday_short_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    def get_weekday_label(day_val, month_name, year_num):
      m_idx = month_num_map.get(month_name, 1)
      try:
        d_obj = date(int(year_num), int(m_idx), int(day_val))
        wd = d_obj.weekday()
        w_name = weekday_short_de[wd]
        if wd in (5, 6):
          return f"{w_name} (WE)"
        return w_name
      except Exception:
        return "-"

    # جلب سجل الساعات اليومية مرة واحدة فقط لهذا العامل والشهر والسنة
    raw_content_json = None
    try:
      existing_rows_res = (
          supabase.table("daily_hours")
          .select("content")
          .eq("emp", clean_emp_name)
          .eq("month", daily_month)
          .eq("year", int(daily_year))
          .limit(1)
          .execute()
      )
      if existing_rows_res.data:
        raw_content_json = existing_rows_res.data[0].get("content")
    except Exception:
      raw_content_json = None

    # ==========================================================
    # 💡 التحذير وحساب الساعات المتبقية للعامل هذا الشهر
    # ==========================================================
    try:
      emp_db_res = (
          supabase.table("employees")
          .select("max_hours")
          .eq("name", clean_emp_name)
          .limit(1)
          .execute()
      )
      raw_max = emp_db_res.data[0].get("max_hours") if emp_db_res.data else None

      emp_current_month_hours = 0.0
      if raw_content_json:
        temp_df = pd.DataFrame(json.loads(raw_content_json))
        if "Gesamtstunden" in temp_df.columns:
          emp_current_month_hours = pd.to_numeric(temp_df["Gesamtstunden"], errors="coerce").fillna(0.0).sum()

      if raw_max is not None:
        emp_max_limit = float(raw_max)
        remaining_hrs = emp_max_limit - emp_current_month_hours

        if remaining_hrs <= 0:
          st.error(f"🚨 تنبيه تجاوز الحد: العامل **{daily_emp}** استهلك كامل ساعاته الشهرية! (أنجز {emp_current_month_hours:.2f} من أصل {emp_max_limit} ساعة).")
        elif remaining_hrs <= 15:
          st.warning(f"⚠️ تنبيه قرب انتهاء الساعات: العامل **{daily_emp}** عمل {emp_current_month_hours:.2f} ساعة والمتبقي له **{remaining_hrs:.2f}** ساعة فقط.")
        else:
          st.info(f"💡 حالة ساعات العامل: أنجز {emp_current_month_hours:.2f} ساعة | متبقي له **{remaining_hrs:.2f}** ساعة لكي يصل إلى حده الأقصى ({emp_max_limit} ساعة).")
      else:
        st.info(f"💡 حالة ساعات العامل: أنجز {emp_current_month_hours:.2f} ساعة (الحد الأقصى غير محدد في Supabase).")
    except Exception:
      pass
    # ==========================================================

    def build_daily_hours_df(content_json):
      if content_json:
        try:
          data = json.loads(content_json)
          df = pd.DataFrame(data)

          if "Pause" in df.columns:
            for idx, val in enumerate(df["Pause"]):
              if pd.notna(val) and str(val).strip() != "" and str(val).strip() != "nan":
                if "Pause 1" not in df.columns or pd.isna(df.loc[idx, "Pause 1"]) or str(df.loc[idx, "Pause 1"]).strip() in ["", "nan"]:
                  df.loc[idx, "Pause 1"] = val
            df = df.drop(columns=["Pause"])

          for i in range(1, 5):
            for col_prefix in ["Ort ", "Beginn ", "Ende ", "Pause ", "Hrs"]:
              col_name = f"{col_prefix}{i}" if col_prefix != "Hrs" else f"Hrs{i}"
              if col_name not in df.columns:
                df[col_name] = ""

          df["Wochentag"] = [
              get_weekday_label(r.get("Datum", idx + 1), daily_month, daily_year)
              for idx, r in df.iterrows()
          ]

          cols_order = [
              "Datum", "Wochentag",
              "Ort 1", "Beginn 1", "Ende 1", "Pause 1", "Hrs1",
              "Ort 2", "Beginn 2", "Ende 2", "Pause 2", "Hrs2",
              "Ort 3", "Beginn 3", "Ende 3", "Pause 3", "Hrs3",
              "Ort 4", "Beginn 4", "Ende 4", "Pause 4", "Hrs4",
              "Gesamtstunden"
          ]
          existing_cols = [c for c in cols_order if c in df.columns]
          other_cols = [c for c in df.columns if c not in existing_cols]
          return df[existing_cols + other_cols]
        except Exception:
          pass

      days_data = [
          {
              "Datum": str(day),
              "Wochentag": get_weekday_label(day, daily_month, daily_year),
              "Ort 1": "", "Beginn 1": "", "Ende 1": "", "Pause 1": "", "Hrs1": "",
              "Ort 2": "", "Beginn 2": "", "Ende 2": "", "Pause 2": "", "Hrs2": "",
              "Ort 3": "", "Beginn 3": "", "Ende 3": "", "Pause 3": "", "Hrs3": "",
              "Ort 4": "", "Beginn 4": "", "Ende 4": "", "Pause 4": "", "Hrs4": "",
              "Gesamtstunden": 0.0,
          }
          for day in range(1, 32)
      ]
      return pd.DataFrame(days_data)

    daily_df = build_daily_hours_df(raw_content_json)

    edited_daily_df = st.data_editor(
        daily_df,
        num_rows="fixed",
        use_container_width=True,
        disabled=["Datum", "Wochentag"],
        key=f"daily_table_{clean_emp_name}_{daily_month}_{daily_year}",
        column_config={
            "Ort 1": st.column_config.SelectboxColumn("Ort 1", options=places_list),
            "Ort 2": st.column_config.SelectboxColumn("Ort 2", options=places_list),
            "Ort 3": st.column_config.SelectboxColumn("Ort 3", options=places_list),
            "Ort 4": st.column_config.SelectboxColumn("Ort 4", options=places_list),
        }
    )

    edited_daily_df = edited_daily_df.astype(object)

    total_daily_sum = 0.0
    for index, row in edited_daily_df.iterrows():
      net_day_total = 0.0

      for i in range(1, 5):
        b_str = str(row.get(f"Beginn {i}", "")).strip()
        e_str = str(row.get(f"Ende {i}", "")).strip()
        p_str = str(row.get(f"Pause {i}", "")).strip()

        hrs = 0.0
        break_val = 0.0

        if b_str and e_str and b_str not in ("nan", "None") and e_str not in ("nan", "None"):
          for fmt in ("%H:%M", "%H.%M", "%H"):
            try:
              t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
              t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
              if t2 < t1:
                t2 += timedelta(days=1)

              gh = (t2 - t1).total_seconds() / 3600
              if gh > 0:
                if p_str and p_str not in ("nan", "None", ""):
                  try:
                    break_val = float(p_str.replace(",", "."))
                  except Exception:
                    break_val = 0.0
                hrs = max(0.0, gh - break_val)
              break
            except Exception:
              continue

        if break_val > 0:
          edited_daily_df.at[index, f"Pause {i}"] = str(break_val)
        elif not p_str or p_str in ("nan", "None"):
          edited_daily_df.at[index, f"Pause {i}"] = ""

        edited_daily_df.at[index, f"Hrs{i}"] = round(hrs, 2) if hrs > 0 else ""
        net_day_total += hrs

      edited_daily_df.at[index, "Gesamtstunden"] = round(net_day_total, 2)
      total_daily_sum += net_day_total

    st.markdown("---")
    col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
    with col_d1:
      pdf_daily_data = generate_daily_pdf(clean_emp_name, daily_month, daily_year, edited_daily_df, total_daily_sum)
      st.download_button(t["pdf_btn"], pdf_daily_data, f"Tägliche_Stunden_{clean_emp_name}_{daily_month}_{daily_year}.pdf", "application/pdf", key="p2_pdf")
    with col_d2:
      if st.button(t["save_btn"], key="p2_save"):
        save_daily_emp_hours(clean_emp_name, daily_month, daily_year, edited_daily_df)
        st.success(t["success_msg"])
        st.rerun()
    with col_d3:
      st.metric(t["sum_label"], f"{total_daily_sum:.2f} St.")

# ---------------------------------------------------------
# الصفحة الثالثة: ملخص ساعات المواقع (Objekt-Stundenübersicht)
# ---------------------------------------------------------
elif page == t["p3"]:
  from datetime import date

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
  weekday_short_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

  def get_easter_sunday(year_num: int) -> date:
    # خوارزمية غريغوري لحساب أحد الفصح لأي سنة
    a = year_num % 19
    b = year_num // 100
    c = year_num % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year_num, month, day)

  def get_austria_holidays(year_num: int) -> set:
    easter = get_easter_sunday(year_num)
    return {
        date(year_num, 1, 1),                      # Neujahr
        date(year_num, 1, 6),                      # Heilige Drei Könige
        easter + timedelta(days=1),                # Ostermontag
        date(year_num, 5, 1),                      # Staatsfeiertag
        easter + timedelta(days=39),               # Christi Himmelfahrt
        easter + timedelta(days=50),               # Pfingstmontag
        easter + timedelta(days=60),               # Fronleichnam
        date(year_num, 8, 15),                     # Mariä Himmelfahrt
        date(year_num, 10, 26),                    # Nationalfeiertag
        date(year_num, 11, 1),                     # Allerheiligen
        date(year_num, 12, 8),                     # Mariä Empfängnis
        date(year_num, 12, 25),                    # Christtag
        date(year_num, 12, 26),                    # Stefanitag
    }

  m_num = month_map.get(loc_month, 10)
  year_int = int(loc_year)
  days_in_month = pd.Period(f"{year_int}-{m_num}").days_in_month
  at_holidays = get_austria_holidays(year_int)

  if places_list and selected_loc_place:
    clean_selected_place = str(selected_loc_place).strip().lower()
    st.subheader(f"Objekt: {selected_loc_place} ({loc_month} {year_int})")

    try:
      res_rows = supabase.table("daily_hours").select("content").eq("month", loc_month).eq("year", year_int).execute()
      rows = res_rows.data if res_rows.data else []
    except Exception:
      rows = []

    loc_days_data = []
    sunday_and_holiday_sum = 0.0
    regular_days_sum = 0.0

    for d in range(1, days_in_month + 1):
      current_date = date(year_int, m_num, d)
      wd_idx = current_date.weekday()
      wd_label = weekday_short_de[wd_idx]
      is_sunday_or_holiday = (wd_idx == 6) or (current_date in at_holidays)

      day_sum = 0.0
      for row in rows:
        try:
          raw_c = row.get("content")
          if not raw_c:
            continue
          emp_data = json.loads(raw_c) if isinstance(raw_c, str) else raw_c
          df_emp = pd.DataFrame(emp_data)
          for _, r in df_emp.iterrows():
            if str(r.get("Datum", "")).strip() == str(d):
              for i in range(1, 5):
                loc_name = str(r.get(f"Ort {i}", "")).strip()
                if loc_name and loc_name.lower() == clean_selected_place:
                  b_str = str(r.get(f"Beginn {i}", "")).strip()
                  e_str = str(r.get(f"Ende {i}", "")).strip()
                  loc_hrs = 0.0

                  if b_str and e_str and b_str.lower() != "nan" and e_str.lower() != "nan":
                    for fmt in ("%H:%M", "%H.%M", "%H"):
                      try:
                        t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
                        t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
                        if t2 < t1:
                          t2 += timedelta(days=1)
                        gh = (t2 - t1).total_seconds() / 3600
                        if gh > 0:
                          loc_hrs = gh
                          break
                      except Exception:
                        continue

                  p_input = str(r.get(f"Pause {i}", "")).strip()
                  break_val = 0.0
                  if p_input and p_input.lower() not in ["none", "nan", ""]:
                    try:
                      break_val = float(p_input.replace(",", "."))
                    except Exception:
                      break_val = 0.0

                  net_loc_hrs = max(0.0, loc_hrs - break_val)
                  day_sum += net_loc_hrs
        except Exception:
          pass

      rounded_day = round(day_sum, 2)
      if is_sunday_or_holiday:
        sunday_and_holiday_sum += day_sum
      else:
        regular_days_sum += day_sum

      loc_days_data.append({
          "Tag": str(d),
          "Wochentag": wd_label,
          "Stunden": rounded_day
      })

    loc_df = pd.DataFrame(loc_days_data)
    st.dataframe(loc_df, use_container_width=True, hide_index=True)

    sunday_and_holiday_sum = round(sunday_and_holiday_sum, 2)
    regular_days_sum = round(regular_days_sum, 2)
    total_loc_sum = round(sunday_and_holiday_sum + regular_days_sum, 2)

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    with m1:
      st.metric("Sonntag & Feiertage (AT):", f"{sunday_and_holiday_sum:.2f} St.")
    with m2:
      st.metric("Übrige Tage (Mo–Sa ohne Feiertag):", f"{regular_days_sum:.2f} St.")
    with m3:
      st.metric(t["sum_label"], f"{total_loc_sum:.2f} St.")

    st.markdown("---")
    loc_pdf_data = generate_single_location_pdf(selected_loc_place, loc_month, year_int, loc_df, total_loc_sum)
    st.download_button(t["pdf_btn"], loc_pdf_data, f"Objekt_{selected_loc_place}_{loc_month}_{year_int}.pdf", "application/pdf", key="p3_pdf")

  st.markdown("---")
  add_col, del_col = st.columns(2)
  with add_col:
    st.subheader(t["add_place"])
    new_place_name = st.text_input("Name des neuen Ortes:", key="p3_new_place")
    if st.button(t["add_btn"], key="p3_add_btn"):
      clean_new_place = new_place_name.strip()
      if clean_new_place and clean_new_place not in places_list:
        places_list.append(clean_new_place)
        save_places(places_list)
        st.cache_data.clear()
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
          st.cache_data.clear()
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

  if places_list and selected_place:
    clean_selected_place = str(selected_place).strip().lower()
    st.subheader(f"Mitarbeiter-Stunden für Ort: {selected_place} ({place_month} {place_year})")

    try:
      res_rows = supabase.table("daily_hours").select("emp, content").eq("month", place_month).eq("year", int(place_year)).execute()
      rows = res_rows.data if res_rows.data else []
    except Exception:
      rows = []

    place_data_rows = []
    for row in rows:
      emp = str(row.get("emp") or "").strip()
      if not emp:
        continue
      try:
        raw_c = row.get("content")
        if not raw_c:
          continue
        emp_data = json.loads(raw_c) if isinstance(raw_c, str) else raw_c
        emp_daily_df = pd.DataFrame(emp_data)
        emp_place_hours = 0.0

        for _, r in emp_daily_df.iterrows():
          # فحص Ort 1 إلى Ort 4 ليشمل المكان الرابع أيضاً
          for i in range(1, 5):
            loc_name = str(r.get(f"Ort {i}", "")).strip()
            b_str = str(r.get(f"Beginn {i}", "")).strip()
            e_str = str(r.get(f"Ende {i}", "")).strip()
            loc_hrs = 0.0

            if b_str and e_str and b_str.lower() != "nan" and e_str.lower() != "nan":
              for fmt in ("%H:%M", "%H.%M", "%H"):
                try:
                  t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
                  t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
                  if t2 < t1:
                    t2 += timedelta(days=1)
                  gh = (t2 - t1).total_seconds() / 3600
                  if gh > 0:
                    loc_hrs = gh
                    break
                except Exception:
                  continue

            # قراءة استراحة هذا الموقع المحددة (Pause 1, 2, 3, 4)
            p_input = str(r.get(f"Pause {i}", "")).strip()
            break_val = 0.0
            if p_input and p_input.lower() not in ["none", "nan", ""]:
              try:
                break_val = float(p_input.replace(",", "."))
              except Exception:
                break_val = 0.0

            # صافي ساعات هذا الموقع (بعد خصم استراحة هذا الموقع فقط)
            net_loc_hrs = max(0.0, loc_hrs - break_val)

            if loc_name.lower() == clean_selected_place and net_loc_hrs > 0:
              emp_place_hours += net_loc_hrs

        if emp_place_hours > 0:
          existing_row = next((r for r in place_data_rows if r["Mitarbeiter"].strip().lower() == emp.lower()), None)
          if existing_row:
            existing_row["Stunden"] = round(existing_row["Stunden"] + emp_place_hours, 2)
          else:
            place_data_rows.append({"Mitarbeiter": emp, "Stunden": round(emp_place_hours, 2)})
      except Exception:
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
  st.title("👥 Clean & Care GmbH - Mitarbeiter- & Städteverwaltung")
  
  employees_list = load_employees()
  cities_list = load_cities()

  tab1, tab2 = st.tabs(["Mitarbeiterverwaltung & Stadtzuweisung", "Städte verwalten"])

  with tab1:
    if employees_list and cities_list:
      # ---------------------------------------------------------
      # 1. قسم ربط المدينة (تحديث المدينة فقط دون لمس max_hours)
      # ---------------------------------------------------------
      st.subheader("Mitarbeiter-Stadtzuweisung")
      selected_emp_for_city = st.selectbox("Mitarbeiter auswählen:", employees_list, key="assign_emp_city")
      
      current_city = get_employee_city(selected_emp_for_city)
      current_city_index = cities_list.index(current_city) if current_city in cities_list else 0
      
      assigned_city = st.selectbox("Stadt auswählen:", cities_list, index=current_city_index, key="assign_city")
      
      if st.button("Stadtzuweisung speichern"):
        clean_emp = selected_emp_for_city.strip()
        set_employee_city(clean_emp, assigned_city)
        try:
            res_upd = supabase.table("employees").update({"city": assigned_city}).eq("name", clean_emp).execute()
            if not res_upd.data:
                supabase.table("employees").insert({"name": clean_emp, "city": assigned_city}).execute()
        except Exception as e:
            st.warning(f"Hinweis zur Datenbank-Synchronisierung: {e}")
        st.success(f"Mitarbeiter {clean_emp} wurde erfolgreich der Stadt {assigned_city} zugewiesen!")
        st.rerun()

    st.markdown("---")
    # ---------------------------------------------------------
    # 2. إضافة عامل جديد (الاسم + المدينة فقط، والساعات تُدار من Supabase)
    # ---------------------------------------------------------
    st.subheader("Neuen Mitarbeiter hinzufügen")
    new_emp_name = st.text_input("Name des Mitarbeiters:")
    default_emp_city = st.selectbox("Hauptstadt für neuen Mitarbeiter:", cities_list, key="new_emp_city")
    
    if st.button("Mitarbeiter hinzufügen", key="add_emp_btn"):
      clean_new_emp = new_emp_name.strip()
      if clean_new_emp and clean_new_emp not in employees_list:
        employees_list.append(clean_new_emp)
        save_employees(employees_list)
        set_employee_city(clean_new_emp, default_emp_city)
        
        try:
            res_chk = supabase.table("employees").select("name").eq("name", clean_new_emp).limit(1).execute()
            if not res_chk.data:
                supabase.table("employees").insert({
                    "name": clean_new_emp,
                    "city": default_emp_city
                }).execute()
            else:
                supabase.table("employees").update({"city": default_emp_city}).eq("name", clean_new_emp).execute()
        except Exception as e:
            st.warning(f"Mitarbeiter lokal gespeichert, aber DB-Eintrag prüfen: {e}")
        
        st.success(f"Mitarbeiter {clean_new_emp} erfolgreich hinzugefügt!")
        st.rerun()

    st.markdown("---")
    # ---------------------------------------------------------
    # 3. حذف عامل
    # ---------------------------------------------------------
    st.subheader("Mitarbeiter löschen")
    if len(employees_list) > 0:
      emp_to_delete = st.selectbox("Mitarbeiter auswählen zum Löschen:", employees_list, key="del_emp_select")
      if st.button("Mitarbeiter löschen", key="del_emp_btn"):
        if len(employees_list) > 1:
          clean_del_emp = emp_to_delete.strip()
          employees_list.remove(emp_to_delete)
          save_employees(employees_list)
          try:
              supabase.table("employees").delete().eq("name", clean_del_emp).execute()
          except Exception:
              pass
          st.success("Mitarbeiter erfolgreich gelöscht!")
          st.rerun()
        else:
          st.warning("Es muss mindestens ein Mitarbeiter bleiben.")

  with tab2:
    st.subheader("Städte hinzufügen & löschen")
    new_city_name = st.text_input("Neue Stadt:")
    if st.button("Stadt hinzufügen", key="add_city_btn"):
      clean_city = new_city_name.strip()
      if clean_city and clean_city not in cities_list:
        cities_list.append(clean_city)
        save_cities(cities_list)
        st.success(f"Stadt {clean_city} erfolgreich hinzugefügt!")
        st.rerun()

    st.markdown("---")
    if len(cities_list) > 0:
      city_to_delete = st.selectbox("Stadt zum Löschen auswählen:", cities_list, key="del_city_select")
      if st.button("Stadt löschen", key="del_city_btn"):
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

    if summary_city == t["all_cities"]:
        allowed_emps = load_employees()
    else:
        allowed_emps = get_employees_by_city(summary_city)

    # 1. جلب الحد الأقصى للساعات لكل عامل من جدول employees في Supabase (بدون فرض 160)
    emp_max_hours_map = {}
    try:
        emp_res = supabase.table("employees").select("name, max_hours").execute()
        if emp_res.data:
            for e in emp_res.data:
                e_name = e.get("name")
                e_max = e.get("max_hours")
                if e_name and e_max is not None:
                    emp_max_hours_map[str(e_name).strip()] = float(e_max)
    except Exception:
        pass

    # 2. جلب الساعات اليومية من جدول daily_hours
    rows = []
    try:
        res_rows = supabase.table("daily_hours").select("emp, content").eq("month", summary_month).eq("year", int(summary_year)).execute()
        rows = res_rows.data if res_rows.data else []
    except Exception:
        rows = []

    # 3. جلب بيانات القطارات وتخزين ساعات وأيام العمل لكل موظف
    zug_hours_per_emp = {}
    zug_days_per_emp = {}
    try:
        zug_res = supabase.table("trains_data").select("emp, content").eq("month", summary_month).eq("year", int(summary_year)).execute()
        zug_rows = zug_res.data if zug_res.data else []
        for z_row in zug_rows:
            z_emp = z_row.get("emp")
            if z_emp and z_row.get("content"):
                clean_z_emp = str(z_emp).strip()
                try:
                    z_df = pd.DataFrame(json.loads(z_row["content"]))
                    if "Gesamtstunden" in z_df.columns:
                        z_df["Gesamtstunden"] = pd.to_numeric(z_df["Gesamtstunden"], errors="coerce").fillna(0.0)
                        z_sum = float(z_df["Gesamtstunden"].sum())
                        zug_hours_per_emp[clean_z_emp] = zug_hours_per_emp.get(clean_z_emp, 0.0) + z_sum

                        if "Datum" in z_df.columns:
                            z_df["Datum_Num"] = pd.to_numeric(z_df["Datum"], errors="coerce")
                            z_worked = z_df[z_df["Gesamtstunden"] > 0]["Datum_Num"].dropna().tolist()
                            zug_days_per_emp.setdefault(clean_z_emp, []).extend(z_worked)
                except Exception:
                    pass
    except Exception:
        pass

    summary_data = []
    total_company_hours = 0.0

    emp_daily_days_map = {}
    emp_daily_hours_map = {}

    for row in rows:
        emp = row.get("emp")
        if not emp:
            continue
        clean_emp_name = str(emp).strip()
        if clean_emp_name not in allowed_emps:
            continue

        try:
            emp_data = json.loads(row["content"])
            emp_daily_df = pd.DataFrame(emp_data)

            if "Gesamtstunden" in emp_daily_df.columns:
                emp_daily_df["Gesamtstunden"] = pd.to_numeric(emp_daily_df["Gesamtstunden"], errors="coerce").fillna(0.0)
                emp_daily_total = float(emp_daily_df["Gesamtstunden"].sum())
                emp_daily_hours_map[clean_emp_name] = emp_daily_hours_map.get(clean_emp_name, 0.0) + emp_daily_total

                if "Datum" in emp_daily_df.columns:
                    emp_daily_df["Datum_Num"] = pd.to_numeric(emp_daily_df["Datum"], errors="coerce")
                    worked_days = emp_daily_df[emp_daily_df["Gesamtstunden"] > 0]["Datum_Num"].dropna().tolist()
                    emp_daily_days_map.setdefault(clean_emp_name, []).extend(worked_days)
        except Exception:
            pass

    all_target_emps = sorted(set(list(emp_daily_hours_map.keys()) + list(zug_hours_per_emp.keys())))

    for clean_emp_name in all_target_emps:
        if clean_emp_name not in allowed_emps:
            continue

        emp_daily_total = emp_daily_hours_map.get(clean_emp_name, 0.0)
        emp_zug_total = zug_hours_per_emp.get(clean_emp_name, 0.0)
        total_emp_combined = emp_daily_total + emp_zug_total

        if total_emp_combined > 0:
            all_worked_days = emp_daily_days_map.get(clean_emp_name, []) + zug_days_per_emp.get(clean_emp_name, [])
            last_work_date = str(int(max(all_worked_days))) if all_worked_days else "-"

            max_limit = emp_max_hours_map.get(clean_emp_name)
            if max_limit is not None:
                remaining = round(max_limit - total_emp_combined, 2)
                max_display = round(max_limit, 2)
            else:
                remaining = "-"
                max_display = "-"

            summary_data.append({
                "Mitarbeiter": clean_emp_name,
                "Stunden bis": last_work_date,
                "Gesamtstunden": round(total_emp_combined, 2),
                "Max Stunden": max_display,
                "Verbleibende Stunden": remaining
            })
            total_company_hours += total_emp_combined

    if not summary_data:
        summary_df = pd.DataFrame([{
            "Mitarbeiter": "Keine Stunden erfasst",
            "Stunden bis": "-",
            "Gesamtstunden": 0.0,
            "Max Stunden": 0.0,
            "Verbleibende Stunden": 0.0
        }])
    else:
        summary_df = pd.DataFrame(summary_data)

    st.dataframe(summary_df, use_container_width=True, hide_index=True)
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

  col1, col2, col3 = st.columns(3)
  with col1:
    ticket_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="ticket_month_select")
  with col2:
    ticket_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="ticket_year_select")
  with col3:
    selected_main_place = st.selectbox("Einsatzort auswählen:", places_list, key="main_place_select")

  if not selected_main_place:
    st.warning("⚠️ Bitte wähle zuerst einen Einsatzort aus, um die Tickets anzuzeigen.")
  else:
    clean_place = selected_main_place.strip()
    st.subheader(f"Monats-Tickets ({clean_place} - {ticket_month} {ticket_year})")

    cache_key = f"tickets_cache_{clean_place}_{ticket_month}_{ticket_year}"

    if cache_key not in st.session_state:
      loaded_df = None
      try:
        res = (
            supabase.table("tickets_data")
            .select("content")
            .eq("place", clean_place)
            .eq("month", ticket_month)
            .eq("year", int(ticket_year))
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0 and res.data[0].get("content"):
          raw_c = res.data[0]["content"]
          parsed = json.loads(raw_c) if isinstance(raw_c, str) else raw_c
          loaded_df = pd.DataFrame(parsed).fillna("")
      except Exception:
        loaded_df = None

      if loaded_df is None or len(loaded_df) != 50 or "T1_Nr" not in loaded_df.columns:
        data_dict = {
            "T1_Nr": [""] * 50, "T1_Beginn": [""] * 50, "T1_Ende": [""] * 50, "T1_Bemerkung": [""] * 50,
            "T2_Nr": [""] * 50, "T2_Beginn": [""] * 50, "T2_Ende": [""] * 50, "T2_Bemerkung": [""] * 50,
            "T3_Nr": [""] * 50, "T3_Beginn": [""] * 50, "T3_Ende": [""] * 50, "T3_Bemerkung": [""] * 50,
            "T4_Nr": [""] * 50, "T4_Beginn": [""] * 50, "T4_Ende": [""] * 50, "T4_Bemerkung": [""] * 50,
            "Netto-Stunden": [0.0] * 50
        }
        loaded_df = pd.DataFrame(data_dict)

      st.session_state[cache_key] = loaded_df

    tickets_df = st.session_state[cache_key]

    edited_tickets_df = st.data_editor(
        tickets_df,
        num_rows="fixed",
        use_container_width=True,
        disabled=["Netto-Stunden"],
        key=f"tickets_table_{clean_place}_{ticket_month}_{ticket_year}"
    )

    edited_tickets_df = edited_tickets_df.astype(object)

    total_tickets_sum = 0.0
    for index, row in edited_tickets_df.iterrows():
      row_net = 0.0
      for i in range(1, 5):
        b_str = str(row.get(f"T{i}_Beginn", "")).strip()
        e_str = str(row.get(f"T{i}_Ende", "")).strip()

        if b_str and e_str and b_str.lower() not in ("nan", "none") and e_str.lower() not in ("nan", "none"):
          for fmt in ("%H:%M", "%H.%M", "%H"):
            try:
              t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
              t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
              if t2 < t1:
                t2 += timedelta(days=1)
              gh = (t2 - t1).total_seconds() / 3600
              if gh > 0:
                row_net += gh
              break
            except Exception:
              continue

      edited_tickets_df.at[index, "Netto-Stunden"] = round(row_net, 2)
      total_tickets_sum += row_net

    st.markdown("---")
    col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
    with col_t1:
      pdf_tickets_data = generate_tickets_pdf(ticket_month, ticket_year, edited_tickets_df, total_tickets_sum)
      st.download_button(
          t["pdf_btn"],
          pdf_tickets_data,
          f"Tickets_{clean_place}_{ticket_month}_{ticket_year}.pdf",
          "application/pdf",
          key="p7_pdf_btn"
      )
    with col_t2:
      if st.button("💾 Speichern / حفظ", key="tickets_save_btn"):
        try:
          clean_save_df = edited_tickets_df.fillna("")
          content_str = clean_save_df.to_json(orient="records", force_ascii=False)
          existing = (
              supabase.table("tickets_data")
              .select("place")
              .eq("place", clean_place)
              .eq("month", ticket_month)
              .eq("year", int(ticket_year))
              .limit(1)
              .execute()
          )
          if existing.data and len(existing.data) > 0:
            supabase.table("tickets_data").update({"content": content_str}).eq("place", clean_place).eq("month", ticket_month).eq("year", int(ticket_year)).execute()
          else:
            supabase.table("tickets_data").insert({
                "place": clean_place,
                "month": ticket_month,
                "year": int(ticket_year),
                "content": content_str
            }).execute()

          st.session_state[cache_key] = clean_save_df
          st.success("Erfolgreich gespeichert! / تم الحفظ بنجاح")
        except Exception as e:
          st.error(f"Fehler beim Speichern: {e}")
    with col_t3:
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



#---------------------------------------------
#Lager
#---------------------------------------------
elif page == t["p9"]:
  st.title("📦 Clean & Care GmbH - Lager- & Materialverwaltung")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  # تحميل بيانات المخزون الرئيسي مرة واحدة في session_state
  if "main_inv_cache" not in st.session_state:
    try:
      res_inv = supabase.table("inventory").select("*").order("id").execute()
      st.session_state["main_inv_cache"] = res_inv.data if res_inv.data else []
    except Exception as e:
      st.error(f"Fehler beim Laden des Lagers: {e}")
      st.session_state["main_inv_cache"] = []

  # تحميل بيانات توزيع الأماكن مرة واحدة في session_state
  if "place_inv_cache" not in st.session_state:
    try:
      res_p_all = supabase.table("place_inventory").select("*").execute()
      st.session_state["place_inv_cache"] = res_p_all.data if res_p_all.data else []
    except Exception as e:
      st.error(f"Fehler beim Laden der Objektdaten: {e}")
      st.session_state["place_inv_cache"] = []

  inventory_data = st.session_state["main_inv_cache"]

  # =========================================================
  # الجزء الأول: الجدول الرئيسي للمخزون (70 سطراً)
  # =========================================================
  st.subheader("1. Hauptlager (70 Zeilen)")

  rows_list = []
  for i in range(70):
    if i < len(inventory_data):
      item = inventory_data[i]
      rows_list.append({
          "Nr.": i + 1,
          "Materialname": str(item.get("material") or "").strip(),
          "Kategorie": str(item.get("category") or "").strip(),
          "Gesamtbestand": int(item.get("gesamtbestand") or 0),
          "Aktueller Bestand": int(item.get("aktueller_bestand") or 0),
      })
    else:
      rows_list.append({
          "Nr.": i + 1,
          "Materialname": "",
          "Kategorie": "",
          "Gesamtbestand": 0,
          "Aktueller Bestand": 0,
      })

  inv_df = pd.DataFrame(rows_list)

  edited_inv_df = st.data_editor(
      inv_df,
      num_rows="fixed",
      use_container_width=True,
      disabled=["Nr.", "Aktueller Bestand"],
      key="main_inventory_70_table",
  )

  if st.button("💾 Hauptlager speichern", key="save_main_inv_btn"):
    try:
      distributed_map = {}
      for d_item in st.session_state.get("place_inv_cache", []):
        m_key = str(d_item.get("material") or "").strip()
        if m_key:
          distributed_map[m_key] = distributed_map.get(m_key, 0) + int(d_item.get("menge") or 0)

      seen_materials = set()
      to_insert = []

      for _, row in edited_inv_df.iterrows():
        mat_name = str(row["Materialname"]).strip()
        if mat_name and mat_name.lower() != "nan" and mat_name not in seen_materials:
          seen_materials.add(mat_name)
          ges_val = int(row["Gesamtbestand"]) if pd.notna(row["Gesamtbestand"]) else 0
          already_dist = distributed_map.get(mat_name, 0)
          akt_val = max(0, ges_val - already_dist)

          to_insert.append({
              "material": mat_name,
              "category": str(row["Kategorie"]).strip(),
              "gesamtbestand": ges_val,
              "aktueller_bestand": akt_val,
          })

      supabase.table("inventory").delete().neq("id", 0).execute()
      if to_insert:
        res_ins = supabase.table("inventory").insert(to_insert).execute()
        st.session_state["main_inv_cache"] = res_ins.data if res_ins.data else to_insert
      else:
        st.session_state["main_inv_cache"] = []

      st.success("Hauptlager erfolgreich gespeichert und Bestände synchronisiert!")
      st.rerun()
    except Exception as e:
      st.error(f"Fehler beim Speichern: {e}")

  st.markdown("---")

  # =========================================================
  # الجزء الثاني: توزيع المواد على الأماكن والخصم التلقائي
  # =========================================================
  st.subheader("2. Materialverteilung auf Objekte / Orte")

  places_list = [""] + load_places()
  selected_objekt = st.selectbox("Objekt / Ort auswählen:", places_list, key="inv_place_select")

  if selected_objekt:
    clean_objekt = str(selected_objekt).strip()
    saved_materials_map = {}
    for item in st.session_state.get("main_inv_cache", []):
      m_name = str(item.get("material") or "").strip()
      if m_name:
        saved_materials_map[m_name] = int(item.get("aktueller_bestand") or 0)

    material_options = [""] + [f"{m} (Verfügbar: {qty})" for m, qty in saved_materials_map.items()]

    with st.container():
      st.markdown(f"**Material an `{clean_objekt}` ausgeben:**")
      c1, c2, c3 = st.columns([2, 1, 1])
      with c1:
        chosen_option = st.selectbox("Material auswählen:", material_options, key="dist_mat_select")
      with c2:
        dist_qty = st.number_input("Menge:", min_value=1, value=1, step=1, key="dist_qty_input")
      with c3:
        st.write("")
        st.write("")
        if st.button("➕ Hinzufügen & vom Lager abziehen", key="add_to_place_btn"):
          if chosen_option:
            chosen_mat = chosen_option.split(" (Verfügbar:")[0].strip()
            try:
              res_m = supabase.table("inventory").select("*").eq("material", chosen_mat).limit(1).execute()
              if res_m.data:
                db_item = res_m.data[0]
                current_stock = int(db_item.get("aktueller_bestand") or 0)
                mat_cat = str(db_item.get("category") or "").strip()

                if current_stock >= dist_qty:
                  new_stock = current_stock - int(dist_qty)
                  supabase.table("inventory").update({"aktueller_bestand": new_stock}).eq("id", db_item["id"]).execute()

                  # تحديث الكاش الرئيسي للمخزون
                  for m_cache in st.session_state.get("main_inv_cache", []):
                    if str(m_cache.get("material") or "").strip() == chosen_mat:
                      m_cache["aktueller_bestand"] = new_stock
                      break

                  res_p = (
                      supabase.table("place_inventory")
                      .select("*")
                      .eq("place", clean_objekt)
                      .eq("material", chosen_mat)
                      .limit(1)
                      .execute()
                  )
                  if res_p.data:
                    old_qty = int(res_p.data[0].get("menge") or 0)
                    updated_qty = old_qty + int(dist_qty)
                    supabase.table("place_inventory").update({"menge": updated_qty}).eq("id", res_p.data[0]["id"]).execute()

                    for p_cache in st.session_state.get("place_inv_cache", []):
                      if (
                          str(p_cache.get("place") or "").strip() == clean_objekt
                          and str(p_cache.get("material") or "").strip() == chosen_mat
                      ):
                        p_cache["menge"] = updated_qty
                        break
                  else:
                    new_p_row = {
                        "place": clean_objekt,
                        "material": chosen_mat,
                        "category": mat_cat,
                        "menge": int(dist_qty),
                    }
                    res_p_ins = supabase.table("place_inventory").insert(new_p_row).execute()
                    inserted_p = res_p_ins.data[0] if res_p_ins.data else new_p_row
                    st.session_state["place_inv_cache"].append(inserted_p)

                  st.success(f"{dist_qty}x {chosen_mat} wurde an {clean_objekt} zugewiesen und vom Lager abgezogen!")
                  st.rerun()
                else:
                  st.error(f"Nicht genug Bestand im Lager! Verfügbar: {current_stock}")
              else:
                st.warning("Bitte speichern Sie das Hauptlager zuerst, bevor Sie Material verteilen.")
            except Exception as e:
              st.error(f"Fehler bei der Verteilung: {e}")

    # عرض جدول المواد المستلمة لهذا المكان من الكاش المحدّث
    st.markdown(f"**Bereits erhaltene Materialien in `{clean_objekt}`:**")
    obj_rows = [
        {
            "Materialname": str(r.get("material") or "").strip(),
            "Kategorie": str(r.get("category") or "").strip(),
            "Erhaltene Menge": int(r.get("menge") or 0),
        }
        for r in st.session_state.get("place_inv_cache", [])
        if str(r.get("place") or "").strip() == clean_objekt
    ]
    if obj_rows:
      place_items_df = pd.DataFrame(obj_rows)
      st.dataframe(place_items_df, use_container_width=True, hide_index=True)
    else:
      st.info("Für dieses Objekt wurden noch keine Materialien eingetragen.")


#---------------------------------------------------
#kleidung
#---------------------------------------------------

elif page == t["p10"]:
  from datetime import date

  st.title("👕 Clean & Care GmbH - Arbeitskleidung")
  st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

  shoe_and_cloth_sizes = [
      "",
      "XS", "S", "M", "L", "XL", "XXL", "XXXL", "4XL",
      "40", "41", "42", "43", "44", "45"
  ]

  # تحميل بيانات المخزون مرة واحدة في session_state
  if "cloth_inv_cache" not in st.session_state:
    try:
      res_cloth = supabase.table("clothing_inventory").select("*").order("id").execute()
      st.session_state["cloth_inv_cache"] = res_cloth.data if res_cloth.data else []
    except Exception as e:
      st.error(f"Fehler beim Laden des Kleiderlagers: {e}")
      st.session_state["cloth_inv_cache"] = []

  clothing_data = st.session_state["cloth_inv_cache"]

  # =========================================================
  # 1. جدول مخزون الملابس الرئيسي (XS-4XL ومقاسات الأحذية 40-45)
  # =========================================================
  st.subheader("1. Kleiderlager (Bestand nach Größe)")

  max_display_rows = max(25, len(clothing_data) + 5)
  cloth_rows = []
  for i in range(max_display_rows):
    if i < len(clothing_data):
      item = clothing_data[i]
      cloth_rows.append({
          "Nr.": i + 1,
          "Kleidungsstück": str(item.get("item_name") or "").strip(),
          "Größe": str(item.get("size") or "").strip(),
          "Gesamtbestand": int(item.get("gesamtbestand") or 0),
          "Aktueller Bestand": int(item.get("aktueller_bestand") or 0),
      })
    else:
      cloth_rows.append({
          "Nr.": i + 1,
          "Kleidungsstück": "",
          "Größe": "",
          "Gesamtbestand": 0,
          "Aktueller Bestand": 0,
      })

  cloth_df = pd.DataFrame(cloth_rows)

  edited_cloth_df = st.data_editor(
      cloth_df,
      num_rows="fixed",
      use_container_width=True,
      disabled=["Nr.", "Aktueller Bestand"],
      key="clothing_inventory_table",
      column_config={
          "Größe": st.column_config.SelectboxColumn(
              "Größe", options=shoe_and_cloth_sizes
          )
      }
  )

  if st.button("💾 Kleiderlager speichern", key="save_clothing_btn"):
    try:
      dist_cloth_map = {}
      if "all_emp_cloth_cache" in st.session_state:
        emp_cloth_rows = st.session_state["all_emp_cloth_cache"]
      else:
        res_all_emp_cloth = supabase.table("employee_clothing").select("item_name, size, menge").execute()
        emp_cloth_rows = res_all_emp_cloth.data if res_all_emp_cloth.data else []

      for d in emp_cloth_rows:
        k = (str(d.get("item_name") or "").strip(), str(d.get("size") or "").strip())
        dist_cloth_map[k] = dist_cloth_map.get(k, 0) + int(d.get("menge") or 0)

      seen_items = set()
      to_insert = []

      for _, row in edited_cloth_df.iterrows():
        c_name = str(row["Kleidungsstück"]).strip()
        c_size = str(row["Größe"]).strip()
        if c_name and c_name.lower() != "nan" and (c_name, c_size) not in seen_items:
          seen_items.add((c_name, c_size))
          ges_val = int(row["Gesamtbestand"]) if pd.notna(row["Gesamtbestand"]) else 0
          already_given = dist_cloth_map.get((c_name, c_size), 0)
          akt_val = max(0, ges_val - already_given)

          to_insert.append({
              "item_name": c_name,
              "size": c_size,
              "gesamtbestand": ges_val,
              "aktueller_bestand": akt_val
          })

      supabase.table("clothing_inventory").delete().neq("id", 0).execute()
      if to_insert:
        res_inserted = supabase.table("clothing_inventory").insert(to_insert).execute()
        st.session_state["cloth_inv_cache"] = res_inserted.data if res_inserted.data else to_insert
      else:
        st.session_state["cloth_inv_cache"] = []

      st.success("Kleiderlager erfolgreich gespeichert!")
      st.rerun()
    except Exception as e:
      st.error(f"Fehler beim Speichern: {e}")

  st.markdown("---")

  # =========================================================
  # 2. تسليم الملابس والأحذية للعمال حسب المدينة والعامل
  # =========================================================
  st.subheader("2. Kleidung an Mitarbeiter ausgeben")

  if "all_emp_cloth_cache" not in st.session_state:
    try:
      res_all_ec = supabase.table("employee_clothing").select("*").order("id", desc=True).execute()
      st.session_state["all_emp_cloth_cache"] = res_all_ec.data if res_all_ec.data else []
    except Exception as e:
      st.error(f"Fehler beim Laden der Mitarbeiterkleidung: {e}")
      st.session_state["all_emp_cloth_cache"] = []

  cities_list = [""] + load_cities()
  selected_city_cloth = st.selectbox("Stadt auswählen:", cities_list, key="cloth_city_select")

  if selected_city_cloth:
    city_emps = get_employees_by_city(selected_city_cloth)
    if not city_emps:
      city_emps = load_employees()

    selected_emp_cloth = st.selectbox("Mitarbeiter auswählen:", [""] + city_emps, key="cloth_emp_select")

    if selected_emp_cloth:
      clean_emp = selected_emp_cloth.strip()

      cloth_options = [""]
      cloth_lookup = {}
      for item in st.session_state.get("cloth_inv_cache", []):
        c_name = str(item.get("item_name") or "").strip()
        c_size = str(item.get("size") or "").strip()
        c_qty = int(item.get("aktueller_bestand") or 0)
        if c_name:
          label = f"{c_name} | Größe: {c_size} (Verfügbar: {c_qty})"
          cloth_options.append(label)
          cloth_lookup[label] = item

      st.markdown(f"**Kleidung an `{clean_emp}` ({selected_city_cloth}) ausgeben:**")
      c1, c2, c3, c4 = st.columns([2.5, 1, 1.2, 1.3])
      with c1:
        chosen_cloth_label = st.selectbox("Kleidungsstück & Größe:", cloth_options, key="cloth_item_select")
      with c2:
        cloth_qty = st.number_input("Menge:", min_value=1, value=1, step=1, key="cloth_qty_input")
      with c3:
        issue_date = st.date_input("Datum:", value=date.today(), key="cloth_date_input")
      with c4:
        st.write("")
        st.write("")
        if st.button("➕ Hinzufügen & abziehen", key="give_cloth_btn"):
          if chosen_cloth_label and chosen_cloth_label in cloth_lookup:
            try:
              db_item = cloth_lookup[chosen_cloth_label]
              current_stock = int(db_item.get("aktueller_bestand") or 0)

              if current_stock >= cloth_qty:
                new_stock = current_stock - int(cloth_qty)
                supabase.table("clothing_inventory").update({"aktueller_bestand": new_stock}).eq("id", db_item["id"]).execute()

                new_rec = {
                    "employee_name": clean_emp,
                    "city": selected_city_cloth,
                    "item_name": db_item["item_name"],
                    "size": db_item["size"],
                    "menge": int(cloth_qty),
                    "ausgabedatum": issue_date.strftime("%d.%m.%Y")
                }
                supabase.table("employee_clothing").insert(new_rec).execute()

                for cached_item in st.session_state.get("cloth_inv_cache", []):
                  if cached_item.get("id") == db_item.get("id"):
                    cached_item["aktueller_bestand"] = new_stock
                    break

                st.session_state["all_emp_cloth_cache"].insert(0, new_rec)
                st.success(f"{cloth_qty}x {db_item['item_name']} ({db_item['size']}) an {clean_emp} ausgegeben!")
                st.rerun()
              else:
                st.error(f"Nicht genug Bestand! Verfügbar: {current_stock}")
            except Exception as e:
              st.error(f"Fehler bei der Ausgabe: {e}")

      st.markdown(f"**Bereits erhaltene Kleidung von `{clean_emp}`:**")
      emp_items = [
          r for r in st.session_state.get("all_emp_cloth_cache", [])
          if str(r.get("employee_name") or "").strip() == clean_emp
      ]
      if emp_items:
        emp_c_df = pd.DataFrame(emp_items)[["item_name", "size", "menge", "ausgabedatum"]]
        emp_c_df.columns = ["Kleidungsstück", "Größe", "Menge", "Datum"]
        st.dataframe(emp_c_df, use_container_width=True, hide_index=True)
      else:
        st.info("Dieser Mitarbeiter hat noch keine Arbeitskleidung erhalten.")
