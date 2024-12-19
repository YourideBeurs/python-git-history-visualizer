from datetime import datetime
import subprocess
from tqdm import tqdm
from collections import defaultdict
import matplotlib.pyplot as plt
import argparse
import seaborn as sns

def get_commit_hashes(repo_path):
    log_results = subprocess.run(['git', 'log', '--pretty=format:%H'], stdout=subprocess.PIPE, text=True, cwd=repo_path)
    commit_hashes = log_results.stdout.strip().split('\n')
    return commit_hashes

def fetch_commit_details(repo_path, commit_hash):
    commit_details = subprocess.run(['git', 'show', '--name-only',  '--pretty=format:%H%n%an%n%s%n%ad', commit_hash], stdout=subprocess.PIPE, encoding='utf-8', text=True, cwd=repo_path)
    commit_details = commit_details.stdout.strip().split('\n', 4)
    
    return commit_details

def export_file_changes_count(commits, path):
    
    file_counts = defaultdict(int)

    for commit in commits:
        files = commit[4].strip().split('\n')
        for file in files:
            file_counts[file] += 1

    sorted_file_counts = dict(sorted(file_counts.items(), key=lambda item: item[1], reverse=True))
    files = list(sorted_file_counts.keys())
    counts = list(sorted_file_counts.values())

    plt.figure(figsize=(10, 10))
    plt.bar(files, counts, color='skyblue')

    plt.xlabel('Files')
    plt.ylabel('Counts')
    plt.title('File Modification Counts in Commits')

    plt.xticks(rotation=90)

    plt.tight_layout()

    plt.savefig(path, dpi=300, bbox_inches='tight')

def export_file_changes_over_time(commits, path):
    
    files = []
    dates = []
    authors = []
    for commit in commits:
        commit_date = commit[3] = datetime.strptime(commit[3], '%a %b %d %H:%M:%S %Y %z')
        commit_author=commit[1]
        files_list = commit[4].strip().split('\n')
        for file in files_list:
            files.append(file)
            dates.append(commit_date)
            authors.append(commit_author)

    plt.figure(figsize=(25, 8))
    sns.scatterplot(x=dates, y=files, hue=authors, palette='viridis', alpha=0.6, edgecolor='w', linewidth=0.5)

    plt.xlabel('Date')
    plt.ylabel('Files')
    plt.title('Files Modified Over Time by Author in Commits')

    plt.gcf().autofmt_xdate()

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)

    plt.tight_layout()

    plt.savefig(path, dpi=300, bbox_inches='tight')

def main(args):
    
    repo_path = args.repo_path
    file_changes_count_path = args.file_changes_count_path
    commits_over_time_path = args.commits_over_time_path

    commit_hashes = get_commit_hashes(repo_path)
    
    all_details = []
    
    for i in tqdm(range(len(commit_hashes))):
        commit_hash = commit_hashes[i]
        
        commit_details = fetch_commit_details(repo_path, commit_hash)
        all_details.append(commit_details)

    filtered_commits = [commit for commit in all_details if len(commit) > 4]

    export_file_changes_count(filtered_commits, file_changes_count_path)
    export_file_changes_over_time(filtered_commits, commits_over_time_path)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process and visualize Git History.") 
    parser.add_argument("repo_path", type=str, help="The folder the repository")
    parser.add_argument("commits_over_time_path", type=str, help="The path for the commits over time visualization")
    parser.add_argument("file_changes_count_path", type=str, help="The path for the files changed count visualization")
    args = parser.parse_args()
    main(args)