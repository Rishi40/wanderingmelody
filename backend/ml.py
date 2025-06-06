import json
import os
import re
import pandas as pd
from typing import List, Callable
from collections import Counter
import nltk
import math
import ssl
from nltk.corpus import wordnet
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import Counter
from nltk.stem import WordNetLemmatizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import scipy.sparse
import numpy as np
from nltk.data import find
import logging

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Define a stopwords list manually
custom_stopwords = set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
    'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her',
    'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs',
    'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
    'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
    'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about',
    'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above',
    'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under',
    'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
    'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
])

# Load datasets
#spotify_df = pd.read_csv("mini_spotify_track_db.csv")
spotify_df = pd.read_json("spotify-tracks-dataset.json")
lyric_df = pd.read_json("spotify_millsongdata.json")
#lyric_df = pd.read_csv("mini_spotify_db.csv")

def polarity_scores_for_songs(df):
    sia = SentimentIntensityAnalyzer() 
    df['sentiment'] = df['text'].apply(lambda song_lyrics: sia.polarity_scores(song_lyrics)['compound'])

print("Spotify Dataset Sample:")
print(spotify_df.head())

print("Lyrics Dataset Sample:")
print(lyric_df.head())

# Tokenization function
def tokenize(text: str) -> List[str]:
    """Returns a list of words that make up the text."""
    return re.findall(r"[a-zA-Z]+", text.lower())

# Tokenize lyrics
def tokenize_lyrics(dict_of_lyrics, tokenize_method: Callable[[str], List[str]]):
    tokenized_lyrics = {}
    nrows = len(lyric_df)
    for i in range(nrows):
        lyrics = dict_of_lyrics[i]['text']
        tokenized_lyrics[i] = tokenize_method(lyrics)
    return tokenized_lyrics

# Remove stop words
def remove_stop_words(stop_words, tokenized_lyrics):
    stop_word_removed_lyrics = {}
    for i, lyrics in tokenized_lyrics.items():
        cleaned_lyrics = [word for word in lyrics if word.lower() not in stop_words]
        stop_word_removed_lyrics[i] = cleaned_lyrics
    return stop_word_removed_lyrics

# Remove stop words from input
def remove_stop_words_input(tokenize, stop_words, input_words):
    list_tokens = tokenize(input_words)
    cleaned_words = [word for word in list_tokens if word not in stop_words]
    return cleaned_words

# Build inverted index
def build_inverted_index(songs: dict) -> dict:
    inverted_index = {}
    for song_num, tokens in songs.items():
        token_counts = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1
        for token, count in token_counts.items():
            if token not in inverted_index:
                inverted_index[token] = []
            inverted_index[token].append((song_num, count))
    return inverted_index

# Compute IDF
def compute_idf(inv_idx, n_docs, min_df=0, max_df_ratio=1):
    return_dict = {}
    for word, word_list in inv_idx.items():
        word_count = len(word_list)
        if word_count >= min_df and word_count / n_docs <= max_df_ratio:
            return_dict[word] = [song_id for song_id, _ in word_list]  # Store song IDs instead of float IDF
    return return_dict

# Get synonyms of a word
def get_synonyms_of_word(word):
    synonyms = []
    for syn in wordnet.synsets(word):
        for i in syn.lemmas():
            synonyms.append(i.name().replace("_", " ").lower())
    return set(synonyms)

# Get antonyms of a word
def get_antonyms(word):
    antonyms = []
    for syn in wordnet.synsets(word):
        for i in syn.lemmas():
            if i.antonyms():
                antonyms.append(i.name().replace("_", " ").lower())
    return set(antonyms)

# Sort songs by polarity scores
def sort_polarity_scores(input_song_list, cleaned_tokenized_lyrics, polarity_type="compound"):
    sia = SentimentIntensityAnalyzer()
    dict_of_polarity_scores = {}
    for song_row_number in input_song_list:
        if song_row_number in cleaned_tokenized_lyrics:
            dict_of_polarity_scores[song_row_number] = sia.polarity_scores(" ".join(cleaned_tokenized_lyrics[song_row_number]))
    sorted_songs = sorted(dict_of_polarity_scores, key=lambda x: dict_of_polarity_scores[x][polarity_type], reverse=True)
    return sorted_songs

print("before the recommended song function")

