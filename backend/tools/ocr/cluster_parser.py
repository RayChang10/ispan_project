import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

# 嘗試讀取 .env（若沒有套件則靜默略過）
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

SentenceSplitterStrategy = Literal["regex", "spacy", "nltk"]
EmbeddingBackend = Literal["openai", "hf"]
ClusterMethod = Literal["kmeans", "hdbscan"]


def split_into_sentences(
    text: str, strategy: SentenceSplitterStrategy = "regex"
) -> List[str]:
    """雙語斷句（中英）。支援 regex/spacy/nltk，若指定策略不可用會回退 regex。"""
    if not text:
        return []

    if strategy == "spacy":
        try:
            import spacy  # type: ignore

            try:
                nlp = spacy.load("xx_sent_ud_sm")
            except Exception:
                try:
                    nlp = spacy.load("en_core_web_sm")
                except Exception:
                    nlp = spacy.blank("xx")
                    if "sentencizer" not in nlp.pipe_names:
                        nlp.add_pipe("sentencizer")
            doc = nlp(text)
            sents = [
                s.text.strip() for s in doc.sents if s.text and len(s.text.strip()) >= 2
            ]
            if sents:
                return sents
        except Exception:
            pass

    if strategy == "nltk":
        try:
            import nltk  # type: ignore

            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)
            sents = nltk.sent_tokenize(text)
            sents = [s.strip() for s in sents if len(s.strip()) >= 2]
            if sents:
                return sents
        except Exception:
            pass

    # regex 回退
    import re

    pattern = r"([^。！？!?\n]*[。！？!?]+|[^。！？!?\n]+)(?=\s|\n|$)"
    parts = re.findall(pattern, text)
    if not parts:
        parts = re.split(r"[\n\r]+", text)

    sentences: List[str] = []
    for p in parts:
        s = p.strip()
        if len(s) >= 2:
            sentences.append(s)
    return sentences


def preprocess_text(raw_text: str) -> str:
    """粗略清洗：
    - 刪常見頁眉/頁腳/雜訊（Powered By, print=true, page x/y）
    - 移除幾乎無字元或純符號行
    - 移除跨頁重複高頻短行
    - 合併過短行為段落
    """
    import re

    if not raw_text:
        return ""

    lines = [ln.strip() for ln in raw_text.splitlines()]

    # 統計行頻以偵測可能的頁眉/頁腳
    from collections import Counter

    freq = Counter(lines)

    def is_noise_line(ln: str) -> bool:
        if not ln:
            return True
        if len(ln) <= 2:
            return True
        # 大量非字母數字符號
        letters = sum(ch.isalpha() for ch in ln)
        digits = sum(ch.isdigit() for ch in ln)
        alnum = letters + digits
        if alnum == 0 and len(ln) > 0:
            return True
        # 頁碼或 print 標記、Powered By
        if re.search(r"\bprint\s*=\s*true\b", ln, flags=re.I):
            return True
        if re.search(r"^\d+\s*/\s*\d+$", ln):
            return True
        if re.search(r"^page\s*\d+\s*of\s*\d+$", ln, flags=re.I):
            return True
        if "Powered By" in ln or "Powered by" in ln:
            return True
        # 明確聯絡/連結雜訊（單獨一行時才移除）
        if len(ln) <= 80:
            if re.search(r"\bhttps?://", ln, flags=re.I):
                return True
            if re.search(r"@.+\.[a-zA-Z]{2,}", ln):  # email
                return True
            if re.search(r"\+?\d[\d\-\s]{6,}\d", ln):  # phone
                return True
        # 高頻短行（疑似頁眉/頁腳）
        if freq[ln] >= 2 and len(ln) <= 40:
            return True
        return False

    filtered = [ln for ln in lines if not is_noise_line(ln)]

    # 將含條列符號的行先切分為子片段
    split_seps = ["•", "·", "・", "●", "○", "▪", "- ", " – ", " — ", ";", "；"]
    expanded: List[str] = []
    for ln in filtered:
        if any(sep.strip() in ln for sep in split_seps):
            # 以多種分隔符切分
            temp = [ln]
            for sep in ["•", "·", "・", "●", "○", "▪"]:
                temp = [p for t in temp for p in t.split(sep)]
            more: List[str] = []
            for t in temp:
                t = (
                    t.replace(" – ", ". ")
                    .replace(" — ", ". ")
                    .replace(";", ". ")
                    .replace("；", ". ")
                )
                parts = [p.strip(" \t-•·・●○▪") for p in t.split(". ")]
                for p in parts:
                    if p:
                        more.append(p)
            expanded.extend(more if more else [ln])
        else:
            expanded.append(ln)

    # 合併行為段落：非結尾標點則與下一行合併
    paragraphs: List[str] = []
    buf = []

    def flush_buf():
        if buf:
            para = " ".join(buf).strip()
            if para:
                paragraphs.append(para)
            buf.clear()

    for ln in expanded:
        if not ln:
            flush_buf()
            continue
        buf.append(ln)
        if re.search(r"[。！？!?。.?!]$", ln):
            flush_buf()
    flush_buf()

    # 去重（保持順序）
    seen = set()
    deduped: List[str] = []
    for p in paragraphs:
        if p not in seen:
            seen.add(p)
            deduped.append(p)

    return "\n".join(deduped)


