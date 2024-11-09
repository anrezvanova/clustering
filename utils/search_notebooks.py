import os
from whoosh import index
from whoosh.qparser import QueryParser

class IndexSearcher:
    def __init__(self, index_name):
        """
        Инициализирует поисковый объект, открывая индекс.
        
        Параметры:
        - index_name: Название папки с индексом.
        """
        idx_path = os.path.join("indexes", index_name)
        self.idx = index.open_dir(idx_path)  # Открываем указанный индекс
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

# Пример использования

# Создаем поисковый объект (открывает индекс)
index_searcher = IndexSearcher("phds_fall_2023")  # Замените на нужное имя индекса

# Выполняем несколько запросов без закрытия поисковика
print(index_searcher.search("ваше_слово_для_поиска"))
print(index_searcher.search("другое_слово_для_поиска"))

# Закрываем поисковик, когда больше не нужен
index_searcher.close()