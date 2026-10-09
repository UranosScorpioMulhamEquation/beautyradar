import datetime
import calendar
import math
import streamlit as st
import pandas as pd
import swisseph as swe

# ==========================================
# 1. القواميس والمراجع التنجيمية (ELECTIONAL RULES & DICTIONARIES)
# ==========================================

ZODIAC_SIGNS = {
    0: {"en": "Aries", "ar": "الحمل", "element": "Fire", "ruler": "Mars", "body_parts": ["Head", "Face", "Scalp", "Brain"]},
    1: {"en": "Taurus", "ar": "الثور", "element": "Earth", "ruler": "Venus", "body_parts": ["Neck", "Throat", "Vocal Cords"]},
    2: {"en": "Gemini", "ar": "الجوزاء", "element": "Air", "ruler": "Mercury", "body_parts": ["Shoulders", "Arms", "Hands", "Lungs"]},
    3: {"en": "Cancer", "ar": "السرطان", "element": "Water", "ruler": "Moon", "body_parts": ["Chest", "Breasts", "Stomach"]},
    4: {"en": "Leo", "ar": "الأسد", "element": "Fire", "ruler": "Sun", "body_parts": ["Heart", "Spine", "Upper Back"]},
    5: {"en": "Virgo", "ar": "العذراء", "element": "Earth", "ruler": "Mercury", "body_parts": ["Abdomen", "Digestive System", "Skin (Purity)"]},
    6: {"en": "Libra", "ar": "الميزان", "element": "Air", "ruler": "Venus", "body_parts": ["Kidneys", "Lower Back", "Buttocks", "Skin (Aesthetics)"]},
    7: {"en": "Scorpio", "ar": "العقرب", "element": "Water", "ruler": "Pluto/Mars", "body_parts": ["Reproductive System", "Excretory System"]},
    8: {"en": "Sagittarius", "ar": "القوس", "element": "Fire", "ruler": "Jupiter", "body_parts": ["Hips", "Thighs"]},
    9: {"en": "Capricorn", "ar": "الجدي", "element": "Earth", "ruler": "Saturn", "body_parts": ["Bones", "Joints", "Knee", "Skin (Structure)"]},
    10: {"en": "Aquarius", "ar": "الدلو", "element": "Air", "ruler": "Uranus/Saturn", "body_parts": ["Calves", "Ankles", "Circulatory System"]},
    11: {"en": "Pisces", "ar": "الحوت", "element": "Water", "ruler": "Neptune/Jupiter", "body_parts": ["Feet", "Toes", "Lymphatic System"]}
}

MONTH_NAMES_AR = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
}

ASPECT_ORBS = {
    0: 8.0,    # Conjunction
    60: 6.0,   # Sextile
    90: 6.0,   # Square
    120: 8.0,  # Trine
    180: 8.0   # Opposition
}

# ==========================================
# 2. المحرك الحسابي التنجيمي (ASTROLOGICAL ENGINE)
# ==========================================