class Embedder:
    def __init__(
        self,
        backend: EmbeddingBackend = "hf",
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
    ) -> None:
        self.backend = backend
        self.model_name = model_name
        self._client = None
        self._model = None

    def _ensure_loaded(self) -> None:
        if self.backend == "openai":
            # 延遲載入 OpenAI client
            if self._client is None:
                try:
                    from openai import OpenAI  # type: ignore
                except Exception as exc:
                    raise RuntimeError(
                        "未安裝 openai 套件，請先安裝: pip install openai"
                    ) from exc
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("缺少 OPENAI_API_KEY 環境變數")
                self._client = OpenAI(api_key=api_key)
        elif self.backend == "hf":
            # 延遲載入 SentenceTransformer
            if self._model is None:
                try:
                    from sentence_transformers import (
                        SentenceTransformer,
                    )  # type: ignore
                except Exception as exc:
                    raise RuntimeError(
                        "未安裝 sentence-transformers，請先安裝: pip install sentence-transformers"
                    ) from exc
                self._model = SentenceTransformer(self.model_name)
        else:
            raise ValueError(f"未知的 backend: {self.backend}")

    def embed(self, texts: List[str]) -> np.ndarray:
        self._ensure_loaded()
        if not texts:
            return np.zeros((0, 1), dtype=float)

        if self.backend == "openai":
            # OpenAI: text-embedding-3-large
            resp = self._client.embeddings.create(model="text-embedding-3-large", input=texts)  # type: ignore[attr-defined]
            vectors = [d.embedding for d in resp.data]
            arr = np.array(vectors, dtype=float)
            # 正規化以利 cosine 相似度
            norm = np.linalg.norm(arr, axis=1, keepdims=True)
            norm[norm == 0] = 1.0
            return arr / norm
        elif self.backend == "hf":
            # HuggingFace: all-mpnet-base-v2
            emb = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)  # type: ignore[union-attr]
            return emb
        else:
            raise ValueError(f"未知的 backend: {self.backend}")


@dataclass
class ClusterResult:
    sentences: List[str]
    labels: List[int]
    centroids: np.ndarray


def cluster_embeddings(
    sentences: List[str],
    embeddings: np.ndarray,
    method: ClusterMethod = "kmeans",
    n_clusters: int = 4,
) -> ClusterResult:
    if embeddings.shape[0] != len(sentences):
        raise ValueError("embeddings 與 sentences 數量不一致")
    if embeddings.shape[0] == 0:
        return ClusterResult(
            sentences=[], labels=[], centroids=np.zeros((0, 1), dtype=float)
        )

    if method == "kmeans":
        num_samples = embeddings.shape[0]
        # 自動調整群數，避免 n_samples < n_clusters 的錯誤
        k = max(1, min(n_clusters, num_samples))
        if k == 1:
            labels = np.zeros(num_samples, dtype=int)
            centroids = np.mean(embeddings, axis=0, keepdims=True)
            return ClusterResult(
                sentences=sentences, labels=list(map(int, labels)), centroids=centroids
            )
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(embeddings)
        centroids = kmeans.cluster_centers_
        return ClusterResult(
            sentences=sentences, labels=list(map(int, labels)), centroids=centroids
        )
    elif method == "hdbscan":
        try:
            import hdbscan  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "未安裝 hdbscan，請改用 --cluster kmeans 或先安裝 hdbscan"
            ) from exc
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=max(2, len(sentences) // 8), metric="euclidean"
        )
        labels = clusterer.fit_predict(embeddings)
        # 估算每個 cluster 的中心
        unique = sorted([l for l in set(labels) if l != -1])
        centroids = []
        for cid in unique:
            idx = np.where(labels == cid)[0]
            centroids.append(np.mean(embeddings[idx], axis=0))
        if len(centroids) == 0:
            centroids_arr = np.zeros((0, embeddings.shape[1]))
        else:
            centroids_arr = np.vstack(centroids)
        # 重新映射 cluster id 至 [0..k-1]
        remap = {old: i for i, old in enumerate(unique)}
        labels_mapped = [remap.get(int(l), -1) for l in labels]
        return ClusterResult(
            sentences=sentences, labels=labels_mapped, centroids=centroids_arr
        )
    else:
        raise ValueError(f"未知的聚類方法: {method}")