def recommend_songs(mood, cleaned_tokenized_lyrics, clean_song_count, weather):
     print("after the recommended song function")
     combined_mood = f"{mood} {weather}".strip()
     clean_genre_input = remove_stop_words(custom_stopwords, {0: tokenize(combined_mood)})
     possible_songs_dict = {}
     for word in clean_genre_input[0]:
         if clean_song_count.get(word) is not None:
             possible_songs_dict[word] = clean_song_count[word]
 
     stemmed_user_input_preserve_original = [word for word in clean_genre_input[0] if possible_songs_dict.get(word) is None]
 
     for word in stemmed_user_input_preserve_original:
         if clean_song_count.get(word) is not None:
             possible_songs_dict[word] = clean_song_count[word]
 
     most_common_songs = []
     if possible_songs_dict:
         # song_counts = Counter(song for song_list in possible_songs_dict.values() for song in song_list)
         song_counts = Counter()
         for song_list in possible_songs_dict.values():
             if isinstance(song_list, list):  # Ensure it's a list
                 song_counts.update(song_list)
             else:
                 print(f"Warning: Unexpected value in possible_songs_dict - {song_list}")
 
         max_number = max(song_counts.values(), default=0)
         most_common_songs = [song for song, count in song_counts.items() if count == max_number]
 
     word_synonym_dict = {word: list(get_synonyms_of_word(word)) for word in stemmed_user_input_preserve_original if possible_songs_dict.get(word) is None}
 
     print(f"Cleaned Input: {clean_genre_input}")
     print(f"Possible Songs: {possible_songs_dict}")
     print(f"Most Common Songs: {most_common_songs}")
 
     return most_common_songs, word_synonym_dict

def other_recommend_songs(user_genre_input, cleaned_tokenized_lyrics, clean_song_count):
    inverted_index = build_inverted_index(cleaned_tokenized_lyrics)
    
    print("after the recommended song function")
    clean_genre_input = remove_stop_words(custom_stopwords, {0: tokenize(user_genre_input)})
    possible_songs_dict = {}
    for word in clean_genre_input[0]:
        if clean_song_count.get(word) is not None:
            possible_songs_dict[word] = clean_song_count[word]
    
    stemmed_user_input_preserve_original = [word for word in clean_genre_input[0] if possible_songs_dict.get(word) is None]
    
    for word in stemmed_user_input_preserve_original:
        if clean_song_count.get(word) is not None:
            possible_songs_dict[word] = clean_song_count[word]
    
    most_common_songs = []
    if possible_songs_dict:
        # song_counts = Counter(song for song_list in possible_songs_dict.values() for song in song_list)
        song_counts = Counter()
        for song_list in possible_songs_dict.values():
            if isinstance(song_list, list):  # Ensure it's a list
                song_counts.update(song_list)
            else:
                print(f"Warning: Unexpected value in possible_songs_dict - {song_list}")

        max_number = max(song_counts.values(), default=0)
        most_common_songs = [song for song, count in song_counts.items() if count == max_number]
        
    if len(most_common_songs) > 40:
        most_common_songs = most_common_songs[:40]  

    sum_of_words_dict = {}

    for word in clean_genre_input[0]:
        if word not in inverted_index:
            continue  

        inv_index_list = inverted_index[word]
        for song_idx, num_words in inv_index_list:
            if song_idx not in most_common_songs:
                continue

            sum_of_words_dict[song_idx] = sum_of_words_dict.get(song_idx, 0) + num_words

    top_30_songs = sorted(sum_of_words_dict, key=sum_of_words_dict.get, reverse=True)[:30]
    
    word_antonyms = {word: get_antonyms(word) for word in clean_genre_input[0]}

    # for the top_30_songs, find the songs with these antonyms
    song_antonym_counts = Counter()

    for word, antonyms in word_antonyms.items():
        for antonym in antonyms:
            if antonym in clean_song_count:
                for song in clean_song_count[antonym]:
                    if song in top_30_songs: 
                        song_antonym_counts[song] += 1 

# Step 3: Add songs with no antonyms with values of 0
    for song in top_30_songs:
        if song not in song_antonym_counts:
            song_antonym_counts[song] = 0