class AstrologicalElectionEngine:
    def __init__(self):
        swe.set_ephe_path('ephe')

    @staticmethod
    def get_julian_day(year: int, month: int, day: int, hour: float = 12.0) -> float:
        return swe.julday(year, month, day, hour)

    def get_planet_position(self, jd: float, planet_id: int):
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        res, _ = swe.calc_ut(jd, planet_id, flags)
        lon = res[0]
        speed = res[3]
        sign_idx = int(lon // 30)
        degree_in_sign = lon % 30
        is_retrograde = speed < 0
        return {
            "longitude": lon,
            "sign_index": sign_idx,
            "degree": degree_in_sign,
            "speed": speed,
            "is_retrograde": is_retrograde
        }

    def get_moon_phase(self, jd: float) -> dict:
        sun_pos = self.get_planet_position(jd, swe.SUN)
        moon_pos = self.get_planet_position(jd, swe.MOON)
        
        diff = (moon_pos["longitude"] - sun_pos["longitude"]) % 360
        is_waxing = diff < 180
        illumination_pct = round((1 - math.cos(math.radians(diff))) / 2 * 100, 1)
        
        return {
            "angle_diff": diff,
            "is_waxing": is_waxing,
            "illumination_pct": illumination_pct
        }

    def check_aspect(self, lon1: float, lon2: float) -> str:
        diff = abs(lon1 - lon2) % 360
        if diff > 180:
            diff = 360 - diff

        for aspect_deg, orb in ASPECT_ORBS.items():
            if abs(diff - aspect_deg) <= orb:
                if aspect_deg == 0: return "Conjunction"
                if aspect_deg == 60: return "Sextile"
                if aspect_deg == 90: return "Square"
                if aspect_deg == 120: return "Trine"
                if aspect_deg == 180: return "Opposition"
        return "None"

    def is_moon_void_of_course(self, jd: float) -> bool:
        moon = self.get_planet_position(jd, swe.MOON)
        curr_sign = moon["sign_index"]
        deg_remaining = 30.0 - moon["degree"]
        
        for hour_offset in [2, 4, 6, 8, 10, 12]:
            future_jd = jd + (hour_offset / 24.0)
            f_moon = self.get_planet_position(future_jd, swe.MOON)
            if f_moon["sign_index"] != curr_sign:
                break
            for p in [swe.SUN, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN]:
                p_pos = self.get_planet_position(future_jd, p)
                asp = self.check_aspect(f_moon["longitude"], p_pos["longitude"])
                if asp in ["Conjunction", "Sextile", "Trine"]:
                    return False
        return deg_remaining < 2.5

# ==========================================
# 3. نظام تقييم الاختيارات (ELECTIONAL SCORING SYSTEM)
# ==========================================

class ElectionalScorer:
    def __init__(self, engine: AstrologicalElectionEngine):
        self.engine = engine

    def evaluate_day(self, year: int, month: int, day: int) -> dict:
        # حساب لقطة منتصف اليوم (للكواكب البطيئة والمؤشرات العامة لليوم)
        jd_noon = self.engine.get_julian_day(year, month, day, 12.0)
        
        # استخراج مواقع الكواكب
        moon = self.engine.get_planet_position(jd_noon, swe.MOON)
        venus = self.engine.get_planet_position(jd_noon, swe.VENUS)
        mars = self.engine.get_planet_position(jd_noon, swe.MARS)
        saturn = self.engine.get_planet_position(jd_noon, swe.SATURN)
        uranus = self.engine.get_planet_position(jd_noon, swe.URANUS)
        neptune = self.engine.get_planet_position(jd_noon, swe.NEPTUNE)
        pluto = self.engine.get_planet_position(jd_noon, swe.PLUTO)
        
        phase = self.engine.get_moon_phase(jd_noon)
        is_voc = self.engine.is_moon_void_of_course(jd_noon)
        
        moon_sign = moon["sign_index"]
        venus_sign = venus["sign_index"]
        
        moon_venus_asp_noon = self.engine.check_aspect(moon["longitude"], venus["longitude"])
        venus_mars_asp = self.engine.check_aspect(venus["longitude"], mars["longitude"])

        # شرطية الاتصال المتناغم بين القمر والزهرة 
        is_moon_venus_harmonious = moon_venus_asp_noon in ["Conjunction", "Sextile", "Trine"]

        # ---------------------------------------------------------
        # التعديل الجديد: فحص الاتصالات السلبية للقمر خلال أوقات دوام العيادات (10 ص - 4 م)
        # سيتم الفحص كل ساعتين: 10:00, 12:00, 14:00, 16:00
        # ---------------------------------------------------------
        has_bad_moon_aspect = False
        malefics_ids = [swe.MARS, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]
        scan_hours = [10.0, 12.0, 14.0, 16.0]
        
        for hour in scan_hours:
            jd_step = self.engine.get_julian_day(year, month, day, hour)
            moon_step = self.engine.get_planet_position(jd_step, swe.MOON)
            
            # 1. فحص الاتصال مع الكواكب النحيسة
            for m_id in malefics_ids:
                m_pos = self.engine.get_planet_position(jd_step, m_id)
                asp = self.engine.check_aspect(moon_step["longitude"], m_pos["longitude"])
                
                if asp in ["Square", "Opposition", "Conjunction"]:
                    has_bad_moon_aspect = True
                    break # خروج من حلقة الكواكب إذا وجدنا اتصال سيء
            
            # 2. فحص اتصال التربيع أو المقابلة مع الزهرة
            venus_step = self.engine.get_planet_position(jd_step, swe.VENUS)
            venus_asp_step = self.engine.check_aspect(moon_step["longitude"], venus_step["longitude"])
            if venus_asp_step in ["Square", "Opposition"]:
                has_bad_moon_aspect = True
            
            if has_bad_moon_aspect:
                break # خروج من حلقة الساعات إذا وجدنا الاتصال السيء
                
        # ---------------------------------------------------------
        # فحص محاق القمر (New Moon) و اكتمال القمر (Full Moon)
        # ---------------------------------------------------------
        moon_sun_diff = phase["angle_diff"]
        is_near_new_moon = (moon_sun_diff <= 37) or (moon_sun_diff >= 323)
        is_near_full_moon = (143 <= moon_sun_diff <= 217)
        is_near_syzygy = is_near_new_moon or is_near_full_moon

        # 1. قص وتزيين الشعر
        hair_score = 50
        if phase["is_waxing"]: hair_score += 20
        if moon_sign in [1, 3, 5, 6, 11]: hair_score += 20
        if moon_sign in [0, 7]: hair_score -= 25
        if venus_sign in [1, 6]: hair_score += 10
        if is_moon_venus_harmonious: hair_score += 20  

        # 2. حقن البوتوكس وتجميل البشرة
        botox_score = 50
        if moon_sign in [0, 1]: botox_score -= 40
        if not venus["is_retrograde"]: botox_score += 15
        if is_moon_venus_harmonious: botox_score += 25  
        if moon_sign in [5, 6]: botox_score += 20

        # 3. العمليات الجراحية التجميلية
        surgery_score = 50
        if not phase["is_waxing"]: surgery_score += 25
        else: surgery_score -= 15
            
        if moon_sign in [0, 1]: surgery_score -= 45
        if mars["is_retrograde"] or venus["is_retrograde"]: surgery_score -= 30
        if is_moon_venus_harmonious: surgery_score += 20  

        # 4. المواعيد الغرامية
        romance_score = 50
        if is_voc: romance_score -= 30
        if venus_mars_asp in ["Trine", "Sextile", "Conjunction"]: romance_score += 30
        elif venus_mars_asp in ["Square", "Opposition"]: romance_score -= 15
        if is_moon_venus_harmonious: romance_score += 25  
        if moon_sign in [1, 3, 6, 11]: romance_score += 15

        # ---------------------------------------------------------
        # تطبيق الخصومات القاسية بناءً على الفحص الزمني الجديد (10ص - 4م)
        # ---------------------------------------------------------
        if has_bad_moon_aspect:
            hair_score -= 65
            botox_score -= 65
            surgery_score -= 65
            romance_score -= 65

        if is_near_syzygy:
            hair_score -= 65
            botox_score -= 65
            surgery_score -= 65
            romance_score -= 40 

        return {
            "day": day,
            "moon_sign": ZODIAC_SIGNS[moon_sign]["ar"],
            "moon_phase": "متزايد (Waxing)" if phase["is_waxing"] else "متناقص (Waning)",
            "is_voc": "نعم" if is_voc else "لا",
            "hair_score": max(0, min(100, hair_score)),
            "botox_score": max(0, min(100, botox_score)),
            "surgery_score": max(0, min(100, surgery_score)),
            "romance_score": max(0, min(100, romance_score)),
        }

# ==========================================
# 4. منشئ تقارير HTML (HTML REPORT GENERATOR)
# ==========================================

class HTMLReportBuilder:
    @staticmethod
    def generate_html(year: int, month: int, results: list) -> str:
        month_name = MONTH_NAMES_AR[month]
        
        best_hair = [str(r["day"]) for r in results if r["hair_score"] >= 65]
        best_botox = [str(r["day"]) for r in results if r["botox_score"] >= 65]
        best_surgery = [str(r["day"]) for r in results if r["surgery_score"] >= 65]
        best_romance = [str(r["day"]) for r in results if r["romance_score"] >= 65]

        rows_html = ""
        for r in results:
            rows_html += f"""
            <tr>
                <td><strong>{r['day']}</strong></td>
                <td>{r['moon_sign']}</td>
                <td>{r['moon_phase']}</td>
                <td><span class="badge {'badge-voc' if r['is_voc']=='نعم' else ''}">{r['is_voc']}</span></td>
                <td style="background-color: rgba(76, 175, 80, {r['hair_score']/100 * 0.3});">{r['hair_score']}%</td>
                <td style="background-color: rgba(156, 39, 176, {r['botox_score']/100 * 0.3});">{r['botox_score']}%</td>
                <td style="background-color: rgba(244, 67, 54, {r['surgery_score']/100 * 0.3});">{r['surgery_score']}%</td>
                <td style="background-color: rgba(233, 30, 99, {r['romance_score']/100 * 0.3});">{r['romance_score']}%</td>
            </tr>
            """

        html_template = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>تقرير الاختيارات الفلكية الشامل - {year}/{month_name}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 30px; line-height: 1.6; }}
                .container {{ max-width: 1100px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 30px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
                .header {{ text-align: center; border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 30px; }}
                .header h1 {{ color: #fbbf24; margin-bottom: 5px; font-size: 28px; }}
                .header p {{ color: #94a3b8; font-size: 16px; }}
                .grid-summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 30px; }}
                .card {{ background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 15px; text-align: center; }}
                .card h3 {{ margin-top: 0; font-size: 14px; color: #cbd5e1; }}
                .card p {{ font-size: 18px; font-weight: bold; color: #38bdf8; margin: 5px 0 0 0; word-wrap: break-word; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
                th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #334155; }}
                th {{ background-color: #0f172a; color: #fbbf24; position: sticky; top: 0; }}
                tr:hover {{ background-color: #334155; }}
                .badge {{ padding: 3px 8px; border-radius: 12px; font-size: 11px; background: #334155; color: #cbd5e1; }}
                .badge-voc {{ background: #991b1b; color: #fca5a5; }}
                .footer {{ text-align: center; margin-top: 40px; font-size: 12px; color: #64748b; border-top: 1px solid #334155; padding-top: 15px; }}
                @media print {{
                    body {{ background: #fff; color: #000; }}
                    .container {{ background: #fff; box-shadow: none; }}
                    th {{ background-color: #f1f5f9; color: #000; }}
                    td, th {{ border-color: #cbd5e1; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>تقرير الاختيارات الفلكية والتجميلية (طاقة عامة)</h1>
                    <p>السنة: {year} | الشهر: {month_name} ({month}) | الطاقة مستندة لحركة القمر، الزهرة، والمريخ</p>
                </div>

                <div class="grid-summary">
                    <div class="card">
                        <h3>✂️ أفضل أيام الشعر</h3>
                        <p>{', '.join(best_hair) if best_hair else 'لا يوجد يوم مثالي جداً'}</p>
                    </div>
                    <div class="card">
                        <h3>💉 حقن البوتوكس والبشرة</h3>
                        <p>{', '.join(best_botox) if best_botox else 'تتطلب مراعاة خاصة'}</p>
                    </div>
                    <div class="card">
                        <h3>🏥 الجراحات التجميلية</h3>
                        <p>{', '.join(best_surgery) if best_surgery else 'توخي الحذر'}</p>
                    </div>
                    <div class="card">
                        <h3>❤️ المواعيد الغرامية</h3>
                        <p>{', '.join(best_romance) if best_romance else 'أيام متوسطة'}</p>
                    </div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>اليوم</th>
                            <th>برج القمر</th>
                            <th>مرحلة القمر</th>
                            <th>خلو المسار</th>
                            <th>قص الشعر</th>
                            <th>البوتوكس</th>
                            <th>الجراحة</th>
                            <th>الغراميات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <div class="footer">
                    تم إنشاء هذا التقرير آلياً بواسطة محرك Swiss Ephemeris وفق قواعد التنجيم الغربي الاختياري Professional Electional Engine.
                </div>
            </div>
        </body>
        </html>
        """
        return html_template

# ==========================================
# 5. واجهة المستخدم streamlit (UI STREAMLIT)
# ==========================================

def main():
    st.set_page_config(
        page_title="نظام الاختيارات الفلكية",
        page_icon="✨",
        layout="wide"
    )

    st.title("✨ نظام الاختيارات الفلكية الاحترافي (طاقة عامة)")
    st.markdown("نظام يوضح أفضل الأيام لتجميل الشعر وحقن البوتوكس وعمليات التجميل والمواعيد الغرامية بناءً على العبور الفلكي العام - برمجة: الفلكي استرو رادار")

    st.sidebar.header("⚙️ إعدادات المدخلات")
    
    selected_year = st.sidebar.selectbox("اختر السنة", list(range(2026, 2047)), index=0)
    
    selected_month = st.sidebar.selectbox(
        "اختر الشهر", 
        list(range(1, 13)), 
        format_func=lambda x: f"{x} - {MONTH_NAMES_AR[x]}"
    )
    
    # تم إزالة حقل "اختر البرج المستهدف" لتصبح الطاقة عامة

    if st.sidebar.button("🚀 تشغيل التحليل الفلكي", type="primary"):
        engine = AstrologicalElectionEngine()
        scorer = ElectionalScorer(engine)
        
        num_days = calendar.monthrange(selected_year, selected_month)[1]
        monthly_results = []
        
        progress_bar = st.progress(0)
        for day in range(1, num_days + 1):
            # تمرير السنة والشهر واليوم فقط للمحرك
            res = scorer.evaluate_day(selected_year, selected_month, day)
            monthly_results.append(res)
            progress_bar.progress(day / num_days)

        st.success("تم الحساب بنجاح وفق الخوارزميات الفلكية الدقيقة والمحدثة للطاقة العامة!")

        df = pd.DataFrame(monthly_results)
        df_display = df.rename(columns={
            "day": "اليوم",
            "moon_sign": "برج القمر",
            "moon_phase": "مرحلة القمر",
            "is_voc": "خلو المسار",
            "hair_score": "قص الشعر (100)",
            "botox_score": "البوتوكس (100)",
            "surgery_score": "الجراحة (100)",
            "romance_score": "الغراميات (100)"
        })

        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("📊 جدول التقييم اليومي المباشر")
            st.dataframe(df_display, width='stretch')

        with col2:
            st.subheader("💡 ملخص التوصيات")
            
            top_hair = df[df["hair_score"] >= 65]["day"].tolist()
            top_botox = df[df["botox_score"] >= 65]["day"].tolist()
            top_surgery = df[df["surgery_score"] >= 65]["day"].tolist()
            top_romance = df[df["romance_score"] >= 65]["day"].tolist()

            st.info(f"**✂️ أفضل أيام الشعر:** {top_hair if top_hair else 'لا توجد ذروة مرتفعة'}")
            st.warning(f"**💉 أفضل أيام البوتوكس:** {top_botox if top_botox else 'تتطلب حذراً'}")
            st.error(f"**🏥 أفضل أيام الجراحة:** {top_surgery if top_surgery else 'تتطلب حذراً'}")
            st.success(f"**❤️ أفضل أيام المواعيد:** {top_romance if top_romance else 'أيام متوسطة'}")

        html_content = HTMLReportBuilder.generate_html(
            selected_year, selected_month, monthly_results
        )

        file_name = f"{selected_year}_{selected_month:02d}_General_Energy.html"

        st.markdown("---")
        st.subheader("📥 تحميل التقرير النهائي (HTML / PDF)")
        st.download_button(
            label=f"💾 تحميل التقرير النهائي ({file_name})",
            data=html_content,
            file_name=file_name,
            mime="text/html"
        )

if __name__ == "__main__":
    main()