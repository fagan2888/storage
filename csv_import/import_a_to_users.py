import contextlib
from email.utils import format_datetime
import sys

import tweepy

from common import *

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: %s <collection_from> <collection_to>", file = sys.stderr)
        exit(-1)

    api = tweepy.API(TWITTER_AUTH, parser = tweepy.parsers.JSONParser())

    accessed_uids = set()

    with contextlib.ExitStack() as exitstack:
        db =  exitstack.enter_context(opendb())
        coll_from = exitstack.enter_context(opencoll(db, sys.argv[1]))
        coll_to = exitstack.enter_context(opencoll(db, sys.argv[3]))

        cursor = coll_from.find(
            projection = ["user.id", "entities.user_mentions", "extended_tweet.entities.user_mentions"],
            no_cursor_timeout = True
        )

        cursor = exitstack.enter_context(contextlib.closing(cursor))

        for r0 in cursor:
            uids = {r0["user"]["id"]} | \
                       {user_mention["id"] for user_mention in r0["entities"]["user_mentions"]} | \
                       {user_mention["id"] for user_mention in r0["extended_tweet"]["entities"]["user_mentions"]}

            for uid in uids:
                if uid in accessed_uids:
                    continue

                try:
                    r = api.get_user(
                        uid,
                        tweet_mode = "extended",
                        include_entities = True,
                        monitor_rate_limit = True,
                        wait_on_rate_limit = True
                    )

                    retrieved_at = datetime.datetime.utcnow().replace(tzinfo = datetime.timezone.utc)

                except tweepy.TweepError:
                    continue

                r["retrieved_at"] = retrieved_at
                r["created_at"] = parsedate_to_datetime(r["created_at"])

                if "status" in r:
                    r["status"]["created_at"] = parsedate_to_datetime(r["status"]["created_at"])

                print("%s -- \"%s\"" % (r["screen_name"], r["description"]))

                coll_to.insert_one(r)

            accessed_uids |= uids
