import json

from textblob import TextBlob
from transformers import pipeline

classifier = None


def main(args):
    global question_answerer

    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    text = args.get('text', r'''
Extractive Question Answering is the task of extracting an answer from a text
given a question. An example of a question answering dataset is the SQuAD
dataset, which is entirely based on that task. If you would like to fine-tune
a model on a SQuAD task, you may leverage the
examples/pytorch/question-answering/run_squad.py script.
''')

    # --------------------------------------------------------------------------
    # Function
    # --------------------------------------------------------------------------
    polarity = TextBlob(text).sentiment.polarity
    if classifier is None:
        classifier = pipeline('sentiment-analysis')
    if polarity < 0:
        res = classifier(text)
        if res['label'] == 'POSITIVE':
            sentiment_analysis = True
        else:
            sentiment_analysis = False
    else:
        sentiment_analysis = True

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    res = {'sentiment_analysis': sentiment_analysis}
    return res
