from nltk.corpus import genesis
from nltk.collocations import BigramAssocMeasures, TrigramAssocMeasures, BigramCollocationFinder
import re
import csv

def sanitize_tweet_word(word):
  if word[0] is '\'':
    word = word[1:]
  if word[len(word) - 1] is '\'':
    word = word[:-1]
  special_word = (word[0] is '#') or (word[0] is '@')
  return word if special_word else word.lower()

def sanitize_tweet(tweet):
  # Remove URLs
  tweet = re.sub(r'http\S+', '', tweet)
  # Purge punctuation
  tweet = re.sub(r'[^\w\s\'#@_\?!]', '', tweet)
  # Separate question and exclamation marks
  tweet = re.sub(r'!', ' !', tweet)
  tweet = re.sub(r'\?', ' ?', tweet)
  # Split into array
  tweet = tweet.split()
  # Sanitize tweet words
  tweet = list(map(sanitize_tweet_word, tweet))
  # Remove retweet preface
  if tweet[0] == 'rt':
    tweet = tweet[2:]
  # Add starting and ending words
  tweet.insert(0, '<start>')
  tweet.append('<end>')
  return tweet

def read_data(filename):
  with open(filename, 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    count = 0
    for row in reader:
      count += 1
      if count is 50:
        break
      tweet = row['text']
      print()
      print(tweet)
      print(sanitize_tweet(tweet))

# '''def train_model(tweet):
  

# '
# words = genesis.words('english-web.txt')

# bigram_measures = BigramAssocMeasures()
# trigram_measures = TrigramAssocMeasures()

# finder = BigramCollocationFinder.from_words(words)

# results = finder.nbest(bigram_measures.pmi, 10)
# print(results)'''

read_data('data/tweets.csv')