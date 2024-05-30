import tweepy
import re
import datetime
import time
from langchain.agents import load_tools
from langchain_openai import ChatOpenAI
import os
import time
from langchain.tools import tool
from dotenv import load_dotenv
import praw
import time
import requests
from telethon.sync import TelegramClient
import asyncio
from research_tweeting.variables import selected_reddit_subs
import re
import logging


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

#reddit
client_id_re= os.environ.get("REDDIT_CLIENT_ID") 
client_secret_re=os.environ.get("REDDIT_CLIENT_SECRET") 

client_id2_re = os.environ.get("REDDIT_CLIENT_ID2") 
client_secret2_re = os.environ.get("REDDIT_CLIENT_SECRET2") 

#telegram
TG_API_ID = os.environ.get("TG_API_ID")
TG_API_HASH = os.environ.get("TG_API_HASH")
phone_number = os.environ.get("PHONE_NUMBER")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # It's good practice to use __name__ to get the correct logger

def clean_content(section):
    """Cleans a given section, removing specific sentences and text between square brackets."""
    # Remove specific sentence
    section = section.replace("Today's Developments in Crypto:", "").strip()

    # Use regex to remove text between square brackets
    section = re.sub(r'\[.*?\]', '', section)

    return section


def split_section_into_tweets(section, limit=277):
    """Splits a section into tweets, ensuring each tweet does not exceed the specified character limit, and places a page break after titles."""
    tweets = []
    # Split by news item blocks, assuming each item starts with a '- ' followed by a title
    items = section.split('\n\n')
    
    for item in items:
        current_tweet = ""
        # Split the item into lines which represent title, details, and link
        lines = item.split('\n')
        for i, line in enumerate(lines):
             # Clean each line to remove text between square brackets
            line = clean_content(line)

            # Check if adding this line would exceed the limit
            if len(current_tweet) + len(line) + 1 > limit:
                # If the current tweet + line exceeds limit, store the current tweet and reset
                if current_tweet:
                    tweets.append(current_tweet.strip())  # Strip to ensure no trailing whitespace
                # Add the line as the start of a new tweet, handling titles differently
                current_tweet = line + ('\n' if i == 0 else ' ')  # Add a newline only after the title
            else:
                # Add line to current tweet, consider handling title differently
                current_tweet += (line + ('\n' if i == 0 else ' ') if current_tweet else line)
        
        # Add last tweet of the current item, stripping trailing spaces and newlines
        if current_tweet:
            tweets.append(current_tweet.strip())

    return tweets


