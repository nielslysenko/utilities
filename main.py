#!/usr/bin/python

from __future__ import print_function
import sys
import progressbar
import text_format
from datetime import datetime
from tabulate import tabulate
from jenkins import Jenkins
from gitlab import Gitlab
from parser import Parser

projects = ""

def getBuilds(d):
    print("Gettings jenkins builds info...")

    jenkins = Jenkins()
    gitlab = Gitlab()

    jobs = jenkins.getJobs()
    
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

    for build in jobs["builds"]:
        b = jenkins.getBuild(build["number"])
        time = datetime.fromtimestamp(b['timestamp'] / 1000.0).strftime("%Y/%m/%d %H:%M")
        building = b['building']
        result = b['result']
        artifacts = b['artifacts']
        
        t = datetime.strptime(time, '%Y/%m/%d %H:%M')
       
        print("\r#{} {} ({} out of {} builds)".format(b['number'], time, index, len(jobs["builds"])), end = "")
        sys.stdout.flush()

        if (t < since):
            break
        if (t < until and t > since):
            build_number = b['number']
            build_log = jenkins.getLog(build_number)
            previous_build_log = jenkins.getLog(build_number - 1)

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
        print("No build jobs found")
        return

    since = datetime.strptime(datetime.fromtimestamp(jenkins.getBuild(build_number - 1)['timestamp'] / 1000.0).strftime("%Y/%m/%d %H:%M"), '%Y/%m/%d %H:%M')
    until = datetime.strptime(datetime.fromtimestamp(jenkins.getBuild(build_number)['timestamp'] / 1000.0).strftime("%Y/%m/%d %H:%M"), '%Y/%m/%d %H:%M')

    print("Looking for commits between build jobs #{} and #{} since: {} until: {}".format(build_number, build_number - 1, since, until))
    projects = gitlab.getGitlabProjects()

    bar = progressbar.ProgressBar(maxval = len(projects), \
    widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()   

    index = 0
    output = []

    commits = {}

    unique_features_list = set()

    for project in projects:
        commits[project['name']] = gitlab.getCommits(project['id'], since, until)

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

            unique_features_list.add(feature)

        bar.update(index)
        index += 1

    bar.finish()

    feature_output = []
    data = []
    tabulate_data = []

    j = 0
    for feature in unique_features_list:
        for repo, commit_list in commits.items():
            for commit in commit_list:
                if feature in commit['title']:
                    title = "{0:<80s}".format(text_format.truncate(commit['title'], 80))
                    data.append([feature,title, commit['author_name'].replace("\t", " "), repo,  commit['short_id']])
                    tabulate_data.append([j, title, commit['author_name'].replace("\t", " "), repo,  commit['short_id']])
                    j += 1           
    print(tabulate(tabulate_data, headers=["#", "Title", "Author", "Repo", "Commit"],  tablefmt="fancy_grid"))

    if len(data) > 0:
        found = False
        while not found:
            bn = input("Choose the commit: ")
            if int(bn) < len(data):
                repo = data[int(bn)][3]
                id = data[int(bn)][4]
                for project in projects:
                    if project['name'] == repo:
                        diffs = gitlab.getDiff(project['id'], id)
                        for diff in diffs:
                            print("old_path: {}".format(diff['old_path']))
                            print("new_path: {}".format(diff['new_path']))
                            print("new_file / renamed file / deleted_file: {}/{}/{}".format(diff['new_file'], diff['renamed_file'], diff['deleted_file']))
                            print(diff['diff'])
                        break

def main():
    if not Jenkins.jenkins_user:
        print("JENKINS_USER is not set")
        return

    if not Jenkins.jenkins_token:
        print("JENKINS_TOKEN is not set")
        return

    if not Jenkins.jenkins_job:
        print("JENKINS_JOB is not set")
        return

    if not Jenkins.jenkins_url:
        print("JENKINS_URL is not set")
        return

    if not Gitlab.gitlab_group:
        print("GITLAB_GROUP is not set")
        return

    if not Gitlab.gitlab_private_token:
        print("GITLAB_PRIVATE_TOKEN is not set")
        return

    if not Gitlab.gitlab_url:
        print("GITLAB_URL is not set")
        return

    try:
        date = Parser.parseOptions()
        getBuilds(date)

    except KeyboardInterrupt:
        print("\n")
        sys.exit()

if __name__ == "__main__":
    main()





