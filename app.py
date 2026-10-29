from datetime import datetime
import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="Clean & Care - Stundenzettel", page_icon="📋", layout="wide"
)

# تخصيص تصميم الطباعة لإخفاء الأزرار والقوائم الجانبية وطباعة النموذج فقط
st.markdown(
    """
    <style>
    @media print {
        /* إخفاء القائمة الجانبية، الأزرار، وعناصر التحكم عند الطباعة */
        [data-testid="stSidebar"], .stButton, header, footer {
            display: none !important;
        }
        body {
            background-color: white !important;
            color: black !important;
        }
        .main {
            padding: 0px !important;
        }
    }
    </style>
""",
    unsafe_allow_html=True,
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
# الصفحة الأولى: إدارة ساعات الموظفين (مطابق للنموذج الرسمي تماماً)
# ---------------------------------------------------------
elif page == "📋 إدارة ساعات الموظفين (Stundenzettel)":
  # رأس الصفحة الرسمي المطابق للنموذج الورقي
  st.markdown(
      """
    <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px;">
        <div>
            <h3 style="margin: 0; color: #111;">CLEAN & CARE GmbH</h3>
            <p style="margin: 2px 0; font-size: 14px; color: #555;">Am Messezentrum 6</p>
            <p style="margin: 2px 0; font-size: 14px; color: #555;">5020 Salzburg</p>
        </div>
        <div style="text-align: left;">
            <h2 style="margin: 0; color: #222;">CLEAN & CARE</h2>
            <p style="margin: 2px 0; font-size: 12px; color: #666; letter-spacing: 2px;">WIR KÜMMERN UNS</p>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

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

  st.markdown("### Stundenzettel")

  # تهيئة جدول الأيام الشهري إذا لم يكن موجوداً
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

  # حساب الساعات وتطبيق الاستراحة تلقائياً أو يدوياً
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
    st.info(
        "🖨️ لطباعة نموذج Stundenzettel نظيف بالشكل الورقي الرسمي بدون قوائم أو"
        " أزرار، اضغط **Ctrl + P** من لوحة المفاتيح وافظ كـ PDF."
    )
  with col_res2:
    st.metric(label="Summe (إجمالي الساعات):", value=f"{total_sum_hours:.2f} h")

  # حقول التوقيعات الرسمية في الأسفل تماماً كالنموذج
  st.markdown("<br><br>", unsafe_allow_html=True)
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
# الصفحة الثالثة: متابعة ساعات المواقع (Objekte) بتصميم أنيق ومخصص للطباعة
# ---------------------------------------------------------
elif page == "🏢 متابعة ساعات المواقع (Objekte)":
  st.markdown(
      """
    <div style="border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px;">
        <h2 style="color: #111; margin: 0;">🏢 Clean & Care GmbH - تقرير ساعات المواقع (Objekte)</h2>
        <p style="color: #555; margin: 5px 0 0 0;">متابعة وتوزيع ساعات العمل الشهرية على الفروع والمواقع المختلفة</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

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

  # حفظ وتثبيت جدول المواقع لضمان عدم حذف البيانات أثناء الإدخال
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
      st.session_state.locations_data,
      num_rows="dynamic",
      use_container_width=True,
      key="loc_table_editor",
  )
  st.session_state.locations_data = edited_locations_df

  # حساب المجموع لكل موقع
  day_cols = [c for c in edited_locations_df.columns if c.startswith("يوم")]
  edited_locations_df["المجموع الكلي (Summe)"] = edited_locations_df[
      day_cols
  ].sum(axis=1)

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
  st.info(
      "🖨️ لطباعة تقرير ومجموع ساعات المواقع بشكل أنيق ومرتب بدون أي قوائم، اضغط"
      " **Ctrl + P** واحفظ كـ PDF."
  )