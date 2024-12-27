from CodeVisualizer import CodeVisualizer
from DependencyVisualizer import DependencyVisualizer
from GitVisualizer import GitVisualizer

db_path = 'codebase.db'

visualizer = CodeVisualizer(db_path)
visualizer.build_db_if_not_exists()

dep_visualizer = DependencyVisualizer('./example-project')
dep_visualizer.parse_python_files()

visualizer.process_dependencies(dep_visualizer)

git_visualizer = GitVisualizer('./example-project')
git_visualizer.parse_commits()
visualizer.process_git_commits(git_visualizer)

def shorten_node_name(node):
    return node.split('/')[-1]

visualizer.show_file_dependencies(rename_node_callback=shorten_node_name)