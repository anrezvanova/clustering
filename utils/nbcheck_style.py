import ast
import inspect
import re
import sys
from typing import Dict, List, Optional

import nbformat
import numpy as np
import requests

# Рассматриваем безопасными следующие типы данных
SAFE_TYPES = (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Name)

SAFE_ARRAYS_AND_TENSORS = [
    # NumPy
    "numpy.array",
    "np.array",
    "numpy.matrix",
    "np.matrix",
    "numpy.linspace",
    "np.linspace",
    "numpy.zeros",
    "np.zeros",
    "numpy.ones",
    "np.ones",
    "numpy.arange",
    "np.arange",
    "numpy.eye",
    "np.eye",
    # Pandas
    "pandas.DataFrame",
    "pd.DataFrame",
    "pandas.Series",
    "pd.Series",
    # PyTorch
    "torch.tensor",
    "torch.tensor",
    "torch.FloatTensor",
    "torch.FloatTensor",
    "torch.zeros",
    "torch.zeros",
    "torch.ones",
    "torch.ones",
    "torch.linspace",
    "torch.linspace",
    "torch.arange",
    "torch.arange",
    "torch.eye",
    "torch.eye",
    "torch.IntTensor",
    "torch.IntTensor",
    # Слои и другие компоненты нейросетей (PyTorch)
    "torch.nn.Linear",
    "nn.Linear",
    "torch.nn.Conv2d",
    "nn.Conv2d",
    "torch.nn.MaxPool2d",
    "nn.MaxPool2d",
    "torch.nn.RNNCell",
    "nn.RNNCell",
    "torch.nn.RNN",
    "nn.RNN",
    "torch.nn.LSTM",
    "nn.LSTM",
    "torch.nn.GRU",
    "nn.GRU",
    "torch.nn.BatchNorm2d",
    "nn.BatchNorm2d",
]


