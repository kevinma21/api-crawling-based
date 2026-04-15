from scripts.request_manager import XRequestManager
from scripts.user_timeline_crawler import XUserTimelineCrawler
from scripts.tweet_crawler import XTweetCrawler
import os, csv, json
from dotenv import load_dotenv

load_dotenv()


# you could get AUTH_TOKEN, CSRF_TOKEN, and BEARER_TOKEN from Cookies and request URL header

if __name__ == "__main__":
    # Initialize shared request manager
    manager = XRequestManager(
        auth_token=os.getenv('AUTH_TOKEN'), 
        csrf_token=os.getenv('CSRF_TOKEN'), 
        bearer_token=os.getenv('BEARER_TOKEN')
    )

    # Crawl tweet IDs from user
    # user_id = "366987179"  # e.g. Jokowi’s user ID
    # user_crawler = XUserTimelineCrawler(manager)
    # tweet_ids = user_crawler.get_recent_tweet_ids(
    #     user_id, 
    #     from_date_str="2022-01-01",
    #     to_date_str="2025-10-31",
    #     limit=500
    # )
    # print(f"Tweet IDs from @jokowi: {tweet_ids}")
    
    # Crawl all replies to tweets from CSV
    
    # Crawl tweet IDs from user
    # user_id = "110312278"  # Anies Baswedan user ID
    # user_crawler = XUserTimelineCrawler(manager)
    # tweet_ids = user_crawler.get_recent_tweet_ids(
    #     user_id, 
    #     from_date_str="2023-01-01",
    #     to_date_str="2025-10-31",
    #     limit=255
    # )
    # print(f"Tweet IDs from @aniesbaswedan: {tweet_ids}")
    
    # # CONFIG
    input_csv = "csv/tweets_110312278_2023-01-01_to_2025-10-31.csv"
    output_csv = "csv/all_replies.csv"
    progress_file = "csv/progress.json"
    REPLIES_PER_TWEET = 150
    
    crawler = XTweetCrawler(manager)
    
    # Load progress
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            done_tweets = set(json.load(f))
    else:
        done_tweets = set()
    
    # Load input tweets
    with open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        tweets = list(reader)
        
    print(f"Starting batch crawl for {len(tweets)} tweets")
    print(f"Already completed: {len(done_tweets)}")
    
    for i, row in enumerate(tweets):
        tweet_id = row["tweet_id"]

        if tweet_id in done_tweets:
            print(f" Skipping already done tweet {tweet_id}")
            continue

        print(f"\n Crawling tweet {i+1}/{len(tweets)} — ID {tweet_id}")
        try:
            crawler.get_all_replies(tweet_id, output_file=output_csv, limit=REPLIES_PER_TWEET, append=True)
            done_tweets.add(tweet_id)

            # Save progress after each tweet
            with open(progress_file, "w") as f:
                json.dump(list(done_tweets), f, indent=2)
            print(f" Completed tweet {tweet_id}")

        except Exception as e:
            print(f" Error on tweet {tweet_id}: {e}")
            print(" Saving progress and stopping...")
            with open(progress_file, "w") as f:
                json.dump(list(done_tweets), f, indent=2)
            break

    print("\n Done crawling batch.")
        