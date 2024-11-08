import os
import json
from whoosh import index
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser

def create_index(folder_path):
    """
    Создает индекс для ноутбуков в указанной папке.
    Индекс сохраняется в папке 'index', если он уже существует, то не создается заново.
    """
    # Определяем схему для индекса
    schema = Schema(
        path=TEXT(stored=True),  # Путь к файлу ноутбука
        content=TEXT(stored=True)  # Содержимое ноутбука
    )

    # Проверяем, существует ли индекс
    index_dir = "index"
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
        idx = index.create_in(index_dir, schema)
        writer = idx.writer()

        # Проходим по всем файлам в папке
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".ipynb"):  # Работаем только с ноутбуками
                    notebook_path = os.path.join(root, file)
                    try:
                        with open(notebook_path, "r", encoding="utf-8") as f:
                            notebook_data = json.load(f)
                            # Извлекаем содержимое ячеек (code и markdown)
                            content = ""
                            for cell in notebook_data.get("cells", []):
                                if cell.get("cell_type") == "code" or cell.get("cell_type") == "markdown":
                                    content += "".join(cell.get("source", ""))
                            
                            # Добавляем документ в индекс
                            writer.add_document(path=notebook_path, content=content)
                    except Exception as e:
                        print(f"Ошибка при обработке файла {notebook_path}: {e}")

        writer.commit()
        print("Индексирование завершено и индекс создан.")
    else:
        print("Индекс уже существует. Можно выполнять поиск.")


def search_in_index(search_word):
    """
    Ищет слово в индексированных ноутбуках.
    """
    idx = index.open_dir("index")
    searcher = idx.searcher()
    query = QueryParser("content", schema=idx.schema).parse(search_word)

    results = searcher.search(query)

    # Выводим результаты
    result_paths = [hit["path"] for hit in results]
    return result_paths