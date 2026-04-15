import json
import os
import csv
from datetime import datetime

class XUserTimelineCrawler:
    def __init__(self, manager):
        self.manager = manager
        # self.endpoint = "fafowSZBCQYf5-CNIZ04bw/UserTweets"
        self.endpoint = "VuJNTKlPrdU-Jiv0Sge__w/UserTweets"
                
        self.features = {
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
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_grok_image_annotation_enabled": True,
            "responsive_web_grok_imagine_annotation_enabled": True,
            "responsive_web_grok_community_note_auto_translation_is_enabled": False,
            "responsive_web_enhance_cards_enabled": False
        }
        
        self.field_toggles = {"withArticlePlainText": False}

    def get_recent_tweet_ids(self, user_id, from_date_str, to_date_str, limit=500, save_json=False, save_csv=True):
        """
        Crawl up to `limit` tweets from a user's timeline within a date range.
        Dates should be in "YYYY-MM-DD" format.
        """
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
        to_date   = datetime.strptime(to_date_str, "%Y-%m-%d")

        tweet_ids = []
        cursor = None
        total_fetched = 0
        stop = False

        print(f"Starting crawl for user {user_id} from {from_date_str} to {to_date_str} (max {limit} tweets)\n")

        while not stop and total_fetched < limit:
            variables = {
                "userId": str(user_id),
                "count": 100,  # fetch 100 tweets per page
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True
            }
            if cursor:
                variables["cursor"] = cursor

            data = self.manager.get_graphql(
                self.endpoint,
                variables,
                self.features,
                self.field_toggles
            )

            if save_json:
                os.makedirs("responses", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"responses/user_{user_id}_{timestamp}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Saved JSON response to {filename}")

            instructions = (
                data.get("data", {})
                    .get("user", {})
                    .get("result", {})
                    .get("timeline", {})
                    .get("timeline", {})
                    .get("instructions", [])
            )

            next_cursor = None
            page_count = 0

            for instr in instructions:
                if "entries" not in instr:
                    continue

                for entry in instr["entries"]:
                    entry_type = entry.get("entryId", "")
                    # get pagination cursor
                    if entry_type.startswith("cursor-bottom-"):
                        next_cursor = entry.get("content", {}).get("value")
                        continue

                    item = entry.get("content", {}).get("itemContent", {})
                    result = item.get("tweet_results", {}).get("result", {})

                    if result.get("__typename") != "Tweet":
                        continue

                    rest_id = result.get("rest_id")
                    legacy = result.get("legacy", {})
                    created_at_str = legacy.get("created_at")

                    if not (rest_id and created_at_str):
                        continue

                    created_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y").replace(tzinfo=None)

                    # Filter tweet date
                    if created_at > to_date:
                        continue
                    if created_at < from_date:
                        stop = True
                        break

                    tweet_ids.append((rest_id, created_at))
                    total_fetched += 1
                    page_count += 1

                    if total_fetched >= limit:
                        stop = True
                        break

                if stop:
                    break

            print(f"Fetched {page_count} new tweets — Total: {total_fetched}/{limit}")

            if not next_cursor or stop:
                break  # no more pages or reached limit

            cursor = next_cursor

        # ---- WRITE CSV ----
        if save_csv:
            os.makedirs("csv", exist_ok=True)
            csv_name = f"csv/tweets_{user_id}_{from_date_str}_to_{to_date_str}.csv"

            with open(csv_name, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["tweet_id", "created_at"])
                writer.writerows(tweet_ids)

        print(f"\n✅ Crawl complete! Saved {len(tweet_ids)} tweets to {csv_name}")

        return [row[0] for row in tweet_ids]