def name_clusters(
    cluster_centroids: np.ndarray,
    label_texts: List[str],
    embedder: Embedder,
) -> Dict[int, str]:
    """以語義相似度對 cluster centroid 進行命名。

    - 將目標標籤（教育/經歷/技能/成就）做嵌入
    - 計算 cos 相似度，取最大者
    """
    if cluster_centroids.shape[0] == 0:
        return {}
    label_vectors = embedder.embed(label_texts)
    sim = cosine_similarity(cluster_centroids, label_vectors)
    assignments: Dict[int, str] = {}
    used = set()
    # 先以貪婪方式配對，避免同一標籤重複過多（允許重複，但嘗試分散）
    for i in range(sim.shape[0]):
        row = sim[i]
        sorted_idx = list(np.argsort(-row))
        for idx in sorted_idx:
            label = label_texts[idx]
            if label not in used:
                assignments[i] = label
                used.add(label)
                break
        if i not in assignments:
            assignments[i] = label_texts[int(np.argmax(row))]
    return assignments


def build_anchor_labels() -> Dict[str, List[str]]:
    return {
        "教育": [
            "Education",
            "教育",
            "學歷",
            "畢業",
            "Bachelor",
            "B.S.",
            "B.A.",
            "Master",
            "M.S.",
            "University",
            "College",
            "Department",
            "系",
            "科",
            "學校",
            "GPA",
            "NTU",
            "National Taiwan University",
            "國立",
            "研究所",
        ],
        "經歷": [
            "Experience",
            "經歷",
            "工作",
            "任職",
            "公司",
            "Project Manager",
            "Software Engineer",
            "Intern",
            "工作經驗",
            "負責",
            "職務",
            "Team Lead",
            "PM",
            "產品經理",
            "資料科學家",
            "AI Data Scientist",
            "Process Engineer",
            "Owner",
            "Led",
            "Built",
            "Deployed",
            "設計",
            "導入",
        ],
        "技能": [
            "Skills",
            "技能",
            "Programming",
            "Tools",
            "Framework",
            "Python",
            "Java",
            "SQL",
            "Git",
            "Docker",
            "語言",
            "證照",
            "Kubernetes",
            "Helm",
            "CI/CD",
            "Azure",
            "Databricks",
            "Grafana",
            "PowerBI",
            "MLflow",
            "Spark",
            "scikit-learn",
        ],
        "成就": [
            "Achievements",
            "成就",
            "獎項",
            "Award",
            "成果",
            "提升",
            "改善",
            "增加",
            "降低",
            "KPI",
            "達成",
            "優化",
            "reduced",
            "improved",
            "increased",
            "decreased",
            "cut",
            "%",
            "節省",
            "提升",
        ],
    }


def assign_by_anchors(
    sentences: List[str],
    sentence_vectors: np.ndarray,
    embedder: Embedder,
    threshold: float = 0.45,
) -> Tuple[Dict[int, str], List[int]]:
    """以 anchors 直接指派類別。
    回傳：assigned_map（index->label）、unassigned_indices
    """
    label_to_anchors = build_anchor_labels()
    labels = list(label_to_anchors.keys())
    anchor_texts: List[str] = []
    anchor_label_index: List[int] = []
    for li, label in enumerate(labels):
        for a in label_to_anchors[label]:
            anchor_texts.append(a)
            anchor_label_index.append(li)

    anchor_vecs = embedder.embed(anchor_texts)
    sims = cosine_similarity(sentence_vectors, anchor_vecs)

    assigned: Dict[int, str] = {}
    unassigned: List[int] = []
    for i in range(sims.shape[0]):
        row = sims[i]
        j = int(np.argmax(row))
        score = float(row[j])
        if score >= threshold:
            label = labels[anchor_label_index[j]]
            assigned[i] = label
        else:
            unassigned.append(i)
    return assigned, unassigned


