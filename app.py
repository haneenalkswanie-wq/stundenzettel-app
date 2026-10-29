from datetime import datetime
import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="Clean & Care - Stundenzettel", page_icon="📋", layout="wide"
)

# القائمة الجانبية للتنقل بين الصفحات
st.sidebar.title("📌 القائمة الرئيسية")
page = st.sidebar.radio(
    "اختر الصفحة:",
    ["📋 إدارة ساعات الموظفين (Stundenzettel)", "🏢 متابعة ساعات المواقع (Objekte)"],
)

# ---------------------------------------------------------
# الصفحة الأولى: إدارة ساعات الموظفين (مع حفظ البيانات والأسماء)
# ---------------------------------------------------------
if page == "📋 إدارة ساعات الموظفين (Stundenzettel)":
  st.title("📋 Clean & Care GmbH - نظام إدارة ساعات العمل")

  # تهيئة بيانات المدخلات الأساسية في الجلسة للحفظ والرجوع
  if "emp_meta" not in st.session_state:
    st.session_state.emp_meta = {
        "name": "اسم العمالة",
        "month_idx": 9,
        "year": 2026,
    }

  col1, col2, col3 = st.columns(3)
  with col1:
    employee_name = st.text_input(
        "اسم الموظف:",
        value=st.session_state.emp_meta["name"],
        key="input_emp_name",
    )
    st.session_state.emp_meta["name"] = employee_name
  with col2:
    selected_month = st.selectbox(
        "الشهر:",
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
        index=st.session_state.emp_meta["month_idx"],
        key="input_month",
    )
    st.session_state.emp_meta["month_idx"] = [
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
    ].index(selected_month)
  with col3:
    selected_year = st.number_input(
        "السنة:", value=st.session_state.emp_meta["year"], key="input_year"
    )
    st.session_state.emp_meta["year"] = selected_year

  st.subheader(" جدول تسجيل الدوام اليومي والاستراحات")

  # تهيئة جدول الأيام الشهري في الجلسة للمحافظة على البيانات
  if "employee_df" not in st.session_state:
    days_data = []
    for day in range(1, 32):
      days_data.append(
          {
              "التاريخ/اليوم": f"يوم {day}",
              "Beginn": "",
              "Ende": "",
              "Arbeitszeit": 0.0,
          }
      )
    st.session_state.employee_df = pd.DataFrame(days_data)

  # تعديل الجدول مع بقاء البيانات محفوظة
  edited_df = st.data_editor(
      st.session_state.employee_df, num_rows="fixed", use_container_width=True
  )
  st.session_state.employee_df = edited_df

  # حساب الساعات وتطبيق استراحة الطعام تلقائياً
  total_sum_hours = 0.0

  for index, row in edited_df.iterrows():
    b_str = str(row["Beginn"]).strip()
    e_str = str(row["Ende"]).strip()

    hrs = 0.0
    if b_str and e_str and b_str != "nan" and e_str != "nan":
      for fmt in ("%H:%M", "%H.%M", "%H"):
        try:
          t1 = datetime.strptime(b_str.replace(".", ":"), fmt)
          t2 = datetime.strptime(e_str.replace(".", ":"), fmt)

          gross_hours = (t2 - t1).total_seconds() / 3600

          if gross_hours > 0:
            # قواعد الاستراحة الجديدة
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

    edited_df.at[index, "Arbeitszeit"] = round(hrs, 2)
    total_sum_hours += hrs

  st.markdown("---")
  col_res1, col_res2 = st.columns([2, 1])
  with col_res1:
    if st.button("🖨️ طباعة تقرير الموظف (PDF)"):
      st.success(
          "تم تجهيز التقارير! اضغط على (Ctrl + P) من لوحة المفاتيح للحفظ كـ PDF"
          " مباشرة."
      )
  with col_res2:
    st.metric(label="إجمالي ساعات العمل للشهر:", value=f"{total_sum_hours:.2f} ساعة")

# ---------------------------------------------------------
# الصفحة الثانية: متابعة ساعات المواقع (مع حفظ الأسماء والبيانات)
# ---------------------------------------------------------
elif page == "🏢 متابعة ساعات المواقع (Objekte)":
  st.title("🏢 Clean & Care GmbH - متابعة ساعات المواقع والمنشآت")

  st.write("قم بإدخال اسم الموقع وتوزيع الساعات اليومية خلال الشهر:")

  col1, col2 = st.columns(2)
  with col1:
    loc_month = st.selectbox(
        "اختر الشهر للمواقع:", list(range(1, 13)), index=datetime.now().month - 1
    )
  with col2:
    loc_year = st.number_input(
        "السنة للمواقع:", min_value=2024, max_value=2030, value=2026
    )

  days_in_month = pd.Period(f"{loc_year}-{loc_month}").days_in_month

  # حفظ جدول وأسماء المواقع في الجلسة لضمان عدم ضياعها عند الرجوع
  if "locations_data" not in st.session_state:
    init_data = {
        "اسم المكان (Objekt)": [
            "Limehome Salzburg",
            "Nespresso Store",
            "IKEA Wals",
        ]
    }
    for day in range(1, days_in_month + 1):
      init_data[f"يوم {day}"] = [0.0] * 3
    st.session_state.locations_data = pd.DataFrame(init_data)

  st.subheader("📝 جدول الساعات الشهرية للمواقع")
  edited_locations_df = st.data_editor(
      st.session_state.locations_data, num_rows="dynamic", use_container_width=True
  )
  st.session_state.locations_data = edited_locations_df

  day_cols = [c for c in edited_locations_df.columns if c.startswith("يوم")]
  edited_locations_df["المجموع الكلي (Summe)"] = edited_locations_df[
      day_cols
  ].sum(axis=1)

  st.markdown("---")
  st.subheader("📊 إجمالي ساعات المواقع لهذا الشهر")
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
  if st.button("🖨️ طباعة تقرير المواقع (PDF)"):
    st.success("تم تجهيز التقرير! يمكنك استخدام (Ctrl + P) للطباعة أو الحفظ كـ PDF.")