import streamlit as st
import os
from io import BytesIO
from utils.clustering_comments_dbscan import *  # Импортируем модуль кластеризации
from utils.search_notebooks import *  # Импортируем функцию поиска по ноутбукам
from utils.results_students import * # Импортируем модуль агрегации результатов

# Функция для сортировки файлов по номеру в названии
def sort_files_by_number(files):
    def extract_number(file_name):
        match = re.search(r'\d+', file_name)
        return int(match.group()) if match else float('inf')
    return sorted(files, key=lambda f: extract_number(f.name))

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
        students = []
        # Список исключаемых студентов
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник']

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
                # Подтверждение о загрузке файла
                st.success(f"Файл {uploaded_file.name} успешно загружен!")
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
            

            # --- Выбор курса ---
            st.markdown("### Выбор курса")
            course = st.selectbox(
                "Выберите курс:",
                ["ds3-поток", "ds4-поток", "Введение в анализ данных", "Ph@ds/Статистика ФБМФ"]
            )


            if course in ["ds3-поток"]:
                # --- Основная сдача ---
                
                st.subheader('Основная сдача - анализ таблиц DS3')
                st.markdown("""
                <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                Загрузите ST/SP/ML - основную сдачу.
                </p>
                """, unsafe_allow_html=True)
                main_task_files = st.file_uploader("Загрузите файлы основной сдачи", type=["xlsx"], accept_multiple_files=True,key="main_tasks_ds3")

                if main_task_files:
                    main_task_files = sort_files_by_number(main_task_files)
                    st.write("Сортированные файлы:")
                    for file in main_task_files:
                        st.write(file.name)

                     # Проверка на наличие результатов в session_state
                    if 'result_table_main' not in st.session_state or 'max_ball_table_main' not in st.session_state:
                        if st.button("Выполнить агрегацию для ds3_потока - Основная сдача", key="ds3_main_"):
                            good_cols = ['Студент'] + pd.read_excel(main_task_files[0], sheet_name='Студенты').columns[3:].tolist()
                            result_table_main = aggregate_scores(students, main_task_files)
                            max_ball_table_main = aggregate_max_ball_table(main_task_files)

                            # Сохранение результатов в session_state
                            st.session_state['result_table_main'] = result_table_main
                            st.session_state['max_ball_table_main'] = max_ball_table_main

                    # Если таблицы уже сохранены в session_state, отобразить их
                    if 'result_table_main' in st.session_state:
                        st.subheader("Таблица результатов для ds3-потока (Основная сдача)")
                        st.dataframe(st.session_state['result_table_main'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для ds3-потока (Основная сдача)")
                        st.dataframe(st.session_state['max_ball_table_main'], use_container_width=True)
                        
                        result_table_main = st.session_state['result_table_main']
                        max_ball_table_main = st.session_state['max_ball_table_main'] 
                        # Сброс уровней индекса и форматирование столбцов
                        result_table_main.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_main.columns]
                        max_ball_table_main.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in max_ball_table_main.columns]
                        # Скачивание файлов
                        result_output = BytesIO()
                        with pd.ExcelWriter(result_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_main'].to_excel(writer, index=False, sheet_name='Результаты')

                        max_ball_output = BytesIO()
                        with pd.ExcelWriter(max_ball_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_main'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для основной сдачи",
                            data=result_output.getvalue(),
                            file_name='Результаты_основная_сдача.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для основной сдачи",
                            data=max_ball_output.getvalue(),
                            file_name='Макс_баллы_основная_сдача.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                # --- Дорешка ---
                st.subheader("Дорешка - анализ таблиц DS3")
                st.markdown("""
                <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                Загрузите ST/SP/ML - дорешки.
                </p>
                """, unsafe_allow_html=True)
                retake_task_files = st.file_uploader("Загрузите файлы для дорешки", type=["xlsx"], accept_multiple_files=True, key="ds3_retake_tasks")

                if retake_task_files:
                    retake_task_files = sort_files_by_number(retake_task_files)
                    st.write("Сортированные файлы для дорешки:")
                    for file in retake_task_files:
                        st.write(file.name)

                    # Проверка на наличие результатов в session_state
                    if 'result_table_additional' not in st.session_state or 'result_table_reset' not in st.session_state or 'max_ball_table_retake' not in st.session_state:
                        if st.button("Выполнить агрегацию для дорешки ds3", key="ds3_dor"):
                            good_cols_additional = ['Сумма добавка']
                            good_cols_reset = ['Сумма с нуля']

                            # Агрегация для "Сумма добавка"
                            result_table_additional = aggregate_scores(students, retake_task_files, good_cols_additional)

                            # Агрегация для "Сумма с нуля"
                            result_table_reset = aggregate_scores(students, retake_task_files, good_cols_reset)

                            # Максимальные баллы
                            max_ball_table_retake = aggregate_max_ball_table(retake_task_files)


                            # Сохранение в session_state
                            st.session_state['result_table_additional'] = result_table_additional
                            st.session_state['result_table_reset'] = result_table_reset
                            st.session_state['max_ball_table_retake'] = max_ball_table_retake

                    # Если таблицы уже сохранены в session_state, отобразить их
                    if 'result_table_additional' in st.session_state:
                        st.subheader("Таблица результатов для дорешки — Сумма добавка")
                        st.dataframe(st.session_state['result_table_additional'], use_container_width=True)

                        st.subheader("Таблица результатов для дорешки — Сумма с нуля")
                        st.dataframe(st.session_state['result_table_reset'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для дорешки")
                        st.dataframe(st.session_state['max_ball_table_retake'], use_container_width=True)

                        result_table_additional = st.session_state['result_table_additional']
                        result_table_reset = st.session_state['result_table_reset'] 
                        max_ball_table_retake = st.session_state['max_ball_table_retake'] 
                        # Сброс уровней индекса и форматирование столбцов
                        result_table_additional.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_additional.columns]
                        result_table_reset.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_reset.columns]
                        max_ball_table_retake.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in max_ball_table_retake.columns]
                        # Скачивание файлов
                        additional_output = BytesIO()
                        with pd.ExcelWriter(additional_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_additional'].to_excel(writer, index=False, sheet_name='Сумма добавка')

                        reset_output = BytesIO()
                        with pd.ExcelWriter(reset_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_reset'].to_excel(writer, index=False, sheet_name='Сумма с нуля')

                        max_ball_output = BytesIO()
                        with pd.ExcelWriter(max_ball_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_retake'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для дорешки ds3 — Сумма добавка",
                            data=additional_output.getvalue(),
                            file_name='Результаты_дорешка_сумма_добавка.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать результаты для дорешки ds3 — Сумма с нуля",
                            data=reset_output.getvalue(),
                            file_name='Результаты_дорешка_сумма_с_нуля.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для дорешки ds3",
                            data=max_ball_output.getvalue(),
                            file_name='Макс_баллы_дорешка.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

            elif course in ["ds4-поток"]:
                # Логика для курса "Введение в анализ данных"
                # --- Основная сдача ---
                st.subheader("Основная сдача - анализ таблиц DS4")
                st.markdown("""
                <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                Загрузите основную сдачу.
                </p>
                """, unsafe_allow_html=True)
                main_task_files4 = st.file_uploader("Загрузите файлы основной сдачи ds4", type=["xlsx"], accept_multiple_files=True, key="main_tasks_ds4")

                if main_task_files4:
                    main_task_files4 = sort_files_by_number(main_task_files4)
                    st.write("Сортированные файлы для ds4:")
                    for file in main_task_files4:
                        st.write(file.name)

                     # Проверка на наличие результатов в session_state
                    if 'result_table_main' not in st.session_state or 'max_ball_table_main' not in st.session_state:
                        if st.button("Выполнить агрегацию для ds4_потока - Основная сдача", key="ds4_main_"):
                            good_cols = ['Студент'] + pd.read_excel(main_task_files4[0], sheet_name='Студенты').columns[3:].tolist()
                            result_table_main = aggregate_scores(students, main_task_files4)
                            max_ball_table_main = aggregate_max_ball_table(main_task_files4)

                            # Сохранение результатов в session_state
                            st.session_state['result_table_main'] = result_table_main
                            st.session_state['max_ball_table_main'] = max_ball_table_main

                    # Если таблицы уже сохранены в session_state, отобразить их
                    if 'result_table_main' in st.session_state:
                        st.subheader("Таблица результатов для ds4-потока (Основная сдача)")
                        st.dataframe(st.session_state['result_table_main'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для ds4-потока (Основная сдача)")
                        st.dataframe(st.session_state['max_ball_table_main'], use_container_width=True)

                        result_table_main = st.session_state['result_table_main']
                        max_ball_table_main = st.session_state['max_ball_table_main'] 
                        # Сброс уровней индекса и форматирование столбцов
                        result_table_main.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_main.columns]
                        max_ball_table_main.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in max_ball_table_main.columns]
                        # Скачивание файлов
                        result_output = BytesIO()
                        with pd.ExcelWriter(result_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_main'].to_excel(writer, index=False, sheet_name='Результаты')

                        max_ball_output = BytesIO()
                        with pd.ExcelWriter(max_ball_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_main'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для основной сдачи",
                            data=result_output.getvalue(),
                            file_name='Результаты_основная_сдача.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для основной сдачи",
                            data=max_ball_output.getvalue(),
                            file_name='Макс_баллы_основная_сдача.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                # --- Дорешка ---
                st.subheader("Дорешка - анализ таблиц DS4")
                st.markdown("""
                <p style="font-size: 12px; font-style: italic; color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 5px;">
                Загрузите дорешки.
                </p>
                """, unsafe_allow_html=True)
                retake_task_files = st.file_uploader("Загрузите файлы для дорешки", type=["xlsx"], accept_multiple_files=True, key="ds4_retake_tasks")

                if retake_task_files:
                    retake_task_files = sort_files_by_number(retake_task_files)
                    st.write("Сортированные файлы для дорешки:")
                    for file in retake_task_files:
                        st.write(file.name)

                    # Проверка на наличие результатов в session_state
                    if 'result_table_additional' not in st.session_state or 'result_table_reset' not in st.session_state or 'max_ball_table_retake' not in st.session_state:
                        if st.button("Выполнить агрегацию для дорешки ds4", key="ds4_dor"):
                            good_cols_additional = ['Сумма добавка']
                            good_cols_reset = ['Сумма с нуля']

                            # Агрегация для "Сумма добавка"
                            result_table_additional = aggregate_scores(students, retake_task_files, good_cols_additional)

                            # Агрегация для "Сумма с нуля"
                            result_table_reset = aggregate_scores(students, retake_task_files, good_cols_reset)

                            # Максимальные баллы
                            max_ball_table_retake = aggregate_max_ball_table(retake_task_files)


                            # Сохранение в session_state
                            st.session_state['result_table_additional'] = result_table_additional
                            st.session_state['result_table_reset'] = result_table_reset
                            st.session_state['max_ball_table_retake'] = max_ball_table_retake

                    # Если таблицы уже сохранены в session_state, отобразить их
                    if 'result_table_additional' in st.session_state:
                        st.subheader("Таблица результатов для дорешки — Сумма добавка")
                        st.dataframe(st.session_state['result_table_additional'], use_container_width=True)

                        st.subheader("Таблица результатов для дорешки — Сумма с нуля")
                        st.dataframe(st.session_state['result_table_reset'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для дорешки")
                        st.dataframe(st.session_state['max_ball_table_retake'], use_container_width=True)

                        result_table_additional = st.session_state['result_table_additional'] 
                        result_table_reset = st.session_state['result_table_reset']
                        max_ball_table_retake = st.session_state['max_ball_table_retake']
                        # Сброс уровней индекса и форматирование столбцов
                        result_table_additional.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_additional.columns]
                        result_table_reset.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_reset.columns]
                        max_ball_table_retake.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in max_ball_table_retake.columns]
                        # Скачивание файлов
                        additional_output = BytesIO()
                        with pd.ExcelWriter(additional_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_additional'].to_excel(writer, index=False, sheet_name='Сумма добавка')

                        reset_output = BytesIO()
                        with pd.ExcelWriter(reset_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_reset'].to_excel(writer, index=False, sheet_name='Сумма с нуля')

                        max_ball_output = BytesIO()
                        with pd.ExcelWriter(max_ball_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_retake'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для дорешки ds4 — Сумма добавка",
                            data=additional_output.getvalue(),
                            file_name='Результаты_дорешка_сумма_добавка.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать результаты для дорешки ds4 — Сумма с нуля",
                            data=reset_output.getvalue(),
                            file_name='Результаты_дорешка_сумма_с_нуля.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для дорешки ds4",
                            data=max_ball_output.getvalue(),
                            file_name='Макс_баллы_дорешка.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

            elif course == "Введение в анализ данных":
                # --- ДЗ ---
                st.subheader("ВвАД - ДЗ")
                main_task_files_ad = st.file_uploader("Загрузите файлы ДЗ", type=["xlsx"], accept_multiple_files=True, key="ad_hw")

                if main_task_files_ad:
                    main_task_files_ad = sort_files_by_number(main_task_files_ad)
                    st.write("Сортированные файлы:")
                    for file in main_task_files_ad:
                        st.write(file.name)

                    if 'result_table_hw_ad' not in st.session_state or 'max_ball_table_hw_ad' not in st.session_state:
                        if st.button("Выполнить агрегацию для ДЗ", key="sem_phds"):
                            result_table_hw_ad = aggregate_scores(students, main_task_files_ad)
                            max_ball_table_hw_ad = aggregate_max_ball_table(main_task_files_ad)

                            # Создаем мультииндекс только для существующих значений
                            valid_columns = [(file, sum_type) for file in max_ball_table_hw_ad.columns
                                            for sum_type in max_ball_table_hw_ad.index
                                            if not pd.isna(max_ball_table_hw_ad.at[sum_type, file])]

                            multiindex_columns = pd.MultiIndex.from_tuples(valid_columns, names=["Файл", "Тип суммы"])
                            values = [max_ball_table_hw_ad.at[sum_type, file] for file, sum_type in valid_columns]
                            final_table_hw = pd.DataFrame([values], columns=multiindex_columns)
                            # Сохранение в session_state
                            st.session_state['result_table_hw_ad'] = result_table_hw_ad
                            st.session_state['max_ball_table_hw_ad'] = final_table_hw

                    # Отображение таблиц из session_state
                    if 'result_table_hw_ad' in st.session_state:
                        st.subheader("Таблица результатов для ВвАД (ДЗ)")
                        st.dataframe(st.session_state['result_table_hw_ad'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для ВвАД (ДЗ)")
                        st.dataframe(st.session_state['max_ball_table_hw_ad'], use_container_width=True)

                        # Сброс уровней MultiIndex перед записью
                        
                        result_table_hw_ad = st.session_state['result_table_hw_ad']
                        final_table_hw = st.session_state['max_ball_table_hw_ad']
                        result_table_hw_ad.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_hw_ad.columns]
                        final_table_hw.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in final_table_hw.columns]
                        # Скачивание таблиц
                        seminar_output = BytesIO()
                        with pd.ExcelWriter(seminar_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_hw_ad'].to_excel(writer, index=False, sheet_name='Результаты')

                        max_ball_seminar_output = BytesIO()
                        with pd.ExcelWriter(max_ball_seminar_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_hw_ad'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для ДЗ",
                            data=seminar_output.getvalue(),
                            file_name='Результаты_ДЗ.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для ДЗ",
                            data=max_ball_seminar_output.getvalue(),
                            file_name='Макс_баллы_ДЗ.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                # --- Дорешки ---
                st.subheader("ВвАД - дорешки")
                main_task_files = st.file_uploader("Загрузите файлы дорешек", type=["xlsx"], accept_multiple_files=True, key="ad_dor")

                if main_task_files:
                    main_task_files = sort_files_by_number(main_task_files)
                    st.write("Сортированные файлы:")
                    for file in main_task_files:
                        st.write(file.name)

                    if 'result_table_ad_dor' not in st.session_state or 'max_ball_table_ad_dor' not in st.session_state:
                        if st.button("Выполнить агрегацию для дорешек - ВвАД", key="hw_phds"):
                            # Список интересующих типов сумм
                            good_cols = ['Добавка Л', 'Добавка С', 'Добавка Ф']
                            result_table_ad_dor = aggregate_scores(students, main_task_files, good_cols)
                            max_ball_table_ad_dor = aggregate_max_ball_table(main_task_files)

                            

                            # Создаем мультииндекс только для существующих значений с нужными типами сумм
                            valid_columns = [
                                (file, sum_type) for file in max_ball_table_ad_dor.columns
                                for sum_type in max_ball_table_ad_dor.index
                                if sum_type in good_cols and not pd.isna(max_ball_table_ad_dor.at[sum_type, file])
                            ]

                            multiindex_columns = pd.MultiIndex.from_tuples(valid_columns, names=["Файл", "Тип суммы"])
                            values = [max_ball_table_ad_dor.at[sum_type, file] for file, sum_type in valid_columns]
                            final_table = pd.DataFrame([values], columns=multiindex_columns)

                            # Сохранение в session_state
                            st.session_state['result_table_ad_dor'] = result_table_ad_dor
                            st.session_state['max_ball_table_ad_dor'] = final_table

                    # Отображение таблиц из session_state
                    if 'result_table_ad_dor' in st.session_state:
                        st.subheader("Таблица результатов для ВвАД (дорешки)")
                        st.dataframe(st.session_state['result_table_ad_dor'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для ВвАД (дорешки)")
                        st.dataframe(st.session_state['max_ball_table_ad_dor'], use_container_width=True)

                        result_table_ad_dor = st.session_state['result_table_ad_dor'] 
                        final_table = st.session_state['max_ball_table_ad_dor'] 
                        # Сброс уровней MultiIndex перед записью
                        result_table_ad_dor.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_ad_dor.columns]
                        final_table.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in final_table.columns]
                        # Скачивание таблиц
                        hw_output = BytesIO()
                        with pd.ExcelWriter(hw_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_ad_dor'].to_excel(writer, index=False, sheet_name='Результаты')

                        max_ball_hw_output = BytesIO()
                        with pd.ExcelWriter(max_ball_hw_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_ad_dor'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для дорешек",
                            data=hw_output.getvalue(),
                            file_name='Результаты_дорешки.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для дорешек",
                            data=max_ball_hw_output.getvalue(),
                            file_name='Макс_баллы_дорешки.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

            elif course == "Ph@ds/Статистика ФБМФ":
                # --- Семинар ---
                st.subheader("Семинар - анализ таблиц ph@ds")
                main_task_files_ph = st.file_uploader("Загрузите файлы семинаров", type=["xlsx"], accept_multiple_files=True, key="phds_sem")

                if main_task_files_ph:
                    main_task_files_ph = sort_files_by_number(main_task_files_ph)
                    st.write("Сортированные файлы ph@ds:")
                    for file in main_task_files_ph:
                        st.write(file.name)

                    if 'result_table_seminar' not in st.session_state or 'max_ball_table_seminar' not in st.session_state:
                        if st.button("Выполнить агрегацию для Семинара - ph@ds", key="sem_phds"):
                            result_table_seminar = aggregate_scores(students, main_task_files_ph)
                            max_ball_table_seminar = aggregate_max_ball_table(main_task_files_ph)

                            # Сохранение в session_state
                            st.session_state['result_table_seminar'] = result_table_seminar
                            st.session_state['max_ball_table_seminar'] = max_ball_table_seminar

                    # Отображение таблиц из session_state
                    if 'result_table_seminar' in st.session_state:
                        st.subheader("Таблица результатов для ph@ds (Семинар)")
                        st.dataframe(st.session_state['result_table_seminar'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для ph@ds (Семинар)")
                        st.dataframe(st.session_state['max_ball_table_seminar'], use_container_width=True)

                        # Сброс уровней MultiIndex перед записью
                        
                        result_table_seminar = st.session_state['result_table_seminar']
                        max_ball_table_seminar = st.session_state['max_ball_table_seminar']
                        result_table_seminar.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_seminar.columns]
                        max_ball_table_seminar.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in max_ball_table_seminar.columns]
                        # Скачивание таблиц
                        seminar_output = BytesIO()
                        with pd.ExcelWriter(seminar_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_seminar'].to_excel(writer, index=False, sheet_name='Результаты')

                        max_ball_seminar_output = BytesIO()
                        with pd.ExcelWriter(max_ball_seminar_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_seminar'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для семинаров",
                            data=seminar_output.getvalue(),
                            file_name='Результаты_семинар.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для семинаров",
                            data=max_ball_seminar_output.getvalue(),
                            file_name='Макс_баллы_семинар.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                # --- ДЗ ---
                st.subheader("ДЗ - анализ таблиц ph@ds")
                main_task_files = st.file_uploader("Загрузите файлы ДЗ", type=["xlsx"], accept_multiple_files=True, key="phds_hw")

                if main_task_files:
                    main_task_files = sort_files_by_number(main_task_files)
                    st.write("Сортированные файлы:")
                    for file in main_task_files:
                        st.write(file.name)

                    if 'result_table_main_hw' not in st.session_state or 'max_ball_table_main_hw' not in st.session_state:
                        if st.button("Выполнить агрегацию для ДЗ - ph@ds", key="hw_phds"):
                            result_table_main_hw = aggregate_scores(students, main_task_files)
                            max_ball_table_main_hw = aggregate_max_ball_table(main_task_files)

                            # Создаем мультииндекс только для существующих значений
                            valid_columns = [(file, sum_type) for file in max_ball_table_main_hw.columns
                                            for sum_type in max_ball_table_main_hw.index
                                            if not pd.isna(max_ball_table_main_hw.at[sum_type, file])]

                            multiindex_columns = pd.MultiIndex.from_tuples(valid_columns, names=["Файл", "Тип суммы"])
                            values = [max_ball_table_main_hw.at[sum_type, file] for file, sum_type in valid_columns]
                            final_table = pd.DataFrame([values], columns=multiindex_columns)

                            # Сохранение в session_state
                            st.session_state['result_table_main_hw'] = result_table_main_hw
                            st.session_state['max_ball_table_main_hw'] = final_table

                    # Отображение таблиц из session_state
                    if 'result_table_main_hw' in st.session_state:
                        st.subheader("Таблица результатов для ph@ds (ДЗ)")
                        st.dataframe(st.session_state['result_table_main_hw'], use_container_width=True)

                        st.subheader("Таблица максимальных баллов для ph@ds (ДЗ)")
                        st.dataframe(st.session_state['max_ball_table_main_hw'], use_container_width=True)

                        result_table_main_hw = st.session_state['result_table_main_hw'] 
                        final_table = st.session_state['max_ball_table_main_hw'] 
                        # Сброс уровней MultiIndex перед записью
                        result_table_main_hw.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in result_table_main_hw.columns]
                        final_table.columns = [' '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in final_table.columns]
                        # Скачивание таблиц
                        hw_output = BytesIO()
                        with pd.ExcelWriter(hw_output, engine='xlsxwriter') as writer:
                            st.session_state['result_table_main_hw'].to_excel(writer, index=False, sheet_name='Результаты')

                        max_ball_hw_output = BytesIO()
                        with pd.ExcelWriter(max_ball_hw_output, engine='xlsxwriter') as writer:
                            st.session_state['max_ball_table_main_hw'].to_excel(writer, index=False, sheet_name='Макс Баллы')

                        st.download_button(
                            label="Скачать результаты для ДЗ",
                            data=hw_output.getvalue(),
                            file_name='Результаты_ДЗ.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )

                        st.download_button(
                            label="Скачать таблицу максимальных баллов для ДЗ",
                            data=max_ball_hw_output.getvalue(),
                            file_name='Макс_баллы_ДЗ.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                        
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
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник']

        # Выбор варианта загрузки списка пользователей
        st.subheader("Пользователи")
        option = st.radio("Выберите способ получения списка пользователей:", ("Загрузить из таблицы", "Ввести вручную"))

        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"])
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
        excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник']

        st.subheader("Пользователи")
        option = st.radio("Выберите способ получения списка пользователей:", ("Загрузить из таблицы", "Ввести вручную"))

        if option == "Загрузить из таблицы":
            uploaded_file = st.file_uploader("Загрузите файл Excel с данными пользователей", type=["xlsx"])
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

        # Шаг 3: Загрузка общей таблицы посещаемости
        st.subheader("Выбор курса")



        # Предустановленные списки преподавателей
        default_teachers = {
            "ds3-поток": {
                "ST": ['Латыпова Екатерина', 'Полозов Дмитрий'],
                "SP": ['Клейдман Полина', 'Плотникова Дарья'],
                "ML": ['Мелещеня Ксения', 'Горбулев Алексей', 'Троешестова Лидия']
            },
            "ds4-поток": {
                "DS4": ['Колтаков Михаил', 'Паненко Семён']
            },
            "Ph@ds": {
                "Ph@ds": ['Жданович Тимофей', 'Логинов Артём', 'Бруттан Мари']
            },
            "Статистика ФБМФ": {
                "Статистика ФБМФ": ['Воронова Алиса', 'Мадан Арина']
            }
        }

        # Выбор курса
        selected_course = st.selectbox("Выберите курс", list(default_teachers.keys()))

        # Получение и редактирование списка преподавателей
        teachers = default_teachers[selected_course]

        with st.expander("Редактировать преподавателей", expanded=False):
            for block, teacher_list in teachers.items():
                st.write(f"Блок: {block}")
                # Редактируемый список преподавателей
                updated_teachers = st.text_area(f"Преподаватели для {block}", "\n".join(teacher_list))
                # Сохранение изменений
                teachers[block] = [teacher.strip() for teacher in updated_teachers.split("\n") if teacher.strip()]

        st.subheader("Посещаемость")
        students_file = st.file_uploader("Выберите файл Посещаемость.xlsx", type=["xlsx", "xls"])
        if students_file:
            try:
                result_tables = process_attendance(students, students_file, teachers)

                for block, table in result_tables.items():
                    st.subheader(f"{block} Таблица")
                    st.dataframe(table)

            except Exception as e:
                st.error(f"Ошибка обработки файла: {e}")
        else:
            st.warning("Пожалуйста, загрузите файл с посещаемостью.")