"""Word TF-IDF cosine retrieval with additive, source-grounded explanations."""
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer


def normalize(text):
    return unicodedata.normalize('NFC', text).casefold()


def token_spans(text):
    """Keep Unicode marks attached to Bangla letters; offsets reference original text."""
    start = None
    for i, char in enumerate(text + ' '):
        valid = unicodedata.category(char)[0] in 'LNM'
        if valid and start is None:
            start = i
        elif not valid and start is not None:
            yield normalize(text[start:i]), start, i
            start = None


def tokenize(text):
    return [token for token, _, _ in token_spans(text)]


class KeywordIndex:
    def __init__(self, fit_records):
        self.vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None,
                                          lowercase=False, norm='l2', smooth_idf=True)
        self.vectorizer.fit([r['text'] for r in fit_records])
        self.terms = self.vectorizer.get_feature_names_out()

    def search(self, text, candidates, k=5, exclude_id=None, include_zero=False):
        if k < 1:
            raise ValueError('k must be positive')
        candidates = [r for r in candidates if r['report_id'] != exclude_id]
        if not candidates:
            return []
        q = self.vectorizer.transform([text])
        matrix = self.vectorizer.transform([r['text'] for r in candidates])
        scores = (matrix @ q.T).toarray().ravel()
        order = sorted(range(len(candidates)), key=lambda i: (-float(scores[i]), candidates[i]['report_id']))
        results = []
        for i in order[:k]:
            if scores[i] <= 0 and not include_zero:
                continue
            product = matrix[i].multiply(q).tocoo()
            signals = []
            for column, value in sorted(zip(product.col, product.data), key=lambda p: (-p[1], p[0])):
                term = str(self.terms[column])
                signals.append(dict(term=term, contribution=float(value),
                                    query_spans=[[a,b] for t,a,b in token_spans(text) if t == term],
                                    candidate_spans=[[a,b] for t,a,b in token_spans(candidates[i]['text']) if t == term]))
            results.append(dict(report=candidates[i], score=float(scores[i]),
                                status='potential relationship', signals=signals))
        return results
