
import subprocess
import nbformat
from pathlib import Path
import subprocess

import requests
import re

# --- Качество ноутбуков ---
class NotebookStyleChecker:
    def __init__(self, notebook_path: str):
        self.notebook_path = notebook_path
        self.issues = 0
        self.notebook = self.load_notebook()

    def load_notebook(self):
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            return nbformat.read(f, as_version=4)

    def check_spelling(self) -> list:
        """Проверяет орфографию Markdown-ячейки, исключая веб-ссылки, код в кавычках и формулы."""
        issues = []
        url = "https://speller.yandex.net/services/spellservice.json/checkText"

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "markdown":
                lines = cell.source.splitlines()
                for line in lines:
                    line = re.sub(r"https?://\S+", "", line)  # Убрать веб-ссылки
                    line = re.sub(r"`[^`]+`", "", line)  # Убрать код в кавычках
                    line = re.sub(r"\$(?!\$)([^$]+?)\$(?!\$)", "", line)  # Убрать формулы

                    try:
                        response = requests.get(url, params={"text": line})
                        errors = response.json()
                    except Exception:
                        continue

                    for error in errors:
                        word = error["word"]
                        suggestions = ", ".join(error.get("s", []))
                        issues.append({
                            "cell": i,
                            "line": line.strip(),
                            "word": word,
                            "suggestions": suggestions
                        })
        return issues

def run_nbqa_tool(tool: str, notebook_path: str, additional_args=None):
    """Выполняет указанный nbqa инструмент."""
    additional_args = additional_args or []
    command = ["nbqa", tool, notebook_path, *additional_args]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

# Функция для удаления ANSI escape кодов
def remove_ansi_escape_codes(text: str) -> str:
    """Удаление ANSI escape кодов из текста."""
    
    return re.sub(r'\x1b\[.*?m', '', text)
def parse_and_format_errors(tool: str, output: str, success: bool) -> str:
    """
    Функция для парсинга и форматирования ошибок/успешных сообщений
    в зависимости от статуса выполнения инструмента.
    """
    lines = output.splitlines()
    formatted_output = []

    if success:
        # Если выполнение инструмента прошло успешно, добавляем блок успешных сообщений
        formatted_output.append(f"✅ **Успех! {tool} завершён без ошибок.**")
        for line in lines:
            formatted_output.append(f"  {line.strip()}")  # Убираем лишние точки
    else:
        # Если произошла ошибка, добавляем блок ошибок
        formatted_output.append(f"⚠️ **Ошибка! {tool} завершён с ошибками.**")
        for line in lines:
            formatted_output.append(f"  {line.strip()}")  # Убираем лишние точки
    
    # Возвращаем отформатированные сообщения
    return "\n".join(formatted_output)