# Step 4: Sort songs by least distinct antonyms
    filtered_songs = sorted(song_antonym_counts.keys(), key=lambda song: song_antonym_counts[song])

    filtered_songs = filtered_songs[:10]
    
    result = sort_polarity_scores(filtered_songs, cleaned_tokenized_lyrics, "pos")
    
    word_synonym_dict = {word: list(get_synonyms_of_word(word)) for word in stemmed_user_input_preserve_original if possible_songs_dict.get(word) is None}

    print(f"Cleaned Input: {clean_genre_input}")
    print(f"Possible Songs: {possible_songs_dict}")
    print("Possible Songs Dictionary:", possible_songs_dict)
    print("Most Common Songs:", most_common_songs)
    print("Top 30 Songs:", top_30_songs)
    print("Antonym Counts:", song_antonym_counts)
    print("Filtered Songs:", filtered_songs)
    print("result:",result )
    
    return result, word_synonym_dict

def get_song_details(song_ids):
    """Return song details (title, artist, album) from the Spotify dataset given a list of song IDs."""
    song_details = []
    for song_id in song_ids:
        song_row = lyric_df.loc[lyric_df.index == song_id]  # Find the row with the given song_id
        if not song_row.empty:
            details = {
                "title": song_row["song"].values[0],
                "artist": song_row["artist"].values[0]
                #"album": song_row["album_name"].values[0],
                #"genre": song_row["track_genre"].values[0]
            }
            song_details.append(details)
    return song_details

def get_song_details_with_ratings(song_tuple_list):
    """Return song details (title, artist, album) from the Spotify dataset given a list of song IDs."""
    song_details = []
    for song_id,song_rating in song_tuple_list:
        song_row = lyric_df.loc[lyric_df.index == song_id]  # Find the row with the given song_id
        if not song_row.empty:
            details = {
                "title": song_row["song"].values[0],
                "artist": song_row["artist"].values[0],
                #"album": song_row["album_name"].values[0],
                #"genre": song_row["track_genre"].values[0],
                "rating": song_rating
            }
            song_details.append(details)
    return song_details

def lemma_words(cleaned_tokenized_lyrics):
    stemmed_cleaned_tokenized_lyrics = {}
    lemmatizer = WordNetLemmatizer()
    for key, list_of_words in cleaned_tokenized_lyrics.items():
        stemmed_cleaned_tokenized_lyrics[key] = [lemmatizer.lemmatize(word) for word in list_of_words]
    return stemmed_cleaned_tokenized_lyrics

def find_song_matches_with_svd_return_indexes(user_input, tfidf_vectorizer, svd, topics_for_songs, top_k=len(lyric_df), score_cutoff = 0):
    user_tfidf = tfidf_vectorizer.transform([user_input])
    user_topics = svd.transform(user_tfidf)

    similarities = cosine_similarity(user_topics, topics_for_songs)[0]
    # similarity score > x 
    # Pos similarity score means some similarity, 0 means no similarity, negative means opposite of similar. scores are 1>x>-1
    pos_similarity_idx = np.where(similarities > score_cutoff)[0]

    pos_similarity_idx = np.argsort(-similarities)[:top_k]

    return [(idx, similarities[idx]) for idx in pos_similarity_idx]


