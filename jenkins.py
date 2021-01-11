#!/usr/bin/python


from __future__ import print_function
import sys
import subprocess
import json
from datetime import datetime
import calendar
import argparse
import os
import progressbar
from tabulate import tabulate

jenkins_user = os.getenv("JENKINS_USER")
jenkins_token = os.getenv("JENKINS_TOKEN")
jenkins_url = os.getenv("JENKINS_URL")
jenkins_job = os.getenv("JENKINS_JOB")
gitlab_group = os.getenv("GITLAB_GROUP")
gitlab_private_token = os.getenv("GITLAB_PRIVATE_TOKEN")
gitlab_url = os.getenv("GITLAB_URL")

projects = ""

def requestJenkinsApi(url):
    bashCommand = "curl -s \"{}\" --user {}:{}".format(url, jenkins_user, jenkins_token)
    response = subprocess.check_output(['bash','-c', bashCommand])
    return response

def requestGitlabApi(url):
    bashCommand = "curl -s \"{}?private_token={}&amp;per_page=999\"".format(url, gitlab_private_token)
    response = subprocess.check_output(['bash', '-c', bashCommand])
    return response

def getGitlabProjects():
    response = json.loads(requestGitlabApi("{}/api/v4/groups/{}/projects".format(gitlab_url, gitlab_group)))
    return response

def getCommits(project_id, since, until):
    bashCommand = "curl -s \"{}/api/v4/projects/{}/repository/commits?private_token={}&amp;per_page=999;since={};until={}\"".format(
        gitlab_url, project_id, gitlab_private_token, since.strftime('%Y/%m/%dT%H:%M'), until.strftime('%Y/%m/%dT%H:%M'))
    response = json.loads(subprocess.check_output(['bash', '-c', bashCommand]))
    return response

def getDiff(project_id, commit):
    bashCommand = "curl -s \"{}/api/v4/projects/{}/repository/commits/{}/diff?private_token={}&amp;per_page=999\"".format(
        gitlab_url, project_id, commit, gitlab_private_token)
    response = json.loads(subprocess.check_output(['bash', '-c', bashCommand]))
    return response

def getBuild(build_number):
    build = json.loads(requestJenkinsApi("{}/job/{}/{}/api/json".format(jenkins_url, jenkins_job, build_number)))
    return build

