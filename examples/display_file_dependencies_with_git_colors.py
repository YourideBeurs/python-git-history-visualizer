"""
This script utilizes the `CodeVisualizer`, `DependencyVisualizer`, and `GitVisualizer` classes 
to analyze and visualize a codebase's structure, dependencies, and Git commit history.

Steps involved:
1. Initialize the `CodeVisualizer` with the path to the database file.
   If the database doesn't exist, it will be created.
2. Initialize the `DependencyVisualizer` with the path to the Python code directory.
   Parse the Python files to extract dependencies.
   To speed up the example, the number of files is limited to only the `./python/kubernetes/base/dynamic` folder.
3. Process the parsed dependencies with the `CodeVisualizer`.
4. Initialize the `GitVisualizer` with the path to the Git repository.
   Parse the commits to extract Git history.
   The repository used for this example is `kubernetes-client/python` and can be cloned from: https://github.com/kubernetes-client/python.git
5. Process the parsed Git commits with the `CodeVisualizer`.
6. Define a function `shorten_node_name` to shorten the node names by taking only the last part of the path.
7. Visualize the file dependencies using the `CodeVisualizer`, renaming nodes using the defined callback function.
"""

from CodeVisualizer import CodeVisualizer
from DependencyVisualizer import DependencyVisualizer
from GitVisualizer import GitVisualizer

db_path = 'codebase.db'

visualizer = CodeVisualizer(db_path)
visualizer.build_db_if_not_exists()

dep_visualizer = DependencyVisualizer('./python/kubernetes/base/dynamic')
dep_visualizer.parse_python_files()

visualizer.process_dependencies(dep_visualizer)

git_visualizer = GitVisualizer('./python')
git_visualizer.parse_commits()
visualizer.process_git_commits(git_visualizer)

def shorten_node_name(node):
    return node.split('/')[-1]

visualizer.show_file_dependencies(rename_node_callback=shorten_node_name)