class NotebookStyleChecker:
    def __init__(
        self, notebook_path: str, libraries: Optional[List[str]] = None, abbreviations: Optional[Dict[str, str]] = None
    ) -> None:
        """Инициализация проверщика стиля Jupyter Notebook.

        Параметры:
        - notebook_path (str): Путь к файлу Jupyter Notebook.
        - libraries (Optional[List[str]]): Список библиотек для анализа функций построения графиков. 
            По умолчанию используются ['matplotlib.pyplot', 'seaborn', 'plotly'].
        - abbreviations (Optional[Dict[str, str]]): Словарь сокращений для библиотек. 
            Например, {'matplotlib.pyplot': 'plt'}. По умолчанию: стандартные сокращения.
        """
        self.notebook_path = notebook_path
        self.notebook = None
        self.load_notebook()

        # Библиотеки по умолчанию
        self.libraries = libraries or ["matplotlib.pyplot", "seaborn", "plotly"]

        # Сокращения по умолчанию
        self.abbreviations = abbreviations or {"matplotlib.pyplot": "plt", "seaborn": "sns", "plotly": "px"}

        # Список функций для построения графиков
        self.plotting_functions = self.load_plotting_functions()

        self.issues = 0.0

        self.error_weights = {
            "check_text_volume": 350,
            "check_numbered_headings": 40,
            "check_function_docstrings": 80,
            "check_explanatory_markdown": 55,
            "check_short_code_cells": 90,
            "check_code_without_comments": 40,
            "check_variable_names": 30,
            "check_no_magic_constants": 15,
            "check_function_names": 45,
            "check_dashes_and_hyphens": 10,
            "check_computation_and_plotting": 35,
            "check_param_comments": 50,
            "check_graphics_style": 20,
            "check_spelling": 10,
        }

    def load_notebook(self) -> None:
        """Загружает Jupyter Notebook из указанного пути.

        Raises:
            FileNotFoundError: Если указанный файл не существует.
        """
        with open(self.notebook_path, encoding="utf-8") as f:
            self.notebook = nbformat.read(f, as_version=4)

    def cell_label(self, index: int, cell: nbformat.NotebookNode) -> str:
        """Формирует идентификатор ячейки на основе её индекса и номера
        выполнения In[...].

        Параметры:
            index (int): Индекс ячейки в списке notebook.cells.
            cell (nbformat.NotebookNode): Объект ячейки.

        Returns:
            str: Идентификатор ячейки в формате "Ячейка #<индекс> (In[<номер>])".
        """
        execution_count = cell.get("execution_count", None)
        execution_label = f"In[{execution_count}]" if execution_count is not None else "In[ ]"
        return f"Ячейка #{index + 1} ({execution_label})"

    def get_magic_commands(self) -> Dict[str, List[str]]:
        """Получает список всех доступных магических команд Jupyter Notebook.

        Returns:
            Dict[str, List[str]]: Словарь с ключами 'line' и 'cell', содержащий списки магических команд.
        """
        try:
            from IPython import get_ipython
            shell = get_ipython()
            if shell is None:
                return {"line": [], "cell": []}
            magics = shell.magics_manager.lsmagic()
            # Преобразуем в словарь, если результат имеет некорректный формат
            if not isinstance(magics, dict):
                return {"line": [], "cell": []}
            return magics
        except Exception as e:
            # Возвращаем пустой словарь, если IPython недоступен
            print(f"Не удалось получить магические команды: {e}")
            return {"line": [], "cell": []}

    def clean_code(self, code: str) -> str:
        """Убирает строки с магическими командами и командой bash из кода.

        Параметры:
            code (str): Исходный код ячейки.

        Returns:
            str: Код без магических команд.
        """
        magics = self.get_magic_commands()
        magic_line_commands = magics.get("line", [])
        magic_cell_commands = magics.get("cell", [])
        magic_prefix = "%"
        bash_prefix = "!"
        cleaned_code = []

        for line in code.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith(bash_prefix):
                continue
            elif any(stripped_line.startswith(magic_prefix + magic) for magic in magic_line_commands + magic_cell_commands):
                continue
            cleaned_code.append(line)

        return "\n".join(cleaned_code)

    def load_plotting_functions(self) -> List[str]:
        """Загружает функции для построения графиков из указанных библиотек.

        Returns:
            List[str]: Список функций, доступных для построения графиков.
        """
        plotting_functions = []

        # Перебираем все загруженные модули
        for module_name, module in sys.modules.items():
            if module_name in self.libraries:
                # Получаем все функции из этого модуля
                plotting_functions += self.get_functions_from_module(module, module_name)

        return plotting_functions

    def get_functions_from_module(self, module: object, module_name: str) -> List[str]:
        """Извлекает функции построения графиков из указанного модуля.

        Параметры:
            module (object): Модуль, из которого извлекаются функции.
            module_name (str): Имя модуля.

        Returns:
            List[str]: Список функций в формате '<сокращение модуля>.<имя функции>'.
        """
        # Используем сокращения для выбранных модулей
        abbreviation = self.abbreviations.get(module_name, module_name.split(".")[-1])

        return [f"{abbreviation}.{name}" for name, obj in inspect.getmembers(module) if inspect.isfunction(obj)]

    def check_text_volume(self, markdown_threshold: float = 0.25, comment_threshold: float = 0.05) -> str:
        """Проверяет объем текста в Markdown и кодовых ячейках.

        Параметры:
            markdown_threshold (float): Минимальная доля текста в Markdown (от общего объема текста).
            comment_threshold (float): Минимальная доля комментариев в кодовых ячейках (от объема текста кода).

        Returns:
            str: Сообщения о предупреждениях, если они есть.
        """
        messages = []
        total_markdown_chars = 0
        total_code_chars = 0
        total_comments_chars = 0

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "markdown":
                total_markdown_chars += len(cell.source)

            elif cell.cell_type == "code":
                code_lines = cell.source.splitlines()
                code_text = ""
                comment_text = ""

                for line in code_lines:
                    stripped_line = line.strip()

                    if stripped_line.startswith("#"):
                        comment_text += stripped_line
                    elif "#" in stripped_line:
                        code_part = stripped_line.split("#")[0].strip()
                        code_text += code_part
                        comment_part = stripped_line.split("#")[1].strip()
                        comment_text += comment_part
                    else:
                        code_text += stripped_line

                total_code_chars += len(code_text)
                total_comments_chars += len(comment_text)

        total_text_chars = total_markdown_chars + total_code_chars

        markdown_percentage = total_markdown_chars / total_text_chars if total_text_chars > 0 else 0
        if markdown_percentage < markdown_threshold:
            messages.append(
                f"[WARNING] Объем текста в Markdown составляет только {markdown_percentage * 100:.2f}% от общего объема текста. "
                f"Это меньше установленной границы {markdown_threshold * 100}%."
            )

        code_percentage = total_comments_chars / total_code_chars if total_code_chars > 0 else 0
        if code_percentage < comment_threshold:
            messages.append(
                f"[WARNING] Объем комментариев в коде составляет только {code_percentage * 100:.2f}% от общего объема текста в коде. "
                f"Это меньше установленной границы {comment_threshold * 100}%."
            )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_text_volume.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_numbered_headings(self) -> str:
        """Проверяет, что заголовки уровней ## и ### в Markdown ячейках
        нумерованы.

        Returns:
            str: Сообщение о предупреждениях, если есть ненумерованные заголовки.
        """
        messages = []
        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "markdown":
                lines = cell.source.splitlines()
                for line in lines:
                    if line.startswith("##") and not line.startswith("####"):
                        heading_content = line.lstrip("# ").strip()
                        if not re.match(r"^\d+\.", heading_content):
                            messages.append(
                                f"[WARNING] {self.cell_label(i, cell)}: Заголовок не нумерован: '{line.strip()}'"
                            )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_numbered_headings.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_function_docstrings(self) -> str:
        """Проверяет, что все функции в кодовых ячейках содержат докстринги.

        Returns:
            str: Сообщение о предупреждениях, если у функций отсутствуют докстринги.
        """
        messages = []
        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                try:
                    clean_source = self.clean_code(cell.source)  # Очистка кода
                    tree = ast.parse(clean_source)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if not ast.get_docstring(node):
                                messages.append(
                                    f"[WARNING] {self.cell_label(i, cell)}: У функции '{node.name}' отсутствует докстринг."
                                )
                except SyntaxError:
                    messages.append(f"[ERROR] {self.cell_label(i, cell)}: Не удалось распарсить.")

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_function_docstrings.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_explanatory_markdown(self, max_code_cells: int = 3) -> str:
        """Проверяет, что в блокноте нет более `max_code_cells` подряд идущих
        ячеек с кодом.

        Параметры:
            max_code_cells (int): Максимально допустимое количество подряд идущих кодовых ячеек.

        Returns:
            str: Сообщение о предупреждениях, если найдены нарушения.
        """
        messages = []
        consecutive_code_cells = 0

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                consecutive_code_cells += 1
            else:
                consecutive_code_cells = 0

            if consecutive_code_cells > max_code_cells:
                messages.append(
                    f"[WARNING] {self.cell_label(i, cell)}: Слишком много ячеек с кодом подряд (более {max_code_cells})."
                )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_explanatory_markdown.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_short_code_cells(self, max_lines: int = 2) -> str:
        """Проверяет, что нет подряд идущих кодовых ячеек, содержащих менее
        `max_lines` строк.

        Параметры:
            max_lines (int): Максимально допустимое количество строк в коротких ячейках.

        Returns:
            str: Сообщение о предупреждениях, если найдены короткие кодовые ячейки подряд.
        """
        messages = []

        for i, (current_cell, next_cell) in enumerate(zip(self.notebook.cells, self.notebook.cells[1:])):
            if current_cell.cell_type == "code" and next_cell.cell_type == "code":
                if (
                    len(current_cell.source.strip().splitlines()) <= max_lines
                    and len(next_cell.source.strip().splitlines()) <= max_lines
                ):
                    messages.append(
                        f"[WARNING] {self.cell_label(i, current_cell)}: Подряд идущие короткие ячейки с кодом."
                    )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_short_code_cells.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_code_without_comments(self, max_lines: int = 20) -> str:
        """Проверяет, что в кодовых ячейках нет более `max_lines` строк подряд
        без комментариев или пустых строк.

        Параметры:
            max_lines (int): Максимально допустимое количество строк кода подряд без комментариев.

        Returns:
            str: Сообщение о предупреждениях, если найдены длинные последовательности строк кода без комментариев.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                code_lines = cell.source.splitlines()
                count = 0
                for line in code_lines:
                    if line.strip() and not line.strip().startswith("#"):
                        count += 1
                        if count > max_lines:
                            messages.append(
                                f"[WARNING] {self.cell_label(i, cell)}: Более {max_lines} строк кода подряд без комментариев."
                            )
                            break
                    else:
                        count = 0

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_code_without_comments.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_variable_names(self) -> str:
        """Проверяет, что переменные имеют понятные имена (не слишком короткие
        или односимвольные).

        Returns:
            str: Сообщение о предупреждениях, если найдены неподходящие имена переменных.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                try:
                    clean_source = self.clean_code(cell.source)  # Очистка кода
                    tree = ast.parse(clean_source)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                            variable_name = node.id
                            if len(variable_name) < 3 or (variable_name.islower() and len(variable_name) == 1):
                                messages.append(
                                    f"[WARNING] {self.cell_label(i, cell)}: Плохое имя переменной '{variable_name}'. Имя должно быть понятным."
                                )
                except SyntaxError:
                    messages.append(f"[ERROR] {self.cell_label(i, cell)}: Не удалось распарсить.")

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_variable_names.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def is_plotting_node(self, fragment: str) -> bool:
        """Проверяет, относится ли фрагмент к построению графика.

        Аргументы:
            fragment (str): Строка, представляющая фрагмент кода.

        Returns:
            bool: True, если фрагмент содержит ключевые слова, связанные с построением графиков, иначе False.
        """
        # Проверка на наличие ключевых слов, связанных с построением графиков
        for keyword in self.plotting_functions:
            if keyword in fragment:
                return True
        return False

    def is_safe_assignment(self, node: ast.Assign) -> bool:
        """Проверяет, является ли присваивание безопасным.

        Args:
            node (ast.Assign): Узел AST, представляющий операцию присваивания.

        Returns:
            bool: True, если присваивание безопасное (например, np.array, pd.DataFrame и т.д.), иначе False.
        """
        if not isinstance(node, ast.Assign):
            return False

        # Анализируем правую часть выражения
        value = node.value

        # Для работы с np.array, np.matrix, pd.DataFrame и pd.Series
        try:
            if isinstance(value, ast.Call):
                func_name = self.get_function_name(value)
                if func_name in SAFE_ARRAYS_AND_TENSORS:
                    return True
        except:
            pass

        if isinstance(value, SAFE_TYPES):
            return True

        return False

    def get_function_name(self, node: ast.Call) -> str:
        """Извлекает имя вызываемой функции из узла AST.

        Аргументы:
            node (ast.Call): Узел AST, представляющий вызов функции.

        Returns:
            str: Имя функции (например, plt.scatter), либо пустая строка, если имя не удалось извлечь.
        """
        if isinstance(node.func, ast.Attribute):
            return f"{node.func.value.id}.{node.func.attr}"  # например, plt.scatter
        elif isinstance(node.func, ast.Name):
            return node.func.id  # например, plt
        return ""

    def is_constant(self, node: ast.AST) -> bool:
        """Проверяет, является ли узел AST магической константой.

        Args:
            node (ast.AST): Узел AST для проверки.

        Returns:
            bool: True, если узел является магической константой, иначе False.
        """
        if isinstance(node, ast.Constant):
            value = node.value
            # Игнорируем значения внутри графических построений (например, s=120 в scatter)
            if isinstance(value, (int, float)) and value not in {0, 1, -1}:
                return True
        return False

    def check_no_magic_constants(self) -> str:
        """Проверяет наличие магических констант в коде ячеек.

        Магическая константа — это числовое значение, не объяснённое через комментарий
        или переменную. Исключения составляют значения, используемые в построении графиков.

        Returns:
            str: Сообщение с предупреждениями или ошибками по каждой ячейке.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type != "code":
                continue

            try:
                clean_source = self.clean_code(cell.source)  # Очистка кода
                # Разбираем код ячейки как AST
                tree = ast.parse(clean_source)
            except SyntaxError:
                messages.append(f"[ERROR] {self.cell_label(i, cell)}: Не удалось распарсить.")
                continue

            for node in tree.body:
                try:
                    fragment = ast.get_source_segment(cell.source, node) or "<не удалось определить>"
                    line_no = getattr(node, "lineno", None)

                    # Игнорируем узлы, относящиеся к построению графиков
                    if self.is_plotting_node(fragment):
                        continue

                    # Пропускаем безопасные присваивания
                    if isinstance(node, ast.Assign) and self.is_safe_assignment(node):
                        continue

                    # Обходим все подузлы строки
                    for subnode in ast.walk(node):
                        # Проверяем только те узлы, которые не связаны с графиками
                        if self.is_constant(subnode):
                            node_line_no = getattr(subnode, "lineno", None)
                            if node_line_no:
                                exact_line = cell.source.splitlines()[node_line_no - 1].strip()
                            else:
                                exact_line = "<строка недоступна>"

                            messages.append(
                                f"[WARNING] {self.cell_label(i, cell)}: "
                                f"Найдена магическая константа в строке {node_line_no}: {exact_line}"
                            )
                            break  # Достаточно одного предупреждения на строку
                except Exception as e:
                    messages.append(f"[DEBUG] Ошибка при обработке узла {type(node).__name__}: {e}")

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_no_magic_constants.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_function_names(self) -> str:
        """Проверяет, имеют ли функции понятные имена.

        Критерии:
        - Имя функции должно быть длиннее двух символов.
        - Имя должно содержать подчёркивания для разделения слов.

        Returns:
            str: Сообщение с предупреждениями или ошибками по каждой функции.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                try:
                    clean_source = self.clean_code(cell.source)  # Очистка кода
                    tree = ast.parse(clean_source)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if len(node.name) < 3 or "_" not in node.name:
                                messages.append(
                                    f"[WARNING] {self.cell_label(i, cell)}: Плохое имя функции '{node.name}'. Используйте понятные имена."
                                )
                except SyntaxError:
                    messages.append(f"[ERROR] {self.cell_label(i, cell)}: Не удалось распарсить.")

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_function_names.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_dashes_and_hyphens(self) -> str:
        """Проверяет корректность использования дефисов и тире в Markdown-
        ячейках.

        Критерии:
        - Дефис с пробелами вокруг (` - `) следует заменять на длинное тире (&mdash;).

        Returns:
            str: Сообщение с предупреждениями для каждой Markdown-ячейки.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "markdown":
                if re.search(r"\s-\s", cell.source):
                    messages.append(
                        f"[WARNING] {self.cell_label(i, cell)}: Обнаружено использование дефиса вместо тире. Используйте &mdash;."
                    )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_dashes_and_hyphens.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_spelling(self) -> str:
        """Проверяет орфографию Markdown-ячейки, исключая веб-ссылки, код в
        кавычках, и формулы.

        Используется API Яндекс.Спеллера для анализа текста.

        Returns:
            str: Сообщения о найденных ошибках с предложениями исправлений.
        """
        messages = []
        url = "https://speller.yandex.net/services/spellservice.json/checkText"

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "markdown":
                lines = cell.source.splitlines()
                for line in lines:
                    # Убрать веб-ссылки
                    line = re.sub(r"https?://\S+", "", line)
                    # Убрать код в кавычках `code`
                    line = re.sub(r"`[^`]+`", "", line)
                    # Убрать формулы
                    line = re.sub(r"\$(?!\$)([^$]+?)\$(?!\$)", "", line)
                    line = re.sub(r"\$\$(?!\$)([^$]+?)\$\$(?!\$)", "", line)

                    try:
                        response = requests.get(url, params={"text": line})
                        errors = response.json()
                    except:
                        continue

                    for error in errors:
                        word = error["word"]
                        suggestions = ", ".join(error.get("s", []))
                        start = error["pos"]
                        end = start + error["len"]
                        messages.append(
                            f"[SPELLING] {self.cell_label(i, cell)}: Ошибка в слове '{word}' в предложении '{line.strip()}'. Возможные исправления: {suggestions}."
                        )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_spelling.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_computation_and_plotting(self) -> str:
        """Проверяет разделение вычислений и построения графиков в ячейках с
        кодом.

        Критерии:
        - Вычисления и графические построения должны быть в разных блоках кода.

        Returns:
            str: Сообщения о ячейках, где обнаружено смешение операций.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                lines = cell.source.splitlines()

                plot_started = False  # Флаг для отслеживания построения графика
                plot_function_started = False  # Флаг для отслеживания функции построения графика
                parentheses_count = 0  # Для отслеживания баланса скобок
                has_computation = False  # Признак наличия вычислений

                for line in lines:
                    # Проверка на начало графического вызова
                    if any(func in line for func in self.plotting_functions):
                        plot_started = True
                        plot_function_started = True

                    # Если линия продолжает графическую функцию, увеличиваем/уменьшаем счетчик скобок
                    if plot_function_started:
                        parentheses_count += line.count("(") - line.count(")")

                    # Если вычисление, а график еще не завершен, то нарушаем правило
                    if (
                        re.search(r"(=|def|return|\+|-|\*|/)", line)
                        and not any(func in line for func in self.plotting_functions)
                        and not re.search(r"\bfor\b", line)
                    ):
                        if plot_started and not plot_function_started:  # Если мы в процессе построения графика
                            has_computation = True

                    # Проверка завершения построения графика
                    if plot_function_started and parentheses_count == 0:
                        plot_function_started = False  # Завершаем построение графика

                # Если были обнаружены смешанные вычисления и графики
                if has_computation:
                    messages.append(
                        f"[WARNING] {self.cell_label(i, cell)}: Вычисления и отрисовка графиков смешаны. Разделите эти операции при наличии возможности (использование индексов в циклах for может обрабатываться некорректно)."
                    )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_computation_and_plotting.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_param_comments(self) -> str:
        """Проверяет, добавлены ли комментарии к параметрам-экспериментам в
        коде.

        Исключение составляют параметры в графических вызовах.

        Returns:
            str: Сообщения о параметрах без комментариев.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                lines = cell.source.splitlines()
                full_line = ""  # Для объединения строк, составляющих один вызов функции
                inside_parentheses = 0  # Счётчик скобок

                for line in lines:
                    stripped_line = line.strip()

                    # Обрабатываем скобки в строке
                    inside_parentheses += stripped_line.count("(")  # Увеличиваем, если открываются скобки
                    inside_parentheses -= stripped_line.count(")")  # Уменьшаем, если закрываются скобки

                    # Собираем строки в одно целое, если мы внутри скобок
                    full_line += stripped_line

                    # Если мы не внутри скобок, то обрабатываем строку
                    if inside_parentheses == 0:
                        # Применяем регулярное выражение к собранной строке
                        if re.match(r"^\s*\w+\s*=\s*[\d\[\]\{\}\"\']", full_line):  # Присваивание
                            # Исключить случаи, связанные с графиками
                            if not re.search(r"(plt\.|sns\.)", full_line) and not re.search(r"#", full_line):
                                messages.append(
                                    f"[WARNING] {self.cell_label(i, cell)}: Параметр '{full_line.strip()}' не имеет комментария. Добавьте пояснение."
                                )

                        # Очищаем строку после обработки
                        full_line = ""

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_param_comments.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def check_graphics_style(self) -> str:
        """Проверяет соответствие стиля графиков рекомендациям.

        Критерии:
        - Вызов `sns.set_style` должен указывать `style` и `font_scale`.
        - Вызов `plt.legend` должен включать параметр `loc`.

        Returns:
            str: Сообщения о несоответствиях стиля графиков.
        """
        messages = []

        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == "code":
                lines = cell.source.splitlines()
                for line in lines:
                    if "sns.set_style" in line and "style" not in line:
                        messages.append(
                            f"[WARNING] {self.cell_label(i, cell)}: Укажите стиль графика style в sns.set_style."
                        )
                    if "sns.set_style" in line and "font_scale" not in line:
                        messages.append(
                            f"[WARNING] {self.cell_label(i, cell)}: Укажите масштаб текста font_scale в sns.set_style."
                        )
                    if "plt.legend" in line and "loc=" not in line:
                        messages.append(
                            f"[WARNING] {self.cell_label(i, cell)}: Легенда на графике не настроена. Укажите параметр 'loc' для её размещения."
                        )

        # Автоматическое определение веса ошибки на основе имени функции
        function_name = self.check_graphics_style.__name__
        weight = self.error_weights.get(function_name, 1)  # Значение по умолчанию - 1
        self.issues += len(messages) * weight

        return "\n".join(messages)

    def calculate_quality_score(self) -> float:
        """Вычисление итоговой оценки качества ноутбука на основе количества
        проблем (включая предупреждения) и общего размера контента ноутбука (в
        символах).

        Оценка вычисляется с использованием формулы, которая учитывает взвешенные ошибки
        и нормализует их по общему объему контента (код + markdown ячейки). Чем больше
        ошибок, тем ниже будет оценка.

        Возвращает:
            float: Итоговая оценка качества, в пределах от 0 до 10, округленная до двух знаков после запятой.
        """
        total_chars = 0
        weighted_errors = 0

        # Подсчет символов в ячейках с кодом и markdown
        for cell in self.notebook.cells:
            if cell.cell_type == "markdown":
                total_chars += len(cell.source)  # Все символы в ячейке markdown
            elif cell.cell_type == "code":
                total_chars += len(cell.source)  # Все символы в ячейке с кодом

        # Подсчет взвешенных ошибок
        weighted_errors = float(self.issues)  # Считаем, что self.issues уже содержит общее количество ошибок с весами

        # Вычисление качества
        if total_chars == 0:  # Защита от деления на 0
            return 10  # Если нет текста в ноутбуке, можно присвоить максимальную оценку

        total_cells = len(self.notebook.cells)
        normalizer = (total_chars + 100 * total_cells) / 2

        # Вычисление итоговой оценки
        quality_score = 10 - np.tanh(3 * weighted_errors / normalizer) * 10

        # Оценка должна быть в пределах от 0 до 10
        quality_score = max(0, min(10, quality_score))

        return round(quality_score, 2)

    def run_all_checks(self, run_check_spelling: bool = False) -> tuple[str, float]:
        """Запускает все предустановленные проверки (объем текста, заголовки,
        докстринги функций и т.д.) на ноутбуке и собирает соответствующие
        предупреждения и сообщения об ошибках. Также вычисляется итоговая
        оценка качества ноутбука.

        Аргументы:
            run_check_spelling (bool): Флаг, указывающий, следует ли запускать проверку орфографии. По умолчанию False.

        Возвращает:
            tuple[str, float]: Кортеж, содержащий:
                - Строку с объединенными предупреждениями и ошибками.
                - Число с итоговой оценкой качества ноутбука (от 0 до 10).
        """
        all_messages = []  # Список для хранения всех сообщений (предупреждений и ошибок)

        # Запускаем все проверки и добавляем сообщения в all_messages
        all_messages.append(self.check_text_volume())

        all_messages.append(self.check_numbered_headings())

        all_messages.append(self.check_function_docstrings())

        all_messages.append(self.check_explanatory_markdown())

        all_messages.append(self.check_short_code_cells())

        all_messages.append(self.check_code_without_comments())

        all_messages.append(self.check_variable_names())

        all_messages.append(self.check_no_magic_constants())

        all_messages.append(self.check_function_names())

        all_messages.append(self.check_dashes_and_hyphens())

        all_messages.append(self.check_computation_and_plotting())

        all_messages.append(self.check_param_comments())

        all_messages.append(self.check_graphics_style())

        if run_check_spelling:
            all_messages.append(self.check_spelling())

        # Объединяем все сообщения в одну строку
        combined_messages = "\n".join(msg for msg in all_messages if msg)

        # Вычисляем итоговую оценку
        quality_score = self.calculate_quality_score()

        # Возвращаем итоговое сообщение и оценку
        return combined_messages, quality_score


# Пример использования:
if __name__ == "__main__":
    checker = NotebookStyleChecker("example_notebook.ipynb")
    checker.run_all_checks()
