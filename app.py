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
    
    st.write("Добро пожаловать в приложение поиска слов по Jupyter ноутбукам 📂")
    
    st.write("""**Статистика ФБМФ**: прошлые задания лежат в ThetaHat.Материалы | NDA | доступ = ph@ds => Phystech@DataScience => **Ph@DS ВЕСНА 2024**""")
    st.write("""**Ph@ds**: прошлые задания лежат в ThetaHat.Материалы | NDA | доступ = ph@ds => Phystech@DataScience => **Ph@DS ОСЕНЬ 2023**""")

    # Путь к локальной папке с индексами
    index_base_dir = "index"

    st.title("Поиск по ноутбукам")

    # Проверяем, что папка с индексами существует
    if os.path.exists(index_base_dir):
        # Получаем список папок внутри `index`
        index_names = [name for name in os.listdir(index_base_dir) if os.path.isdir(os.path.join(index_base_dir, name))]

        # Если найдены подкаталоги, выводим их для выбора
        if index_names:
            selected_index = st.selectbox("Выберите папку для поиска", index_names)

            # Полный путь к выбранному индексу
            selected_index_path = os.path.join(index_base_dir, selected_index)

            # Инициализация поисковика
            index_searcher = IndexSearcher(selected_index_path)

            # Поле для ввода слова для поиска
            search_word = st.text_input("Введите слово для поиска")

            # Кнопка для поиска
            if st.button("Искать") and search_word:
                results = index_searcher.search(search_word)
                if results:
                    st.write("Результаты поиска:")
                    for path in results:
                        st.write(path)  # Можно изменить на ссылку, если нужно
                else:
                    st.write("Совпадений не найдено.")

            # Кнопка для закрытия поисковика после завершения
            if st.button("Закрыть поисковик"):
                index_searcher.close()
                st.write("Поисковик закрыт.")
        else:
            st.warning("В папке `index` не найдено папок с индексами.")
    else:
        st.error("Папка `index` не найдена. Убедитесь, что структура проекта правильная.")