def post_to_twitter_callback(task_output, night_owl=False, early_bird=False):
    logger.info("Callback function has been triggered.")
    # Initialize Tweepy client (assuming bearer_token, api_key, etc. are defined)

    client = tweepy.Client(bearer_token=bearer_token_tw,
                           consumer_key=api_key_tw,
                           consumer_secret=api_key_secret_tw,
                           access_token=access_token_tw,
                           access_token_secret=access_token_secret_tw)

    # Split the section into tweets
    tweets = split_section_into_tweets(task_output)
    total_tweets = len(tweets) + 1  # +1 for the initial header tweet
    sleep_duration = 0.4
    reply_to_tweet_id = None

    # Prepare the initial tweet
    today_date = datetime.datetime.now().strftime("%B %d, %Y")
    edition = "NIGHT OWL EDITION" if night_owl else "EARLY BIRD EDITION" if early_bird else ""
    initial_tweet_text = f"Your Daily Crypto Updates of {today_date} {edition} (1/{total_tweets})".strip()

    try:
        # Post the initial header tweet
        response = client.create_tweet(text=initial_tweet_text)
        reply_to_tweet_id = response.data['id']
        logger.info(f"Posted initial Tweet ID: {response.data['id']}")
        time.sleep(sleep_duration)
    except Exception as e:
        logger.info(f"Error posting initial tweet: {e}")

    # Post the rest of the tweets
    for index, tweet in enumerate(tweets, start=2):
        tweet_with_count = f"{tweet} ({index}/{total_tweets})"
        max_length = 270  # Twitter's maximum tweet length

        if len(tweet_with_count) <= max_length:
            try:
                response = client.create_tweet(text=tweet_with_count, in_reply_to_tweet_id=reply_to_tweet_id)
                reply_to_tweet_id = response.data['id']
                logger.info(f"Posted Tweet ID: {response.data['id']}")
                logger.info(tweet_with_count)
                time.sleep(sleep_duration)
            except Exception as e:
                logger.info(f"Error posting tweet: {e}")
        else:
            # Find the last space before the link or cut-off to prevent breaking the content
            last_space = tweet.rfind(' ', 0, max_length)
            primary_tweet = tweet[:last_space] + "..."
            follow_up_tweet = tweet[last_space:].strip()

            # Post the main part of the tweet
            try:
                response = client.create_tweet(text=f"{primary_tweet} ({index}/{total_tweets})", in_reply_to_tweet_id=reply_to_tweet_id)
                reply_to_tweet_id = response.data['id']
                logger.info(f"Posted Tweet ID: {response.data['id']}")
                logger.info(primary_tweet)
                time.sleep(sleep_duration)
            except Exception as e:
                logger.info(f"Error posting primary tweet part: {e}")

            # Post the remaining part as a new tweet, especially if it includes the link
            try:
                response = client.create_tweet(text=f"{follow_up_tweet} ({index}/{total_tweets})", in_reply_to_tweet_id=reply_to_tweet_id)
                reply_to_tweet_id = response.data['id']
                logger.info(f"Posted Follow-Up Tweet ID: {response.data['id']}")
                logger.info(follow_up_tweet)
                time.sleep(sleep_duration)
            except Exception as e:
                logger.info(f"Error posting follow-up tweet: {e}")

class BrowserTool:
    @tool("Scrape reddit content")
    def scrape_reddit(subreddits=selected_reddit_subs, max_comments_per_post=7):
        """Scrape Reddit content from specified subreddits."""
        reddit = praw.Reddit(
            client_id=client_id_re,
            client_secret=client_secret_re,
            user_agent="user-agent",
        )
        scraped_data = []
        today = datetime.datetime.utcnow().date()  # Get today's date in UTC to match Reddit's timestamp

        for subreddit_name in subreddits:
            logger.info(f"handling {subreddit_name}...")
            subreddit = reddit.subreddit(subreddit_name)

            for post in subreddit.hot(limit=100):  # Increased limit to ensure finding today's posts
                post_date = datetime.datetime.fromtimestamp(post.created_utc).date()  # Convert post timestamp to date
                if post_date == today:  # Check if the post date is today
                    post_data = {"title": post.title, "url": post.url, "comments": []}

                    try:
                        post.comments.replace_more(limit=0)  # Load top-level comments only
                        comments = post.comments.list()
                        if max_comments_per_post is not None:
                            comments = comments[:max_comments_per_post]  # Respect the max_comments_per_post limit

                        for comment in comments:
                            post_data["comments"].append(comment.body)

                        scraped_data.append(post_data)

                    except praw.exceptions.APIException as e:
                        logger.info(f"API Exception: {e}")
                        time.sleep(60)  # Sleep for 1 minute before retrying

        return scraped_data
        
def post_to_socials(result_explorers):
    # Get the current time
    current_time = datetime.datetime.now()
    early_bird = current_time.hour <= 9
    night_owl = current_time.hour >= 22

    logger.info("posting to Twitter...")
    post_to_twitter_callback(result_explorers, night_owl=night_owl, early_bird=early_bird)
    logger.info("done posting to twitter!")


def validate_report(report):
    for bullet_point in report.strip().split('\n\n'):
        # Trim extra spaces from each bullet point before checking
        trimmed_bullet_point = bullet_point.strip()
        if trimmed_bullet_point:  # Ensure it's not an empty line
            logger.info("Checking a bullet point....")  # Debugging logger.info
            if "http://" not in trimmed_bullet_point and "https://" not in trimmed_bullet_point:
                logger.info('Link not present')  # Debugging logger.info
                return False, "Missing link in bullet point."
    return True, "Report is valid."


