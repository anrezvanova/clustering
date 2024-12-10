
import streamlit as st
import requests
from streamlit_sortables import sort_items
import os
from io import BytesIO
from utils.clustering_comments_dbscan import *  # Импортируем модуль кластеризации
from utils.search_notebooks import *  # Импортируем функцию поиска по ноутбукам
from utils.results_students import * # Импортируем модуль агрегации результатов
import re

db_username = st.secrets["username"]
db_token = st.secrets["token"]

# Задаем URL для получения репозиториев
url = "https://api.github.com/user/repos"

# Заголовок для авторизации
headers = {"Authorization": f"token {db_token}"}

# Выполняем запрос к GitHub API с использованием токена
response = requests.get(url, headers=headers)

# Проверяем статус ответа
try:
    db_username = st.secrets["username"]
    db_token = st.secrets["token"]
    st.write(f"GitHub username: {db_username}")
    st.write(f"GitHub token: {db_token[:5]}...")  # Частичное отображение токена
except KeyError as e:
    st.error(f"Ошибка: отсутствует ключ {e}")
st.markdown(
    """
    <style>
        #загрузчик
        [data-testid="stFileUploaderDropzoneInstructions"] div::before {color:black; font-size: 0.9em; content:"Загрузите или перетяните файлы сюда"}
        [data-testid="stFileUploaderDropzoneInstructions"] div span{display:none;}
        [data-testid="stFileUploaderDropzoneInstructions"] div::after {color:black; font-size: .8em; content:"Загрузите или перетяните файлы сюда\AЛимит 200MB на файл";white-space: pre; /* Для переноса строки */}
        [data-testid="stFileUploaderDropzoneInstructions"] div small{display:none;}
        [data-testid="stFileUploaderDropzoneInstructions"] button{display:flex;width: 30%; padding: 0px;}
        [data-testid="stFileUploaderDropzone"]{background-color:white; border-radius: 15px; /* Скругленные углы */border: 2px solid #4985c1; /* Прозрачная граница для эффекта */}
    
       /* Основной контейнер */
    [data-baseweb="select"] {
        background-color: #4985c1 !important; /* Голубой фон для основного контейнера */
        color: black !important; /* Черный текст */
        border: 2px solid #4985c1; /* Граница совпадает с фоном */
        border-radius: 10px; /* Скругленные углы */
        padding: 0px; /* Убираем внутренние отступы */
        overflow: hidden; /* Убираем возможные выступающие элементы */
    }

    /* Вложенный элемент, отвечающий за белую полосу */
    [data-baseweb="select"] .st-cg {
        background-color: transparent !important; /* Убираем белый фон */
        border: none !important; /* Убираем границу */
        padding: 0 !important; /* Убираем отступы */
    }

    /* Текст внутри select */
    [data-baseweb="select"] .st-d8 {
        color: black !important; /* Белый текст на голубом фоне */
        padding: 0 !important; /* Убираем лишние отступы */
    }

    /* Для input внутри select */
    [data-baseweb="select"] input {
        background-color: transparent !important; /* Прозрачный фон */
        
        border: none !important; /* Убираем рамку */
        padding: 0 !important; /* Минимизируем отступы */
    }

    /* Для SVG и иконки стрелки */
    [data-baseweb="select"] svg {
        fill: black !important; /* Черная иконка стрелки */
    }
    </style>
    """,
    unsafe_allow_html=True
    )
