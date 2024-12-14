import numpy as np
import torch
from torch import Tensor
from transformers import AutoModel, AutoTokenizer


class E5Embedder:
    """
    Класс для создания эмбеддингов с использованием модели E5.
    """

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        """
        Инициализация эмбеддера.
        * model_name : str
            Название предобученной модели (по умолчанию "intfloat/multilingual-e5-small").
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, clean_up_tokenization_spaces=True)
        self.model = AutoModel.from_pretrained(model_name)

    @staticmethod
    def average_pool(hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
        """
        Выполняет среднее пуллинг по скрытым состояниям.
        * hidden_states : Tensor
            Последние скрытые состояния модели.
        * attention_mask : Tensor
            Маска внимания (0 для токенов паддинга).

        Возвращает:
        * Tensor : Средние эмбеддинги по каждому предложению.
        """
        # Замена значений, соответствующих токенам паддинга, на 0
        hidden_states = hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
        # Вычисление среднего значения скрытых состояний с учетом маски
        return hidden_states.sum(dim=1) / attention_mask.sum(dim=1, keepdim=True)

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        Генерация эмбеддингов для списка текстов.
        * texts : list[str]
            Список входных текстов.

        Возвращает:
        * np.ndarray : Массив эмбеддингов размерности (N, D), где N — количество текстов, D — размер эмбеддинга.
        """
        # Предобработка текстов
        if not texts:
            raise ValueError("Список текстов пуст")
        input_texts = [f"passage: {text}" for text in texts]

        # Определение максимальной длины на основе 97.5-го перцентиля
        max_length = min(
            max(int(2 ** np.ceil(np.log2(np.quantile([len(t.split()) for t in input_texts], 0.975)))), 128), 512
        )

        # Токенизация текстов
        tokenized_inputs = self.tokenizer(
            input_texts, max_length=max_length, padding=True, truncation=True, return_tensors="pt"
        )

        # Получение скрытых состояний модели без вычисления градиентов
        with torch.no_grad():
            outputs = self.model(**tokenized_inputs)

        # Вычисление эмбеддингов через среднее пуллинг
        embeddings = self.average_pool(outputs.last_hidden_state, tokenized_inputs["attention_mask"])

        return embeddings.detach().cpu().numpy()
