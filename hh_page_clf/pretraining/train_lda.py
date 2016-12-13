import argparse
from itertools import islice, chain
from typing import Tuple

import json_lines
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.pipeline import make_pipeline
from sklearn.externals import joblib
import stop_words
from tqdm import tqdm


def LDAPageVctorizer(*,
                     n_topics: int,
                     min_df: int,
                     max_features: int,
                     max_iter: int,
                     ngram_range: Tuple[int, int],
                     batch_size: int=1024,
                     verbose=1):
    vec = CountVectorizer(
        preprocessor=_text_preprocessor,
        stop_words=get_stop_words(),
        min_df=min_df,
        max_features=max_features,
        ngram_range=ngram_range,
    )
    lda = LatentDirichletAllocation(
        learning_method='online',
        n_topics=n_topics,
        batch_size=batch_size,
        evaluate_every=2,
        verbose=verbose,
        max_iter=max_iter,
        n_jobs=1,
    )
    return make_pipeline(vec, lda)


def _text_preprocessor(text):
    return text.lower()


def get_stop_words():
    return set(chain.from_iterable(
        stop_words.get_stop_words(lang)
        for lang in stop_words.AVAILABLE_LANGUAGES
    ))


def _iter_text(path):
    with json_lines.open(path) as f:
        for item in f:
            yield item['text']


def train(input_jlgz, limit=None, **lda_kwargs):
    lda_pipe = LDAPageVctorizer(**lda_kwargs)
    data = _iter_text(input_jlgz)
    if limit:
        data = islice(data, limit)
    lda_pipe.fit(tqdm(data, desc='Loading text'))
    for name, step in lda_pipe.steps:
        step.verbose = False
    return lda_pipe


def main():
    parser = argparse.ArgumentParser()
    arg = parser.add_argument
    arg('input', help='In .jl.gz format with text in "text" field')
    arg('output', help='Output LDA model in joblib format')
    arg('--n-topics', type=int, default=50)
    arg('--max-features', type=int, default=100000)
    arg('--ngram', type=int, default=1)
    arg('--max-iter', type=int, default=10)
    arg('--min-df', type=int, default=10)
    arg('--limit', type=int, help='limit to first N pages')
    args = parser.parse_args()

    pipe = train(
        args.input,
        n_topics=args.n_topics,
        max_features=args.max_features,
        limit=args.limit,
        ngram_range=(1, args.ngram),
        max_iter=args.max_iter,
        min_df=args.min_df,
    )
    joblib.dump(pipe, args.output, compress=3)
