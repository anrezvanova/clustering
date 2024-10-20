import pandas as pd
import re
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
import nltk
from nltk.corpus import stopwords
from openpyxl.styles import Font, PatternFill
import io
import streamlit as st


nltk.download('stopwords')
russian_stopwords = stopwords.words("russian")

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
    
    for sheet in task_sheets:
        print(f"\nЛист: {sheet}")
        df = pd.read_excel(xls, sheet_name=sheet)
        df = clean_column_headers(df)
        
         # Сброс индексов на случай, если в данных есть дубликаты индексов
        df = df.reset_index(drop=True)
        
        # Проверяем наличие целевых колонок
        if all(col in df.columns for col in target_columns):
            print(f"Найдены все колонки на листе: {sheet}")
            print(df.head(5))  # Показываем первые 60 строк

        #Отладка, если код не видит комментарии, до кластеризации ли он их не видит
        #if sheet == "Задача 1":
            #print(f"Найдены все колонки на листе: {sheet}")
            #print(df.iloc[:60, :10]) 
            #for row in range(60):
                #for col in range(10):
                    #cell_value = df.iloc[row, col]
                    #print(f"Тип данных ячейки [{row}, {col}] -> {type(cell_value)}: {cell_value}")
            
            df['Задача'] = sheet  # Добавляем колонку с названием задачи
            df = df[target_columns + ['Задача']]

           
            
            print(f"DataFrame перед добавлением:\n{df.head()}\n")
            # Проверка на дублирующиеся названия колонок
            if df.columns.duplicated().any():
                #print(f"Обнаружены дублирующиеся колонки: {df.columns[df.columns.duplicated()]}")
                df = make_column_names_unique(df)
            stop_bot_index = df[df.apply(lambda row: row.astype(str).str.contains('STOP BOT').any(), axis=1)].index
            if len(stop_bot_index) > 0:
                stop_bot_index = stop_bot_index[0]  # Берем первую найденную строку с "STOP BOT"
                df = df.iloc[:stop_bot_index]  # Оставляем строки до этой строки
            all_data.append(df)
        else:
            print(f"Не все колонки найдены на листе: {sheet}")
    
    if all_data:
        # Объединяем все данные, игнорируя индексы
        combined_data = pd.concat(all_data, ignore_index=True)

        # Проверяем уникальность индексов после объединения
        if not combined_data.index.is_unique:
            print("Обнаружены дублирующиеся индексы после объединения данных.")
            combined_data = combined_data.reset_index(drop=True)
        
        return combined_data
    else:
        return pd.DataFrame()
    
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

def cluster_comments(df, base_columns_i, base_columns_o):
    """
    Выполняет кластеризацию комментариев с обработкой всех колонок комментариев (индивидуальных и общих).

    :param df: DataFrame с данными.
    :param base_columns_i: Базовые названия колонок с индивидуальными комментариями.
    :param base_columns_o: Базовые названия колонок с общими комментариями.
    :return: DataFrame с результатами кластеризации.
    """
    # Удаляем лишние пробелы из названий колонок
    df.columns = df.columns.str.strip()
    
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
    
    for index, row in df.iterrows():
        for col in comment_columns_o:  # Обрабатываем свободные комментарии справа
            if row[col]:
                comment_rows.append((row['Студент'], row['Проверяющий'], row['Задача'], "*" + row[col], "Индивидуальный комментарий"))
        for col in comment_columns_i:  # Обрабатываем комментарии под колонками
            if row[col]:
                comment_rows.append((row['Студент'], row['Проверяющий'], row['Задача'], row[col], "Общий комментарий"))

    # Проверка, если после фильтрации комментарии все еще пусты
    if not comment_rows:
        raise ValueError("После фильтрации не осталось данных для обработки.")

    # Создаем DataFrame для кластеризации
    comments_df = pd.DataFrame(comment_rows, columns=['Студент', 'Проверяющий', 'Задача', 'Комментарии', 'Тип комментария'])

    #print(f"После фильтрации и разделения комментариев: {len(comments_df)} строк")
    #print(comments_df.head(20))

    # Кластеризация комментариев
    vectorizer = TfidfVectorizer(stop_words=russian_stopwords)
    X = vectorizer.fit_transform(comments_df['Комментарии'])
    
    # Использование DBSCAN для кластеризации
    dbscan = DBSCAN(eps=0.89, min_samples=2, metric='cosine')
    comments_df['Кластер'] = dbscan.fit_predict(X)

    # Удаляем шум (кластеры с меткой -1)
    comments_df = comments_df[comments_df['Кластер'] != -1]
    
    # Проверяем, есть ли кластеры после удаления шума
    if comments_df.empty:
        raise ValueError("Все комментарии были отнесены к шуму (кластер -1).")
    
    # Увеличиваем номера кластеров на 1, чтобы начинались с 1
    comments_df['Кластер'] += 1

    # Получаем центры кластеров для дальнейшей обработки
    centers = pd.Series(index=comments_df['Кластер'].unique(), dtype=object)
    for cluster in centers.index:
        cluster_points = comments_df[comments_df['Кластер'] == cluster]
        centers[cluster] = cluster_points[['Студент', 'Проверяющий', 'Задача', 'Комментарии']].values.tolist()
    
    # Сортируем по кластеру
    comments_df = comments_df.sort_values(by=['Кластер'])

    return comments_df




