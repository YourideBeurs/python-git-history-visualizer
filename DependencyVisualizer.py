import os
import ast
import random

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import networkx as nx

from collections import defaultdict

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

    relative_path = file_path.replace('\\', '/')
    functions = defaultdict(set)
    imports = {}

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                imports[alias.asname or alias.name] = alias.name

        def visit_ImportFrom(self, node):
            module = node.module
            for alias in node.names:
                if module:
                    full_name = f"{module}.{alias.name}"
                    imports[alias.asname or alias.name] = full_name
                else:
                    imports[alias.asname or alias.name] = alias.name

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
            current_function = f"{relative_path}.{node.name}"
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        module = child.func.value.id if isinstance(child.func.value, ast.Name) else None
                        called_function = child.func.attr
                        if module and module in imports:
                            callee = f"{imports[module]}.{called_function}"
                        elif module:
                            callee = f"{module}.{called_function}"
                        else:
                            callee = f"{relative_path}.{called_function}"
                    elif isinstance(child.func, ast.Name):
                        called_function = child.func.id
                        if called_function in imports:
                            callee = imports[called_function]
                        else:
                            callee = f"{relative_path}.{called_function}"
                    else:
                        continue
                    functions[current_function].add(callee)
            self.generic_visit(node)

    ImportVisitor().visit(tree)
    FunctionVisitor().visit(tree)

    function_dependencies = {
        (caller, callee)
        for caller, callees in functions.items()
        for callee in callees
    }

    return function_dependencies

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
        self.excluded_files = None
        self.git_visualiser = None

    def reset(self):
        """
        Resets the internal state, clearing any previously parsed data.
        """
        self.function_dependencies = set()
        self.file_dependencies = set()
        self.files_count = 0

    def parse_python_files(self):
        """
        Parses all Python files in the specified directory, extracting function dependencies.

        This method identifies all `.py` files in the directory (and subdirectories),
        filters them based on `included_files` and `exclude_files` (if specified),
        and extracts function dependencies using the `parse_file` function.
        """
        self.reset()

        file_asts = {}
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r") as f:
                        file_asts[file_path] = ast.parse(f.read(), filename=file_path)

        function_map = {}
        for file_path, tree in file_asts.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_map[node.name] = f"{file_path}.{node.name}"

        dependencies = set()
        for file_path, tree in file_asts.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    caller = f"{file_path}.{node.name}"
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                            callee = child.func.id
                            if callee in function_map:
                                dependencies.add((caller, function_map[callee]))
                        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                            callee = child.func.attr
                            if callee in function_map:
                                dependencies.add((caller, function_map[callee]))

        self.function_dependencies = {(caller.replace("\\", "/"), callee.replace("\\", "/")) for caller, callee in dependencies}

        for caller, callee in self.function_dependencies:
            caller_file = '.'.join(caller.split('.')[:-1])
            callee_file = '.'.join(callee.split('.')[:-1])
            self.file_dependencies.add((caller_file, callee_file))

    def show_file_dependencies(self, files_callback=None, **kwargs):
        """ Visualizes the file dependencies as a directed graph.

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
        - alpha (float): Transparency of the plot (default: 0.8). """
        G = nx.DiGraph()

        dependencies = self.file_dependencies.copy()
        if files_callback:
            dependencies = files_callback(dependencies)

        for caller, callee in dependencies:
            caller_base = caller.split('.')[0]
            callee_base = callee.split('.')[0]
            G.add_edge(caller_base, callee_base)

        plt.figure(figsize=kwargs.get('figsize', (10, 8))) 
        pos = nx.spring_layout(G)

        node_colors = {node: self.generate_random_color() for node in G.nodes()}
        node_color_list = [node_colors[node] for node in G.nodes()]
        
        nx.draw(G, pos, 
                with_labels=kwargs.get('with_labels', True), 
                node_color=node_color_list,
                # node_color=kwargs.get('node_color', 'skyblue'), 
                node_size=kwargs.get('node_size', 2000), 
                edge_color=kwargs.get('edge_color', 'gray'), 
                linewidths=kwargs.get('linewidths', 1), 
                font_size=kwargs.get('font_size', 10), 
                font_weight=kwargs.get('font_weight', 'bold'), 
                arrowsize=kwargs.get('arrowsize', 20), 
                alpha=kwargs.get('alpha', 0.8)) 
        
        sns.set(style=kwargs.get('style', 'whitegrid')) 
        plt.title(kwargs.get('title', 'File Dependency Graph'), fontsize=15)
        
        plt.show()

    def show_function_dependencies(self, functions_callback=None, **kwargs):
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

        dependencies = self.function_dependencies.copy()
        if functions_callback:
            dependencies = functions_callback(dependencies)

        for caller, callee in dependencies:
                G.add_edge(caller, callee)

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

    def generate_random_color(self):
        blue = (0 ,0, 255)
        red = (255, 0, 0)
        random_factor = random.random()
        mixed_color = ( 
            int(blue[0] * (1 - random_factor) + red[0] * random_factor), 
            int(blue[1] * (1 - random_factor) + red[1] * random_factor), 
            int(blue[2] * (1 - random_factor) + red[2] * random_factor)
        )

        return '#%02x%02x%02x' % mixed_color

    def calculate_file_changes(self):
        """
        Calculates the number of changes for each file based on the git history.
        
        Returns:
            dict: A dictionary with file names as keys and the number of changes as values.
        """
        file_changes = defaultdict(int)
        
        if self.git_visualiser and hasattr(self.git_visualiser, 'commits'):
            for commit in self.git_visualiser.commits:
                for file in commit.files:
                    file_changes[file] += 1
        
        return file_changes
    

    def generate_dynamic_color(self, num_changes, max_changes):
        """
        Generates a color between light blue and red based on the number of changes.

        Args:
            num_changes (int): The number of changes for the file.
            max_changes (int): The maximum number of changes among all files.

        Returns:
            str: A hex color code.
        """
        light_blue = np.array([173, 216, 230])  # RGB for light blue
        red = np.array([255, 0, 0])  # RGB for red

        if max_changes == 0:
            return '#add8e6'  # Return light blue if there are no changes

        ratio = num_changes / max_changes
        mixed_color = (1 - ratio) * light_blue + ratio * red
        mixed_color = mixed_color.astype(int)
        
        return '#%02x%02x%02x' % tuple(mixed_color)


    def save_dependencies(self, path:str, **kwargs):
        """
        Saves the function dependency graph as an image.

        Args:
            path (str): The file path where the image will be saved.
            **kwargs: Optional parameters for customizing the plot (same as `show_dependencies`).
        """
        G = nx.DiGraph()

        for func, deps in self.function_dependencies.items():
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