def getBuilds(d):
    print("Gettings jenkins builds info...")
    builds = json.loads(requestJenkinsApi("{}/job/{}/api/json".format(jenkins_url, jenkins_job)))
    since = datetime(d.year, d.month, d.day, 00, 00, 00)
    until = datetime(d.year, d.month, d.day, 23, 59, 59)
    print("Searching for builds since {} until {}".format(since, until))

    count = 0
    index = 0
    idxs = []
    build_numbers = []

    output = ""
    build_number = -1

    builds_found = []
    build_log = ""
    previous_build_log = ""

    for build in builds["builds"]:
        b = getBuild(build["number"])
        time = datetime.fromtimestamp(b['timestamp'] / 1000.0).strftime("%Y/%m/%d %H:%M")
        building = b['building']
        result = b['result']
        artifacts = b['artifacts']
        
        t = datetime.strptime(time, '%Y/%m/%d %H:%M')
       
        print("\r#{} {} ({} out of {} builds)".format(b['number'], time, index, len(builds["builds"])), end = "")
        sys.stdout.flush()

        if (t < since):
            break
        if (t < until and t > since):
            build_number = b['number']
            build_log = getLog(build_number)
            previous_build_log = getLog(build_number - 1)

            idxs.append(index)
            build_numbers.append(build_number)
            image = ""
            count = count + 1
            for artifact in artifacts:
                if "gsdf" in artifact["fileName"]:
                    image = artifact["fileName"]
                    break
            build_info = {'index' : index, 'build_number' : build_number, 'time' : time, 'building' : building, 'result': result, 'image': image}
            feeds = []
            
            # log -> feeds
            feeds_before = set()
            feeds_after = set()

            for line in previous_build_log.splitlines():
                if "src-git" in line:
                    words = line.split()
                    feed_url = words[2]
                    feeds_before.add(feed_url)
        

            for line in build_log.splitlines():
                if "src-git" in line:
                    words = line.split()
                    feed_url = words[2]
                    feeds_after.add(feed_url)

            feeds_before_diff = feeds_before - feeds_after
            feeds_after_diff = feeds_after - feeds_before

            for i in range(len(feeds_before_diff)):
                feeds.append([list(feeds_before_diff)[i], list(feeds_after_diff)[i]])


            builds_found.append([build_info, feeds])


        index += 1

    print("\rDone                                      ", end = "")
    sys.stdout.flush()

    print("\n")

    for build_found in builds_found:
        print("#{} {} ".format(build_found[0]['build_number'], build_found[0]['image']))

    bn = ""
    if (count > 1):
        while (build_number == -1 or bn not in build_numbers):
            bn = input("Choose the build: ")
            index = 0
            for n in build_numbers:
                if n == bn:
                    build_number = n
                    break
                index += 1
    
    for build_found in builds_found:
        if build_found[0]['build_number'] == build_number:
            if not build_found[1]:
                print("\tFor {} no feeds tag changed".format(jenkins_job))
            else:
                print(tabulate(build_found[1], headers=["old", "new"],  tablefmt="fancy_grid"))
                
    if len(builds_found) == 0:
        print("No builds found")
        return

    since = datetime.strptime(datetime.fromtimestamp(getBuild(build_number - 1)['timestamp'] / 1000.0).strftime("%Y/%m/%d %H:%M"), '%Y/%m/%d %H:%M')
    until = datetime.strptime(datetime.fromtimestamp(getBuild(build_number)['timestamp'] / 1000.0).strftime("%Y/%m/%d %H:%M"), '%Y/%m/%d %H:%M')

    print("Looking for commits between builds #{} and #{} since: {} until: {}".format(build_number, build_number - 1, since, until))
    projects = getGitlabProjects()

    bar = progressbar.ProgressBar(maxval = len(projects), \
    widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()   

    index = 0
    output = []

    commits = {}

    unique_features_list = set()

    for project in projects:
        commits[project['name']] = getCommits(project['id'], since, until)

        for commit in commits[project['name']]:
            title = commit['title']
            title_words = title.split()
            feature = ""
            if "Daily" in title_words:
                feature = title
            elif len(title_words) > 2 and title_words[0] == "Merge" and title_words[1] == "branch":
                feature = title_words[2].replace("'", "").split('_')[0]
            else:
                feature = title_words[0].replace(":", "")

            #if feature.isalpha():
             #   feature = "unknown"

            unique_features_list.add(feature)

        bar.update(index)
        index += 1

    bar.finish()

    feature_output = []
    data = []
    tabulate_data = []

    j = 0
    for feature in unique_features_list:
        for repo, commit_list in commits.iteritems():
            for commit in commit_list:
                if feature in commit['title']:
                    title = "{0:<80s}".format(truncate(commit['title'], 80))
                    data.append([feature,title, commit['author_name'].replace("\t", " "), repo,  commit['short_id']])
                    tabulate_data.append([j, title, commit['author_name'].replace("\t", " "), repo,  commit['short_id']])
                    j += 1           
    print(tabulate(tabulate_data, headers=["#", "Title", "Author", "Repo", "Commit"],  tablefmt="fancy_grid"))

    if len(data) > 0:
        found = False
        while not found:
            bn = input("Choose the commit: ")
            #found = len(data)   
            if bn < len(data):
                repo = data[bn][3]
                id = data[bn][4]
                for project in projects:
                    if project['name'] == repo:
                        diffs = getDiff(project['id'], id)
                        for diff in diffs:
                            print("old_path: {}".format(diff['old_path']))
                            print("new_path: {}".format(diff['new_path']))
                            print("new_file / renamed file / deleted_file: {}/{}/{}".format(diff['new_file'], diff['renamed_file'], diff['deleted_file']))
                            print(diff['diff'])
                        #found = True
                        break
               # break

def truncate(string, width):
    if len(string) > width:
        string = string[:width-3] + '...'
    return string




def getLog(build_number):
    return requestJenkinsApi("{}/job/{}/{}/logText/progressiveText?start=0".format(jenkins_url, jenkins_job, build_number))

def parseOptions():
    parser = argparse.ArgumentParser()
    parser.add_argument("date", type=lambda s: datetime.strptime(s, '%Y-%m-%d'), help="Example: 2020-12-20")
    args = parser.parse_args()

    getBuilds(args.date)

def main():

    if not jenkins_user:
        print("JENKINS_USER is not set")
        return

    if not jenkins_token:
        print("JENKINS_TOKEN is not set")
        return

    if not jenkins_job:
        print("JENKINS_JOB is not set")
        return

    if not jenkins_url:
        print("JENKINS_URL is not set")
        return

    if not gitlab_group:
        print("GITLAB_GROUP is not set")
        return

    if not gitlab_private_token:
        print("GITLAB_PRIVATE_TOKEN is not set")
        return

    if not gitlab_url:
        print("GITLAB_URL is not set")
        return

    try:
        parseOptions()
    except KeyboardInterrupt:
        print("\n")
        sys.exit()

if __name__ == "__main__":
    main()





