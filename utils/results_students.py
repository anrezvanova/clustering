import pandas as pd
import numpy as np
from tqdm.autonotebook import tqdm
import io

# --- БЛОК 1: Агрегация баллов ---
def get_students_from_file(file_path, excluded_students):
    """Загружает студентов из Excel-файла, исключая тестовые записи."""
    data = pd.read_excel(file_path)[['status', 'fullname']]
    students = data[data['status'] != 'teacher']['fullname']
    print('Количество студентов до фильтрации:', len(students))
    print('Количество исключаемых студентов:', len(excluded_students))
    excluded_students = ['Тест Анастасия', 'Тест Анна', 'Тест Тест2', 'Тестов Ник']
    students = students[~students.isin(excluded_students)]
    print('Количество студентов после фильтрации:', len(students))
    return list(students)

def aggregate_scores(students, task_files, good_cols=None):
    """Выполняет агрегацию баллов студентов по загруженным файлам заданий."""
    result_table = pd.DataFrame(index=students, columns=pd.MultiIndex.from_arrays([[], []]))
    

    for task_file in tqdm(task_files):
        try:
            # Парсим баллы студентов
            table = pd.read_excel(task_file, sheet_name='Студенты')
            print(table)
            # Используем good_cols, если он передан, иначе выбираем 'Студент' и колонки начиная с D
            if good_cols:
                actual_cols = ['Студент'] + [col for col in good_cols if col in table.columns]
            else:
                actual_cols = ['Студент'] + table.columns[3:].tolist()
            table = table[actual_cols].iloc[5:-1].set_index('Студент') # оставляем нужные колонки
            table = table.loc[:, ~table.isna().all()] # отбрасываем пустые колонки, такое бывает

            # Форматируем названия колонок
            task_name = task_file.name.split(' [')[0]
            table.columns = [[task_name] * len(table.columns), table.columns]
            result_table = result_table.join(table, how='left').loc[students]
        except Exception as e:
            print(f"Не удалось обработать файл {task_file.name}: {e}")

        
    return result_table 



def aggregate_max_ball_table(task_files):
    """
    Создает таблицу, где строки — это типы сумм, а столбцы — файлы.
    Заполняет только те суммы, которые присутствуют, оставляя NaN для отсутствующих значений.
    """
    # Словарь для сбора данных
    sum_dict = {}

    # Проходим по каждому файлу
    for task_file in tqdm(task_files):
        try:
            # Считываем файл
            max_ball = pd.read_excel(
                task_file, 
                sheet_name='Список задач', 
                skiprows=3, 
                usecols="C:D", 
                header=None
            ).dropna(how='all')
            max_ball.columns = ['Сумма', 'Значение']

            file_name = task_file.name

            # Обрабатываем каждую строку файла
            for _, row in max_ball.iterrows():
                sum_type = row['Сумма']
                value = row['Значение']
                
                # Инициализируем вложенные словари, если их еще нет
                if sum_type not in sum_dict:
                    sum_dict[sum_type] = {}
                
                # Записываем значение для текущего файла
                sum_dict[sum_type][file_name] = value

        except Exception as e:
            print(f"Ошибка при обработке файла {task_file.name}: {e}")

    # Преобразуем данные в DataFrame
    max_ball_table = pd.DataFrame(sum_dict).T
    
    return max_ball_table



# --- БЛОК 2: Обработка результатов вопросов ---
def filter_question_files(uploaded_files, excluded_files=None):
    """
    Фильтрует загруженные файлы, исключая файлы с именами из списка excluded_files.

    Parameters:
    uploaded_files (list): Список файлов, загруженных через st.file_uploader.
    excluded_files (list): Список исключаемых файлов. По умолчанию содержит файлы для исключения.

    Returns:
    list: Отфильтрованные файлы.
    """
    if excluded_files is None:
        excluded_files = ['Оценивание занятий.xlsx', 'Посещаемость.xlsx']
    
    # Преобразуем список файлов в массив NumPy для более быстрой фильтрации
    file_names = np.array([file.name for file in uploaded_files])  # Массив имен файлов
    excluded_files = np.array(excluded_files)  # Массив исключаемых файлов
    
    # Применяем фильтрацию с помощью np.in1d
    mask = ~np.in1d(file_names, excluded_files)  # Создаем маску, исключающую указанные файлы
    file_names = list(file_names[mask])
    # Возвращаем отфильтрованные файлы
    return [uploaded_files[i] for i in range(len(uploaded_files)) if mask[i]]

def find_author(question_id, answers_list, question_id_len=4):
    answers_list = np.array(answers_list)
    question_txt_name = answers_list[[
        (x[:question_id_len] == question_id) & (x.split('.')[-1] == 'txt')
        for x in answers_list
    ]]
    
    if len(question_txt_name) == 0:
        return "Автор не найден"
    
    question_txt_name = question_txt_name[0]    
    teacher_name = ' '.join(question_txt_name[:-4].split(' ')[2:])
    return teacher_name

