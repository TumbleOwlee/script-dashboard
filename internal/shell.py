import io
import os
import subprocess
from typing import List


class Shell:
    def __init__(self, working_directory: str, env: dict | None = dict(), log_dir: str | None = None) -> None:
        self.working_directory: str = working_directory
        if log_dir is None:
            self.log: io.TextIOWrapper = open(os.path.join(working_directory, 'commands.log'), 'a')
        else:
            self.log: io.TextIOWrapper = open(os.path.join(log_dir, 'commands.log'), 'a')
        self.env = env

    def run(self, commands: List[List[str]]) -> int:
        env = os.environ.copy()
        env = {**env, **self.env}
        for cmd in commands:
            try:
                self.log.write(f"[!] Run command: {cmd}\n")
                self.log.flush()

                p: subprocess.CompletedProcess[str] = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                                                                     stdout=self.log,
                                                                     stderr=self.log, cwd=self.working_directory, env=env, capture_output=False, timeout=30)
                if p.returncode != 0:
                    return p.returncode
            except FileNotFoundError:
                return 1
        return 0

    def check_output(self, command: List[str]) -> str:
        env = os.environ.copy()
        env = {**env, **self.env}
        returncode: int = 0
        output: str = ''
        try:
            self.log.write(f"[!] Run command: {command}\n")
            self.log.flush()

            output = subprocess.check_output(command, timeout=30, text=True, cwd=self.working_directory, env=env)
        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            output = e.output
        return returncode, output
