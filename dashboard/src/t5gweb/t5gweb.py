"""core CRUD functions for t5gweb"""
import json
import logging
import re
from copy import deepcopy
from datetime import date, datetime, timezone

import click
from flask.cli import with_appcontext
from t5gweb.fake_data import generate_fake_data
from t5gweb.utils import set_cfg

from . import cache, libtelco5g


def get_new_cases():
    """get new cases created since X days ago"""

    # get cases from cache
    cases = libtelco5g.redis_get("cases")

    interval = 7
    today = date.today()
    new_cases = {
        c: d
        for (c, d) in sorted(cases.items(), key=lambda i: i[1]["severity"])
        if (
            today - datetime.strptime(d["createdate"], "%Y-%m-%dT%H:%M:%SZ").date()
        ).days
        <= interval
    }
    for case in new_cases:
        new_cases[case]["severity"] = re.sub(
            r"\(|\)| |[0-9]", "", new_cases[case]["severity"]
        )
    return new_cases


def get_new_comments(new_comments_only=True, account=None):
    # fetch cards from redis cache
    cards = libtelco5g.redis_get("cards")
    if account is not None:
        cards = {c: d for (c, d) in cards.items() if d["account"] == account}
    logging.warning("found %d JIRA cards" % (len(cards)))
    time_now = datetime.now(timezone.utc)

    # filter cards for comments created in the last week
    detailed_cards = {}
    account_list = []

    for card in cards:
        comments = []
        if new_comments_only:
            if cards[card]["comments"] is not None:
                comments = [
                    comment
                    for comment in cards[card]["comments"]
                    if (
                        time_now
                        - datetime.strptime(comment[1], "%Y-%m-%dT%H:%M:%S.%f%z")
                    ).days
                    < 7
                ]
        else:
            if cards[card]["comments"] is not None:
                comments = [comment for comment in cards[card]["comments"]]
        if len(comments) == 0:
            continue  # no updates
        else:
            detailed_cards[card] = cards[card]
            detailed_cards[card]["comments"] = comments
        account_list.append(cards[card]["account"])
    account_list.sort()
    logging.warning("found %d detailed cards" % (len(detailed_cards)))

    # organize cards by status
    accounts = organize_cards(detailed_cards, account_list)
    return accounts


def get_trending_cards():
    # fetch cards from redis cache
    cards = libtelco5g.redis_get("cards")

    # get a list of trending cards
    trending_cards = [card for card in cards if "Trends" in cards[card]["labels"]]

    # TODO: timeframe?
    detailed_cards = {}
    account_list = []
    for card in trending_cards:
        detailed_cards[card] = cards[card]
        account = cards[card]["account"]
        if account not in account_list:
            account_list.append(cards[card]["account"])

    accounts = organize_cards(detailed_cards, account_list)
    return accounts


def plots():
    summary = libtelco5g.get_card_summary()
    return summary


def organize_cards(detailed_cards, account_list):
    """Group cards by account"""

    accounts = {}

    states = {"Waiting on Red Hat": {}, "Waiting on Customer": {}, "Closed": {}}

    for account in account_list:
        accounts[account] = deepcopy(states)

    for i in detailed_cards.keys():
        status = detailed_cards[i]["case_status"]
        account = detailed_cards[i]["account"]
        accounts[account][status][i] = detailed_cards[i]

    return accounts


@click.command("init-cache")
@click.option(
    "--fake-data",
    envvar="fake_data",
    is_flag=True,
    default=False,
    help="Do you want to generate fake data?",
)
@click.option(
    "--overwrite-cache",
    envvar="overwrite_cache",
    is_flag=True,
    default=False,
    help=(
        "Do you want to overwrite your database with fake data? If set to false, "
        "fake data will only be inserted if the relevant db entry is empty."
    ),
)
@click.option(
    "--number-of-cases",
    envvar="number_of_cases",
    default=10,
    help="How many fake cases to create in your db",
)
@with_appcontext
def init_cache(fake_data, overwrite_cache, number_of_cases):
    """Initialize cache with real data if it's empty, or fake data if specified by user

    Args:
        fake_data (bool): Determines if fake data should be generated
        overwrite_cache (bool): Determines if existing cache entries should be
            overwritten by fake data
        number_of_cases (int): Amount of fake cases that should be created
    """
    if not fake_data:
        cfg = set_cfg()
        logging.warning("checking caches")
        cases = libtelco5g.redis_get("cases")
        cards = libtelco5g.redis_get("cards")
        bugs = libtelco5g.redis_get("bugs")
        issues = libtelco5g.redis_get("issues")
        details = libtelco5g.redis_get("details")
        escalations = libtelco5g.redis_get("escalations")
        watchlist = libtelco5g.redis_get("watchlist")
        stats = libtelco5g.redis_get("stats")
        if cases == {}:
            logging.warning("no cases found in cache. refreshing...")
            cache.get_cases(cfg)
        if details == {}:
            logging.warning("no details found in cache. refreshing...")
            cache.get_case_details(cfg)
        if bugs == {}:
            logging.warning("no bugs found in cache. refreshing...")
            cache.get_bz_details(cfg)
        if issues == {}:
            logging.warning("no issues found in cache. refreshing...")
            cache.get_issue_details(cfg)
        if escalations == {}:
            logging.warning("no escalations found in cache. refreshing...")
            cache.get_escalations(cfg)
        if watchlist == {}:
            logging.warning("no watchlist found in cache. refreshing...")
            cache.get_watchlist(cfg)
        if cards == {}:
            logging.warning("no cards found in cache. refreshing...")
            cache.get_cards(cfg)
        if stats == {}:
            logging.warning("no t5g stats found in cache. refreshing...")
            cache.get_stats()
    else:
        data = generate_fake_data(number_of_cases)
        for key, value in data.items():
            if overwrite_cache or libtelco5g.redis_get(key) == {}:
                libtelco5g.redis_set(key, json.dumps(value))


def init_app(app):
    app.cli.add_command(init_cache)
