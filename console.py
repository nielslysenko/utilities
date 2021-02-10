import subprocess

class Console:
    def execute(cmd):
        out = subprocess.check_output(['bash', '-c', cmd])
        return out
