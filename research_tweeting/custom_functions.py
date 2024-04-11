import tweepy
import re
import datetime
import time
from langchain.agents import load_tools
from langchain_openai import ChatOpenAI
import os
llm=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
import time
from langchain.tools import tool
from dotenv import load_dotenv

#load environment vars
load_dotenv() 

#twitter
api_key_tw = os.environ.get("TWITTER_API_KEY") 
api_key_secret_tw =os.environ.get("TWITTER_API_KEY_SECRET") 
access_token_tw = os.environ.get("TWITTER__ACCESS_TOKEN") 
access_token_secret_tw = os.environ.get("TWITTER__ACCESS_TOKEN_SECRET") 
bearer_token_tw = os.environ.get("TWITTER_BEARER_TOKEN") 
client_id_tw = os.environ.get("TWITTER_CLIENT_ID") 
client_secret_tw = os.environ.get("TWITTER_CLIENT_SECRET") 


def split_section_into_tweets(section, limit=280):
    """Splits a section of the message into parts that fit within the tweet limit, accounting for URL shortening."""
    url_placeholder = "https://t.co/xxxxxxxxxx"  # Placeholder for URLs, adjust length as needed
    urls = re.findall(r'(https?://\S+)', section)
    adjusted_section = re.sub(r'(https?://\S+)', url_placeholder, section)  # Replace URLs with placeholder

    if len(adjusted_section) <= limit:
        return [section]  # Return the original section if it fits
    
    # Adjust the splitting logic to account for item markers
    item_pattern = re.compile(r'\d+\.\s')  # Pattern to detect item numbering
    sentences = adjusted_section.split('. ')
    tweets = []
    current_tweet = ""
    
    for sentence in sentences:
        if len(current_tweet) + len(sentence) + 1 > limit or item_pattern.match(sentence):
            if current_tweet:
                # Replace placeholders with actual URLs when adding tweet to list
                for url in urls:
                    current_tweet = current_tweet.replace(url_placeholder, url, 1)
                    urls = [u for u in urls if u != url]  # Remove used URL
                    break
                tweets.append(current_tweet)
                current_tweet = sentence
            else:
                # Directly add if alone it exceeds the limit
                tweets.append(sentence)
        else:
            if current_tweet:
                current_tweet += ". "
            current_tweet += sentence
    
    # Replace placeholders with actual URLs for the last tweet
    for url in urls:
        current_tweet = current_tweet.replace(url_placeholder, url, 1)
    if current_tweet:
        tweets.append(current_tweet)
    
    return tweets


def post_to_twitter_callback(task_output):
    print("Callback function has been triggered.")
    # Initialize Tweepy client (assuming bearer_token, api_key, etc. are defined)
    client = tweepy.Client(bearer_token=bearer_token_tw,
                        consumer_key=api_key_tw,
                        consumer_secret=api_key_secret_tw,
                        access_token=access_token_tw,
                        access_token_secret=access_token_secret_tw)


    # Assuming 'result' contains the content to be tweeted
    tweets = split_section_into_tweets(task_output)
    total_tweets = len(tweets) + 1  # +1 for the initial header tweet
    sleep_duration = 0.4
    reply_to_tweet_id = None

    # Prepare the initial tweet
    today_date = datetime.datetime.now().strftime("%B %d, %Y")
    initial_tweet_text = f"Your Daily Crypto Updates of {today_date} MORNING EDITION (1/{total_tweets})"

    try:
        # Post the initial header tweet
        response = client.create_tweet(text=initial_tweet_text)
        reply_to_tweet_id = response.data['id']
        print(f"Posted initial Tweet ID: {response.data['id']}")
        time.sleep(sleep_duration)
    except Exception as e:
        print(f"Error posting initial tweet: {e}")

    # Post the rest of the tweets
    for index, tweet in enumerate(tweets, start=2):  # Start from 2 since the first tweet is the header
        tweet_with_count = f"{tweet} ({index}/{total_tweets})"
        if len(tweet_with_count) > 270:
            allowed_length = 270 - len(f" ({index}/{total_tweets})") - 3
            tweet_with_count = tweet[:allowed_length] + "..." + f" ({index}/{total_tweets})"
            print(tweet_with_count)
        try:
            response = client.create_tweet(text=tweet_with_count, in_reply_to_tweet_id=reply_to_tweet_id)
            
            reply_to_tweet_id = response.data['id']
            
            print(f"Posted Tweet ID: {response.data['id']}")
            print(f'sleeping for {sleep_duration} sec...')
            time.sleep(sleep_duration)
        except Exception as e:
            print(f"Error posting tweet: {e}")
