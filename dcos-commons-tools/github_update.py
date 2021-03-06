#!/usr/bin/python

import base64
import json
import os
import os.path
import pprint
import re
import sys
import subprocess

try:
    from http.client import HTTPSConnection
except ImportError:
    # Python 2
    from httplib import HTTPSConnection

class GithubStatusUpdater(object):

    def __init__(self, context_label):
        self.__context_label = context_label


    def __get_dotgit_path(self):
        '''returns the path to the .git directory for the repo'''
        gitdir = '.git'
        startdir = os.environ.get('GIT_REPOSITORY_ROOT', '')
        if not startdir:
            startdir = os.getcwd()
        # starting at 'startdir' search up the tree for a directory named '.git':
        checkdir = os.path.join(startdir, gitdir)
        while not checkdir == '/' + gitdir:
            if os.path.isdir(checkdir):
                return checkdir
            checkdir = os.path.join(os.path.dirname(os.path.dirname(checkdir)), gitdir)
        raise Exception('Unable to find {} in any parent of {}. '.format(gitdir, startdir) +
                        'Run this command within the git repo, or provide GIT_REPOSITORY_ROOT')


    def __get_commit_sha(self):
        '''returns the sha1 of the commit being reported upon'''
        # 1. try 'ghprbActualCommit' and 'GIT_COMMIT' envvars:
        commit_sha = os.environ.get('ghprbActualCommit', '')
        if not commit_sha:
            commit_sha = os.environ.get('GIT_COMMIT', '')
        if not commit_sha and 'GIT_COMMIT_ENV_NAME' in os.environ:
            # 2. grab the commit from the specified custom envvar
            commit_sha = os.environ.get(os.environ['GIT_COMMIT_ENV_NAME'], '')
            if not commit_sha:
                raise Exception('Unable to retrieve git commit id from envvar named "{}". Env is: {}'.format(
                    os.environ['GIT_COMMIT_ENV_NAME'], os.environ))
        if not commit_sha:
            # 3. fall back to using current commit according to .git/ (note: not present in teamcity)
            dotgit_path = self.__get_dotgit_path()
            ret = subprocess.Popen(['git', '--git-dir={}'.format(dotgit_path), 'rev-parse', 'HEAD'],
                                   stdout=subprocess.PIPE)
            commit_sha = ret.stdout.readline().decode('utf-8').strip()
        if not commit_sha:
            raise Exception('Failed to retrieve current revision from git: {}'.format(dotgit_path))
        return commit_sha


    def __get_repo_path(self):
        '''returns the repository path, in the form "mesosphere/some-repo"'''
        repo_path = os.environ.get('GITHUB_REPO_PATH', '')
        if repo_path:
            return repo_path
        dotgit_path = self.__get_dotgit_path()
        ret = subprocess.Popen(['git', '--git-dir={}'.format(dotgit_path), 'config', 'remote.origin.url'],
                               stdout=subprocess.PIPE)
        full_url = ret.stdout.readline().decode('utf-8').strip()
        # expected url formats:
        # 'https://github.com/mesosphere/foo'
        # 'git@github.com:/mesosphere/foo.git'
        # 'git@github.com:/mesosphere/foo'
        # 'git@github.com/mesosphere/foo.git
        # 'git@github.com/mesosphere/foo'
        # all should result in 'mesosphere/foo'
        re_match = re.search('([a-zA-Z0-9-]+/[a-zA-Z0-9-]+)(\\.git)?$', full_url)
        if not re_match:
            raise Exception('Failed to get remote url from git path {}: no match in {}'.format(
                dotgit_path, full_url))
        return re_match.group(1)


    def __get_details_link_url(self, details_url):
        '''returns the url to be included as the details link in the status'''
        if not details_url:
            details_url = os.environ.get('GITHUB_COMMIT_STATUS_URL', '') # custom URL via env
        if not details_url:
            details_url = os.environ.get('BUILD_URL', '') # provided by jenkins
            if details_url:
                details_url += 'console'
        if not details_url:
            raise Exception(
                'Failed to determine URL for details link. ' +
                'Provide either GITHUB_COMMIT_STATUS_URL or BUILD_URL in env.')
        return details_url


    def __get_auth_token(self):
        github_token = os.environ.get('GITHUB_TOKEN_REPO_STATUS', '')
        if not github_token:
            github_token = os.environ.get('GITHUB_TOKEN', '')
        if not github_token:
            raise Exception(
                'Failed to determine auth token to use with GitHub. ' +
                'Provide either GITHUB_TOKEN or GITHUB_TOKEN_REPO_STATUS in env.')
        encoded_tok = base64.encodestring(github_token.encode('utf-8'))
        return encoded_tok.decode('utf-8').rstrip('\n')


    def __build_request(self, state, message, details_url = ''):
        '''returns everything needed for the HTTP request, except the auth token'''
        return {
            'method': 'POST',
            'path': '/repos/{}/commits/{}/statuses'.format(
                self.__get_repo_path(),
                self.__get_commit_sha()),
            'headers': {
                'User-Agent': 'github_update.py',
                'Content-Type': 'application/json',
                'Authorization': 'Basic HIDDENTOKEN'}, # replaced within update_query
            'payload': {
                'context': self.__context_label,
                'state': state,
                'description': message,
                'target_url': self.__get_details_link_url(details_url)
            }
        }


    def __send_request(self, request, debug = False):
        '''sends the provided request which was created by __build_request()'''
        request_headers_with_auth = request['headers'].copy()
        request_headers_with_auth['Authorization'] = 'Basic {}'.format(self.__get_auth_token())
        conn = HTTPSConnection('api.github.com')
        if debug:
            conn.set_debuglevel(999)
        conn.request(
            request['method'],
            request['path'],
            body = json.dumps(request['payload']).encode('utf-8'),
            headers = request_headers_with_auth)
        return conn.getresponse()


    def update(self, state, message, details_url = ''):
        '''sends an update to github.
        returns True on success or False otherwise.
        state should be one of 'pending', 'success', 'error', or 'failure'.'''
        print('[STATUS] {} {}: {}'.format(self.__context_label, state, message))
        if details_url:
            print('[STATUS] URL: {}'.format(details_url))

        if not 'JENKINS_HOME' in os.environ:
            # not running in CI. skip actually sending anything to GitHub
            return True

        request = self.__build_request(state, message, details_url)
        response = self.__send_request(request)
        if response.status < 200 or response.status >= 300:
            print('Got {} response to update request:'.format(response.status))
            print('Request:')
            pprint.pprint(request)
            print('Response:')
            pprint.pprint(response.read())
            return False
        print('Updated GitHub PR with status: {}'.format(request['path']))
        return True


def print_help(argv):
    print('Syntax: {} <state: pending|success|error|failure> <context_label> <status message>'.format(argv[0]))


def main(argv):
    if len(argv) < 4:
        print_help(argv)
        return 1
    state = argv[1]
    if state != 'pending' \
            and state != 'success' \
            and state != 'error' \
            and state != 'failure':
        print_help(argv)
        return 1
    context_label = argv[2]
    message = ' '.join(argv[3:])
    if GithubStatusUpdater(context_label).update(state, message):
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
