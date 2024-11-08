import streamlit as st
import os
import tempfile
from git import Repo
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
    st.write("На Яндекс Диске скачай папки с ноутбуками.")
    # Ввод пути к папке и слова для поиска
    # Загружаем несколько файлов
    # Ввод пути к папке
    # Ввод данных для клонирования приватного репозитория
    repo_url = st.text_input("Введите URL Git-репозитория с ноутбуками")
    token = st.text_input("Введите GitHub токен (для приватного репозитория)", type="password")
    search_word = st.text_input("Введите слово для поиска", "")

    if st.button("Искать"):
        if repo_url and token and search_word:
            # Создаем временную директорию для репозитория
            temp_folder = tempfile.mkdtemp()
            repo_folder = os.path.join(temp_folder, "repo")

            try:
                # Формируем URL с токеном для доступа
                auth_repo_url = repo_url.replace("https://", f"https://{token}@")
                
                # Клонируем репозиторий
                Repo.clone_from(auth_repo_url, repo_folder)
                st.write(f"Репозиторий успешно загружен в папку: {repo_folder}")

                # Выполняем поиск слова в ноутбуках
                results = search_in_notebooks(repo_folder, search_word)
                
                if results:
                    st.write("Результаты поиска:")
                    for result in results:
                        st.write(result)
                else:
                    st.write("Совпадений не найдено.")
            except Exception as e:
                st.write(f"Ошибка при клонировании репозитория: {e}")
        else:
            st.warning("Пожалуйста, укажите URL репозитория, токен и слово для поиска.")