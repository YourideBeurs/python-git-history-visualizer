from datetime import datetime
from collections import Counter
from tqdm import tqdm

import seaborn as sns
import matplotlib.pyplot as plt

import subprocess
import re

class GitVisualizer:
    """
    A class to analyze and visualize Git repository commit history and file changes.

    Attributes:
        repo_path (str): The path to the Git repository.
        include_files (list[str] or None): Specific files to include in the analysis.
        exclude_files (list[str] or None): Specific files to exclude from the analysis.
        include_files_by_pattern (list[str] or None): Patterns of files to include in the analysis.
        exclude_files_by_pattern (list[str] or None): Patterns of files to exclude from the analysis.
    """

    def __init__(self, repo_path: str):
        """
        Initializes the GitVisualizer with the specified repository path.

        Args:
            repo_path (str): The path to the Git repository.
        """
        self.repo_path = repo_path
        self.include_files = None
        self.exclude_files = None
        self.include_files_by_pattern = None
        self.exclude_files_by_pattern = None

    def reset(self):
        """
        Resets the internal state by clearing previously fetched commit hashes and details.
        """
        self.hashes = []
        self.commits = []

    def parse_commits(self):
        """
        Fetches and parses commit history from the Git repository.

        This method extracts commit hashes and details (e.g., author, date, and changed files),
        applying any specified inclusion or exclusion filters.
        """
        self.reset()

        log_results = subprocess.run(['git', 'log', '--pretty=format:%H'], stdout=subprocess.PIPE, text=True, cwd=self.repo_path)
        commit_hashes = log_results.stdout.strip().split('\n')

        [self.hashes.append(commit) for commit in commit_hashes]

        for i in tqdm(range(len(self.hashes))):
            hash = self.hashes[i]
            commit_details = subprocess.run(['git', 'show', '--name-only',  '--pretty=format:%H%n%an%n%s%n%ad', hash], stdout=subprocess.PIPE, encoding='utf-8', text=True, cwd=self.repo_path)
            commit_details = commit_details.stdout.strip().split('\n', 4)

            commit = git_commit()
            commit.author = commit_details[1]
            commit.date = datetime.strptime(commit_details[3], '%a %b %d %H:%M:%S %Y %z')
            if len(commit_details) > 4:
                files_list = commit_details[4].strip().split('\n')
                for file in files_list:
                    if self.include_files:
                        if file not in self.include_files:
                            continue
                    if self.exclude_files:
                        if file in self.exclude_files:
                            continue
                    if self.include_files_by_pattern:
                        include_match = any(re.match(pattern, file) for pattern in self.include_files_by_pattern)
                        if not include_match:
                            continue
                    if self.exclude_files_by_pattern:
                        exclude_match = any(re.match(pattern, file) for pattern in self.exclude_files_by_pattern)
                        if exclude_match:
                                continue

                    commit.files.append(file)
            else:
                commit.files = []

            self.commits.append(commit)

    def custom_filter_commits(self, callback):
        """
        Applies a custom filter to the parsed commits.

        Args:
            callback (function): A function that takes a list of commits and returns a filtered list.
        """
        self.commits = callback(self.commits)

    def show_file_changes_scatter(self):
        """
        Visualizes file changes as a scatter plot, showing files modified by commit date and author.

        This method focuses on the top 25 most frequently changed files.
        """
        authors = []
        dates = []
        files = []

        file_counter = Counter()
        for commit in self.commits:
            for file in commit.files:
                file_counter[file] += 1

        top_files = sorted({file for file, count in file_counter.most_common(25)})

        for commit in self.commits:
            for file in commit.files:
                if file in top_files:
                    authors.append(commit.author)
                    dates.append(commit.date)
                    files.append(file)

        plt.figure(figsize=(12, 8))

        scatter_plot = sns.scatterplot(x=dates, y=files, hue=authors, palette='viridis')

        plt.title('Files by Commit Date and Author')
        plt.xlabel('Commit Date')
        plt.ylabel('Filename')
        plt.xticks(rotation=45)
        plt.grid(True)

        plt.legend(title='Author', bbox_to_anchor=(1.005, 1), loc='upper left')

        plt.tight_layout()
        plt.show()

class git_commit:
    """
    A simple class to represent details of a Git commit.

    Attributes:
        author (str): The author of the commit.
        date (datetime): The date and time of the commit.
        files (list[str]): A list of files changed in the commit.
    """

    def __init__(self):
        """
        Initializes an empty git_commit instance.
        """
        self.author = None
        self.date = None
        self.files = []