def group_by_named_clusters(
    cluster_result: ClusterResult,
    cluster_name_map: Dict[int, str],
) -> Dict[str, List[Tuple[str, int]]]:
    groups: Dict[str, List[Tuple[str, int]]] = {}
    for sent, lab in zip(cluster_result.sentences, cluster_result.labels):
        if lab == -1:
            bucket = "未分群"
        else:
            bucket = cluster_name_map.get(lab, f"群組{lab}")
        groups.setdefault(bucket, []).append((sent, lab))
    return groups


def run_pipeline(
    text: str,
    backend: EmbeddingBackend = "hf",
    cluster_method: ClusterMethod = "kmeans",
    n_clusters: int = 4,
    enable_preprocess: bool = True,
    use_anchors: bool = True,
    anchor_threshold: float = 0.45,
) -> Dict[str, List[str]]:
    # 前處理
    working_text = preprocess_text(text) if enable_preprocess else text

    # 斷句策略可由環境變數 SENT_SPLITTER 控制
    splitter: str = os.getenv("SENT_SPLITTER", "regex")
    if splitter not in ("regex", "spacy", "nltk"):
        splitter = "regex"
    sentences = split_into_sentences(working_text, strategy=splitter)  # type: ignore[arg-type]
    if not sentences:
        return {"未分群": []}

    embedder = Embedder(backend=backend)
    emb = embedder.embed(sentences)
    assigned_map: Dict[int, str] = {}
    remaining_indices: List[int] = list(range(len(sentences)))
    if use_anchors:
        assigned_map, remaining_indices = assign_by_anchors(
            sentences, emb, embedder, threshold=anchor_threshold
        )

    # 對未指派者進行聚類
    if remaining_indices:
        emb_remaining = emb[remaining_indices]
        result = cluster_embeddings(
            [sentences[i] for i in remaining_indices],
            emb_remaining,
            method=cluster_method,
            n_clusters=n_clusters,
        )
        labels_target = ["教育", "經歷", "技能", "成就"]
        centroids = result.centroids
        if centroids.shape[0] == 0 and cluster_method == "hdbscan":
            cluster_name_map: Dict[int, str] = {}
        else:
            cluster_name_map = name_clusters(centroids, labels_target, embedder)
        clustered_groups = group_by_named_clusters(result, cluster_name_map)
    else:
        clustered_groups = {}

    # 合併 anchors 指派結果
    final_groups: Dict[str, List[str]] = {}
    for idx, label in assigned_map.items():
        final_groups.setdefault(label, []).append(sentences[idx])
    for label, pairs in clustered_groups.items():
        final_groups.setdefault(label, []).extend([s for s, _ in pairs])

    return final_groups


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resume sentence clustering into 教育/經歷/技能/成就"
    )
    parser.add_argument(
        "--input", "-i", type=str, default="", help="輸入檔路徑（若省略則讀取 STDIN）"
    )
    parser.add_argument(
        "--backend",
        choices=["openai", "hf"],
        default="hf",
        help="嵌入後端：openai 或 hf",
    )
    parser.add_argument(
        "--cluster", choices=["kmeans", "hdbscan"], default="kmeans", help="聚類方式"
    )
    parser.add_argument("--k", type=int, default=4, help="KMeans 的群數（預設 4）")
    parser.add_argument(
        "--splitter",
        choices=["regex", "spacy", "nltk"],
        default="regex",
        help="斷句策略（預設 regex）",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="停用前處理清洗（預設啟用）",
    )
    parser.add_argument(
        "--no-anchors",
        action="store_true",
        help="停用 anchor 引導分類（預設啟用）",
    )
    parser.add_argument(
        "--anchor-threshold",
        type=float,
        default=0.38,
        help="anchor 相似度門檻（預設 0.38）",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> None:
    args = parse_args(argv)
    # 讓 CLI 覆寫環境設定
    os.environ["SENT_SPLITTER"] = getattr(args, "splitter", "regex") or "regex"
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    result = run_pipeline(
        text=text,
        backend=args.backend,
        cluster_method=args.cluster,
        n_clusters=args.k,
        enable_preprocess=not args.no_preprocess,
        use_anchors=not args.no_anchors,
        anchor_threshold=getattr(args, "anchor_threshold", 0.38),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
