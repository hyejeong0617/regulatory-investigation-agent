"""BM25 retrieval: transparent, offline, no embeddings or benchmark routes."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict

from .corpus import Corpus

STOP = set("a an the of to for in is are be and or on by with from which what when how this that as at it its does do if so eu regulation regulations article articles applicable case question above currently requirements legislation".split())


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    words = re.findall(r"[a-z0-9]+", text)
    # Conservative inflection normalization plus a country spelling alias.
    return ["turkiye" if w == "turkey" else w[:-1] if len(w) > 4 and w.endswith("s") else w
            for w in words if w not in STOP and (len(w) > 1 or w.isdigit())]


class SearchIndex:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus
        self.postings = defaultdict(dict)
        self.lengths = []
        for i, record in enumerate(corpus.records):
            counts = Counter(tokens(record.text + " " + record.location + " " + record.regulation))
            self.lengths.append(sum(counts.values()))
            for word, count in counts.items():
                self.postings[word][i] = count
        self.average = sum(self.lengths) / max(1, len(self.lengths))

    def search(self, query: str, limit: int = 6, regulation: str = "", kind: str = ""):
        words = set(tokens(query))
        scores = defaultdict(float)
        matched = defaultdict(set)
        n = len(self.lengths)
        for word in words:
            postings = self.postings.get(word, {})
            idf = math.log(1 + (n - len(postings) + 0.5) / (len(postings) + 0.5))
            for i, count in postings.items():
                record = self.corpus.records[i]
                if regulation and regulation != record.regulation or kind and kind != record.kind:
                    continue
                scores[i] += idf * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * self.lengths[i] / self.average))
                matched[i].add(word)
        # Reward coverage so a single rare word doesn't defeat the complete question.
        for i in scores:
            scores[i] *= 0.4 + 0.6 * len(matched[i]) / max(1, len(words))
        ranking = sorted(scores, key=lambda i: (-scores[i], self.corpus.records[i].id))[:max(1, min(limit, 12))]
        return [(self.corpus.records[i], round(scores[i], 5)) for i in ranking]