# CSS для уменьшения размера кнопок и текста
st.markdown("""
    <style>
    .compact-list {
        font-size: 0.85em;
        padding: 0.3em 0;
        margin-bottom: 0.3em;
    }
    .stButton > button {
        font-size: 0.65em !important;
        padding: 0.2em 0.5em !important;
        margin-left: 5px !important;
    }
    </style>
""", unsafe_allow_html=True)
def display_dataframe_table(df):
    
    # Отображаем стиль с границей через markdown
    # Стилизация для первых двух строк
    
    # Если у DataFrame есть многоуровневые колонки
    if isinstance(df.columns, pd.MultiIndex):
        # Извлекаем уровни колонок
        top_level = df.columns.get_level_values(0)  # Первый уровень
        second_level = df.columns.get_level_values(1)  # Второй уровень

        # Добавляем новые строки, которые будут содержать уровни колонок
        top_row = pd.DataFrame([top_level.values], columns=df.columns, index=["Для копирования"])
        second_row = pd.DataFrame([second_level.values], columns=df.columns, index=["Для копирования"])

        # Конкатенируем эти строки к оригинальному DataFrame
        # Сохраняем исходную индексацию студентов и добавляем строки с уровнями
        df_with_levels = pd.concat([top_row, second_row, df], axis=0)
        df_with_levels= df_with_levels.apply(
        lambda col: col.map(
            lambda x: (
                str(x).replace('.', ',') if isinstance(x, float) and x % 1 != 0 
                else str(int(x)) if isinstance(x, (int, float)) 
                else str(x)
            )
        )
    )
    else:
        # Если нет многоуровневых колонок, просто отображаем DataFrame
        df_with_levels = df.apply(
        lambda col: col.map(
            lambda x: (
                str(x).replace('.', ',') if isinstance(x, float) and x % 1 != 0 
                else str(int(x)) if isinstance(x, (int, float)) 
                else str(x)
            )
        )
    )
    # Отображаем таблицу с уровнями в заголовках
    st.dataframe(df_with_levels,use_container_width=True)


# Функция для сортировки файлов по номеру и тексту
def sort_files_by_number(files):
    def extract_key(file_name):
        # Регулярное выражение для разделения на части: текст и число
        match = re.match(r'(.*?)(\d+)(.*)', file_name)
        if match:
            prefix, number, suffix = match.groups()
            return (prefix.strip(), int(number), suffix.strip())
        else:
            # Если формат не совпадает, использовать весь файл как ключ
            return (file_name, 0, "")
    
    # Сортировка по извлеченным ключам
    return sorted(files, key=lambda f: extract_key(f.name))



st.title("Инструменты для таблиц")
# Разделение интерфейса на вкладки
tab1, tab2, tab3 = st.tabs(["Кластеризация комментариев", "Поиск по ноутбукам", "Агрегация результатов"])


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

    st.subheader("Поиск по ноутбукам")

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

