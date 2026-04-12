import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. CẤU HÌNH API KEY (Sử dụng API của bạn)
API_KEY = "AIzaSyBXa1_zxKW2yqEqNiyDrp1rUtciL6cZ6Lw"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. CẤU HÌNH TRANG
st.set_page_config(page_title="Chatbot Dự đoán Điểm chuẩn", page_icon="🎓", layout="wide")
st.title("🎓 Trợ lý AI Tư vấn Tuyển sinh Đại học")

@st.cache_data 
def load_data():
    try:
        data = pd.read_csv("dataset_2026_updated.csv")
        # Đổi tên các cột sang Tiếng Việt ngay từ đầu để đồng bộ [cite: 58]
        column_mapping = {
            'year': 'Năm',
            'university': 'Trường Đại học',
            'major': 'Ngành học',
            'quota': 'Chỉ tiêu',
            'applicants': 'Số lượng ĐK',
            'cutoff': 'Điểm chuẩn',
            'subject_group': 'Tổ hợp môn',
            'admission_method': 'Phương thức'
        }
        data = data.rename(columns=column_mapping)
        return data
    except FileNotFoundError:
        st.error("Không tìm thấy file 'dataset_2026_updated.csv'. Vui lòng để file này cùng thư mục với app.py!")
        return None

df = load_data()

# KHỞI TẠO BIẾN NGỮ CẢNH
context_data = ""

# 3. SIDEBAR - ĐIỀU KHIỂN
with st.sidebar:
    st.header("⚙️ Cài đặt hệ thống")
    if df is not None:
        tab_search, tab_compare = st.tabs(["🔍 Tra cứu", "⚖️ So sánh"])
        
        with tab_search:
            st.subheader("Tra cứu chi tiết")
            universities = ["Tất cả"] + sorted(df['Trường Đại học'].unique().tolist())
            selected_uni = st.selectbox("Chọn Trường:", universities)
            
            if selected_uni != "Tất cả":
                majors = ["Tất cả"] + sorted(df[df['Trường Đại học'] == selected_uni]['Ngành học'].unique().tolist())
            else:
                majors = ["Tất cả"] + sorted(df['Ngành học'].unique().tolist())
                
            selected_major = st.selectbox("Chọn Ngành:", majors)

            if selected_uni != "Tất cả" and selected_major != "Tất cả":
                f_df = df[(df['Trường Đại học'] == selected_uni) & (df['Ngành học'] == selected_major)].sort_values(by='Năm')
                st.line_chart(f_df.set_index('Năm')['Điểm chuẩn'])
                
                latest_info = f_df.iloc[-1]
                st.subheader("📋 Thông tin năm 2026")
                
                to_hop = latest_info.get('Tổ hợp môn', 'A00, A01, D01')
                p_thuc = latest_info.get('Phương thức', 'Xét điểm thi THPT')
                c_tieu = latest_info.get('Chỉ tiêu', 'Đang cập nhật')
                
                st.write(f"**🔹 Tổ hợp:** {to_hop}")
                st.write(f"**🔹 Phương thức:** {p_thuc}")
                st.write(f"**🔹 Chỉ tiêu:** {c_tieu}")
                
                # Cập nhật ngữ cảnh cho AI xử lý [cite: 61, 62]
                context_data = f"DỮ LIỆU {selected_major} TẠI {selected_uni}:\n"
                context_data += f"- Tổ hợp: {to_hop}\n- Phương thức: {p_thuc}\n"
                for _, row in f_df.iterrows():
                    quota_val = row['Chỉ tiêu'] if row['Chỉ tiêu'] > 0 else 1
                    ratio = round(row['Số lượng ĐK'] / quota_val, 2)
                    context_data += f"- Năm {row['Năm']}: {row['Điểm chuẩn']} (Tỷ lệ chọi 1/{ratio})\n"

        with tab_compare:
            st.subheader("So sánh ngành")
            u_list = sorted(df['Trường Đại học'].unique().tolist())
            comp_uni = st.multiselect("Chọn 2 trường:", u_list, max_selections=2)
            c_major = st.selectbox("Ngành so sánh:", sorted(df['Ngành học'].unique().tolist()), key="c_major")
            
            if len(comp_uni) == 2:
                comp_df = df[(df['Trường Đại học'].isin(comp_uni)) & (df['Ngành học'] == c_major)]
                if not comp_df.empty:
                    st.line_chart(comp_df.pivot(index='Năm', columns='Trường Đại học', values='Điểm chuẩn'))

        st.divider()
        st.subheader("🎯 Đề xuất nguyện vọng")
        user_score = st.number_input("Nhập điểm của bạn:", 0.0, 30.0, 25.0, step=0.1)
        
        # FIX LỖI HIỂN THỊ TẠI ĐÂY
        if st.button("Gợi ý ngành phù hợp"):
            latest_year = df['Năm'].max()
            # Lọc các ngành năm 2026 có điểm chuẩn phù hợp [cite: 63]
            recommendations = df[(df['Năm'] == latest_year) & (df['Điểm chuẩn'] <= user_score + 0.5)].sort_values(by='Điểm chuẩn', ascending=False)
            
            if not recommendations.empty:
                st.write(f"**Các ngành phù hợp với {user_score} điểm:**")
                # Hiển thị bảng trực tiếp ra Sidebar
                st.dataframe(recommendations[['Trường Đại học', 'Ngành học', 'Điểm chuẩn']].head(10), hide_index=True)
                
                # Gửi danh sách này vào bộ nhớ AI để tư vấn thêm [cite: 62]
                rec_text = recommendations[['Trường Đại học', 'Ngành học', 'Điểm chuẩn']].head(5).to_string(index=False)
                context_data += f"\nDANH SÁCH GỢI Ý CHO {user_score} ĐIỂM:\n{rec_text}"
            else:
                st.warning("Chưa có ngành nào phù hợp mức điểm này.")

# 4. GIAO DIỆN CHAT
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Xin chào! Mình là AI tư vấn tuyển sinh. Bạn muốn tra cứu điểm chuẩn hay cần mình gợi ý trường phù hợp với điểm của bạn?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_query := st.chat_input("Nhập câu hỏi..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    prompt = f"""
    Bạn là chuyên gia tư vấn tuyển sinh đại học.
    Dữ liệu lịch sử: {context_data}
    Điểm của học sinh: {user_score}
    
    Yêu cầu:
    1. Trả lời dựa trên dữ liệu thật (Điểm chuẩn, tỷ lệ chọi, tổ hợp môn).
    2. Tư vấn chiến thuật dựa trên mức điểm {user_score}.
    3. Câu hỏi: "{user_query}"
    """

    with st.chat_message("assistant"):
        try:
            with st.spinner("Đang phân tích dữ liệu..."):
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Lỗi API: {e}")