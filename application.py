from datetime import datetime
import threading

from flask import Flask, request, render_template, make_response
import requests

app = Flask(__name__)

GITHUB_REPO_SEARCH_URL = 'https://api.github.com/search/repositories?q={}'


@app.route('/navigator/')
def navigator():
    """
    View to render repositories information fetched from Github.
    """
    search_term = request.args.get('search_term')
    
    if not search_term:
        return make_response('search_term parameter is missing or incorrect.', 400)

    success, repos = get_repos_info(search_term)

    if not success:
        return make_response('Incorrect response received from Github API.', 500)

    context = {
        'search_term': search_term,
        'repos': repos,
    }

    return render_template('navigator.html', **context)


def get_repos_info(search_term):
    """
    Fetch and return information about five github repos found against `search_term`.

    Arguments:
        search_term (str): query string to be searched

    Returns:
        tuple (bool, list): first item tells whether the operation is completed successfully or not
                            second item contains the information about each repo found. empty list if error.
    """
    threads = []
    response = requests.get(GITHUB_REPO_SEARCH_URL.format(search_term))
    
    if not response.ok:
        return False, []

    # lambda function to convert datetime string to datetime object for comparision and render
    to_datetime = lambda date_str: datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')

    response = response.json()
    sorted_repos = sorted(
        response.get('items'), 
        key=lambda item: to_datetime(item.get('created_at')),
        reverse=True
    )
    repos = sorted_repos[:5]
    repos_info = []
        
    for repo in repos:
        repo_info = {
            'full_name': repo.get('full_name'),
            'created_at': to_datetime(repo.get('created_at')),
            'owner': {
                'username': repo.get('owner').get('login'),
                'url': repo.get('owner').get('html_url'),
                'avatar_url': repo.get('owner').get('avatar_url'),
            },
            'latest_commit': {}  # this will avoid crash during rendering in case there are no commits
        }

        # commit are sorted as decending(latest first) order. so we need to fetch 1 commit only
        commits_url = repo.get('commits_url').replace('{/sha}', '?per_page=1')
        t = threading.Thread(target=commit_fetcher, args=(commits_url, repo_info))
        threads.append(t)
        t.start()

        repos_info.append(repo_info) 

    # let threads finish their work
    __ = [thread.join() for thread in threads]

    return True, repos_info


def commit_fetcher(commits_url, repo_info):
    """
    Thread worker function to fetch commits for a repo.

    Arguments:
        commits_url (str): Github commits API url
        repo_info (dict): Github commits API url
    """
    response = requests.get(commits_url)
        
    if not response.ok:
        # do nothing in case of error...this can happen if a repo has nothing
        return

    latest_commit = response.json()[0]
    repo_info['latest_commit'] = {
        'sha': latest_commit.get('sha'),
        'message': latest_commit.get('commit').get('message'),
        'author_name': latest_commit.get('commit').get('author').get('name'),
    }