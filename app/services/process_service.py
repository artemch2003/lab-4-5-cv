"""Сервис алгоритмов обработки изображений (градации серого, порогование, k-means).

Дизайн и принципы:
- SRP (Single Responsibility): класс отвечает только за преобразования изображений.
- OCP (Open/Closed): новые алгоритмы добавляются новыми методами без изменения существующих.
- LSP (Liskov): все публичные методы возвращают корректные `PIL.Image.Image` и не нарушают ожиданий.
- ISP (Interface Segregation): UI вызывает только нужные методы; нет «толстых» интерфейсов.
- DIP (Dependency Inversion): контроллер использует этот сервис как зависимость; сам сервис не знает про UI.

Чистый код:
- Читабельные имена и явные докстринги с контрактами входа/выхода.
- Без побочных эффектов: исходные изображения не мутируются, возвращаются новые экземпляры.
- Производительность: векторизация NumPy, готовые фильтры Pillow, избегаем лишних копий.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


class ProcessService:
    """Набор чистых (без побочных эффектов) операций над изображениями.

    Контракты:
    - Вход: `PIL.Image.Image` любого режима; внутри приводим к "L", где требуется.
    - Выход: новое `PIL.Image.Image`; бинарные маски возвращаются в режиме "L" (0/255).
    - Иммутабельность: исходный объект `Image` не изменяется.
    - Ошибки: аргументы проверяются минимально; предполагается корректное изображение.
    """
    def to_grayscale(self, image: Image.Image) -> Image.Image:
        """Преобразует изображение в оттенки серого (8-бит, режим "L").

        Args:
            image: Входное изображение в любом режиме (RGB, RGBA, L и т.д.).

        Returns:
            Новое изображение в режиме "L". Если вход уже "L", вернётся копия.
        """
        if image.mode == "L":
            return image.copy()
        return image.convert("L")

    # ---------- Вспомогательные функции ----------
    def _image_to_gray_np(self, image: Image.Image) -> np.ndarray:
        """
        Возвращает numpy-массив float32 в диапазоне [0, 255] (градации серого).
        """
        gray = self.to_grayscale(image)
        arr = np.asarray(gray, dtype=np.float32)
        return arr

    def _apply_binary_mask(self, mask_bool: np.ndarray) -> Image.Image:
        """
        Преобразует булеву маску в 8-битное бинарное изображение (0/255).
        """
        out = np.where(mask_bool, 255, 0).astype(np.uint8)
        return Image.fromarray(out, mode="L")

    def _otsu_threshold(self, arr_0_255: np.ndarray) -> float:
        """
        Порог Отсу для массива значений [0..255] (float/uint8).
        Возвращает порог T в тех же единицах.
        """
        # Приведём к uint8 для стабильной гистограммы
        arr_u8 = np.clip(np.rint(arr_0_255), 0, 255).astype(np.uint8)
        hist = np.bincount(arr_u8.flatten(), minlength=256).astype(np.float64)
        total = arr_u8.size
        if total == 0:
            return 0.0

        prob = hist / total
        omega = np.cumsum(prob)  # кумулятивные вероятности
        mu = np.cumsum(prob * np.arange(256))  # кумулятивные средние
        mu_t = mu[-1]

        # Межклассовая дисперсия
        numerator = (mu_t * omega - mu) ** 2
        denominator = omega * (1.0 - omega)
        # избегаем деления на ноль
        with np.errstate(divide="ignore", invalid="ignore"):
            sigma_b2 = np.where(denominator > 0, numerator / denominator, 0.0)
        t = np.argmax(sigma_b2)
        return float(t)

    # ---------- 1) Сегментация по границам (Собель + Отсу) ----------
    def segment_edges_sobel(self, image: Image.Image) -> Image.Image:
        """
        Поиск неоднородностей через выделение границ:
        - Градиент Собеля
        - Порогование по Отсу на карте градиента
        Возвращает бинарное изображение (границы = 255).
        """
        arr = self._image_to_gray_np(image)
        # Паддинг отражением по краям
        p = np.pad(arr, ((1, 1), (1, 1)), mode="edge")

        # Классические Собель-фильтры, векторизованная свёртка через сдвиги
        gx = (
            (p[0:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:])
            - (p[0:-2, 0:-2] + 2 * p[1:-1, 0:-2] + p[2:, 0:-2])
        )
        gy = (
            (p[2:, 0:-2] + 2 * p[2:, 1:-1] + p[2:, 2:])
            - (p[0:-2, 0:-2] + 2 * p[0:-2, 1:-1] + p[0:-2, 2:])
        )
        mag = np.hypot(gx, gy)  # magnitude
        # Масштабирование в [0..255] для стабильного порога
        mag_norm = mag
        if mag_norm.size > 0:
            mmax = float(mag_norm.max())
        else:
            mmax = 0.0
        if mmax > 0:
            mag_norm = (mag_norm * (255.0 / mmax)).astype(np.float32)
        else:
            mag_norm = np.zeros_like(mag_norm, dtype=np.float32)

        t = self._otsu_threshold(mag_norm)
        edges = mag_norm >= t
        return self._apply_binary_mask(edges)

    # ---------- 2) Пороговые методы с глобальным порогом T ----------
    # 2.1) P-tile (на основе площади)
    def threshold_ptile(self, image: Image.Image, p: float = 0.30) -> Image.Image:
        """
        P-tile: выбираем такой порог T, чтобы доля пикселей ярче T была равна p.
        Предполагаем, что 'объект' светлее фона.
        """
        p = float(np.clip(p, 0.0, 1.0))
        arr = self._image_to_gray_np(image)
        arr_u8 = np.clip(np.rint(arr), 0, 255).astype(np.uint8)
        hist = np.bincount(arr_u8.flatten(), minlength=256).astype(np.int64)
        total = int(arr_u8.size)
        if total == 0:
            return self._apply_binary_mask(np.zeros_like(arr_u8, dtype=bool))

        # Кумулятив с верха (от 255 к 0)
        cumsum_from_top = np.cumsum(hist[::-1])[::-1]
        target = int(round(p * total))
        # Найдём минимальный T, при котором >= target пикселей ярче/равно T
        # cumsum_from_top[T] = count(I >= T)
        T = 255
        for t in range(255, -1, -1):
            if cumsum_from_top[t] >= target:
                T = t
            else:
                break
        mask = arr_u8 >= T
        return self._apply_binary_mask(mask)

    # 2.2) Последовательные приближения (итеративный метод)
    def threshold_iterative(self, image: Image.Image, tol: float = 0.5, max_iter: int = 100) -> Image.Image:
        """
        Итеративный выбор порога:
        1) T0 = среднее по изображению
        2) Делим пиксели на G1: I<=T, G2: I>T
        3) T' = (mean(G1) + mean(G2)) / 2
        4) Повторять до |T'-T| < tol или max_iter
        """
        arr = self._image_to_gray_np(image)
        T = float(arr.mean()) if arr.size else 0.0
        for _ in range(max_iter):
            g1 = arr[arr <= T]
            g2 = arr[arr > T]
            if g1.size == 0 or g2.size == 0:
                break
            T_new = 0.5 * (float(g1.mean()) + float(g2.mean()))
            if abs(T_new - T) < tol:
                T = T_new
                break
            T = T_new
        mask = arr > T
        return self._apply_binary_mask(mask)

    # 2.3) Метод k-средних (сегментация по интенсивности)
    def kmeans_segment(self, image: Image.Image, k: int = 2, max_iter: int = 50) -> Image.Image:
        """
        K-средних над интенсивностями [0..255].
        Возвращает изображение, где каждый кластер заменён своим центроидом (постеризация).
        """
        arr = self._image_to_gray_np(image)
        flat = arr.reshape(-1, 1)
        # Инициализация центроидов равномерно по диапазону
        centroids = np.linspace(0.0, 255.0, num=k, dtype=np.float32).reshape(k, 1)

        for _ in range(max_iter):
            # Назначение ближайшего центроида
            dists = np.abs(flat - centroids.T)  # (N, k)
            labels = np.argmin(dists, axis=1)
            new_centroids: List[float] = []
            changed = False
            for ci in range(k):
                pts = flat[labels == ci]
                if pts.size == 0:
                    # Реинициализация пустого кластера случайным значением из данных
                    new_c = float(np.random.choice(flat.squeeze())) if flat.size else 0.0
                else:
                    new_c = float(pts.mean())
                new_centroids.append(new_c)
                if abs(new_c - float(centroids[ci, 0])) > 1e-3:
                    changed = True
            centroids = np.array(new_centroids, dtype=np.float32).reshape(k, 1)
            if not changed:
                break

        # Финальное присвоение и сборка постеризованного изображения
        dists = np.abs(flat - centroids.T)
        labels = np.argmin(dists, axis=1)
        out = centroids.squeeze()[labels].reshape(arr.shape).astype(np.uint8)
        return Image.fromarray(out, mode="L")

    def kmeans_compare(self, image: Image.Image, ks: Iterable[int] = (2, 3, 4)) -> Image.Image:
        """
        Сравнение результатов k-средних для нескольких k.
        Возвращает горизонтально склеенное изображение с подписями k.
        """
        imgs: List[Tuple[str, Image.Image]] = []
        for k in ks:
            seg = self.kmeans_segment(image, k=max(2, int(k)))
            imgs.append((f"k={int(k)}", seg))

        # Рисуем подписи сверху (24px) и склеиваем по ширине
        if not imgs:
            return self.to_grayscale(image)
        w, h = imgs[0][1].size
        label_h = 24
        gap = 12
        total_w = w * len(imgs) + gap * (len(imgs) - 1)
        total_h = h + label_h
        canvas = Image.new("L", (total_w, total_h), color=255)
        draw = ImageDraw.Draw(canvas)

        x = 0
        for label, img in imgs:
            # Вставка блока с подписью
            # Белый фон уже есть; подпись чёрным
            draw.text((x + 6, 4), label, fill=0)
            canvas.paste(img, (x, label_h))
            x += w + gap
        return canvas

    # ---------- 3) Пороговый метод с адаптивным порогом ----------
    def _local_stat(self, gray_img: Image.Image, window_size: int, stat: str) -> np.ndarray:
        """
        Локальная статистика по окрестности:
        - 'mean'     -> среднее (box blur)
        - 'median'   -> медиана
        - 'midrange' -> (min + max)/2
        Возвращает float32 массив [0..255].
        """
        w = max(3, int(window_size))
        if w % 2 == 0:
            w += 1
        stat_key = (stat or "mean").lower()

        if stat_key == "mean":
            # BoxBlur(radius) эквивалентен усреднению в окне (2r+1)
            radius = max(1, (w - 1) // 2)
            filt = gray_img.filter(ImageFilter.BoxBlur(radius))
            return np.asarray(filt, dtype=np.float32)
        elif stat_key == "median":
            filt = gray_img.filter(ImageFilter.MedianFilter(size=w))
            return np.asarray(filt, dtype=np.float32)
        elif stat_key in ("midrange", "minmax", "min+max/2"):
            mn = gray_img.filter(ImageFilter.MinFilter(size=w))
            mx = gray_img.filter(ImageFilter.MaxFilter(size=w))
            mn_arr = np.asarray(mn, dtype=np.float32)
            mx_arr = np.asarray(mx, dtype=np.float32)
            return 0.5 * (mn_arr + mx_arr)
        else:
            # По умолчанию — среднее
            radius = max(1, (w - 1) // 2)
            filt = gray_img.filter(ImageFilter.BoxBlur(radius))
            return np.asarray(filt, dtype=np.float32)

    def adaptive_threshold(
        self,
        image: Image.Image,
        k: int = 15,
        C: float = 1.0,
        T: float = 0.0,
        stat: str = "mean",
        polarity: str = "bright",
    ) -> Image.Image:
        """
        Адаптивный порог по формуле:
            I(x,y) >= C * S_k(x,y) + T   (для bright)
            I(x,y) <= C * S_k(x,y) + T   (для dark)
        где S_k — локальная статистика (среднее, медиана или (min+max)/2) в окне k×k.
        """
        gray = self.to_grayscale(image)
        I = np.asarray(gray, dtype=np.float32)
        S = self._local_stat(gray, window_size=k, stat=stat)
        thresh = (float(C) * S) + float(T)
        pol = (polarity or "bright").lower()
        if pol == "dark":
            mask = I <= thresh
        else:
            mask = I >= thresh
        return self._apply_binary_mask(mask)

    def _compose_labeled_row(self, labeled_images: List[Tuple[str, Image.Image]]) -> Image.Image:
        """
        Склейка по ширине с подписью над каждым блоком (h=24).
        """
        if not labeled_images:
            # Defensive: пусто — возвращаем белый пиксель
            return Image.new("L", (1, 1), color=255)
        w, h = labeled_images[0][1].size
        label_h = 24
        gap = 12
        total_w = w * len(labeled_images) + gap * (len(labeled_images) - 1)
        total_h = h + label_h
        canvas = Image.new("L", (total_w, total_h), color=255)
        draw = ImageDraw.Draw(canvas)
        x = 0
        for label, img in labeled_images:
            draw.text((x + 6, 4), label, fill=0)
            canvas.paste(img, (x, label_h))
            x += w + gap
        return canvas

    def adaptive_compare_k(
        self,
        image: Image.Image,
        ks: Iterable[int] = (3, 5, 9, 15),
        C: float = 1.0,
        T: float = 0.0,
        stat: str = "mean",
        polarity: str = "bright",
    ) -> Image.Image:
        """
        Сравнение адаптивного порога для разных k (размер окна).
        """
        labeled: List[Tuple[str, Image.Image]] = []
        for k in ks:
            kk = int(k)
            if kk < 3:
                kk = 3
            if kk % 2 == 0:
                kk += 1
            img = self.adaptive_threshold(image, k=kk, C=C, T=T, stat=stat, polarity=polarity)
            labeled.append((f"k={kk}", img))
        return self._compose_labeled_row(labeled)

    def adaptive_compare_C(
        self,
        image: Image.Image,
        Cs: Iterable[float] = (0.8, 1.0, 1.2),
        k: int = 15,
        T: float = 0.0,
        stat: str = "mean",
        polarity: str = "bright",
    ) -> Image.Image:
        """
        Сравнение адаптивного порога для разных значений C.
        """
        kk = int(k)
        if kk < 3:
            kk = 3
        if kk % 2 == 0:
            kk += 1
        labeled: List[Tuple[str, Image.Image]] = []
        for c in Cs:
            img = self.adaptive_threshold(image, k=kk, C=float(c), T=T, stat=stat, polarity=polarity)
            labeled.append((f"C={float(c):.3g}", img))
        return self._compose_labeled_row(labeled)

    def adaptive_compare_T(
        self,
        image: Image.Image,
        Ts: Iterable[float] = (-10.0, 0.0, 10.0),
        k: int = 15,
        C: float = 1.0,
        stat: str = "mean",
        polarity: str = "bright",
    ) -> Image.Image:
        """
        Сравнение адаптивного порога для разных значений T.
        """
        kk = int(k)
        if kk < 3:
            kk = 3
        if kk % 2 == 0:
            kk += 1
        labeled: List[Tuple[str, Image.Image]] = []
        for t in Ts:
            img = self.adaptive_threshold(image, k=kk, C=C, T=float(t), stat=stat, polarity=polarity)
            # Покажем T без лишних нулей
            labeled.append((f"T={float(t):.3g}", img))
        return self._compose_labeled_row(labeled)


