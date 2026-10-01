import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import MangaCache, UserMangaList, RecommendationFeedback, FeedbackType

class MangaRecommender:
    """Machine Learning Engine to recommend mangas, using TF-IDF and Cosine Similairty"""

    @staticmethod
    def _extract_feature_string(manga: MangaCache) -> str:
        """Convert the manga metadata into a tokenized feature string"""
        tokens: List[str] = []

        if manga.tags:
            for tag in manga.tags:
                clean_tag = tag.lower().replace(" ", "_").replace("-", "_")
                tokens.append(f"tag::{clean_tag}")

        if manga.authors:
            for author in manga.authors:
                clean_author = author.lower().replace(" ", "_")
                tokens.append(f"author:{clean_author}")

        if manga.demographic:
            clean_demo = manga.demographic.lower().replace(" ", "_")
            tokens.append(f"demographic:{clean_demo}")

        if manga.publication_status:
            clean_status = manga.publication_status.lower().replace(" ", "_")
            tokens.append(f"status:{clean_status}")

        return " ".join(tokens)

    @staticmethod
    def _normalize_score(score: Optional[float]) -> float:
        """Normalize a 1.0-10.0 scale rating into centered weight range [-1.0, +1.0]"""
        if score is None:
            return 0.1
        return (score - 5.5) / 4.5

    def build_recommendation(
            self,
            all_cached_manga: List[MangaCache],
            user_list_entries: List[UserMangaList],
            feedback_entries: List[RecommendationFeedback],
            top_n: int = 10,
            shuffle: bool = False,
            temperature: float = 0.5,
    ) -> List[Tuple[MangaCache, float]]:
        """Gives recommendations for a user given their library history and feedback
        Returns a list of (MangaCache object, calculated_match_score) tuples"""
        if not all_cached_manga:
            return []

        manga_dict = {m.manga_id: m for m in all_cached_manga}
        df = pd.DataFrame([
            {
                "manga_id": m.manga_id,
                "feature_str": self._extract_feature_string(m),
            }
            for m in all_cached_manga
        ])

        df = df[df["feature_str"].str.len() > 0]
        if df.empty:
            return []

        vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[\w:-]+\b", binary=False)
        tfidf_matrix = vectorizer.fit_transform(df["feature_str"])

        manga_id_to_index = {m_id: idx for idx, m_id in enumerate(df["manga_id"])}

        user_vector = np.zeros((1, tfidf_matrix.shape[1]))
        user_manga_ids = set()

        for entry in user_list_entries:
            user_manga_ids.add(entry.manga_id)
            if entry.manga_id in manga_id_to_index:
                idx = manga_id_to_index[entry.manga_id]
                weight = self._normalize_score(entry.score)
                user_vector += weight * tfidf_matrix[idx].toarray()

        hate_manga_ids = set()
        not_interested_manga_ids = set()
        interested_manga_ids = set()

        for fb in feedback_entries:
            if fb.feedback_type == FeedbackType.HATE:
                hate_manga_ids.add(fb.manga_id)
                if fb.manga_id in manga_id_to_index:
                    idx = manga_id_to_index[fb.manga_id]
                    user_vector -= 1.5 * tfidf_matrix[idx].toarray()
            elif fb.feedback_type == FeedbackType.NOT_INTERESTED:
                not_interested_manga_ids.add(fb.manga_id)
            elif fb.feedback_type == FeedbackType.INTERESTED:
                interested_manga_ids.add(fb.manga_id)
                if fb.manga_id in manga_id_to_index:
                    idx = manga_id_to_index[fb.manga_id]
                    user_vector += 0.5 * tfidf_matrix[idx].toarray()

        candidate_mask = ~df["manga_id"].isin(user_manga_ids)
        candidate_df = df[candidate_mask].copy()

        if candidate_df.empty:
            return []

        candidate_indicies = [manga_id_to_index[m_id] for m_id in candidate_df["manga_id"]]
        candidate_matrix = tfidf_matrix[candidate_indicies]

        if np.all(user_vector == 0):
            user_vector = np.ones((1, tfidf_matrix.shape[1]))

        similarities = cosine_similarity(user_vector, candidate_matrix).flatten()

        candidates: List[Tuple[MangaCache, float]] = []

        for idx, row in candidate_df.reset_index(drop=True).iterrows():
            m_id = row["manga_id"]
            raw_score = float(similarities[idx])

            if m_id in hate_manga_ids:
                final_score = 0.0
            elif m_id in not_interested_manga_ids:
                final_score = raw_score * 0.15
            elif m_id in interested_manga_ids:
                final_score = min(1.0, raw_score * 1.35 + 0.1)
            else:
                final_score = raw_score

            final_score = max(0.0, min(1.0, round(final_score, 4)))
            if final_score > 0.0:
                candidates.append((manga_dict[m_id], final_score))

        candidates.sort(key=lambda x: x[1], reverse=True)

        if not candidates:
            return []

        if not shuffle or len(candidates) <= top_n:
            return candidates[:top_n]

        pool = candidates[: min(len(candidates), top_n * 3)]
        scores = np.array([sc for _, sc in pool])

        logits = scores / max(temperature, 0.01)
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)

        selected_indices = np.random.choice(
            len(pool), size=min(top_n, len(pool)), replace=False, p=probs
        )

        selected = [pool[i] for i in selected_indices]
        selected.sort(key=lambda x: x[1], reverse=True)
        return selected

manga_recommender = MangaRecommender()