# --- Успеваемость ---
with tab3:

    st.write("Добро пожаловать в приложение обработки результатов студентов за семестр!👋🏻 ")
    
    st.markdown("""
    С его помощью вы можете:
    - Собрать баллы по всем заданиям 
    - Анализировать ответы на вопросы в боте 
    - Отслеживать посещаемость занятий 
    """)

    # Радио-кнопка для выбора блока
    selected_block = st.selectbox(
        "Выберите блок для работы:",
        ("Агрегация баллов", "Обработка вопросов", "Посещаемость")
    )
    st.divider()

    # --- Блок 1: Агрегация баллов ---
    if selected_block == "Агрегация баллов":
      
        st.header("Агрегация баллов")
        st.markdown("""
        
        Вам понадобятся:

        1. 📥 Файл **Пользователи.xlsx** с Яндекс.Диска.
        2. 📁 Папка **Проверка ДЗ** с таблицами проверок с Google Диска.
        """)

        
        # Загрузка студентов
        all_students = []
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник', 'Тест Никита', 'Тест Фотофон']

        st.markdown("### Пользователи")
        st.markdown("""
        Загрузите список студентов из файла *Пользователи.xlsx* или введите их вручную.
        """)
        
        option = st.radio("Выберите:", ("Загрузить из таблицы", "Ввести вручную"))
        
        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"])
            if uploaded_file:
                all_students = get_students_from_file(uploaded_file)   
         
        else:
            # Ручной ввод студентов
            students_input = st.text_area("Введите имена студентов, разделяя их новой строкой:")
            all_students = students_input.split("\n")
            all_students = [s.strip() for s in all_students if s.strip()]
            
        col1, col2 = st.columns([3, 2])
        if all_students:
            
            excluded_detected = [s for s in all_students if s in excluded_students]
            valid_students = [s for s in all_students if s not in excluded_students]

            # Подсвечивание и возврат исключённых
            if excluded_detected:

                st.warning(f"Исключены тестовые пользователи: {', '.join(excluded_detected)}. Вы можете их вернуть.")
                
                # Возможность вернуть исключённых
                returned_users = []  # Перенесли сюда инициализацию
                with col2:
                    with st.expander("### Список тестовых пользователей:"):
                        for user in excluded_detected:
                            if st.checkbox(f"Вернуть {user}", key=f"return_{user}"):
                                returned_users.append(user)

                # Добавляем возвращённых пользователей к основному списку
                valid_students.extend(returned_users)
            with col1:
                # Обновляем текст в редакторе после возврата исключённых
                with st.expander("Cписок студентов"):
                    # Перезаписываем текст редактора с учётом возвращённых
                    editable_students = st.text_area(
                        "Отредактируйте список студентов:", 
                        "\n".join(valid_students)  # Отображаем обновлённый список
                    )
                    valid_students = editable_students.split("\n")
                    valid_students = [s.strip() for s in valid_students if s.strip()]
                
            if valid_students:

                st.subheader('Баллы')
                st.markdown("""
                Загрузите таблицы проверок из папки *Проверка ДЗ* .
                """)
    
                # Функция для кэширования загрузки данных
                @st.cache_data(ttl=3600)
                def load_and_extract_sum_types(file):
                    try:
                        # Извлечение уникальных типов сумм из файла
                        sum_types = pd.read_excel(file, sheet_name='Список задач', skiprows=3, usecols="C:D", header=None).dropna(how='all')
                        return sum_types.iloc[:, 0].dropna().astype(str).tolist()
                    except Exception as e:
                        st.error(f"Ошибка при обработке файла {file.name}: {e}")
                        return []

                # Инициализация сессий    
                if "previous_files" not in st.session_state:  
                    st.session_state["previous_files"] = []
                if "good_cols" not in st.session_state:
                    st.session_state["good_cols"] = []
                if "display_mode" not in st.session_state:
                    st.session_state["display_mode"] = "Все типы сумм"
                if "aggregation_needs_update" not in st.session_state: # Флаг обновления
                    st.session_state["aggregation_needs_update"] = False    
                if "result_table_main" not in st.session_state:
                    st.session_state["result_table_main"] = None
                if "max_ball_table_main" not in st.session_state:
                    st.session_state["max_ball_table_main"] = None
                if "uploader_key" not in st.session_state:
                    st.session_state["uploader_key"] = 0    
                if "show_sort_expander" not in st.session_state:
                    st.session_state["show_sort_expander"] = False
                if "main_task_files_sorted" not in st.session_state:
                    st.session_state["main_task_files_sorted"] = []

                main_task_files = st.file_uploader("Загрузите файлы", type=["xlsx"], accept_multiple_files=True,key=f"uploader_{st.session_state['uploader_key']}")

                if main_task_files:
                    sorted_files = sort_files_by_number(main_task_files)

                    # Проверка, изменились ли файлы
                    new_file_names = [file.name for file in main_task_files]
                    previous_file_names = [file.name for file in st.session_state["previous_files"]]
                    if new_file_names != previous_file_names:
                        st.session_state["previous_files"] = main_task_files
                        
                    # Основной макет с кнопками
                    col1, col2 = st.columns([8, 2])
                    with col1:
                        with st.expander("✏️Порядок файлов", expanded=True):
                            st.markdown("Список отсортирован автоматически. Перетащите файл, чтобы поменять порядок. ")
                            # Создаем список имен файлов с индексами
                            file_names_with_index = [f"{i + 1}: {file.name}" for i, file in enumerate(sorted_files)]
                            ordered_file_names_with_index = sort_items(file_names_with_index, direction="vertical", key="sortable_list")

                            # Извлекаем индексы из отсортированных имен
                            ordered_indices = [int(name.split(":")[0]) - 1 for name in ordered_file_names_with_index]

                            # Обновляем список файлов на основе отсортированных индексов
                            new_finish_sorted = [sorted_files[i] for i in ordered_indices]
                            finish_sorted = [file for file in st.session_state["main_task_files_sorted"]]
                            if new_finish_sorted != finish_sorted:
                                st.session_state["main_task_files_sorted"] = [sorted_files[i] for i in ordered_indices]
                   
                    with col2:
                        # Кнопка для очистки всех файлов
                        if st.button("Очистить все"):
                            st.session_state["uploader_key"] += 1

                    # Извлечение уникальных типов сумм из файлов
                    all_sum_types = set()
                    for task_file in st.session_state["previous_files"]:
                        all_sum_types.update(load_and_extract_sum_types(task_file))

                    st.session_state["good_cols"] = list(all_sum_types)

                    # Отображаем и позволяем редактировать список столбцов
                    new_good_cols = st.text_area("Типы сумм из загруженных таблиц. Вы можете их редактировать(через запятую).", value=", ".join(st.session_state["good_cols"]))
                        
                    # Преобразуем введенный список в список столбцов
                    updated_good_cols = [col.strip() for col in new_good_cols.split(",")]
                    # Проверяем, изменились ли типы сумм
                    if updated_good_cols != st.session_state["good_cols"]:
                        st.session_state["good_cols"] = updated_good_cols
                
                        st.session_state["aggregation_needs_update"] = True


                    # Кнопка для выполнения агрегации
                    if st.button("Выполнить агрегацию"):
                        with st.spinner("Выполняется агрегация..."):
                            # Проверяем, нужно ли обновлять данные (если флаг False, то просто выполняем агрегацию)
                            if st.session_state["aggregation_needs_update"]:
                                st.session_state["result_table_main"] = aggregate_scores(
                                    valid_students, st.session_state["main_task_files_sorted"], st.session_state["good_cols"]
                                )
                                st.session_state["max_ball_table_main"] = aggregate_max_ball_table(
                                    st.session_state["main_task_files_sorted"], st.session_state["good_cols"]
                                )
                                st.session_state["aggregation_needs_update"] = False
                            else:
                                # Если флаг False, просто выполняем агрегацию без изменений флага
                                st.session_state["result_table_main"] = aggregate_scores(
                                    valid_students, st.session_state["main_task_files_sorted"], st.session_state["good_cols"]
                                )
                                st.session_state["max_ball_table_main"] = aggregate_max_ball_table(
                                    st.session_state["main_task_files_sorted"], st.session_state["good_cols"]
                                )

            
                    # Показываем переключатели только если данные есть
                    if (
                        st.session_state["result_table_main"] is not None
                        and st.session_state["max_ball_table_main"] is not None
                    ):
                        # Переключатель режима отображения
                        st.session_state["display_mode"] = st.radio(
                            'Выберите режим отображения', 
                            options=["Все типы сумм", "По отдельным типам сумм"], 
                            index=["Все типы сумм", "По отдельным типам сумм"].index(st.session_state["display_mode"]),
                            help=(
                                'Каждый режим позволяет отображать типы сумм по-разному, чтобы копировать данные было быстрее.\n\n'
                                '"Все типы сумм" — подходит для  ph@ds, Статистики ФБМФ и ВвАД. \n\n'
                                '"По отдельным типам сумм" — подходит для ds3-потока и ds4-потока. '
                            )
                        )
                        
                        # Режим отображения: Все типы сумм
                        if st.session_state["display_mode"] == "Все типы сумм":

                            # Вывод таблицы баллов
                            st.subheader(f"Таблица баллов — Все типы сумм")
                            display_dataframe_table(st.session_state["result_table_main"])

                            # Создание таблицы максимальных баллов
                            valid_columns = [
                                (file, sum_type)
                                for file in st.session_state["max_ball_table_main"].columns
                                for sum_type in st.session_state["good_cols"]
                                if sum_type in st.session_state["max_ball_table_main"].index and not pd.isna(
                                    st.session_state["max_ball_table_main"].at[sum_type, file]
                                )
                            ]

                            if valid_columns:
                                # Формируем финальную таблицу
                                multiindex_columns = pd.MultiIndex.from_tuples(valid_columns, names=["Файл", "Тип суммы"])
                                values = [
                                    st.session_state["max_ball_table_main"].at[sum_type, file]
                                    for file, sum_type in valid_columns
                                ]
                                final_table = pd.DataFrame([values], columns=multiindex_columns)
                                
                                # Вывод таблицы максимальных баллов
                                st.subheader(f"Таблица макс.баллов — Все типы сумм")
                                display_dataframe_table(final_table)

                                # Генерация файла для скачивания
                                result_output_all = BytesIO()
                                with pd.ExcelWriter(result_output_all, engine='xlsxwriter') as writer:
                                    # Подготовка данных для записи
                                    result_table_download = st.session_state["result_table_main"].copy()
                                    max_ball_table_download = final_table.copy()

                                    # Форматирование колонок
                                    result_table_download.columns = pd.MultiIndex.from_tuples([tuple(map(str, col)) if isinstance(col, tuple) else (col,) for col in result_table_download.columns])
                                    max_ball_table_download.columns = pd.MultiIndex.from_tuples([tuple(map(str, col)) if isinstance(col, tuple) else (col,) for col in max_ball_table_download.columns])

                                    # Запись таблиц
                                    result_table_download.to_excel(writer, index=True, sheet_name="Результаты")
                                    max_ball_table_download.to_excel(writer, index=True, sheet_name="Макс Баллы")

                                # Кнопка скачивания
                                st.download_button(
                                    label="Скачать результаты (Все типы сумм)",
                                    data=result_output_all.getvalue(),
                                    file_name="Результаты_все_типы_сумм.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            else:
                                st.warning("Нет доступных данных для создания таблицы максимальных баллов.")

                        elif st.session_state["display_mode"] == "По отдельным типам сумм":
                            # Проверяем, выполнена ли агрегация
                            
                                
                            for good_col in st.session_state["good_cols"]:
                                # Найти столбцы, относящиеся к текущему типу суммы
                                matching_cols = [
                                    col for col in st.session_state["result_table_main"].columns if col[1] == good_col
                                ]
                                
                                if matching_cols:
                                    # Фильтруем result_table_main по найденным столбцам
                                    filtered_result_table = st.session_state["result_table_main"].loc[:, matching_cols]

                                    # Отображаем таблицу баллов для текущего типа суммы
                                    st.subheader(f"Таблица баллов — {good_col}")
                                    display_dataframe_table(filtered_result_table)

                                    # Фильтруем max_ball_table_main для текущего типа суммы
                                    if good_col in st.session_state["max_ball_table_main"].index:
                                        filtered_max_ball_table = st.session_state["max_ball_table_main"].loc[good_col]
                                        filtered_max_ball_table = filtered_max_ball_table.to_frame().transpose()

                                        # Отображаем таблицу максимальных баллов
                                        st.subheader(f"Таблица макс.баллов — {good_col}")
                                        display_dataframe_table(filtered_max_ball_table)
                                    else:
                                        st.warning(f"Для типа суммы {good_col} нет данных в таблице максимальных баллов.")

                            # Подготовка данных для скачивания
                            result_output_separate = BytesIO()
                            with pd.ExcelWriter(result_output_separate, engine="xlsxwriter") as writer:
                                for good_col in st.session_state["good_cols"]:
                                    # Генерация данных для текущего типа суммы
                                    matching_cols = [
                                        col for col in st.session_state["result_table_main"].columns if col[1] == good_col
                                    ]
                                    if matching_cols:
                                        # Создаем таблицу результатов
                                        filtered_result_table = st.session_state["result_table_main"].loc[:, matching_cols]
                                        filtered_result_table.columns = pd.MultiIndex.from_tuples([tuple(map(str, col)) if isinstance(col, tuple) else (col,) for col in filtered_result_table.columns])
                                        filtered_result_table.to_excel(
                                            writer, index=True, sheet_name=f"Результаты_{good_col}"
                                        )

                                # Сохранение max_ball_table_main
                                max_ball_table_download = st.session_state["max_ball_table_main"].copy()
                                max_ball_table_download.columns = [
                                    " ".join(map(str, col)).strip() if isinstance(col, tuple) else col
                                    for col in max_ball_table_download.columns
                                ]
                                max_ball_table_download.to_excel(
                                    writer, index=True, sheet_name="Макс Баллы"
                                )


                            # Кнопка скачивания файла
                            st.download_button(
                                label="Скачать результаты (отдельные суммы)",
                                data=result_output_separate.getvalue(),
                                file_name="Результаты_по_типам_сумм.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
        

            
    # --- Блок 2: Обработка результатов вопросов ---
    elif selected_block == "Обработка вопросов":
        st.header("Обработка вопросов")

        st.markdown("""
        Вам понадобится:

        1. 📥 Файл **Пользователи.xlsx** с Яндекс.Диска.
        2. 📁 Папка **Вопросы** с Яндекс.Диска.
        """)
       

        # Загрузка студентов
        all_students = []
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник', 'Тест Никита', 'Тест Фотофон']

        st.markdown("### Пользователи")
        st.markdown("""
        Загрузите список студентов из файла *Пользователи.xlsx* или введите их вручную.
        """)
        
        option = st.radio("Выберите:", ("Загрузить из таблицы", "Ввести вручную"))
        
        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"])
            if uploaded_file:
                all_students = get_students_from_file(uploaded_file)   
         
        else:
            # Ручной ввод студентов
            students_input = st.text_area("Введите имена студентов, разделяя их новой строкой:")
            all_students = students_input.split("\n")
            all_students = [s.strip() for s in all_students if s.strip()]
            
        col1, col2 = st.columns([3, 2])
        if all_students:
            
            excluded_detected = [s for s in all_students if s in excluded_students]
            valid_students = [s for s in all_students if s not in excluded_students]

            # Подсвечивание и возврат исключённых
            if excluded_detected:

                st.warning(f"Исключены тестовые пользователи: {', '.join(excluded_detected)}. Вы можете их вернуть.")
                
                # Возможность вернуть исключённых
                returned_users = []  # Перенесли сюда инициализацию
                with col2:
                    with st.expander("### Список тестовых пользователей:"):
                        for user in excluded_detected:
                            if st.checkbox(f"Вернуть {user}", key=f"return_{user}"):
                                returned_users.append(user)

                # Добавляем возвращённых пользователей к основному списку
                valid_students.extend(returned_users)
            with col1:
                # Обновляем текст в редакторе после возврата исключённых
                with st.expander("Cписок студентов"):
                    # Перезаписываем текст редактора с учётом возвращённых
                    editable_students = st.text_area(
                        "Отредактируйте список студентов:", 
                        "\n".join(valid_students)  # Отображаем обновлённый список
                    )
                    valid_students = editable_students.split("\n")
                    valid_students = [s.strip() for s in valid_students if s.strip()]
            if valid_students:
                st.subheader("Вопросы")
                # Функция для исключения файла
                def exclude_file(file_name):
                    if file_name not in st.session_state["excluded_files"]:
                        st.session_state["excluded_files"].append(file_name)
                        st.session_state["filtered_files"] = [
                            file for file in st.session_state["filtered_files"] if file.name != file_name
                        ]

                # Функция для добавления файла обратно
                def include_file(file_name):
                    file_to_include = next(
                        (file for file in st.session_state["uploaded_files"] if file.name == file_name), None
                    )
                    if file_to_include:
                        st.session_state["filtered_files"].append(file_to_include)
                        st.session_state["excluded_files"].remove(file_name)
                # Код для обработки результатов вопросов
                question_files = st.file_uploader("Загрузите файлы с вопросами и ответами", type=["xlsx", "txt"], accept_multiple_files=True)
                if question_files:
                # Инициализация состояния для загруженных файлов
                    if "uploaded_files" not in st.session_state:
                        st.session_state["uploaded_files"] = []

                    if question_files:
                        st.session_state["uploaded_files"] = question_files

                    # Инициализация состояния для фильтрованных и исключенных файлов
                    if "filtered_files" not in st.session_state:
                        st.session_state["filtered_files"], st.session_state["excluded_files"] = filter_files_by_keywords(st.session_state["uploaded_files"])
                    # Проверка, существуют ли необходимые сессионные переменные

                    # Левый экспандер: Фильтрованные файлы
                    with st.expander("Фильтрованные и отсортированные файлы", expanded=False):
                        st.write("Введите текст для поиска файла:")
                        search_query = st.text_input("Поиск файлов", "")
                        
                        # Фильтрация по имени файла
                        filtered_files_for_search = [file for file in st.session_state["filtered_files"] if search_query.lower() in file.name.lower()]
                        
                        if filtered_files_for_search:
                            st.write("Вы можете добавить файлы в исключенные или удалить их из списка.")
                            for file in filtered_files_for_search:
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.write(f"<div class='compact-list'>{file.name}</div>", unsafe_allow_html=True)
                                with col2:
                                    st.button("Исключить", key=f"exclude_{file.name}", on_click=exclude_file, args=(file.name,))
                        else:
                            st.write("Нет файлов для отображения по вашему запросу.")

                    # Правый экспандер: Исключенные файлы
                    with st.expander("Исключенные файлы", expanded=False):
                        if st.session_state["excluded_files"]:
                            st.write("Вы можете добавить исключенные файлы обратно в список вопросов.")
                            for file_name in st.session_state["excluded_files"]:
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.write(f"<div class='compact-list'>{file_name}</div>", unsafe_allow_html=True)
                                with col2:
                                    st.button("Добавить обратно", key=f"include_{file_name}", on_click=include_file, args=(file_name,))
                        else:
                            st.write("Нет исключенных файлов.")
                    
                    if "result_table" not in st.session_state:
                        st.session_state["result_table"] = None

                    if "unsent_questions" not in st.session_state:
                        st.session_state["unsent_questions"] = {}

                    if "error_questions" not in st.session_state:
                        st.session_state["error_questions"] = {}
                    if st.button("Выполнить обработку вопросов"):
                        try:
                            # Обработка вопросных файлов
                            st.session_state["result_table"], st.session_state["unsent_questions"], st.session_state["error_questions"] = process_question_files(valid_students, [file.name for file in st.session_state["filtered_files"]], st.session_state["filtered_files"])
                             # Сохраняем результаты в сессию
                            
                        except Exception as e:
                            st.error(f"Произошла ошибка при обработке файлов: {e}")
                        
                 
                        # Вывод результата
                        st.subheader("Таблица с результатами")
                        if st.session_state["result_table"] is not None and not st.session_state["result_table"].empty:
                            st.markdown("""
                            <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                            Эти данные "хорошие", их надо перенести в публичную таблицу.
                            </p>
                            """, unsafe_allow_html=True)
                            
                            st.dataframe(st.session_state["result_table"])
                            
                        else:
                            st.markdown("""
                            <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                            Эти данные "хорошие", их надо перенести в публичную таблицу.
                            </p>
                            """, unsafe_allow_html=True)
                            st.write("Не получено результатов.")

                        st.subheader("Неразосланные вопросы")
                        if st.session_state["unsent_questions"]:
                            st.markdown("""
                            <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                            Эти вопросы не были отправлены студентам, они не учитываются в итогах. Нужно написать преподавателям.
                            </p>
                            """, unsafe_allow_html=True)
                            for key, value in st.session_state["unsent_questions"].items():
                                st.text(f"Вопрос {key}:\n{value}")
                        else:
                            st.markdown("""
                            <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                            Эти вопросы не были отправлены студентам, они не учитываются в итогах. Нужно написать преподавателям.
                            </p>
                            """, unsafe_allow_html=True)
                            st.write("Нет неразосланных вопросов.")
                            

                        st.subheader("Ошибки вопросов")
                        if st.session_state["error_questions"]:
                            st.markdown("""
                            <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                            В случае наличия ошибок нужно посмотреть, может получится поправить. Если нет - написать преподавателям.
                            </p>
                            """, unsafe_allow_html=True)
                            for key, value in st.session_state["error_questions"].items():
                                st.text(f"Вопрос {key}:\n{value}")
                        else:
                            st.markdown("""
                            <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                            В случае наличия ошибок нужно посмотреть, может получится поправить. Если нет - написать преподавателям.
                            </p>
                            """, unsafe_allow_html=True)
                            st.write("Ошибок нет.")

                        if st.session_state["result_table"] is not None and not st.session_state["result_table"].empty:
                            result_table =  st.session_state["result_table"].copy()
                            # Подготовка файла для скачивания
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                result_table.to_excel(writer, sheet_name='Результаты')
                            output.seek(0)

                            # Кнопка для скачивания
                            st.download_button(
                                label="Скачать таблицу результатов",
                                data=output,
                                file_name="Результаты.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )


    # --- Блок 3: Посещаемость ---
    elif selected_block == "Посещаемость":
        st.header("Посещаемость студентов")
        
        st.markdown("""
        Вам понадобится:

        1. 📥 **Скачать файл** *Пользователи.xlsx* с Яндекс.Диска.
        2. 📥 **Скачать файл** *Посещаемость.xlsx* с папки 'Вопросы' Яндекс.Диска.
        """)


        # Загрузка студентов
        all_students = []
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник', 'Тест Никита', 'Тест Фотофон']

        st.markdown("### Пользователи")
        st.markdown("""
        Загрузите список студентов из файла *Пользователи.xlsx* или введите их вручную.
        """)
        
        option = st.radio("Выберите:", ("Загрузить из таблицы", "Ввести вручную"))
        
        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"])
            if uploaded_file:
                all_students = get_students_from_file(uploaded_file)   
         
        else:
            # Ручной ввод студентов
            students_input = st.text_area("Введите имена студентов, разделяя их новой строкой:")
            all_students = students_input.split("\n")
            all_students = [s.strip() for s in all_students if s.strip()]
            
        col1, col2 = st.columns([3, 2])
        if all_students:
            
            excluded_detected = [s for s in all_students if s in excluded_students]
            valid_students = [s for s in all_students if s not in excluded_students]

            # Подсвечивание и возврат исключённых
            if excluded_detected:

                st.warning(f"Исключены тестовые пользователи: {', '.join(excluded_detected)}. Вы можете их вернуть.")
                
                # Возможность вернуть исключённых
                returned_users = []  # Перенесли сюда инициализацию
                with col2:
                    with st.expander("### Список тестовых пользователей:"):
                        for user in excluded_detected:
                            if st.checkbox(f"Вернуть {user}", key=f"return_{user}"):
                                returned_users.append(user)

                # Добавляем возвращённых пользователей к основному списку
                valid_students.extend(returned_users)
            with col1:
                # Обновляем текст в редакторе после возврата исключённых
                with st.expander("Cписок студентов"):
                    # Перезаписываем текст редактора с учётом возвращённых
                    editable_students = st.text_area(
                        "Отредактируйте список студентов:", 
                        "\n".join(valid_students)  # Отображаем обновлённый список
                    )
                    valid_students = editable_students.split("\n")
                    valid_students = [s.strip() for s in valid_students if s.strip()]

            st.subheader("Посещаемость")
            # Получение и редактирование списка преподавателей
            
            
            students_file = st.file_uploader("Выберите файл Посещаемость.xlsx", type=["xlsx", "xls"])
            if students_file:
                try:
                    with st.spinner("Выполняется агрегация..."):
                        result_table = process_attendance(students_file, valid_students)

                        # Выводим объединённый результат
                        st.subheader("Таблица")
                        st.dataframe(result_table)

                        # Кнопка для скачивания результата
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            result_table.to_excel(writer, index=True, sheet_name="Результат")
                        st.download_button(
                            label="Скачать результат",
                            data=buffer.getvalue(),
                            file_name="Результат_посещаемости.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                except Exception as e:
                    st.error(f"Ошибка обработки файла: {e}")
            else:
                st.warning("Пожалуйста, загрузите файл с посещаемостью.")