def svd_recommend_songs(user_description_input, cleaned_tokenized_lyrics, clean_song_count, user_age_input):
    print("using SVD")
    #This is a dict: {0: user input as token words}
    clean_user_description_input = remove_stop_words(custom_stopwords, {0: tokenize(user_description_input)})
    #This is also a dict: {0: user input as token words}
    lemma_clean_user_description_input = lemma_words(clean_user_description_input)
    
    song_lyrics = cleaned_tokenized_lyrics.values()
    
    print("big files")
    joined_song_lyrics = []
    for lyrics in song_lyrics:
        joined_song_lyrics.append(" ".join(lyrics))
    vectorizer = joblib.load('vectorizer.pkl')
    #tfidf_matrix = scipy.sparse.load_npz('tfidf_matrix.npz')
    svd = joblib.load('svd_model.pkl')
    topics_for_songs = scipy.sparse.load_npz('topics_for_songs.npz')

    # Match songs based on general sentiments(topics)
    list_of_songs_based_on_topics = find_song_matches_with_svd_return_indexes(user_description_input, vectorizer, svd, topics_for_songs, score_cutoff=0)[:50]
    
    print("possible songs check")
    # Append (song_idx, score) to topic_possible_songs if the sentiment difference is not too great
    topic_possible_songs = []
    for song_idx, score in list_of_songs_based_on_topics:
        sentiment = lyric_df['sentiment'][song_idx]
        ideal_sentiment = 1 - (user_age_input / 50)
        sentiment_difference = abs(ideal_sentiment - sentiment)
        if sentiment_difference < 1:
            topic_possible_songs.append((song_idx, score))
    
    inverted_index = build_inverted_index(cleaned_tokenized_lyrics)
    
    set_of_all_user_input_words_and_adjacents = set(clean_user_description_input[0] + lemma_clean_user_description_input[0])
    
    # Set of all songs that contain (not lemma) user input words
    possible_songs = set() 
    for word in set_of_all_user_input_words_and_adjacents:
        song_list = clean_song_count.get(word)
        if song_list:
            possible_songs.update(song_list)

    print("song index check")
    # KEY - Song index (Song in possible_songs): VALUE - Total number of relevant user input words
    sum_of_words_dict = {}
    for word in set_of_all_user_input_words_and_adjacents:
        if word not in inverted_index:
            continue  
        inv_index_list = inverted_index[word]
        for song_idx, num_words in inv_index_list:
            if song_idx not in possible_songs:
                continue
            sum_of_words_dict[song_idx] = sum_of_words_dict.get(song_idx, 0) + num_words
    
    list_of_sums = list(sum_of_words_dict.values())
    min_sum = min(list_of_sums)
    max_sum = max(list_of_sums)
            
    print("score addition check")
    song_list_sim_word_count_scores = []
    for song_idx, score in list_of_songs_based_on_topics:
        if song_idx in possible_songs:
            normalized_sum = (sum_of_words_dict[song_idx] - min_sum) / (max_sum - min_sum) if max_sum > min_sum else 0
            new_score = score + normalized_sum * 0.25
            song_list_sim_word_count_scores.append((song_idx, new_score))
        else:
            song_list_sim_word_count_scores.append((song_idx, score))
    
    song_list_sim_word_count_scores = sorted(song_list_sim_word_count_scores, key=lambda x: -x[1])
    
    word_antonyms = {word: get_antonyms(word) for word in set_of_all_user_input_words_and_adjacents}

    print("antonym check")
    song_antonym_counts = Counter()
    for word, antonyms in word_antonyms.items(): 
        for antonym in antonyms:
            if antonym in clean_song_count:
                for song in clean_song_count[antonym]:
                    if song in [song_tup[0] for song_tup in song_list_sim_word_count_scores]: 
                        song_antonym_counts[song] += 1 
                        
    # Normalize antonym counts
    if song_antonym_counts:
        min_antonym_count = min(song_antonym_counts.values())
        max_antonym_count = max(song_antonym_counts.values())

        normalized_antonym_counts = {}
        for song_idx, count in song_antonym_counts.items():
            normalized_antonym_counts[song_idx] = (count - min_antonym_count) / (max_antonym_count - min_antonym_count) if max_antonym_count > min_antonym_count else 0
    else:
        normalized_antonym_counts = {}

    song_list_sim_word_count_antonym_scores = []
    for song_idx, score in song_list_sim_word_count_scores:
        new_score = score

        if song_idx in normalized_antonym_counts:
            antonym_score = normalized_antonym_counts[song_idx]
            new_score -= antonym_score * 0.1
            
        song_list_sim_word_count_antonym_scores.append((song_idx, new_score))

    print("sort")
    song_list_sim_word_count_antonym_scores = sorted(song_list_sim_word_count_antonym_scores, key=lambda x: -x[1])
    
    # This part, the synonyms, is pretty much useless
    word_synonym_dict = {word: list(get_synonyms_of_word(word)) for word in set_of_all_user_input_words_and_adjacents if word not in clean_song_count}

    print(f"Cleaned Input: {clean_user_description_input}")
    print(f"Possible Songs: {possible_songs}")
    print("Possible Songs Dictionary:", clean_song_count)
    print("Antonym Counts:", song_antonym_counts)
    print("Filtered Songs:", topic_possible_songs)
    
    return song_list_sim_word_count_antonym_scores[:10], word_synonym_dict

print('loaded all functions ml.py')

# if __name__ == "__main__":
#     print("Calling recommend_songs manually for debugging...")
#     test_genre = "sad"
#     recommended_songs, synonyms = recommend_songs(test_genre, {}, {})
#     print(f"Recommended Songs: {recommended_songs}")
#     print(f"Synonyms Used: {synonyms}")
