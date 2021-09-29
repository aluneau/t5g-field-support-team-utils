"""core CRUD functions for t5gweb"""
import logging
import os
import jira
from datetime import datetime, timezone
import pkg_resources
import re
from werkzeug.exceptions import abort
from . import libtelco5g
import json
import sys


def set_cfg():
        # Set the default configuration values
    cfg = libtelco5g.set_defaults()

    # Override the defaults and configuration file settings 
    # with any environmental settings
    trcfg = libtelco5g.read_env_config(cfg.keys())
    for key in trcfg:
        cfg[key] = trcfg[key]

    # Fix some of the settings so they are easier to use
    cfg['labels'] = cfg['labels'].split(',')

    cfg['offline_token'] = os.environ.get('offline_token')
    cfg['jira_user'] = os.environ.get('jira_user')
    cfg['jira_pass'] = os.environ.get('jira_pass')
    cfg['accounts'] = json.loads(os.environ.get('accounts'))
    cfg['options'] = { 'server': cfg['server'] }

    return cfg

def get_new_cases():
    """get new cases created since X days ago"""
    # Set the default configuration values
    cfg = set_cfg()

    try:
        conn = jira.JIRA(cfg['options'], basic_auth=(cfg['jira_user'], cfg['jira_pass']))
    except jira.exceptions as e:
        if e.status_code == 401:
            print("Login to JIRA failed. Check your username and password")
            exit (1)
        if e.status_code == 503:
            print("JIRA is down.")
            exit (1)
    
    token=libtelco5g.get_token(cfg['offline_token'])
    cases=libtelco5g.get_cases_json(token,cfg['query'],cfg['fields'])
    interval = 7
    new_cases = []
    logging.warning("new cases opened in the last %d days:" % interval)
    for case in sorted(cases, key = lambda i: i['case_severity']):
        create_date = datetime.strptime(case['case_createdDate'], '%Y-%m-%dT%H:%M:%SZ')
        time_diff = datetime.now() - create_date
        if time_diff.days < 7:
            case['case_severity'] = re.sub('\(|\)| |[0-9]', '', case['case_severity'])
            logging.warning("https://access.redhat.com/support/cases/#/case/%s\t%s\t%s" % (case['case_number'], case['case_severity'], case['case_summary']))
            new_cases.append(case)
    return new_cases

def get_new_comments():

    # Set the default configuration values
    cfg = set_cfg()
    cfg['query'] = "case_summary:*webscale* OR case_tags:*shift_telco5g* OR case_summary:*cnv,* OR case_tags:*cnv*"    
    try:
        conn = jira.JIRA(cfg['options'], basic_auth=(cfg['jira_user'], cfg['jira_pass']))
    except jira.exceptions as e:
        if e.status_code == 401:
            print("Login to JIRA failed. Check your username and password")
            exit (1)
    board = libtelco5g.get_board_id(conn, cfg['board'])
    sprint = libtelco5g.get_latest_sprint(conn, board.id, cfg['sprintname'])
    cards = conn.search_issues("sprint=" + str(sprint.id) + " AND updated >= '-7d'", maxResults=1000)

    token=libtelco5g.get_token(cfg['offline_token'])

    cases_json=libtelco5g.get_cases_json(token,cfg['query'],cfg['fields'], exclude_closed= False)
    cases=libtelco5g.get_cases(cases_json, include_tags=True)


    cards_dict = {}
    for card in cards:
        cards_dict[card.key] = None

    #Associate each card with its corresponding case number
    for card_id in cards_dict:
        links = conn.remote_links(card_id)
        for link in links:
            t = conn.remote_link(card_id, link)
            if t.raw['object']['title'] == "Support Case":
                t_case_number = libtelco5g.get_case_number(t.raw['object']['url'])
                if len(t_case_number) > 0:
                    cards_dict[card_id] = t_case_number

    # Get rid of cards with no Support Case Link
    linked_cards = {card: case for card, case in cards_dict.items() if case is not None}

    time_now = datetime.now(timezone.utc)

    # Add other details to dictionary, like case number and comments on card that were made in the last seven days
    detailed_cards= {}
    for card_name in linked_cards:
        issue = conn.issue(card_name) 
        case_num = linked_cards[card_name]
        if linked_cards[card_name] in cases: # Check if casenum exists in cases
            detailed_cards[card_name] = {'case': case_num, 'summary': issue.fields.summary, "account": cases[case_num]['account'], "card_status": issue.fields.status.name, "comments": [comment.body for comment in issue.fields.comment.comments if (time_now - datetime.strptime(comment.updated, '%Y-%m-%dT%H:%M:%S.%f%z')).days < 7], "assignee": issue.fields.assignee, "tags": cases[case_num]['tags'] }
            if len(detailed_cards[card_name]['comments']) == 0:
                detailed_cards.pop(card_name)
    # Replace Jira links with HTML links
    for card in detailed_cards:
        for comment in range(len(detailed_cards[card]["comments"])):
            detailed_cards[card]["comments"][comment] = re.sub(r'(?<!\||\s)\s*?((http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])?)',"<a href=\""+r'\g<0>'+"\" target='_blank'>"+r'\g<0>'"</a>", detailed_cards[card]["comments"][comment])
            detailed_cards[card]["comments"][comment] = re.sub(r'\[([\s\w!"#$%&\'()*+,-.\/:;<=>?@[^_`{|}~]*?\s*?)\|\s*?((http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])?[\s]*)\]',"<a href=\""+r'\2'+"\" target='_blank'>"+r'\1'+"</a>", detailed_cards[card]["comments"][comment])
    # Grouping Cards by Account
    accounts = cfg['accounts']
    for i in detailed_cards:
        for account in accounts:
            for status in accounts[account]:
                if account.lower() in detailed_cards[i]['account'].lower() and status == detailed_cards[i]['card_status']:
                    accounts[account][status].update({i: detailed_cards[i]})
                if "cnv" in detailed_cards[i]['summary'].lower() and status == detailed_cards[i]['card_status'] and account == "CNV":
                    accounts[account][status].update({i: detailed_cards[i]})
                else:
                    for k in detailed_cards[i]['tags']:
                        if "cnv" in k.lower() and status == detailed_cards[i]['card_status'] and account == "CNV":
                            accounts[account][status].update({i: detailed_cards[i]})

    # If an account has no updated cards, replace its empty dictionary with "No Updates"
    for account in accounts:
        if sum([len(accounts[account][status]) for status in accounts[account]])==0:
            accounts[account] = "No Updates"

    return accounts

def plots():
    # Set the default configuration values
    cfg = set_cfg()

    try:
        conn = jira.JIRA(cfg['options'], basic_auth=(cfg['jira_user'], cfg['jira_pass']))
    except jira.exceptions as e:
        if e.status_code ==401:
            print("Login to JIRA failed. Check your username and password")
            exit (1)
    project = libtelco5g.get_project_id(conn, cfg['project'])
    component = libtelco5g.get_component_id(conn, project.id, cfg['component'])
    board = libtelco5g.get_board_id(conn, cfg['board'])
    sprint = libtelco5g.get_latest_sprint(conn, board.id, cfg['sprintname'])
    summary = libtelco5g.get_card_summary(conn, sprint.id)
    return summary