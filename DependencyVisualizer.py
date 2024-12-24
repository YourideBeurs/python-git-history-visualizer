import os
import ast

import seaborn as sns
import matplotlib.pyplot as plt
import networkx as nx

from collections import defaultdict

class DependencyVisualizer:
    """
    A class to visualize and analyze function dependencies in Python files.

    Attributes:
        directory (str): The directory containing Python files to analyze.
        included_files (list[str] or None): A list of specific files to include in the analysis.
        exclude_files (list[str] or None): A list of specific files to exclude from the analysis.
        git_visualiser (GitVisualizer or None): An instance of GitVisualizer to fetch commit history.
    """

    def __init__(self, folder:str):
        """
        Initializes the DependencyVisualizer with the specified directory.

        Args:
            folder (str): The directory containing Python files.
        """
        self.directory = folder
        self.included_files = None
        self.exclude_files = None
        self.git_visualiser = None

    def reset(self):
        """
        Resets the internal state, clearing any previously parsed data.
        """
        self.all_functions = {}
        self.files_count = 0

    def parse_python_files(self):
        """
        Parses all Python files in the specified directory, extracting function dependencies.

        This method identifies all `.py` files in the directory (and subdirectories),
        filters them based on `included_files` and `exclude_files` (if specified),
        and extracts function dependencies using the `parse_file` function.
        """
        self.reset()

        python_files = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.py'):
                    abs_path = os.path.join(root, file).replace('\\', '/')
                    python_files.append(abs_path)

        if self.included_files:
            files = [file for file in python_files if file in self.included_files]
        if self.excluded_files:
            files = [file for file in python_files if file not in self.excluded_files]

        for file in files:
            self.files_count += 1
            print(f"Parsing {file}", end='\r')

            filename = os.path.basename(file)
            functions = parse_file(file)
            
            for func, deps in functions.items():
                self.all_functions[f"{filename}.{func}"] = {f"{filename}.{dep}" for dep in deps}
        print(' ' * 40, end='\r')
        print(f"Python files parsed: {self.files_count}")	

    def show_dependencies(self,  **kwargs):
        """
        Visualizes the function dependencies as a directed graph.

        Args:
            **kwargs: Optional parameters to customize the plot, such as:
                - figsize (tuple): Size of the figure (default: (10, 8)).
                - with_labels (bool): Whether to display labels on nodes (default: True).
                - node_color (str): Color of the nodes (default: 'skyblue').
                - node_size (int): Size of the nodes (default: 2000).
                - edge_color (str): Color of the edges (default: 'gray').
                - linewidths (float): Width of the edges (default: 1).
                - font_size (int): Font size for labels (default: 10).
                - font_weight (str): Font weight for labels (default: 'bold').
                - arrowsize (int): Size of the arrows (default: 20).
                - alpha (float): Transparency of the plot (default: 0.8).
        """
        G = nx.DiGraph()

        for func, deps in self.all_functions.items():
            for dep in deps:
                G.add_edge(func, dep)

        plt.figure(figsize=kwargs.get('figsize', (10, 8)))
        pos = nx.spring_layout(G)

        nx.draw(G, pos,
                with_labels=kwargs.get('with_labels', True),
                node_color=kwargs.get('node_color', 'skyblue'),
                node_size=kwargs.get('node_size', 2000),
                edge_color=kwargs.get('edge_color', 'gray'),
                linewidths=kwargs.get('linewidths', 1),
                font_size=kwargs.get('font_size', 10),
                font_weight=kwargs.get('font_weight', 'bold'),
                arrowsize=kwargs.get('arrowsize', 20),
                alpha=kwargs.get('alpha', 0.8))

        sns.set(style=kwargs.get('style', 'whitegrid'))
        plt.title(kwargs.get('title', 'Function Dependency Graph'), fontsize=15)

        plt.show()
        
    def save_dependencies(self, path:str, **kwargs):
        """
        Saves the function dependency graph as an image.

        Args:
            path (str): The file path where the image will be saved.
            **kwargs: Optional parameters for customizing the plot (same as `show_dependencies`).
        """
        G = nx.DiGraph()

        for func, deps in self.all_functions.items():
            for dep in deps:
                G.add_edge(func, dep)

        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G)
        
        nx.draw(G, pos,
                with_labels=kwargs.get('with_labels', True),
                node_color=kwargs.get('node_color', 'skyblue'),
                node_size=kwargs.get('node_size', 2000),
                edge_color=kwargs.get('edge_color', 'gray'),
                linewidths=kwargs.get('linewidths', 1),
                font_size=kwargs.get('font_size', 10),
                font_weight=kwargs.get('font_weight', 'bold'),
                arrowsize=kwargs.get('arrowsize', 20),
                alpha=kwargs.get('alpha', 0.8))

        sns.set(style=kwargs.get('style', 'whitegrid'))
        plt.title(kwargs.get('title', 'Function Dependency Graph'), fontsize=15)

        plt.savefig(path, dpi=300, bbox_inches='tight')

def parse_file(file_path:str):
    """
    Parses a Python file and extracts function dependencies.

    Args:
        file_path (str): The path to the Python file.

    Returns:
        dict: A dictionary where keys are function names and values are sets of
              called function names within the same file.
    """
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read(), filename=file_path)

    functions = defaultdict(set)
    class FunctionVisitor(ast.NodeVisitor):
        """
        AST visitor class to extract function calls within function definitions.
        """
        def visit_FunctionDef(self, node):
            """
            Visits a function definition node and collects its dependencies.

            Args:
                node (ast.FunctionDef): The function definition node.
            """
            current_function = node.name
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    functions[current_function].add(child.func.attr)
                elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    functions[current_function].add(child.func.id)
            self.generic_visit(node)

    FunctionVisitor().visit(tree)

    return functions