import typing as tp

import nltk
import numpy as np
from nltk.corpus import stopwords
from rake_nltk import Metric, Rake
from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from utils.embedder import E5Embedder

nltk.download("stopwords", quiet=True)
nltk.download("punkt", quiet=True)


class Clusterer:
    """
    Класс для кластеризации текстов и выделения ключевых фраз.
    """

    def __init__(self):
        """Инициализирует эмбеддер и необходимые стоп-слова."""
        self.stopwords_ru = self._prepare_stopwords()
        self.e5_embedder = E5Embedder() 
    @staticmethod
    def _prepare_stopwords() -> list[str]:
        """
        Создает список стоп-слов на русском языке с дополнительными исключениями.
        Возвращает:
        * list[str] : Список стоп-слов.
        """
        stopwords_ru = stopwords.words("russian")
        additional_stopwords = [
            "который",
            "затем",
            "т",
            "к",
            "тк",
            "значит",
            "это",
            "вроде",
            "скорее",
            "ибо",
            "нем",
            "теории",
            "так",
            "как",
        ]
        stopwords_ru.extend(additional_stopwords)
        return stopwords_ru

    def extract_keyphrases(self, text: str) -> list[str]:
        """
        Выделяет ключевые фразы из текста.
        * text : str
            Текст для извлечения ключевых фраз.

        Возвращает:
        * list[str] : Список ключевых фраз.
        """
        r = Rake(
            stopwords=self.stopwords_ru,
            punctuations=",.()!?",
            language="russian",
            min_length=1,
            ranking_metric=Metric.WORD_FREQUENCY,
            include_repeated_phrases=False,
        )
        r.extract_keywords_from_text(text)
        return r.get_ranked_phrases()

    def cluster(self, strings: tp.List[tp.Any], eps: float = 15.0, min_samples: int = 2) -> np.ndarray:
        """
        Кластеризует строки и возвращает номера кластеров.
        * strings : list[tp.Any]
            Список строк для кластеризации. Может включать строки или np.nan.
        * eps : float
            Максимальное расстояние между точками для создания кластера (по умолчанию 15.0).
        * min_samples : int
            Минимальное количество точек для образования кластера (по умолчанию 2).

        Возвращает:
        * np.ndarray : Массив меток кластеров для каждой строки.
        """
        # Предобработка строк: замена np.nan на пустые строки
        strings = [str(s) if isinstance(s, str) or (isinstance(s, float) and not np.isnan(s)) else "" for s in strings]
        
        # Инициализация TF-IDF векторизатора
        vectorizer = TfidfVectorizer(stop_words=self.stopwords_ru, max_features=1000)
        
        # Преобразование строк в матрицу признаков с использованием TF-IDF
        tfidf_matrix = vectorizer.fit_transform(strings)
        
        # Получение эмбеддингов на основе TF-IDF
        tfidf_embeddings = tfidf_matrix.toarray()
        
        # Получение эмбеддингов с помощью e5_embedder (предположительно более сложный метод эмбеддинга)
        e5_embeddings = self.e5_embedder.get_embeddings(strings)
        
        # Объединяем эмбеддинги TF-IDF и e5_embedder
        combined_embeddings = np.concatenate([tfidf_embeddings, e5_embeddings], axis=1)
        
        # Нормализация объединенных эмбеддингов
        scaled_embeddings = StandardScaler().fit_transform(combined_embeddings)

        # Кластеризация методом DBSCAN
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(scaled_embeddings)
        # Проверка на наличие кластеров
        if len(np.unique(clustering.labels_)) == 1 and -1 in clustering.labels_:
            return np.array([])  # Возвращаем пустой массив, если кластеров нет
        return clustering.labels_
