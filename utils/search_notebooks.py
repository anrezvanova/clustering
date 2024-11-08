import os
import json


def search_in_notebooks(folder_path, search_word):
    # Проходим по всем файлам в папке и подпапках
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".ipynb"):
                notebook_path = os.path.join(root, file)
                try:
                    with open(notebook_path, "r", encoding="utf-8") as f:
                        notebook_data = json.load(f)
                        # Ищем слово в ячейках
                        for cell in notebook_data.get("cells", []):
                            if (
                                cell.get("cell_type") == "code"
                                or cell.get("cell_type") == "markdown"
                            ):
                                source = "".join(cell.get("source", ""))
                                if search_word in source:
                                    print(f"Найдено в файле: {notebook_path}")
                                    break
                except Exception as e:
                    print(f"Ошибка при обработке файла {notebook_path}: {e}")


# Указываем путь к папке на рабочем столе и слово для поиска
desktop_path = os.path.join(
    os.path.expanduser("~"), "Ноутбуки"
)  # Замените 'your_folder' на имя папки
search_word = "Проверка гипотез"  # Замените на слово, которое хотите искать

# Запускаем поиск
search_in_notebooks(desktop_path, search_word)
