import pandas as pd
import math
import re
import os
import numpy as np
import torch
from torch import Tensor
from transformers import AutoTokenizer, AutoModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import nltk
from nltk.corpus import stopwords
from openpyxl.styles import Font, PatternFill
from collections import defaultdict
from rake_nltk import Rake, Metric

import io
import streamlit as st


nltk.download('stopwords')
nltk.download('punkt')
russian_stopwords = stopwords.words("russian")

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

def find_task_sheets(xls):
    """
    Находит все листы, которые начинаются с "Задача" и заканчиваются цифрой.

    :param xls: объект Excel-файла, загруженного через pd.ExcelFile.
    :return: Список найденных листов.
    """
    task_sheets = [sheet for sheet in xls.sheet_names if re.match(r'Задача \d+', sheet)]
    return task_sheets

def clean_column_headers(df):
    """
    Обрабатывает заголовки таблицы, чтобы извлечь правильные имена колонок.

    :param df: DataFrame с данными.
    :return: DataFrame с очищенными заголовками.
    """
    # Используем 5-ю строку как заголовки колонок
    df.columns = df.iloc[4]
    # Удаляем первые 5 строк, которые не содержат данные
    df = df.drop([0, 1, 2, 3, 4])
    df = df.reset_index(drop=True)
     
    return df

# Функция для преобразования индекса колонки в Excel-формат
def get_excel_column_name(n):
    result = ""
    while n >= 0:
        result = chr(n % 26 + ord('A')) + result
        n = n // 26 - 1
    return result

# Функция для получения координат ячейки
def get_cell_coordinates(row, col):
    col_letter = get_excel_column_name(col)  # Преобразование индекса колонки в буквы (A, B, ..., Z, AA, AB и т.д.)
    return f"{col_letter}{row + 7}"  # Добавляем 7 к индексу строки, чтобы номер строки соответствовал Excel, так как удаляем шапку

def make_column_names_unique(df):
    """
    Делает названия колонок уникальными, добавляя суффиксы в случае повторений (без этого происходит лаг).

    :param df: DataFrame с данными.
    :return: DataFrame с уникальными заголовками колонок.
    """
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    
    return df
     
def find_comment_columns(df, base_columns):
    """
    Ищет все колонки, связанные с комментариями, включая уникальные названия.

    :param df: DataFrame с данными.
    :param base_columns: Базовые названия колонок для поиска (например, "Комментарий" и "Индивидуальный комментарий").
    :return: Список найденных колонок.
    """
    comment_columns = []
    for col in df.columns:
        for base_col in base_columns:
            if col.startswith(base_col):  # Поиск колонок, которые начинаются с базового имени
                comment_columns.append(col)
    return comment_columns

