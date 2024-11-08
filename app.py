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
            styled_data = clustered_data.style.applymap(highlight_tasks_and_clusters)

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
    st.write("#### Подготовка файлов:")
    st.write("""
    На Яндекс Диске скачайте папки с ноутбуками.
    """)

    # Список с элементами
    st.markdown("""
    - **Статистика ФБМФ:** ThetaHat. Материалы | NDA | доступ = ph@ds => Phystech@DataScience => Ph@DS ВЕСНА 2024
    - **Ph@DS:** ThetaHat. Материалы | NDA | доступ = ph@ds => Phystech@DataScience => Ph@DS ОСЕНЬ 2023
    - **DS-поток, 3 курс:** ThetaHat. Материалы | NDA | доступ = 4 и 5+ => 3 курс, DS-поток
    """)


    st.write("#### Введите данные:")
    st.markdown("""
    - Щёлкните правой кнопкой мыши по папке и выберите **«Копировать путь»**.
    - Вставьте скопированный путь в строку ниже.
""")
    # Ввод пути к папке с ноутбуками
    folder_path = st.text_input("Введите путь к папке с ноутбуками", placeholder=r"Например: C:\Users\имя_пользователя\Рабочий стол\Ph@DS ВЕСНА 2024")

    st.markdown("""
    - Введите слово для поиска
""")
    # Ввод слова для поиска
    search_word = st.text_input("Введите слово для поиска", placeholder="Введите искомое слово: например, тета")

    st.write("#### Запуск поиска")
    st.markdown("""
    - Нажмите на Индексацию, чтобы создать поисковый индекс для папки с ноутбуками — это нужно сделать только один раз для каждой новой папки.
""")
    # Проверка наличия индекса
    if os.path.exists("index"):
        st.write("✅Индекс уже создан. Можно начать поиск.")
    else:
        st.write("Индекс еще не создан. Чтобы начать поиск, сначала индексируйте ноутбуки.")

    # Кнопка для индексации
    if st.button("Индексировать ноутбуки"):
        if folder_path:
            if os.path.isdir(folder_path):  # Проверка, что это действительно папка
                # Индексируем ноутбуки в указанной папке
                create_index(folder_path)
                st.write("Индексирование завершено! Теперь вы можете искать.")
            else:
                st.warning("Пожалуйста, укажите корректный путь к папке.")
        else:
            st.warning("Пожалуйста, укажите путь к папке для индексирования.")

    st.markdown("""
    - Нажмите Искать
""")
    # Кнопка для поиска
    if st.button("Искать"):
        if search_word:
            results = search_in_index(search_word)
            
            if results:
                st.write("Результаты поиска:")
                for result in results:
                    st.write(result)
            else:
                st.write("Совпадений не найдено.")
        else:
            st.warning("Пожалуйста, укажите слово для поиска.")