def add_block_separation(df, student_column, reviewer_column, task_column, cluster_column):
    """
     Добавляет блоки кластеров с разделением строками и нумерацией.

    :param df: DataFrame с данными после кластеризации.
    :param student_column: Название колонки со студентом.
    :param reviewer_column: Название колонки с проверяющим.
    :param task_column: Название колонки с задачами.
    :param cluster_column: Название колонки с номером кластера.
    :return: DataFrame с блоками кластеров и разделениями.
    """
    final_data = []
    
    for task, task_group in df.groupby(task_column):
        final_data.append([f'--- {task} ---', '', '', ''])  # Заголовок задачи
        
        # Для каждой задачи разбиваем на кластеры
        for cluster_num, cluster_group in task_group.groupby(cluster_column):
            final_data.append([f'Кластер {cluster_num}:', '', '', ''])  # Заголовок кластера
            
            # Сбрасываем нумерацию для каждого кластера
            cluster_group = cluster_group.reset_index(drop=True)
            cluster_group['Номер'] = cluster_group.index + 1
            
            for _, row in cluster_group.iterrows():
                final_data.append([row['Номер'], row[student_column], row[reviewer_column], row['Комментарии']])
            
            # Добавляем пустую строку после каждого кластера
            final_data.append(['', '', '', ''])
    
    # Преобразуем в DataFrame
    final_df = pd.DataFrame(final_data, columns=['Номер', student_column, reviewer_column, 'Комментарии'])
    
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

def main(file_path, student_column, reviewer_column, comment_column_o, comment_column_i):
    target_columns = [student_column, reviewer_column, comment_column_o, comment_column_i]
    all_task_data = find_columns_in_sheets(file_path, target_columns)

    combined_df = pd.DataFrame()

    task_names = all_task_data['Задача'].unique()
    
    for task in task_names:
        task_data = all_task_data[all_task_data['Задача'] == task]
        task_data = make_column_names_unique(task_data)
        if not task_data.empty:
            #print(f"Кластеризация для задачи {task}")
            clustered_df = cluster_comments(task_data, comment_column_i, comment_column_o)
            combined_df = pd.concat([combined_df, clustered_df])
    
    if not combined_df.empty:
        final_df = add_block_separation(combined_df, student_column, reviewer_column, 'Задача', 'Кластер')
        #print(f"Итоговая таблица с кластеризацией:\n{final_df}")
        base_file_name = "clustering_" + os.path.splitext(os.path.basename(file_path))[0]
        save_results_to_excel(final_df, base_file_name)
    else:
        print("Данные не были найдены.")






