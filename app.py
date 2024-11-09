import streamlit as st
import os
from utils.clustering_comments_dbscan import *  # Импортируем модуль кластеризации
from utils.search_notebooks import *  # Импортируем функцию поиска по ноутбукам

st.title("Инструменты для таблиц")
# Разделение интерфейса на вкладки
tab1, tab2 = st.tabs(["Кластеризация комментариев", "Поиск по ноутбукам"])

# --- Кластеризация комментариев ---
with tab1:
    # Добавляем приветственное сообщение 
    st.write("Добро пожаловать в приложение для кластеризации комментариев! 👋🏻")
    st.write("📄 Для начала скачайте таблицу проверки в формате Excel (.xlsx) на Google Диске.")
    st.write("⬇️ Загрузите ее по кнопке ниже, и система автоматически разделит комментарии на кластеры.")
    uploaded_file = st.file_uploader("Загрузка таблиц", type=['xlsx'],accept_multiple_files=False,key="fileUploader")

    if uploaded_file is not None:
        # Сохраняем файл на диск
        with open(f"./temp/{uploaded_file.name}", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Получаем путь к сохраненному файлу
        file_path = f"./temp/{uploaded_file.name}"
        clustered_data = main(file_path, "Студент", "Проверяющий", "Индивидуальный комментарий", "Комментарий")
        
        # Проверяем, что функция вернула результат
        if clustered_data is not None:
            # Определяем функцию для стилизации
            def highlight_tasks_and_clusters(val):
                # Если значение содержит '---', выделяем его как название задачи
                if '---' in str(val):
                    return 'background-color: #ccffcc;'  # Светло-зелёный фон
                # Убираем лишнюю проверку для кластеров
                return ""  # Оставляем остальные ячейки без изменений
            styled_data = clustered_data.style.map(highlight_tasks_and_clusters)

            # Применяем стилизацию
            styled_data = clustered_data.style.map(highlight_tasks_and_clusters)

            # Применяем автоширину к столбцам
            col_widths = {
                col: max(clustered_data[col].astype(str).map(len).max(), len(col)) + 5
                for col in clustered_data.columns
            }
            
            # Устанавливаем ширину столбцов
            for col, width in col_widths.items():
                styled_data.set_properties(subset=[col], **{'width': f'{width}ch'})

            st.write("Результаты кластеризации:")
            st.table(styled_data)
            
            # Отображаем DataFrame с кластеризацией
        else:
            st.write("Ошибка: Кластеризация не вернула данных.")

# --- Поиск по ноутбукам ---
with tab2:
    # Список с индексами, которые уже созданы
    index_names = {
        "Статистика ФБМФ (Ph@DS ВЕСНА 2024)": "statistics_fbmf_spring_2024",
        "Ph@DS ОСЕНЬ 2023": "phds_fall_2023"
    }
    st.write("Добро пожаловать в приложение поиска слов по Jupyter ноутбукам 📂")
    st.write("#### Подготовка файлов:")
    st.write("""На Яндекс Диске скачайте папки с ноутбуками.""")

    st.write("#### Выберите папку с индексом:")

    # Отображаем список папок с индексами
    selected_index_name = None
    for label, folder_name in index_names.items():
        if st.checkbox(label, key=folder_name):
            selected_index_name = folder_name

    if selected_index_name:
        st.write(f"Вы выбрали индекс: {selected_index_name}")
    
    st.write("#### Введите данные:")

    # Ввод слова для поиска
    search_word = st.text_input("Введите слово для поиска", placeholder="Введите искомое слово: например, тета")

    st.write("#### Запуск поиска")

    # Кнопка для поиска
    if st.button("Искать"):
        if selected_index_name:
            if search_word:
                results = search(selected_index_name, search_word)
                
                if results:
                    st.write("Результаты поиска:")
                    for result in results:
                        st.write(result)
                else:
                    st.write("Совпадений не найдено.")
            else:
                st.warning("Пожалуйста, укажите слово для поиска.")
        else:
            st.warning("Пожалуйста, выберите папку с индексом.")
