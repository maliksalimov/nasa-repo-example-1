# Streamlit oyuncaq qutusudur. Onu çağırırıq və qısaca "st" adlandırırıq.
import streamlit as st

# Səhifənin ən yuxarısına böyük hərflərlə ad yazırıq, kitabın üz qabığındakı ad kimi.
st.title("Space App")

# Ekrana düymə qoyuruq. "Əgər uşaq düyməni basdısa..." deyə soruşuruq.
if st.button("Bas"):
    # Düymə basılıbsa, ekrana salam yazırıq. Sətir içəri çəkilib, çünki yalnız basanda işləyir.
    st.write("SALAM DÜNYA")
