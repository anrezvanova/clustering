
import streamlit as st
from streamlit_sortables import sort_items
import os
from io import BytesIO
from utils.clustering_comments_dbscan import *  # Импортируем модуль кластеризации
from utils.search_notebooks import *  # Импортируем функцию поиска по ноутбукам
from utils.results_students import * # Импортируем модуль агрегации результатов
from utils.nbcheck_code import * # Импортируем модуль агрегации результатов
from io import BytesIO
import tempfile
import re

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
    
        /* Селектор для контейнера с атрибутом data-baseweb="select" */
    [data-baseweb="select"] {
        background-color: white !important; /* Белый фон для основного контейнера */
        color: black !important; /* Черный текст */
        border: 2px solid #4985c1; /* Легкая синяя граница */
        border-radius: 12px; /* Скругленные углы */
        padding: 5px; /* Внутренние отступы */
    }

    /* Стили для раскрывающегося элемента */
    [data-baseweb="select"] .st-cg {
        background-color: white !important; /* Белый фон для вложенного элемента */
        border: 1px solid white !important; /* Белая внутренняя рамка */
    }

    /* Текст внутри select */
    [data-baseweb="select"] .st-d8 {
        color: black !important; /* Черный текст для значения */
    }

    /* Для input внутри select */
    [data-baseweb="select"] input {
        background-color: white !important; /* Белый фон */
        color: black !important; /* Черный текст */
    }

    /* Для SVG и иконки стрелки */
    [data-baseweb="select"] svg {
        fill: black !important; /* Черный цвет иконки */
    }    
    </style>
    """,
    unsafe_allow_html=True
    )

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
tab1, tab2, tab3, tab4 = st.tabs(["Кластеризация комментариев", "Поиск по ноутбукам", "Агрегация результатов", "Качество ноутбуков"])


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
    - **Собрать баллы по всем заданиям** 📝
    - **Анализировать ответы на вопросы в боте** 💬
    - **Отслеживать посещаемость занятий** 📅
    """)

    st.markdown("---")


     # Радио-кнопка для выбора блока
    selected_block = st.selectbox(
        "Выберите блок для работы:",
        ("Агрегация баллов", "Обработка результатов вопросов", "Посещаемость")
    )

    # --- Блок 1: Агрегация баллов ---
    if selected_block == "Агрегация баллов":
        # --- Успеваемость ---
        st.header("Агрегация баллов студентов")

        st.markdown("""
        Подготовка файлов:

        1. 📥 **Скачайте файл** *Пользователи.xlsx* с Яндекс.Диска.
        2. 📁 **Скачайте папку** *'Проверка ДЗ'* с таблицами проверок с Google Диска.
        """)

        st.divider()
        # Инициализация списка студентов, если он ещё не загружен
        all_students = []
        # Список исключаемых студентов
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник', 'Тест Никита', 'Тест Фотофон']

        # Выбор варианта загрузки списка пользователей
        # Секция для получения списка пользователей
        st.markdown("### Пользователи")

        st.markdown("""
        Загрузите список студентов из файла *Пользователи.xlsx* или введите их вручную.
        """)
        option = st.radio("Выберите способ получения списка пользователей:", ("Загрузить из таблицы", "Ввести вручную"))
        
        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"])
            if uploaded_file:
                all_students = get_students_from_file(uploaded_file) 
                st.success(f"Файл {uploaded_file.name} успешно загружен!") 
            # Попытка загрузить студентов из файла
             
         
        else:
            # Ручной ввод студентов
            students_input = st.text_area("Введите имена студентов, разделяя их новой строкой:")
            all_students = students_input.split("\n")
            all_students = [s.strip() for s in all_students if s.strip()]
            st.success(f"Файл {uploaded_file.name} успешно загружен!") 
        
        if all_students:
            # Выделение исключённых пользователей
            
            excluded_detected = [s for s in all_students if s in excluded_students]
            valid_students = [s for s in all_students if s not in excluded_students]
            # Подсвечивание и возврат исключённых
            if excluded_detected:
                st.warning(f"Исключены тестовые пользователи: {', '.join(excluded_detected)}. Вы можете их вернуть.")
                
                # Возможность вернуть исключённых
                returned_users = []  # Перенесли сюда инициализацию
                with st.expander("### Список тестовых пользователей:"):
                    for user in excluded_detected:
                        if st.checkbox(f"Вернуть {user}", key=f"return_{user}"):
                            returned_users.append(user)

                # Добавляем возвращённых пользователей к основному списку
                valid_students.extend(returned_users)

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
                <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                Загрузите файлы.
                </p>
                """, unsafe_allow_html=True)
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
                if "previous_files" not in st.session_state:  # Для отслеживания предыдущих файлов
                    st.session_state["previous_files"] = []
                if "good_cols" not in st.session_state:
                    st.session_state["good_cols"] = []
                if "display_mode" not in st.session_state:
                    st.session_state["display_mode"] = "Все типы сумм"
                # Флаг обновления
                if "aggregation_needs_update" not in st.session_state:
                    st.session_state["aggregation_needs_update"] = False    
                if "result_table_main" not in st.session_state:
                    st.session_state["result_table_main"] = None
                if "max_ball_table_main" not in st.session_state:
                    st.session_state["max_ball_table_main"] = None
                main_task_files = st.file_uploader("Загрузите файлы", type=["xlsx"], accept_multiple_files=True,key="main_tasks_table")

                if main_task_files:
                    new_file_names = [file.name for file in main_task_files]
                    previous_file_names = [file.name for file in st.session_state["previous_files"]]
                    
                    if new_file_names != previous_file_names:
                    # Если файлы изменились, сбрасываем состояния
                        st.session_state["good_cols"] = []
                        st.session_state["result_table_main"] = None
                        st.session_state["max_ball_table_main"] = None
                        st.session_state["previous_files"] = main_task_files 
                    
                    sorted_files = sort_files_by_number(main_task_files)
                        # Обновляем список загруженных файлов
                    with st.expander("Изменить порядок файлов", expanded=False):
                        # Drag-and-drop сортировка
                        file_names = [file.name for file in sorted_files]
                        ordered_file_names = sort_items(file_names, direction="vertical", key="sortable_list")

                        # Сопоставление нового порядка
                        main_task_files = [file for name in ordered_file_names for file in sorted_files if file.name == name]

                    st.write("Файлы в пользовательском порядке:")
                    for file in main_task_files:
                        st.write(f"📄 {file.name}")
                        # Проверка на наличие результатов в session_state
                    
                    # Извлечение уникальных типов сумм из файлов
                    all_sum_types = set()
                    for task_file in main_task_files:
                        all_sum_types.update(load_and_extract_sum_types(task_file))

                    # Сохраняем уникальные типы сумм в session_state
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
                                # Выполняем агрегацию и сбрасываем флаг после завершения
                                st.session_state["result_table_main"] = aggregate_scores(
                                    valid_students, st.session_state["previous_files"], st.session_state["good_cols"]
                                )
                                st.session_state["max_ball_table_main"] = aggregate_max_ball_table(
                                    st.session_state["previous_files"], st.session_state["good_cols"]
                                )
                                
                                # Сбрасываем флаг после выполнения агрегации
                                st.session_state["aggregation_needs_update"] = False
                            else:
                                # Если флаг False, просто выполняем агрегацию без изменений флага
                                st.session_state["result_table_main"] = aggregate_scores(
                                    valid_students, st.session_state["previous_files"], st.session_state["good_cols"]
                                )
                                st.session_state["max_ball_table_main"] = aggregate_max_ball_table(
                                    st.session_state["previous_files"], st.session_state["good_cols"]
                                )
                        
                            # Обновление прогресса
            
                    # Показываем переключатели только если данные есть
                    if (
                        st.session_state["result_table_main"] is not None
                        and st.session_state["max_ball_table_main"] is not None
                    ):
                        # Переключатель режима отображения
                        st.session_state["display_mode"] = st.radio(
                            'Выберите режим отображения', 
                            options=["Все типы сумм", "По отдельным типам сумм"], 
                            index=["Все типы сумм", "По отдельным типам сумм"].index(st.session_state["display_mode"])
                        )
                        
                        # Режим отображения: Все типы сумм
                        if st.session_state["display_mode"] == "Все типы сумм":

                            # Вывод таблицы баллов
                            st.subheader(f"Таблица баллов — Все типы сумм")
                            st.dataframe(st.session_state["result_table_main"], use_container_width=True)

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
                                st.dataframe(final_table, use_container_width=True)

                                

                                # Генерация файла для скачивания
                                result_output_all = BytesIO()
                                with pd.ExcelWriter(result_output_all, engine='xlsxwriter') as writer:
                                    # Подготовка данных для записи
                                    result_table_download = st.session_state["result_table_main"].copy()
                                    max_ball_table_download = final_table.copy()

                                    # Форматирование колонок
                                    result_table_download.columns = [
                                        ' '.join(map(str, col)).strip() if isinstance(col, tuple) else col
                                        for col in result_table_download.columns
                                    ]
                                    max_ball_table_download.columns = [
                                        ' '.join(map(str, col)).strip() if isinstance(col, tuple) else col
                                        for col in max_ball_table_download.columns
                                    ]

                                    # Запись таблиц
                                    result_table_download.to_excel(writer, index=True, sheet_name="Результаты")
                                    max_ball_table_download.to_excel(writer, index=True, sheet_name="Макс Баллы")

                                    # Настройка ширины колонок
                                    for sheet_name in writer.sheets:
                                        worksheet = writer.sheets[sheet_name]
                                        dataframe = result_table_download if sheet_name == "Результаты" else max_ball_table_download
                                        for idx, col in enumerate(dataframe.columns):
                                            max_length = max(
                                                dataframe[col].astype(str).map(len).max(),
                                                len(str(col))
                                            ) + 2
                                            worksheet.set_column(idx + 1, idx + 1, max_length)

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
                                    st.dataframe(filtered_result_table, use_container_width=True)

                                    # Фильтруем max_ball_table_main для текущего типа суммы
                                    if good_col in st.session_state["max_ball_table_main"].index:
                                        filtered_max_ball_table = st.session_state["max_ball_table_main"].loc[good_col]
                                        filtered_max_ball_table = filtered_max_ball_table.to_frame().transpose()

                                        # Отображаем таблицу максимальных баллов
                                        st.subheader(f"Таблица макс.баллов — {good_col}")
                                        st.dataframe(filtered_max_ball_table, use_container_width=True)
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
                                        filtered_result_table.columns = [
                                            " ".join(map(str, col)).strip() if isinstance(col, tuple) else col
                                            for col in filtered_result_table.columns
                                        ]
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

                                # Настройка ширины колонок
                                for sheet_name in writer.sheets:
                                    worksheet = writer.sheets[sheet_name]
                                    dataframe = max_ball_table_download if sheet_name == "Макс Баллы" else filtered_result_table
                                    for idx, col in enumerate(dataframe.columns):
                                        max_length = max(
                                            dataframe[col].astype(str).map(len).max(), len(str(col))
                                        ) + 2
                                        worksheet.set_column(idx + 1, idx + 1, max_length)

                            # Кнопка скачивания файла
                            st.download_button(
                                label="Скачать результаты (отдельные суммы)",
                                data=result_output_separate.getvalue(),
                                file_name="Результаты_по_типам_сумм.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
        else:        
            st.warning("Список студентов пока пуст. Загрузите или введите данные.")     

            
    # --- Блок 2: Обработка результатов вопросов ---
    elif selected_block == "Обработка результатов вопросов":
        st.header("Обработка результатов вопросов")

        st.markdown("""
        Вам понадобится:

        1. 📥 **Скачать файл** *Пользователи.xlsx* с Яндекс.Диска.
        2. 📁 **Скачать папку** *'Вопросы'* с Яндекс.Диска.
        """)
        st.divider()

        students = []
        # Список исключаемых студентов
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник', 'Тест Никита', 'Тест Фотофон']

        # Выбор варианта загрузки списка пользователей
        st.subheader("Пользователи")
        option = st.radio("Выберите способ получения списка пользователей:", ("Загрузить из таблицы", "Ввести вручную"))

        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"], key="questions")
            if uploaded_file:
                students = get_students_from_file(uploaded_file, excluded_students)
        else:
            # Ручной ввод студентов
            students_input = st.text_area("Введите имена студентов, разделяя их новой строкой:")
            students = students_input.split("\n")
            students = [s.strip() for s in students if s.strip()]

        # Проверка на случай, если список студентов пустой
        if not students:
            st.warning("Список студентов пока пуст. Загрузите или введите данные.")
        else:
            # Возможность редактировать список студентов
            with st.expander("Cписок студентов"):
                editable_students = st.text_area("Отредактируйте список студентов:", "\n".join(students))
                students = editable_students.split("\n")
                students = [s.strip() for s in students if s.strip()]
            
        st.subheader("Вопросы")
        # Код для обработки результатов вопросов
        question_files = st.file_uploader("Загрузите файлы с вопросами и ответами", type=["xlsx", "txt"], accept_multiple_files=True)

        if question_files:
            # Фильтруем загруженные файлы
            filtered_files = filter_question_files(question_files)

            # Сортируем отфильтрованные файлы по числовому идентификатору
            sorted_files = sort_files_by_number(filtered_files)

            # Выводим отфильтрованные и отсортированные имена файлов
            st.write("Фильтрованные и отсортированные файлы:")
            for file in sorted_files:
                st.write(file.name)
            for file in sorted_files:
                if file.name.endswith('.txt'):
                    question_id = file.name[:4]  # предположим, что question_id — первые 4 символа
                    author = find_author(question_id, [f.name for f in sorted_files])

            if st.button("Выполнить обработку вопросов"):
                try:
                    # Обработка вопросных файлов
                    result_table, unsent_questions, error_questions = process_question_files(students, [file.name for file in sorted_files], sorted_files)

                    # Вывод результата
                    st.subheader("Таблица с результатами")
                    if not result_table.empty:
                        st.markdown("""
                        <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                        Эти данные "хорошие", их надо перенести в публичную таблицу.
                        </p>
                        """, unsafe_allow_html=True)
                        st.dataframe(result_table)
                        
                    else:
                        st.markdown("""
                        <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                        Эти данные "хорошие", их надо перенести в публичную таблицу.
                        </p>
                        """, unsafe_allow_html=True)
                        st.write("Не получено результатов.")

                    st.subheader("Неразосланные вопросы")
                    if unsent_questions:
                        st.markdown("""
                        <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                        Эти вопросы не были отправлены студентам, они не учитываются в итогах. Нужно написать преподавателям.
                        </p>
                        """, unsafe_allow_html=True)
                        for key, value in unsent_questions.items():
                            st.text(f"Вопрос {key}:\n{value}")
                    else:
                        st.markdown("""
                        <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                        Эти вопросы не были отправлены студентам, они не учитываются в итогах. Нужно написать преподавателям.
                        </p>
                        """, unsafe_allow_html=True)
                        st.write("Нет неразосланных вопросов.")
                        

                    st.subheader("Ошибки вопросов")
                    if error_questions:
                        st.markdown("""
                        <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                        В случае наличия ошибок нужно посмотреть, может получится поправить. Если нет - написать преподавателям.
                        </p>
                        """, unsafe_allow_html=True)
                        for key, value in error_questions.items():
                            st.text(f"Вопрос {key}:\n{value}")
                    else:
                        st.markdown("""
                        <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                        В случае наличия ошибок нужно посмотреть, может получится поправить. Если нет - написать преподавателям.
                        </p>
                        """, unsafe_allow_html=True)
                        st.write("Ошибок нет.")

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
                except Exception as e:
                    st.error(f"Произошла ошибка при обработке файлов: {e}")


    # --- Блок 3: Посещаемость ---
    elif selected_block == "Посещаемость":
        st.header("Посещаемость студентов")
        
        st.markdown("""
        Вам понадобится:

        1. 📥 **Скачать файл** *Пользователи.xlsx* с Яндекс.Диска.
        2. 📥 **Скачать файл** *Посещаемость.xlsx* с папки 'Вопросы' Яндекс.Диска.
        """)
       
        st.divider()
        
        # Шаг 1: Загрузка списка студентов

        students = []
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник', 'Тест Никита', 'Тест Фотофон']

        st.subheader("Пользователи")
        option = st.radio("Выберите способ получения списка пользователей:", ("Загрузить из таблицы", "Ввести вручную"))

        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"], key="attendance")
            if uploaded_file:
                students = get_students_from_file(uploaded_file, excluded_students)
        else:
            students_input = st.text_area("Введите имена студентов, разделяя их новой строкой:")
            students = students_input.split("\n")
            students = [s.strip() for s in students if s.strip()]

        if not students:
            st.warning("Список студентов пока пуст. Загрузите или введите данные.")
        else:
            with st.expander("Cписок студентов"):
                editable_students = st.text_area("Отредактируйте список студентов:", "\n".join(students))
                students = editable_students.split("\n")
                students = [s.strip() for s in students if s.strip()]

            st.subheader("Посещаемость")
            # Получение и редактирование списка преподавателей
            
            
            students_file = st.file_uploader("Выберите файл Посещаемость.xlsx", type=["xlsx", "xls"])
            if students_file:
                try:
                    with st.spinner("Выполняется агрегация..."):
                        result_table = process_attendance(students_file, students)

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

# --- Качество ноутбуков ---
with tab4:
    # Добавляем приветственное сообщение 
    st.write("Добро пожаловать в приложение для проверки качества ноутбуков! 👋🏻")
    st.subheader("Качество ноутбуков")

     # Загрузка файла
    uploaded_file = st.file_uploader("Загрузите файл Jupyter Notebook", type=["ipynb"])

    

    if uploaded_file:
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ipynb", dir="/tmp") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_file_path = temp_file.name
        if not os.path.exists(temp_file_path):
            raise FileNotFoundError(f"Файл {temp_file_path} не найден.")
        # Опция длины строки для black
        line_length = st.number_input(
            "Укажите длину строки для инструмента black (по умолчанию 80):",
            min_value=10,
            max_value=200,
            value=80,
            step=1,)
        check_spelling = st.checkbox("Проверять орфографию в Markdown ячейках", value=True)
        log_output = []
        total_warnings = 0  # Подсчёт ошибок

        if st.button("Запустить проверку"):
            # Сразу показываем раздел Логов
            st.subheader("Логи")
            
            # 1. Запуск инструментов nbqa
            tools = [
                ("ruff", ["--fix"]),
                ("pyupgrade", ["--py37-plus"]),
                ("black", ["-l", str(line_length)]),
                ("docformatter", ["--in-place"]),  # Исправленный вызов docformatter
                ("blacken-docs", []),
                ("mypy", []),
            ]

            error_keywords = ["warning", "error", "refactor", "fatal"]

            for tool, args in tools:
                with st.spinner(f"Запуск {tool}..."): 
                
                    # Запуск инструмента
                    stdout, stderr, returncode = run_nbqa_tool(tool, temp_file_path, args)
                    # Убираем ANSI escape коды из stdout и stderr
                    clean_stdout = remove_ansi_escape_codes(stdout)
                    clean_stderr = remove_ansi_escape_codes(stderr)
                    if returncode == 0:
                        st.text(f"{tool} успешно выполнен.")
                        
                        if stdout.strip():
                            with st.expander(f"Сообщения {tool} (успешно)"):
                                st.markdown(parse_and_format_errors(tool, stdout, success=True))

                             
                    
                       
                    else:
                        # Подсчёт ошибок по ключевым словам
                        error_count = sum(
                            1 for line in (stdout + stderr).splitlines() if any(keyword in line.lower() for keyword in error_keywords)
                        )
                        total_warnings += error_count
                        st.text(f"{tool} завершился с ошибками.")
                        # Для инструментов, которые пишут в stdout вместо stderr
                        combined_output = stdout + "\n" + stderr
                        if combined_output.strip():
                            with st.expander(f"Ошибки {tool}"):
                                st.markdown(parse_and_format_errors(tool, combined_output, success=False))

                    
                    

            # 2. Проверка орфографии
            if check_spelling:
                with st.spinner("Проверка орфографии..."):
                    checker = NotebookStyleChecker(temp_file_path)
                    spelling_issues = checker.check_spelling()

                    # Подсчёт орфографических ошибок
                    total_warnings += len(spelling_issues)

                    # Вывод орфографических ошибок в логах
                    if spelling_issues:
                        st.text("Проверка орфографии завершена с ошибками.")
                        with st.expander("Ошибки орфографии в Markdown ячейках"):
                            for issue in spelling_issues:
                                st.write(f"Ячейка {issue['cell']} — Строка: {issue['line']}")
                                st.write(f"Ошибка в слове: {issue['word']}")
                                st.write(f"Предложенные исправления: {issue['suggestions']}")
                                st.markdown("---")
                    else:
                        st.text("Орфография без ошибок")


            # 3. Оценка качества
            total_tools = len(tools) + (1 if check_spelling else 0)
            score = max(0.0, 10.0 - total_warnings / 5)  # Оценка от 10 до 0

            # Оценка без орфографии
            score_without_spelling = score
            if check_spelling:
                score_without_spelling = max(0.0, 10.0 - (total_warnings - len(spelling_issues)) / 5)

            st.subheader("Оценка качества")
            st.write(f"Итоговая оценка: {score:.2f}/10")
            st.write(f"Оценка без ошибок орфографии: {score_without_spelling:.2f}/10")

            # 4. Сохранение исправленного ноутбука
            with open(temp_file_path, "rb") as corrected_file:
                st.download_button(
                    label="Скачать исправленный ноутбук",
                    data=corrected_file,
                    file_name="corrected_notebook.ipynb",
                    mime="application/x-ipynb+json",
                )
