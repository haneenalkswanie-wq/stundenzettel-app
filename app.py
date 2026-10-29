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
# الصفحة الأولى: إدارة ساعات الموظفين (الجدول الكامل)
# ---------------------------------------------------------
if page == "📋 إدارة ساعات الموظفين (Stundenzettel)":
  st.title("📋 Clean & Care GmbH - نظام إدارة ساعات العمل")

  # إدخال بيانات الموظف الشهرية
  col1, col2, col3 = st.columns(3)
  with col1:
    employee_name = st.text_input("اسم الموظف:", "اسم العمالة")
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
        index=9,
    )
  with col3:
    selected_year = st.number_input("السنة:", value=2026)

  st.subheader(" جدول تسجيل الدوام اليومي")

  # تهيئة جدول الأيام الشهري إذا لم يكن موجوداً
  if "employee_df" not in st.session_state:
    days_data = []
    for day in range(1, 32):
      days_data.append(
          {"التاريخ/اليوم": f"يوم {day}", "Beginn": "", "Ende": "", "Arbeitszeit": 0.0}
      )
    st.session_state.employee_df = pd.DataFrame(days_data)

  # تعديل الجدول من قبل المستخدم
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

          # إجمالي ساعات العمل
          gross_hours = (t2 - t1).total_seconds() / 3600

          if gross_hours > 0:
            # تحديد الاستراحة حسب القواعد الجديدة
            if gross_hours <= 4.5:
              break_val = 0.0
            elif 5.0 <= gross_hours <= 8.0:
              break_val = 0.5
            else:
              break_val = 1.0

            # صافي الساعات بعد خصم الاستراحة
            hrs = max(0.0, gross_hours - break_val)
          break
        except ValueError:
          continue

    edited_df.at[index, "Arbeitszeit"] = round(hrs, 2)
    total_sum_hours += hrs

  st.markdown("---")
  col_res1, col_res2 = st.columns([2, 1])
  with col_res2:
    st.metric(label="إجمالي ساعات العمل للشهر:", value=f"{total_sum_hours:.2f} ساعة")

# ---------------------------------------------------------
# الصفحة الثانية: متابعة ساعات المواقع وتصدير PDF
# ---------------------------------------------------------
elif page == "🏢 متابعة ساعات المواقع (Objekte)":
  st.title("🏢 Clean & Care GmbH - متابعة ساعات المواقع والمنشآت")

  st.write("قم بإدخال اسم الموقع وتوزيع الساعات اليومية خلال الشهر:")

  col1, col2 = st.columns(2)
  with col1:
    month = st.selectbox(
        "اختر الشهر للمواقع:", list(range(1, 13)), index=datetime.now().month - 1
    )
  with col2:
    year = st.number_input(
        "السنة للمواقع:", min_value=2024, max_value=2030, value=2026
    )

  days_in_month = pd.Period(f"{year}-{month}").days_in_month

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
  st.subheader("🖨️ طباعة وتصدير التقرير")
  if st.button("توليد تقرير PDF للمواقع"):
    st.success(
        "تم تحضير البيانات للطباعة! يمكنك استخدام خيار الطباعة المباشرة من"
        " المتصفح (Ctrl + P) للفظ كـ PDF."
    )