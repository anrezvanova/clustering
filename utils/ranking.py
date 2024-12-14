import typing as tp
import warnings

import networkx as nx
import numpy as np
from datasketch import MinHash, MinHashLSH
from transformers import BertTokenizer
from umap import UMAP

from utils.embedder import E5Embedder

# Suppress the UMAP warnings
warnings.filterwarnings("ignore", category=UserWarning, module="umap.umap_")


class PreClustering:
    """
    Класс для предварительной кластеризации строк с использованием LSH и MinHash.
    """

    def __init__(self, lowercase_strings: tp.List[str]):
        """
        Инициализирует класс с заданными строками и параметрами.
        * lowercase_strings : list[str]
            Список строк в нижнем регистре.
        """
        self.lowercase_strings = lowercase_strings
        self.MAX_THRESH = 0.97
        self.tokenizer = BertTokenizer.from_pretrained("sberbank-ai/ruBert-base", clean_up_tokenization_spaces=True)

    def LSH_cluster(self, strings: tp.List[str]) -> tp.Tuple[tp.List[tp.List[int]], tp.List[int]]:
        """
        Кластеризует строки с использованием LSH и MinHash.
        * strings : list[str]
            Список текстовых строк.

        Возвращает:
        * clusters : list[list[int]]
            Список кластеров (список списков индексов).
        * outcasts : list[int]
            Список индексов выбросов.
        """
        if len(strings) < 5:
            return [], list(range(len(strings)))

        min_hashes = []
        for s in strings:
            m = MinHash(num_perm=128)
            for word in set(self.tokenizer.tokenize(s)):
                m.update(word.encode("utf8"))
            min_hashes.append(m)

        prev_threshold, prev_num_edges = 0.2, np.inf
        threshold = 0.2 + len(strings) / 1600
        combo, tried_backtrack = 0, False

        while True:
            close_nodes = []
            for i, min_hash in enumerate(min_hashes):
                lsh = MinHashLSH(threshold=threshold, num_perm=128)
                for j, mh in enumerate(min_hashes):
                    if i != j:
                        lsh.insert(j, mh)
                group = [i] + lsh.query(min_hash)
                close_nodes.append(group)

            # Построение графа и определение компонент
            pairs = [(clust[i], clust[i + 1]) for clust in close_nodes for i in range(len(clust) - 1)]
            G = nx.Graph()
            G.add_edges_from(pairs)

            if not list(nx.connected_components(G)):
                tried_backtrack = True
                if abs(threshold - prev_threshold) < 1e-4:
                    break
                threshold = (threshold + prev_threshold) / 2
                continue

            if tried_backtrack:
                break

            num_edges = len(pairs)
            if prev_num_edges == num_edges:
                combo += 1
            else:
                combo = 0

            if max(len(comp) for comp in nx.connected_components(G)) > int(0.4 * len(strings)) and combo < 4:
                prev_threshold = threshold
                if threshold != self.MAX_THRESH:
                    threshold += 0.01 * (num_edges / len(strings))
                    threshold = min(threshold, self.MAX_THRESH)
                else:
                    break
                prev_num_edges = num_edges
            else:
                break

        clusters = [list(comp) for comp in nx.connected_components(G)]
        outcasts = [group[0] for group in close_nodes if len(group) == 1]

        return clusters, outcasts

    def get_clustering(self) -> tp.Tuple[tp.List[tp.List[int]], tp.List[int]]:
        """
        Получает результаты кластеризации.

        Возвращает:
        * clusters : list[list[int]]
            Список кластеров.
        * outcasts : list[int]
            Список выбросов.
        """
        return self.LSH_cluster(self.lowercase_strings)


class Ranker:
    """
    Класс для ранжирования строк с использованием эмбеддингов и кластеризации.
    """

    def __init__(self):
        """Инициализирует эмбеддер и пороговое значение для объема LSH."""
        self.e5_embedder = E5Embedder()
        self.LSH_volume_thresh = 48

    def rank(self, strings: tp.List[str]) -> np.ndarray:
        """
        Ранжирует строки на основе эмбеддингов и UMAP.
        * strings : list[str]
            Список строк для ранжирования.

        Возвращает:
        * np.ndarray : Индексы строк в порядке ранжирования.
        """
        if len(strings) < 3:
            return np.arange(len(strings))

        strings = [str(s).lower() for s in strings]
        embeddings = self.e5_embedder.get_embeddings(strings)

        fit_embeddings = UMAP(n_components=1).fit(embeddings)

        if len(strings) <= self.LSH_volume_thresh:
            clusters, _ = PreClustering(strings).get_clustering()
            cluster_features = np.zeros((len(strings), len(clusters)), dtype=int)

            for i, cluster in enumerate(clusters):
                cluster_features[cluster, [i] * len(cluster)] = 1

            # Проверка, что признаки кластеров не пустые
            if cluster_features.shape[1] == 0:
                print("Признаки кластеров пусты. Не удается выполнить кластеризацию.")
                # Возвращаем пустую структуру и подпись
                return np.arange(len(strings))  
            fit_clusters = UMAP(n_components=1, metric="jaccard").fit(cluster_features)
            fit_intersection = fit_embeddings * fit_clusters
            reduced = fit_intersection.embedding_.ravel()
        else:
            reduced = fit_embeddings.embedding_.ravel()

        order = np.argsort(reduced)
        return order
