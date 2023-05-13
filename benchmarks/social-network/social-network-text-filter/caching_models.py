import json
import time

from transformers import pipeline
from transformers.pipelines import check_task

text = r'''
The titular threat of The Blob has always struck me as the ultimate movie
monster: an insatiably hungry, amoeba-like mass able to penetrate
virtually any safeguard, capable of--as a doomed doctor chillingly
describes it--"assimilating flesh on contact.
Snide comparisons to gelatin be damned, it's a concept with the most
devastating of potential consequences, not unlike the grey goo scenario
proposed by technological theorists fearful of
artificial intelligence run rampant.
'''

context = r'''
Extractive Question Answering is the task of extracting an answer from a text
given a question. An example of a question answering dataset is the SQuAD
dataset, which is entirely based on that task. If you would like to fine-tune
a model on a SQuAD task, you may leverage the
examples/pytorch/question-answering/run_squad.py script.
'''

# transformers: sentiment-analysis
classifier = pipeline('sentiment-analysis')
targeted_task = check_task('sentiment-analysis')[0]['default']['model']
print('sentiment-analysis model: {}'.format(targeted_task))
t = time.time()
result = classifier(text)
print('sentiment-analysis result: {}'.format(json.dumps(result)))
print('time: {}'.format(time.time() - t))

# transformers: question-answering
question_answerer = pipeline('question-answering')
targeted_task = check_task('question-answering')[0]['default']['model']
print('question-answering model: {}'.format(targeted_task))
t = time.time()
result = question_answerer(question='What is extractive question answering?',
                           context=context)
print('question-answering result: {}'.format(json.dumps(result)))
print('time: {}'.format(time.time() - t))
