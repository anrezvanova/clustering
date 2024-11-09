import os
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.analysis import StandardAnalyzer
from nbformat import read
import glob

# Создаем схему индекса
def create_schema():
    return Schema(
        title=TEXT(stored=True),
        path=ID(stored=True),  # Хранит путь к файлу
        content=TEXT(stored=True, analyzer=StandardAnalyzer())  # Содержимое ячеек
    )

# Функция для индексации всех ноутбуков в указанной папке
def index_notebooks(root_folder, index_path):
    """
    root_folder: Путь к корневой папке с ноутбуками, откуда начинается сохранение относительных путей.
    index_path: Путь для сохранения индекса.
    """
    # Проверяем, существует ли папка для индекса
    if not os.path.exists(index_path):
        os.makedirs(index_path)

    # Создаем индекс в указанной папке
    schema = create_schema()
    idx = create_in(index_path, schema)
    writer = idx.writer()

    # Обрабатываем все .ipynb файлы в указанной папке
    for notebook_file in glob.glob(os.path.join(root_folder, "**", "*.ipynb"), recursive=True):
        try:
            with open(notebook_file, 'r', encoding='utf-8') as f:
                notebook = read(f, as_version=4)
                # Объединяем содержимое всех markdown ячеек
                content = " ".join(cell['source'] for cell in notebook.cells if cell.cell_type == 'markdown')

                # Получаем относительный путь от корневой папки
                relative_path = os.path.relpath(notebook_file, root_folder)

                # Добавляем файл в индекс
                writer.add_document(
                    title=os.path.basename(notebook_file),
                    path=relative_path,  # Сохраняем относительный путь
                    content=content
                )
        except Exception as e:
            print(f"Ошибка при обработке {notebook_file}: {e}")
    
    # Закрываем writer после завершения
    writer.commit()
    print(f"Индекс для папки {root_folder} успешно создан.")

# Укажите папки с ноутбуками и пути для сохранения индексов
notebook_folders = {
    r"C:\Users\milka\Ноутбуки\Ph@DS ОСЕНЬ 2023": r"C:\Users\milka\OneDrive\Рабочий стол\clustering\index\Ph@ds осень 2023",
    r"C:\Users\milka\Ноутбуки\PhDS_ВЕСНА_2024": r"C:\Users\milka\OneDrive\Рабочий стол\clustering\index\Ph@ds весна 2024 (Статистика ФБМФ)"
}

# Индексируем каждую папку из списка
for root_folder, index_path in notebook_folders.items():
    if not os.path.exists(index_path):  # Проверка, если индекс еще не создан
        print(f"Создание индекса для папки: {root_folder}")
        index_notebooks(root_folder, index_path)
    else:
        print(f"Индекс для {root_folder} уже существует. Пропускаем.")

print("Все папки проиндексированы.")

#Посмотреть индексы:
#from whoosh.index import open_dir

#def view_index_contents(index_path):
    # Открываем индекс
    #idx = open_dir(index_path)
    
    # Создаем поисковик для получения всех документов
    #with idx.searcher() as searcher:
        # Ищем все документы
        #results = searcher.all_stored_fields()
        
        # Выводим каждый документ, включая поля
        #for result in results:
            #print(f"Title: {result['title']}")
            #print(f"Path: {result['path']}")
            #print(f"Content: {result['content'][:200]}...")  # Показываем первые 200 символов содержимого
            #print("-" * 50)

# Пример использования:
#index_path = "C:/Users/milka/OneDrive/Рабочий стол/clustering/index/Ph@ds весна 2024 (Статистика ФБМФ)"  # Укажите путь к папке с индексами
#view_index_contents(index_path)