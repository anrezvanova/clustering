import os
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.analysis import StemmingAnalyzer
from nbformat import read
import glob

# Создаем схему индекса
def create_schema():
    return Schema(
        title=TEXT(stored=True),
        path=ID(stored=True),
        content=TEXT(stored=True, analyzer=StemmingAnalyzer())
    )

# Функция для индексации всех ноутбуков в указанной папке
def index_notebooks(folder_path, index_path):
    # Проверяем, существует ли папка для индекса
    if not os.path.exists(index_path):
        os.makedirs(index_path)

    # Создаем индекс в указанной папке
    schema = create_schema()
    idx = create_in(index_path, schema)
    writer = idx.writer()

    # Обрабатываем все .ipynb файлы в указанной папке
    for notebook_file in glob.glob(os.path.join(folder_path, "*.ipynb")):
        try:
            with open(notebook_file, 'r', encoding='utf-8') as f:
                notebook = read(f, as_version=4)
                content = " ".join(cell['source'] for cell in notebook.cells if cell.cell_type == 'markdown')
                
                # Добавляем файл в индекс
                writer.add_document(
                    title=os.path.basename(notebook_file),
                    path=notebook_file,
                    content=content
                )
        except Exception as e:
            print(f"Ошибка при обработке {notebook_file}: {e}")
    
    # Закрываем writer после завершения
    writer.commit()
    print(f"Индекс для папки {folder_path} успешно создан.")

# Укажите папки с ноутбуками и пути для сохранения индексов
notebook_folders = {
    r"C:\Users\milka\Ноутбуки\Ph@DS ОСЕНЬ 2023": r"C:\Users\milka\OneDrive\Рабочий стол\clustering\index\Ph@ds осень 2023",
    r"C:\Users\milka\Ноутбуки\PhDS_ВЕСНА_2024": r"C:\Users\milka\OneDrive\Рабочий стол\clustering\index\Ph@ds весна 2024 (Статистика ФБМФ)"
}

# Индексируем каждую папку из списка
for folder_path, index_path in notebook_folders.items():
    if not os.path.exists(index_path):  # Проверка, если индекс еще не создан
        print(f"Создание индекса для папки: {folder_path}")
        index_notebooks(folder_path, index_path)
    else:
        print(f"Индекс для {folder_path} уже существует. Пропускаем.")

print("Все папки проиндексированы.")