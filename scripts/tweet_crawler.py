import csv
import time
import os
import json

from scripts.request_manager import XRequestManager

class XTweetCrawler:
    def __init__(self, manager: 'XRequestManager'):
        self.manager = manager

    def _get_conversation(self, tweet_id: str, cursor=None, ranking_mode="Relevance", save_raw=False):
        """
        Fetch a batch of replies (GraphQL TweetDetail endpoint)
        """
        # change endpoint based on endpoint of the things you need to crawl
        # endpoint = "bj0Uyae1s0en3ti3POB5fQ/TweetDetail"
        endpoint = "LAqRa-lcEK_HAzopWYYuLg/TweetDetail"
        variables = {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "rankingMode": ranking_mode,
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True
        }
        
        if cursor:
            variables["cursor"] = cursor

        features = {
            "rweb_video_screen_enabled": False,
            "payments_enabled": False,
            "profile_label_improvements_pcf_label_in_post_enabled": True,
            "responsive_web_profile_redirect_enabled": False,
            "rweb_tipjar_consumption_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "premium_content_api_read_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
            "responsive_web_grok_analyze_post_followups_enabled": True,
            "responsive_web_jetfuel_frame": True,
            "responsive_web_grok_share_attachment_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "responsive_web_grok_show_grok_translated_post": False,
            "responsive_web_grok_analysis_button_from_backend": True,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": False,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_grok_image_annotation_enabled": True,
            "responsive_web_grok_imagine_annotation_enabled": True,
            "responsive_web_grok_community_note_auto_translation_is_enabled": False,
            "responsive_web_enhance_cards_enabled": False,
            "responsive_web_tweet_result_by_rest_id_enabled": True,
        }

        field_toggles = {
            "withArticleRichContentState": True,
            "withArticlePlainText": False,
            "withGrokAnalyze": False,
            "withDisallowedReplyControls": False
        }
        
        data = self.manager.get_graphql(endpoint, variables, features, field_toggles)
        
        if save_raw and data:
            os.makedirs("raw", exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"raw/tweet_{tweet_id}_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved raw JSON to {filename}")
        
        return data
        
    def get_all_replies(self, tweet_id: str, output_file="replies.csv", limit=None, append=False):
        """ 
        Crawl all replies to a tweet and save to CSV 
        """
        all_replies = []
        total_count = 0
        cursor = None
        count = 0
        
        # Fetch Jokowi's original tweet first
        data = self._get_conversation(tweet_id)
        author_tweet_text = "N/A"
        author_name = "N/A"

        if data:
            instructions = data.get("data", {}).get("threaded_conversation_with_injections_v2", {}).get("instructions", [])
            for instr in instructions:
                for entry in instr.get("entries", []):
                    entry_id = entry.get("entryId", "")
                    if entry_id == f"tweet-{tweet_id}":
                        tweet_data = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                        legacy = tweet_data.get("legacy", {})
                        user_data = tweet_data.get("core", {}).get("user_results", {}).get("result", {})
                        user_core = user_data.get("core", {})

                        author_tweet_text = legacy.get("full_text", "N/A")
                        author_name = user_core.get("name", "N/A")
                        print(f"Found focal tweet by {author_name}")
                        break

        if author_tweet_text == "N/A":
            print("Could not find the focal tweet text in response.")

        while True:
            data = self._get_conversation(tweet_id, cursor)
            if not data:
                break

            instructions = data.get("data", {}).get("threaded_conversation_with_injections_v2", {}).get("instructions", [])
            entries = []
            for instr in instructions:
                entries += instr.get("entries", [])

            new_cursor = None
            for e in entries:
                entry_id = e.get("entryId", "")
                if entry_id.startswith(("cursor-bottom-", "cursor-showMoreThreads")):
                    new_cursor = e["content"].get("value")
                elif entry_id.startswith("conversationthread-"):
                    items = e["content"]["items"]
                    for item in items:
                        item_content = item.get("item", {}).get("itemContent", {})
                        
                        tweet_data = item_content.get("tweet_results", {}).get("result", {})
                        tweet = tweet_data.get("legacy", {})
                        
                        user_data = tweet_data.get("core", {}).get("user_results", {}).get("result", {})
                        user_core = user_data.get("core", {})
                        
                        if tweet and user_core:
                            all_replies.append({
                                "author_tweet": author_tweet_text,
                                "username": user_core.get("screen_name"),
                                "name": user_core.get("name"),
                                "created_at": tweet.get("created_at"),
                                "text": tweet.get("full_text"),
                                "likes": tweet.get("favorite_count"),
                                "retweets": tweet.get("retweet_count")
                            })
                            count += 1
                            total_count += 1
                            if limit and total_count >= limit:
                                break
                if limit and total_count >= limit:
                    break

            if not new_cursor or new_cursor == cursor or count == 0 or (limit and total_count >= limit):
                print("No new replies or reached the end of conversation.")
                break

            cursor = new_cursor
            time.sleep(1.2)
            print(f"Collected {count} replies")

        # Save to CSV
        keys = ["author_tweet","username", "name", "created_at", "text", "likes", "retweets"]
        
        # Append mode support
        write_header = not append or not os.path.exists(output_file)
        mode = "a" if append else "w"
        
        with open(output_file, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            if write_header:
                writer.writeheader()
            writer.writerows(all_replies)

        print(f"\nSaved {len(all_replies)} total replies to {output_file}")
        return all_replies