def find_columns_in_sheets(file_path, target_columns):
    """
    Ищет целевые колонки на листах Excel, которые соответствуют шаблону "Задача N".

    :param file_path: Путь к Excel файлу.
    :param target_columns: Целевые колонки для поиска.
    :return: Словарь с данными из найденных колонок по листам.
    """
    xls = pd.ExcelFile(file_path)
    task_sheets = find_task_sheets(xls)
    
    all_data = []
    cell_coordinates = {}
     # Создаем словарь соответствий

    for sheet in task_sheets:
        print(f"\nЛист: {sheet}")
        df = pd.read_excel(xls, sheet_name=sheet)
        df = clean_column_headers(df)
        
        # Сброс индексов на случай, если в данных есть дубликаты индексов
        df = df.reset_index(drop=True)
          # Обнуляем словарь для текущего листа
        
        
        #for row in range(df.shape[0]):
            #for col in range(df.shape[1]):
                #print(f"Текущая колонка: {col}, Имя колонки: {get_excel_column_name(col)}")
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                cell_value = df.iat[row, col]
                
                coord = get_cell_coordinates(row, col)  # Получаем координаты текущей ячейки
                cell_coordinates[(row, col)] = coord  # Сохраняем координаты в словаре
                #print(f"Значение ячейки ({row}, {col}): {cell_value}, Координаты: {coord}")
                df.iat[row, col] = f"{cell_value} + {coord}"
                #print(f"Обновленная ячейка ({row}, {col}): {df.iat[row, col]}")
        #print(cell_coordinates)
        #print(df.head(40))
       
        # Проверяем наличие целевых колонок
        if all(col in df.columns for col in target_columns):
            #print(f"Найдены все колонки на листе: {sheet}")
            #print(df.head(5))  # Показываем первые 5 строк

             # Сохраняем координаты ячеек до внесения изменений в DataFrame
            
            df['Задача'] = sheet  # Добавляем колонку с названием задачи
            df = df[target_columns + ['Задача']]
            
            #print(f"DataFrame перед добавлением:\n{df.head(40)}\n")
            
            # Проверка на дублирующиеся названия колонок
            if df.columns.duplicated().any():
                df = make_column_names_unique(df)
                
            stop_bot_index = df[df.apply(lambda row: row.astype(str).str.contains('STOP BOT').any(), axis=1)].index
            if len(stop_bot_index) > 0:
                stop_bot_index = stop_bot_index[0]  # Берем первую найденную строку с "STOP BOT"
                df = df.iloc[:stop_bot_index]  # Оставляем строки до этой строки
            
            all_data.append(df)
            #print(f"Все1............... {all_data}")
            #print(cell_coordinates)  - все хорошо         
        else:
            print(f"Не все колонки найдены на листе: {sheet}")
    #print(cell_coordinates)  
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        
        #print(f"Все1............... Индивидуальный комментарий_19: {combined_data['Индивидуальный комментарий_19']}, Задача: {combined_data['Задача']}")
        if not combined_data.index.is_unique:
            print("Обнаружены дублирующиеся индексы после объединения данных.")
            combined_data = combined_data.reset_index(drop=True)
        #print(f"Все1............... {combined_data.head(60)}")  
        # Возвращаем combined_data и cell_coordinates (это важно)
        
        return combined_data, cell_coordinates
    else:
        # Возвращаем пустой DataFrame и пустой словарь, если данные не были найдены
        return pd.DataFrame(), {}

def creating_dictionary(df, base_columns_i, base_columns_o, cell_coordinates):
    """
    Создает словарь отфильтрованных комментариев с их исходными координатами.

    :param df: DataFrame с данными.
    :param base_columns_i: Базовые названия колонок с индивидуальными комментариями.
    :param base_columns_o: Базовые названия колонок с общими комментариями.
    :return: Словарь с отфильтрованными комментариями.
    """
    # Удаляем лишние пробелы из названий колонок
    df.columns = df.columns.str.strip()
    #print(f"Все1............... {df.head(60)}")
    
    # Делаем названия колонок уникальными, если есть дубли
    df = make_column_names_unique(df)
    # Найти все колонки с комментариями (индивидуальные и общие)
    comment_columns_i = find_comment_columns(df, [base_columns_i])
    comment_columns_o = find_comment_columns(df, [base_columns_o])

    # Заполнение пропущенных значений и удаление строк с короткими или пустыми комментариями
    for col in comment_columns_i + comment_columns_o:
        df.loc[:, col] = df[col].fillna('').str.strip()
    
    # Фильтруем строки, где все комментарии слишком короткие или пустые
    df = df[~df[comment_columns_i + comment_columns_o].apply(lambda row: all(len(val) <= 5 for val in row), axis=1)]
    # Объединяем комментарии из всех колонок в одну колонку для кластеризации
    
    comment_rows = []
     # Обрабатываем комментарии и сохраняем их исходные координаты
    for index, row in df.iterrows():
        for col in comment_columns_o:  # Обрабатываем комментарии справа
            if row[col]:
                
                comment_rows.append({
                    'Ячейка': cell_coordinates[(index, df.columns.get_loc(col))],
                    'Студент': row['Студент'],
                    'Проверяющий': row['Проверяющий'],
                    'Задача': row['Задача'],
                    'Комментарии': "*" + row[col],
                    'Тип комментария': "Общий комментарий",
                
                })
        
        for col in comment_columns_i:  # Обрабатываем индивидуальные комментарии
            if row[col]:
                comment_rows.append({
                    'Ячейка': cell_coordinates[(index, df.columns.get_loc(col))],
                    'Студент': row['Студент'],
                    'Проверяющий': row['Проверяющий'],
                    'Задача': row['Задача'],
                    'Комментарии': row[col],
                    'Тип комментария': "Индивидуальный комментарий",
                    
                })
    
    comments_df = pd.DataFrame(comment_rows)

    experts_comments_dict = {}

    for _, row in comments_df.iterrows():
        # Проверяем наличие "+" и что первая часть не является NaN
        if '+' in row['Комментарии'] and pd.notna(row['Комментарии'].split('+')[0].strip()):
            student = row['Студент']
            reviewer = row['Проверяющий']
            
            # Извлекаем ключ и значение из 'Комментарии'
            comment_key = row['Комментарии'].split('+')[1].strip()
            comment_value = row['Комментарии'].split('+')[0].strip()
            
            # Проверка на 'nan' и '*nan' в значении комментария
            if comment_value.lower() != 'nan' and '*nan' not in comment_value.lower():
                # Если студента еще нет в словаре, добавляем его с вложенной структурой
                if student not in experts_comments_dict:
                    experts_comments_dict[student] = {'Проверяющий': reviewer, 'Комментарии': {}}
                
                # Добавляем или обновляем комментарий для данного студента
                experts_comments_dict[student]['Комментарии'][comment_key] = comment_value

    #print(df.head(20))
    #print(experts_comments_dict)   # Для проверки
    
    return experts_comments_dict