def add_question_info(dict_info, question_id, answers_list, date, question_text, info="", question_id_len=4):
    teacher_name = find_author(question_id, answers_list, question_id_len=question_id_len)
    
    text = (
        f"=== Вопрос {question_id}, {teacher_name} ===\n"
        + f"Дата ответа: {date}\n{question_text}\n"
        + ((info+"\n\n") if info else "\n")
    )
    
    if teacher_name not in dict_info:
        dict_info[teacher_name] = text
    else:
        dict_info[teacher_name] += text

def process_question_files(students, file_names, question_files):
    """
    Обрабатывает файлы с вопросами и ответами, собирает результаты.
    """
    students = np.array(students)
    students = [s.lstrip() for s in students if s.strip()]
    question_id_len = 4
    unsent_questions = {}
    error_questions = {}
    result_table = pd.DataFrame(index=students)
    
    print(students)
    print(file_names)
    print(question_files)
    
    # Перебор всех загруженных файлов
    for i in range(len(file_names)):
        # Читаем только xlsx
        if file_names[i].split('.')[-1] != 'xlsx':
            continue
        question_id = file_names[i][:question_id_len] 
        
        table = pd.read_excel(question_files[i])

        # Проверяем, что значение в ячейке [1, 1] является строкой и начинается с 'не'
        if table.iloc[0, 1][:2] == 'не':
            add_question_info(
                unsent_questions,
                question_id,
                answers_list=file_names,
                date=table.iloc[1, 1],  
                question_text=table.columns[1]
            )
            continue

        max_ball = float(table.iloc[2, 1])
        
        try:
            if np.isnan(max_ball) or max_ball<=0:
                # запоминаем информацию
                add_question_info(
                    error_questions,
                    question_id,
                    answers_list=file_names,
                    date=table.iloc[1, 1],
                    question_text=table.columns[1],
                    info="Некорректный максимальный балл",
                )
                continue

            table = table.iloc[7:, [1, 3]]  # Выделяем студентов и их баллы
            table.columns = ['Студент', int(file_names[i].split(' ')[0])]
            table = table.set_index('Студент')
            table = table / max_ball  # нормировка

            result_table = result_table.join(table, how='left')
            
        except Exception as e:
            # запоминаем информацию
            add_question_info(
                error_questions,
                question_id,
                answers_list=file_names,
                date=table.iloc[1, 1],
                question_text=table.columns[1],
                info=f"Что-то пошло не так: {e}",
            )
     
   
    result_table = result_table.loc[students].fillna(0)

    
    return result_table, unsent_questions, error_questions


# --- БЛОК 3: Обработка посещаемости ---
def process_attendance(student_list, file_path, teachers):
    from openpyxl import load_workbook
    wb = load_workbook(file_path)
    sheet = wb.active

    # Разбиваем объединенные ячейки
    merged_ranges = sheet.merged_cells.ranges
    data = []

    for row in sheet.iter_rows(values_only=True):
        data.append(list(row))

    for merged in merged_ranges:
        top_left_value = sheet.cell(merged.min_row, merged.min_col).value
        for row in range(merged.min_row, merged.max_row + 1):
            for col in range(merged.min_col, merged.max_col + 1):
                if data[row - 1][col - 1] is None:
                    data[row - 1][col - 1] = top_left_value

    # Создание DataFrame
    df = pd.DataFrame(data)

    first_row = df.iloc[0]  # Преподаватели
    second_row = df.iloc[1]  # Названия занятий
    third_row = df.iloc[2]  # Дата и время

    students_data = df.iloc[3:].reset_index(drop=True)
    students_data.columns = ['Автор'] + list(range(1, len(students_data.columns)))

    students_data['Автор'] = students_data['Автор'].str.strip()
    students_data = students_data.set_index('Автор').reindex(student_list).reset_index()

    metadata = pd.DataFrame({
        'Автор': ['Преподаватель', 'Название занятия', 'Дата и время'],
        **{col: [first_row[col], second_row[col], third_row[col]] for col in range(1, len(first_row))}
    })

    students_data = pd.concat([metadata, students_data], ignore_index=True)

    def filter_columns_by_teachers(columns, teacher_list):
        return [col for col in columns if first_row[col] in teacher_list]

    # Фильтрация по блокам преподавателей
    result_tables = {}
    for block, teacher_list in teachers.items():
        filtered_columns = ['Автор'] + filter_columns_by_teachers(range(1, len(students_data.columns)), teacher_list)
        result_tables[block] = students_data[filtered_columns]

    return result_tables