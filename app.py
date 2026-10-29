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
    [
        "📋 إدارة ساعات الموظفين (Stundenzettel)",
        "👥 إدارة العمال (Mitarbeiter)",
        "🏢 متابعة ساعات المواقع (Objekte)",
    ],
)

# ---------------------------------------------------------
# صفحة إدارة العمال (مع إضافة وحذف العمال)
# ---------------------------------------------------------
if page == "👥 إدارة العمال (Mitarbeiter)":
  st.title("👥 Clean & Care GmbH - إدارة العمال والموظفين")
  st.write("إضافة أو حذف أسماء العمال لتظهر تلقائياً في قائمة إدخال الساعات:")

  # تهيئة قائمة العمال الأساسية في الجلسة
  if "employees_list" not in st.session_state:
    st.session_state.employees_list = [
        "Sakleh Alsoudi",
        "Alaa Edin Ibrahim",
        "موظف جديد",
    ]

  # قسم إضافة موظف جديد
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

  # قسم حذف موظف
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
  else:
    st.info("لا توجد أسماء عمال حالياً.")

  st.markdown("---")
  st.subheader("📋 قائمة العمال الحاليين:")
  for idx, emp in enumerate(st.session_state.employees_list, 1):
    st.write(f"{idx}. {emp}")

# ---------------------------------------------------------
# الصفحة الأولى: إدارة ساعات الموظفين (مطابق للنموذج الرسمي)
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
      st.session_state.employee_df, num_rows="fixed", use_container_width=True
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
    if st.button("🖨️ طباعة نموذج Stundenzettel كـ PDF"):
      st.success(
          "تم تجهيز النموذج للطباعة الرسمية! اضغط (Ctrl + P) من لوحة المفاتيح"
          " واحفظ كـ PDF."
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