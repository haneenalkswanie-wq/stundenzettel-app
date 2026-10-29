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
# الصفحة الأولى: إدارة ساعات الموظفين
# ---------------------------------------------------------
if page == "📋 إدارة ساعات الموظفين (Stundenzettel)":
  st.title("📋 Clean & Care GmbH - نظام إدارة ساعات العمل")

  # (هنا يمكنك وضع نموذج إدخال الموظفين والجدول الخاص بهم كما كان سابقاً)
  st.info("صفحة تسجيل وحساب ساعات الموظفين واستراحاتهم تلقائياً.")

# ---------------------------------------------------------
# الصفحة الثانية: متابعة ساعات المواقع وتصدير PDF
# ---------------------------------------------------------
elif page == "🏢 متابعة ساعات المواقع (Objekte)":
  st.title("🏢 Clean & Care GmbH - متابعة ساعات المواقع والمنشآت")

  st.write("قم بإدخال اسم الموقع وتوزيع الساعات اليومية خلال الشهر:")

  # اختيار الشهر والسنة
  col1, col2 = st.columns(2)
  with col1:
    month = st.selectbox(
        "اختر الشهر:", list(range(1, 13)), index=datetime.now().month - 1
    )
  with col2:
    year = st.number_input("السنة:", min_value=2024, max_value=2030, value=2026)

  days_in_month = pd.Period(f"{year}-{month}").days_in_month

  # تهيئة البيانات الأساسية في الجلسة للحفظ والرجوع
  if "locations_data" not in st.session_state:
    # جدول افتراضي بـ 3 مواقع
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

  # جدول قابل للتعديل والتفاعل
  edited_locations_df = st.data_editor(
      st.session_state.locations_data, num_rows="dynamic", use_container_width=True
  )

  # حفظ التعديلات في سياق الجلسة للرجوع إليها
  st.session_state.locations_data = edited_locations_df

  # حساب مجموع الساعات لكل موقع
  day_cols = [c for c in edited_locations_df.columns if c.startswith("يوم")]
  edited_locations_df["المجموع الكلي (Summe)"] = edited_locations_df[
      day_cols
  ].sum(axis=1)

  st.markdown("---")
  st.subheader("📊 إجمالي ساعات المواقع لهذا الشهر")

  # عرض المجموع بطريقة مرتبة
  summary_df = edited_locations_df[
      ["اسم المكان (Objekt)", "المجموع الكلي (Summe)"]
  ]
  st.dataframe(summary_df, use_container_width=True)

  total_all_locations = summary_df["المجموع الكلي (Summe)"].sum()
  st.metric(
      label="إجمالي كافة الساعات لجميع المواقع:",
      value=f"{total_all_locations:.2f} ساعة",
  )

  # زر تصدير بطاقة الطباعة / PDF
  st.markdown("---")
  st.subheader("🖨️ طباعة وتصدير التقرير")

  if st.button("توليد تقرير PDF للمواقع"):
    st.success(
        "تم تحضير البيانات للطباعة! يمكنك استخدام خيار الطباعة المباشرة من"
        " المتصفح (Ctrl + P) للفظ كـ PDF."
    )