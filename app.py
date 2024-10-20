import streamlit as st
from utils.clustering_comments_dbscan import *
import sys
import os

# Добавляем путь к папке utils в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
st.title("Кластеризация комментариев")

uploaded_file = st.file_uploader("Загрузка таблиц", type=['xlsx'],accept_multiple_files=False,key="fileUploader")

if uploaded_file is not None:
    # Сохраняем файл на диск
    with open(f"./temp/{uploaded_file.name}", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Получаем путь к сохраненному файлу
    file_path = f"./temp/{uploaded_file.name}"
    comment_column_i = "Комментарий"
    comment_column_o = "Индивидуальный комментарий"
    reviewer_column = "Проверяющий"
    student_column = "Студент"
    
    main(file_path, student_column, reviewer_column, comment_column_i, comment_column_o)
