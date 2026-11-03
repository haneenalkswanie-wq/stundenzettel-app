from datetime import datetime
import io
import json
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
# بيانات الاتصال بقاعدة البيانات السحابية المدفوعة (Supabase)
# ---------------------------------------------------------
SUPABASE_URL = "https://knzrtbjwqqhxghtfasvy.supabase.co"
SUPABASE_KEY = "ضعي_المفتاح_الكامل_الظاهر_في_الشاشة_هنا"

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# ---------------------------------------------------------
# نظام الحماية وتسجيل الدخول
# ---------------------------------------------------------
def check_password():
    def password_entered():
        user_input = st.session_state["username"].strip()
        pass_input = st.session_state["password"].strip()
        if user_input == "admin" and pass_input == "clean2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🔐 Clean & Care GmbH - Login")
        st.markdown("Bitte melden Sie sich an, um fortzufahren. / يرجى تسجيل الدخول للمتابعة.")
        st.text_input("Benutzername (Username):", key="username")
        st.text_input("Passwort (Password):", type="password", key="password")
        st.button("Anmelden / دخول", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔐 Clean & Care GmbH - Login")
        st.text_input("Benutzername (Username):", key="username")
        st.text_input("Passwort (Password):", type="password", key="password")
        st.button("Anmelden / دخول", on_click=password_entered)
        st.error("😕 Benutzername oder Passwort ist falsch / اسم المستخدم أو كلمة السر غير صحيحة.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ---------------------------------------------------------
# دوال التعامل مع السحاب (Supabase Cloud)
# ---------------------------------------------------------
def load_employees():
    try:
        res = supabase.table("employees").select("name").execute()
        if res.data:
            return sorted([r["name"] for r in res.data])
    except:
        pass
    return ["Sakleh Alsoudi", "Alaa Edin Ibrahim"]

def save_employees(emp_list):
    supabase.table("employees").delete().neq("name", "").execute()
    for emp in emp_list:
        supabase.table("employees").insert({"name": emp}).execute()

def load_places():
    try:
        res = supabase.table("places").select("name").execute()
        if res.data:
            return sorted([r["name"] for r in res.data])
    except:
        pass
    return ["Limehome Salzburg", "Nespresso Store", "IKEA Wals", "Villach Hauptplatz"]

def save_places(places_list):
    supabase.table("places").delete().neq("name", "").execute()
    for place in places_list:
        supabase.table("places").insert({"name": place}).execute()

def load_employee_month_hours(emp_name, month_str, year_val):
    try:
        res = supabase.table("monthly_hours").select("content").eq("emp", emp_name).eq("month", month_str).eq("year", year_val).execute()
        if res.data and len(res.data) > 0:
            return pd.DataFrame(json.loads(res.data[0]["content"]))
    except:
        pass
    days_data = []
    for day in range(1, 32):
        days_data.append({"Datum": str(day), "Ort": "", "Beginn": "", "Ende": "", "Pause": "", "Arbeitszeit (abzgl. Pause)": 0.0})
    return pd.DataFrame(days_data)

def save_employee_month_hours(emp_name, month_str, year_val, df):
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("monthly_hours").upsert({"emp": emp_name, "month": month_str, "year": year_val, "content": content}).execute()

def load_daily_emp_hours(emp_name, month_str, year_val):
    try:
        res = supabase.table("daily_hours").select("content").eq("emp", emp_name).eq("month", month_str).eq("year", year_val).execute()
        if res.data and len(res.data) > 0:
            df = pd.DataFrame(json.loads(res.data[0]["content"]))
            for i in range(1, 4):
                if f"Hrs{i}" not in df.columns: df[f"Hrs{i}"] = ""
            return df
    except:
        pass
    days_data = []
    for day in range(1, 32):
        days_data.append({"Datum": str(day), "Ort 1": "", "Beginn 1": "", "Ende 1": "", "Hrs1": "", "Ort 2": "", "Beginn 2": "", "Ende 2": "", "Hrs2": "", "Ort 3": "", "Beginn 3": "", "Ende 3": "", "Hrs3": "", "Pause": "", "Gesamtstunden": 0.0})
    return pd.DataFrame(days_data)

def save_daily_emp_hours(emp_name, month_str, year_val, df):
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("daily_hours").upsert({"emp": emp_name, "month": month_str, "year": year_val, "content": content}).execute()

def load_tickets_data(month_str, year_val):
    try:
        res = supabase.table("tickets_data").select("content").eq("month", month_str).eq("year", year_val).execute()
        if res.data and len(res.data) > 0:
            return pd.DataFrame(json.loads(res.data[0]["content"]))
    except:
        pass
    month_map = {"Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6, "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12}
    m_num = month_map.get(month_str, 10)
    days_in_m = pd.Period(f"{year_val}-{m_num}").days_in_month
    tickets_rows = []
    for day in range(1, days_in_m + 1):
        tickets_rows.append({"Datum": str(day), "Ort": "", "Ticket-Nummer": "", "Beginn": "", "Ende": "", "Bemerkung": "", "Netto-Stunden": 0.0})
    return pd.DataFrame(tickets_rows)

def save_tickets_data(month_str, year_val, df):
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("tickets_data").upsert({"month": month_str, "year": year_val, "content": content}).execute()

def load_trains_data(emp_name, month_str, year_val):
    try:
        res = supabase.table("trains_data").select("content").eq("emp", emp_name).eq("month", month_str).eq("year", year_val).execute()
        if res.data and len(res.data) > 0:
            df = pd.DataFrame(json.loads(res.data[0]["content"]))
            for i in range(1, 6):
                if f"Beginn {i}" not in df.columns: df[f"Beginn {i}"] = ""
                if f"Ende {i}" not in df.columns: df[f"Ende {i}"] = ""
                if f"Verspätung {i}" not in df.columns: df[f"Verspätung {i}"] = 0
            return df
    except:
        pass
    month_map = {"Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6, "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12}
    m_num = month_map.get(month_str, 10)
    days_in_m = pd.Period(f"{year_val}-{m_num}").days_in_month
    trains_rows = []
    for day in range(1, days_in_m + 1):
        row_data = {"Datum": str(day)}
        for i in range(1, 6):
            row_data[f"Beginn {i}"] = ""
            row_data[f"Ende {i}"] = ""
            row_data[f"Verspätung {i}"] = 0
        row_data["Gesamtstunden"] = 0.0
        trains_rows.append(row_data)
    return pd.DataFrame(trains_rows)

def save_trains_data(emp_name, month_str, year_val, df):
    content = json.dumps(df.to_dict(orient="list"), ensure_ascii=False)
    supabase.table("trains_data").upsert({"emp": emp_name, "month": month_str, "year": year_val, "content": content}).execute()

# ---------------------------------------------------------
# القائمة الجانبية وإعدادات الصفحة
# ---------------------------------------------------------
months_list_de = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
years_list = [2024, 2025, 2026, 2027, 2028, 2029, 2030]

now = datetime.now()
default_year_index = years_list.index(now.year) if now.year in years_list else 2
default_month_index = now.month - 1

st.sidebar.title("⚙️ Einstellungen")
lang_choice = st.sidebar.radio("Sprache / اللغة:", ["Deutsch", "العربية"])
is_arabic = (lang_choice == "العربية")

t = {
    "menu": "📌 القائمة الرئيسية (Hauptmenü)" if is_arabic else "📌 Hauptmenü",
    "p1": "📋 استمارة ساعات العمال (Mitarbeiter Stundenzettel)" if is_arabic else "📋 Mitarbeiter Stundenzettel",
    "p2": "📝 الساعات اليومية (Tägliche Stunden)" if is_arabic else "📝 Tägliche Stunden",
    "p3": "🏢 ملخص ساعات المواقع (Objekt-Stundenübersicht)" if is_arabic else "🏢 Objekt-Stundenübersicht",
    "p4": "🏢 الأماكن وساعات العمال (Orte & Mitarbeiter)" if is_arabic else "🏢 Orte & Mitarbeiter-Stunden",
    "p5": "👥 إدارة العمال (Mitarbeiterverwaltung)" if is_arabic else "👥 Mitarbeiterverwaltung",
    "p6": "📅 ملخص الأشهر (Monatsübersicht)" if is_arabic else "📅 Monatsübersicht",
    "p7": "🎫 تذاكر المهام (Einsatz-Tickets)" if is_arabic else "🎫 Einsatz-Tickets",
    "p8": "🚆 جدول القطارات (Zug-Fahrten)" if is_arabic else "🚆 Zug-Fahrten (Züge)",
    "emp_label": "Mitarbeiter wählen:", "month_label": "Monat auswählen:", "year_label": "Jahr auswählen:",
    "save_btn": "💾 Speichern / حفظ", "success_msg": "Erfolgreich auf Cloud gespeichert! / تم الحفظ بالسحاب بنجاح 🔒",
    "pdf_btn": "📥 PDF herunterladen", "sum_label": "Summe:"
}

page = st.sidebar.radio(t["menu"], [t["p1"], t["p2"], t["p3"], t["p4"], t["p5"], t["p6"], t["p7"], t["p8"]])

# ---------------------------------------------------------
# دوال طباعة PDF للقطارات
# ---------------------------------------------------------
def generate_trains_pdf(emp_name, month_str, year_val, df, total_hours):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=13, leading=16, textColor=colors.HexColor("#111111"))
    elements.append(Paragraph("<b>CLEAN & CARE GmbH - Zug-Fahrten Bericht</b>", title_style))
    elements.append(Paragraph("Am Messezentrum 6, 5020 Salzburg", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Mitarbeiter:</b> {emp_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Monat:</b> {month_str} {year_val}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    table_data = [["Tag", "B1", "E1", "V1", "B2", "E2", "V2", "B3", "E3", "V3", "B4", "E4", "V4", "B5", "E5", "V5", "Gesamt"]]
    for _, row in df.iterrows():
        table_data.append([
            str(row["Datum"]),
            str(row.get("Beginn 1", "")), str(row.get("Ende 1", "")), str(row.get("Verspätung 1", "")),
            str(row.get("Beginn 2", "")), str(row.get("Ende 2", "")), str(row.get("Verspätung 2", "")),
            str(row.get("Beginn 3", "")), str(row.get("Ende 3", "")), str(row.get("Verspätung 3", "")),
            str(row.get("Beginn 4", "")), str(row.get("Ende 4", "")), str(row.get("Verspätung 4", "")),
            str(row.get("Beginn 5", "")), str(row.get("Ende 5", "")), str(row.get("Verspätung 5", "")),
            str(row["Gesamtstunden"])
        ])
    table_data.append(["Summe:", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", f"{total_hours:.2f} St."])
    
    t_pdf = Table(table_data, colWidths=[25, 45, 45, 35, 45, 45, 35, 45, 45, 35, 45, 45, 35, 45, 45, 35, 50])
    t_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#666666"))
    ]))
    elements.append(t_pdf)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------------------------------------
# الصفحة الثامنة: جدول القطارات (البداية، النهاية، التأخير لـ 5 قطارات)
# ---------------------------------------------------------
if page == t["p8"]:
    st.title("🚆 Clean & Care GmbH - Zug-Fahrten (Züge)")
    st.markdown("**Am Messezentrum 6, 5020 Salzburg**")

    employees_list = load_employees()

    col1, col2, col3 = st.columns(3)
    with col1: train_emp = st.selectbox(t["emp_label"], employees_list, key="train_emp_select")
    with col2: train_month = st.selectbox(t["month_label"], months_list_de, index=default_month_index, key="train_month_select")
    with col3: train_year = st.selectbox(t["year_label"], years_list, index=default_year_index, key="train_year_select")

    st.subheader(f"Zug-Fahrten für: {train_emp} ({train_month} {train_year})")

    trains_df = load_trains_data(train_emp, train_month, train_year)

    edited_trains_df = st.data_editor(
        trains_df, num_rows="fixed", use_container_width=True, key=f"trains_table_{train_emp}_{train_month}_{train_year}",
        column_config={
            "Beginn 1": st.column_config.TextColumn("Beginn 1"),
            "Ende 1": st.column_config.TextColumn("Ende 1"),
            "Verspätung 1": st.column_config.NumberColumn("Versp. 1 (Min)", min_value=0, step=1),
            "Beginn 2": st.column_config.TextColumn("Beginn 2"),
            "Ende 2": st.column_config.TextColumn("Ende 2"),
            "Verspätung 2": st.column_config.NumberColumn("Versp. 2 (Min)", min_value=0, step=1),
            "Beginn 3": st.column_config.TextColumn("Beginn 3"),
            "Ende 3": st.column_config.TextColumn("Ende 3"),
            "Verspätung 3": st.column_config.NumberColumn("Versp. 3 (Min)", min_value=0, step=1),
            "Beginn 4": st.column_config.TextColumn("Beginn 4"),
            "Ende 4": st.column_config.TextColumn("Ende 4"),
            "Verspätung 4": st.column_config.NumberColumn("Versp. 4 (Min)", min_value=0, step=1),
            "Beginn 5": st.column_config.TextColumn("Beginn 5"),
            "Ende 5": st.column_config.TextColumn("Ende 5"),
            "Verspätung 5": st.column_config.NumberColumn("Versp. 5 (Min)", min_value=0, step=1),
        }
    )

    edited_trains_df = edited_trains_df.astype(object)
    total_trains_sum = 0.0

    for index, row in edited_trains_df.iterrows():
        day_total_hrs = 0.0
        for i in range(1, 6):
            b_str = str(row.get(f"Beginn {i}", "")).strip()
            e_str = str(row.get(f"Ende {i}", "")).strip()
            
            try:
                delay_min = float(row.get(f"Verspätung {i}", 0))
            except:
                delay_min = 0.0

            trip_hrs = 0.0
            if b_str and e_str and b_str != "nan" and e_str != "nan":
                for fmt in ("%H:%M", "%H.%M", "%H"):
                    try:
                        t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
                        t2 = datetime.strptime(e_str.replace(".", ":"), fmt)
                        diff = (t2 - t1).total_seconds() / 3600
                        if diff > 0:
                            trip_hrs = diff
                        break
                    except:
                        continue

            if trip_hrs > 0:
                day_total_hrs += max(0.0, trip_hrs + (delay_min / 60.0))

        edited_trains_df.at[index, "Gesamtstunden"] = round(day_total_hrs, 2)
        total_trains_sum += day_total_hrs

    st.markdown("---")
    col_tr1, col_tr2, col_tr3 = st.columns([2, 1, 1])
    with col_tr1:
        pdf_trains_data = generate_trains_pdf(train_emp, train_month, train_year, edited_trains_df, total_trains_sum)
        st.download_button(t["pdf_btn"], pdf_trains_data, f"Zug_Fahrten_{train_emp}_{train_month}_{train_year}.pdf", "application/pdf", key="p8_pdf_btn")
    with col_tr2:
        if st.button(t["save_btn"], key="trains_save_btn"):
            save_trains_data(train_emp, train_month, train_year, edited_trains_df)
            st.success(t["success_msg"])
    with col_tr3:
        st.metric(t["sum_label"], f"{total_trains_sum:.2f} St.")