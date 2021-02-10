import os
import console
import json
from console import Console

class Jenkins:
    def __init__(self):
        self._jenkins_user  = os.getenv("JENKINS_USER")
        self._jenkins_token = os.getenv("JENKINS_TOKEN")
        self._jenkins_job   = os.getenv("JENKINS_JOB")
        self._jenkins_url   = os.getenv("JENKINS_URL")

    @property
    def jenkins_user(self):
        return self._jenkins_user

    @property
    def jenkins_token(self):
        return self._jenkins_token

    @property
    def jenkins_url(self):
        return self._jenkins_url

    @property
    def jenkins_job(self):
        return self._jenkins_job

    def requestJenkinsApi(self, url):
        bashCommand = "curl -s \"{}\" --user {}:{}".format(url, self.jenkins_user, self.jenkins_token)
        output = Console.execute(bashCommand)
        return output.decode("utf-8")

    def getBuild(self, build_number):
        return json.loads(self.requestJenkinsApi("{}/job/{}/{}/api/json".format(self.jenkins_url, self.jenkins_job, build_number)))

    def getLog(self, build_number):
        return self.requestJenkinsApi("{}/job/{}/{}/logText/progressiveText?start=0".format(self.jenkins_url, self.jenkins_job, build_number))

    def getJobs(self):
        #print("{}/job/{}/api/json".format(self.jenkins_url, self.jenkins_job))
        output = self.requestJenkinsApi("{}/job/{}/api/json".format(self.jenkins_url, self.jenkins_job))
        
        return json.loads(output)