class E5Embedder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained('intfloat/multilingual-e5-small')
        self.model = AutoModel.from_pretrained('intfloat/multilingual-e5-small')

    @staticmethod
    def average_pool(last_hidden_states: Tensor,
                     attention_mask: Tensor) -> Tensor:
        '''avg pooling для модели E5'''
        last_hidden = last_hidden_states.masked_fill(
            ~attention_mask[..., None].bool(), 0.0)
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

    def get_embeddings(self, comments):
        # get text embeddings
        input_texts = ["passage: " + str(ans) for ans in comments]
        quantile = np.quantile([len(ans.split())
                               for ans in input_texts], 0.975)
        MAX_LENGTH = int(2 ** np.ceil(np.log2(quantile)))
        batch_dict = self.tokenizer(
            input_texts, max_length=MAX_LENGTH, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            outputs = self.model(**batch_dict)
        embeddings = self.average_pool(
            outputs.last_hidden_state, batch_dict['attention_mask']).detach().numpy()
        return embeddings


class Clustering:
    def __init__(self, N_NEIGHBORS=3, PRINT_LIMIT=5):
        '''
        * N_NEIGHBORS: max количество представителей 1 кластера
        * PRINT_LIMIT: max количество выводимых кластеров'''

        self.e5_embedder = E5Embedder()
        self.one_word_answers = ['да', 'нет', 'верно',
                                 'неверно', 'является', 'можно', 'нельзя', 'можем']
        self.N_NEIGHBORS = N_NEIGHBORS  # кол-во представителей
        self.PRINT_LIMIT = PRINT_LIMIT  # кол-во кластеров

    @staticmethod
    def extract_keyphrases(text):
        '''выделяет из text num_keyphrases фраз'''

        stopwords_ru = stopwords.words("russian")
        
        for w in ['да', 'нет', 'не']:
            stopwords_ru.remove(w)
        
        r = Rake(stopwords=stopwords_ru, punctuations='.()!?',
                 language='russian', min_length=1,
                 ranking_metric=Metric.WORD_FREQUENCY,
                 include_repeated_phrases=False)

        r.extract_keywords_from_text(text)
        keyphrases = r.get_ranked_phrases()
        return keyphrases

    
    def cluster(self, experts_comments_dict: dict[str, any]) -> str:
        '''
        Кластеризует комментарии экспертов и возвращает информацию о кластерах.

        * experts_comments_dict -- словарь, где ключи - ячейка комментария, значения - комментарии.
        Комментарии могут принимать вид строки или np.nan.
        '''
        lengths = []
        comments = []
        keys = []       # Сохраняем ключи для комментариев
        students = []   # Сохраняем соответствующих студентов
        reviewers = []  # Сохраняем соответствующих проверяющих

        for student, data in experts_comments_dict.items():
            reviewer = data['Проверяющий']
            for cell_key, com in data['Комментарии'].items():
                if isinstance(com, str) and not pd.isna(com):
                    comments.append(f'{com}')
                    keys.append(cell_key)      # Сохраняем ключ ячейки
                    students.append(student)   # Сохраняем имя студента
                    reviewers.append(reviewer) # Сохраняем имя проверяющего
                    lengths.append(len(com.split(" ")))  # Длина комментария
        
        # Сохраняем текст для кластеризации
        self.texts = comments

        # Получаем эмбеддинги и нормализуем
        self.embeddings = self.e5_embedder.get_embeddings(self.texts)
        self.embeddings = StandardScaler().fit_transform(self.embeddings)

        # Определяем стоп-слова и строим TF-IDF матрицу
        stopwords_ru = stopwords.words("russian")
        vectorizer = TfidfVectorizer(stop_words=stopwords_ru, min_df=2)

        # Применяем DBSCAN для кластеризации
        clustering = DBSCAN(eps=22, min_samples=2).fit(self.embeddings)
        unique = np.unique(clustering.labels_, return_counts=True)
        big_cluster_ids = [i for (i, count) in zip(*unique) if count > 2]

        # Заменяем небольшие кластеры на -1 (шум)
        self.labels = [l if l in big_cluster_ids else -1 for l in clustering.labels_]

        # Отфильтровываем шум и сохраняем комментарии, кластеры, ключи, студента и проверяющего
        filtered_comments_labels_keys = []
        for i in range(len(comments)):
            if self.labels[i] != -1:  # Игнорируем шум
                filtered_comments_labels_keys.append((comments[i], self.labels[i], keys[i], students[i], reviewers[i]))

        if filtered_comments_labels_keys == []:
            print("Нет кластеров")
            comments_df = pd.DataFrame({
                'Ячейка': [],
                'Студент': [],
                'Проверяющий': [],
                'Комментарии': [],
                'Кластер': []
            })
            
            return comments_df

        else:
            # Разворачиваем отфильтрованные данные для создания DataFrame
            filtered_comments, filtered_labels, filtered_keys, filtered_students, filtered_reviewers = zip(*filtered_comments_labels_keys)

            comments_df = pd.DataFrame({
                'Ячейка': filtered_keys,
                'Студент': filtered_students,
                'Проверяющий': filtered_reviewers,
                'Комментарии': filtered_comments,
                'Кластер': filtered_labels
            })

            # Присваиваем уникальные номера кластерам
            unique_labels = {label: i + 1 for i, label in enumerate(sorted(set(filtered_labels)))}
            comments_df['Кластер'] = comments_df['Кластер'].map(unique_labels)

            # Сортируем и возвращаем DataFrame с нужными колонками
            comments_df = comments_df.sort_values(by='Кластер').reset_index(drop=True)
            #print(f"вывод кластеринга {comments_df}")
            return comments_df

def create_formatted_dataframe(dataframes):
    # Список для хранения обработанных датафреймов
    formatted_dfs = []
    
    #переформирование списка задач для соответствия результатов полученных фреймов кластеризации в итоговой таблице
    task_numbers = []
    for df in dataframes:
        task_numbers.append(df["Задача"].tolist()[0])

    for task, df in zip(task_numbers, dataframes):
        # Добавляем заголовок с номером задачи
        header_df = pd.DataFrame({ 
            "Номер": [f"--- {task} ---"], 
            "Студент": [""], 
            "Проверяющий": [""], 
            "Комментарии": [""]
        })
        formatted_dfs.append(header_df)
        
        # Обработка кластеров
        for cluster_num, cluster_df in df.groupby("Кластер"):
            # Добавляем строку с номером кластера
            cluster_header = pd.DataFrame({
                "Номер": [f"Кластер {cluster_num}:"], 
                "Студент": [""], 
                "Проверяющий": [""], 
                "Комментарии": [""]
            })
            formatted_dfs.append(cluster_header)
            
            # Сбрасываем индексы и добавляем кластерные данные
            formatted_dfs.append(cluster_df.reset_index(drop=True))
    
    # Объединяем все обработанные части в один датафрейм
    final_df = pd.concat(formatted_dfs, ignore_index=True)

    return final_df


    
def save_results_to_excel(df, base_file_name):
    """
    Сохраняет DataFrame в Excel и выводит результат в Streamlit для скачивания.
    
    :param df: DataFrame с результатами кластеризации.
    :param base_file_name: Название файла для сохранения.
    """
    # Генерируем имя файла
    file_name = f"{base_file_name}.xlsx"
    
    # Создаем буфер для временного хранения файла
    buffer = io.BytesIO()

    # Создаем Excel файл в памяти
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.fillna("", inplace=True)
        df.to_excel(writer, index=False, sheet_name='Результаты')

        workbook = writer.book
        worksheet = writer.sheets['Результаты']

        # Форматирование ширины колонок
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter  # Получаем букву колонки
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = max_length + 2  # Добавляем небольшой отступ
            worksheet.column_dimensions[column].width = adjusted_width

        # Форматирование ячеек с названиями задач
        for row in worksheet.iter_rows():
            for cell in row:
                if '---' in str(cell.value):  # Названия задач начинаются с '---'
                    cell.fill = PatternFill(start_color='00FF00', end_color='00FF00', fill_type='solid')  # Зеленый фон
                    cell.font = Font(bold=True)  # Жирный шрифт

                if 'Кластер' in str(cell.value):  # Названия кластеров
                    cell.font = Font(bold=True)  # Жирный шрифт

    # Перемещаем курсор в начало буфера
    buffer.seek(0)

    # Кнопка для скачивания файла через Streamlit
    st.download_button(
        label="Скачать результаты в Excel",
        data=buffer,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.success(f"Файл '{file_name}' успешно создан и готов к скачиванию.")
    return df

def main(file_path, student_column, reviewer_column, comment_column_i, comment_column_o):
    target_columns = [student_column, reviewer_column, comment_column_i, comment_column_o]
    all_task_data, cell_coordinates = find_columns_in_sheets(file_path, target_columns)
    task_names = all_task_data['Задача'].unique()

    clustering_instance = Clustering()

    list_clustered_info = []
    for task in task_names:
        task_data = all_task_data[all_task_data['Задача'] == task]
        #task_data = make_column_names_unique(task_data)
        if not task_data.empty:
           print(f"Кластеризация для задачи {task}")
               # Создаем словарь комментариев для текущей задачи
           experts_comments_dict = creating_dictionary(task_data, comment_column_i, comment_column_o, cell_coordinates)
           
           # Выполняем кластеризацию
           if not experts_comments_dict:  # Проверка, пуст ли словарь
               print("Внимание: experts_comments_dict пустой. Пропускаем кластеризацию.")
               continue
           clustered_info = clustering_instance.cluster(experts_comments_dict)
           
           clustered_info['Задача'] = task  # Добавляем колонку с названием задачи

           if not clustered_info.empty:
              list_clustered_info.append(clustered_info)
           else:
               print("Данные не были найдены.")
    
    

    final_df = create_formatted_dataframe(list_clustered_info)
    final_df = final_df.drop(columns=["Кластер","Задача"])
    final_df["Студент"] = final_df["Студент"].apply(lambda x: x.split("+")[0] if isinstance(x, str) else x)
    final_df["Проверяющий"] = final_df["Проверяющий"].apply(lambda x: x.split("+")[0] if isinstance(x, str) else x)
    base_file_name = "clustering_" + os.path.splitext(os.path.basename(file_path))[0]
    return save_results_to_excel(final_df, base_file_name)








