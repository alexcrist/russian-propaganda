import re
import csv
import time
from random import choice
from nltk.data import load
from collections import defaultdict

TWEET_FILE = 'data/tweets.csv'
START_TOKEN = '<START>'
END_TOKEN = '<END>'

def sanitize_tweet_word(word):
  # Remove leading and trailing apostrophes
  word = word[1:] if (word[0] is '\'') else word
  if len(word) == 0:
    return word
  word = word[:-1] if (word[len(word) - 1] is '\'') else word
  
  # Lowercase if not a mention (@) or a hashtag (#)
  special_word = (word[0] is '#') or (word[0] is '@')
  word = word if (special_word or word.isupper()) else word.lower()

  return word

def sanitize_tweet(tweet):
  tweet = re.sub(r'http\S+', '', tweet)           # Remove URLs
  tweet = re.sub(r'[^\w\s\'#@_\?!\.]', '', tweet) # Purge punctuation
  tweet = re.sub(r'!', ' !', tweet)               # Separate question marks 
  tweet = re.sub(r'\?', ' ?', tweet)              # Separate exclamation marks
  tweet = re.sub(r'\?', ' .', tweet)              # Separate periods
  tweet = tweet.split()                           # Split into array
  tweet = list(map(sanitize_tweet_word, tweet))   # Sanitize individual words
  if (len(tweet) > 0) and (tweet[0] == 'RT'):     # Remove retweet stuff
    tweet = tweet[2:]

  # Add starting and ending tokens
  tweet.insert(0, START_TOKEN)
  tweet.append(END_TOKEN)
  return tweet

def read_tweets_from_file(file):
  with open(file, 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    tweets = []
    for row in reader:
      tweet = row['text']
      tweets += sanitize_tweet(tweet)
  return tweets

# Builds a flat n-gram
# i.e.: [('this', 'was'), ('was', 'a'), ('a', 'triumph')]
def build_flat_ngram(string, n):
  strings = [string[i:] for i in range(n)]
  return zip(*strings)

# Builds a bigram using a nested dictionary structure with weighted values
# i.e.: {'this': {'was': 1}, 'was': {'a': 1}, 'a': {'triumph': 1}}
def build_bigram(string):
  flat_bigram = build_flat_ngram(string, 2)
  bigram = defaultdict(lambda: defaultdict(int))
  for word1, word2 in flat_bigram:
    bigram[word1][word2] += 1
  return bigram

# Builds a trigram using a nested dictionary structure with weighted values
# i.e.: {'this': {'was': {'a': 1}}, 'was': {'a': {'triumph': 1}}}
def build_trigram(string):
  flat_trigram = build_flat_ngram(string, 3)
  ngram = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
  for word1, word2, word3 in flat_trigram:
    ngram[word1][word2][word3] += 1
  return ngram

# Generates a tweet using the given bigram and trigram
def generate_tweet(bigram, trigram):
  tweet = ''
  word1 = ''
  word2 = START_TOKEN

  # Keeping adding words until we reach an end token
  while word2 != END_TOKEN:
    
    # First try to use the trigram
    choices = trigram[word1][word2]

    # Fallback on bigram if necessary
    if len(choices.items()) == 0:
      choices = bigram[word2]
    
    # Choose a new word based on the weighted values of the choices
    flat_choices = []
    for key, value in choices.items():
      flat_choices += [key] * value
    word3 = choice(flat_choices)
    tweet += word3 + ' '
    
    # Advance generator words
    word1 = word2
    word2 = word3

  # Reformat tweet
  tweet = tweet[:-(len(END_TOKEN) + 2)] # Remove end token
  tweet = re.sub(r' !', '!', tweet)     # Join question marks 
  tweet = re.sub(r' \?', '?', tweet)    # Join exclamation marks
  tweet = re.sub(r' \.', '.', tweet)    # Join periods marks

  # Capitalize sentences
  sentence_tokenizer = load('tokenizers/punkt/english.pickle')
  sentences = sentence_tokenizer.tokenize(tweet)
  sentences = [(sentence[0].upper() + sentence[1:]) for sentence in sentences]
  tweet = ' '.join(sentences)

  # Validate tweet
  is_valid_tweet = len(tweet) <= 280
  if is_valid_tweet:
    return tweet
  else:
    return generate_tweet(bigram, trigram)

if __name__ == '__main__':
  print('Loading tweets...')
  tweets = read_tweets_from_file(TWEET_FILE)
  print('Building bigram...')
  bigram = build_bigram(tweets)
  print('Building trigram...')
  trigram = build_trigram(tweets)
  print('Tweet generator ready.')
  while True:
    input('Press [Enter] to generate.')
    tweet = generate_tweet(bigram, trigram)
    print(tweet)