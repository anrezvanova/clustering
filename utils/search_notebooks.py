import os
from whoosh import index
from whoosh.qparser import QueryParser

class IndexSearcher:
    def __init__(self, index_path):
        """
        Инициализирует поисковый объект, открывая индекс по указанному пути.

        Параметры:
        - index_path: Полный путь к папке с индексом.
        """
        if not os.path.exists(index_path):
            raise ValueError(f"Указанный путь {index_path} не существует.")
        
        self.idx = index.open_dir(index_path)  # Открываем указанный индекс
        self.searcher = self.idx.searcher()   # Создаем поисковик, который будет открыт на протяжении сеанса

    def search(self, search_word):
        """
        Выполняет поиск по индексу и возвращает исходные пути к файлам с совпадением.

        Параметры:
        - search_word: Слово или фраза для поиска.

        Возвращает:
        - Список исходных путей к файлам, где найдено совпадение.
        """
        query = QueryParser("content", schema=self.idx.schema).parse(search_word)
        results = self.searcher.search(query)
        
        # Получаем оригинальные пути из результатов
        original_paths = [hit["original_path"] for hit in results]
        return original_paths

    def close(self):
        """Закрывает поисковик."""
        self.searcher.close()