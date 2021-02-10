import os
import json
from console import Console

class Gitlab:
    def __init__(self):
        self._gitlab_group = os.getenv("GITLAB_GROUP")
        self._gitlab_private_token = os.getenv("GITLAB_PRIVATE_TOKEN")
        self._gitlab_url = os.getenv("GITLAB_URL")

    @property
    def gitlab_group(self):
        return self._gitlab_group

    @property
    def gitlab_private_token(self):
        return self._gitlab_private_token

    @property
    def gitlab_url(self):
        return self._gitlab_url

    def requestGitlabApi(self, url):
        bashCommand = "curl -s \"{}?private_token={}&amp;per_page=999\"".format(url, self.gitlab_private_token)
        return Console.execute(bashCommand).decode("utf-8")

    def getGitlabProjects(self):
        response = json.loads(self.requestGitlabApi("{}/api/v4/groups/{}/projects".format(self.gitlab_url, self.gitlab_group)))
        return response

    def getCommits(self, project_id, since, until):
        bashCommand = "curl -s \"{}/api/v4/projects/{}/repository/commits?private_token={}&amp;per_page=999;since={};until={}\"".format(self.gitlab_url, project_id, self.gitlab_private_token, since.strftime('%Y/%m/%dT%H:%M'), until.strftime('%Y/%m/%dT%H:%M'))
        response = json.loads(Console.execute(bashCommand).decode("utf-8"))
        return response

    def getDiff(self, project_id, commit):
        bashCommand = "curl -s \"{}/api/v4/projects/{}/repository/commits/{}/diff?private_token={}&amp;per_page=999\"".format(self.gitlab_url, project_id, commit, self.gitlab_private_token)
        response = json.loads(Console.execute(bashCommand).decode("utf-8"))
        return response


