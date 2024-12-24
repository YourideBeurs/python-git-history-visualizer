import os
import ast

import seaborn as sns
import matplotlib.pyplot as plt
import networkx as nx

from collections import defaultdict

class DependencyVisualizer:
    def __init__(self, folder:str):
        self.directory = folder
        self.included_files = None
        self.exclude_files = None

    def reset(self):
        self.all_functions = {}
        self.files_count = 0
        

    def parse_python_files(self):

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
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read(), filename=file_path)

    functions = defaultdict(set)
    class FunctionVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            current_function = node.name
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    functions[current_function].add(child.func.attr)
                elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    functions[current_function].add(child.func.id)
            self.generic_visit(node)

    FunctionVisitor().visit(tree)

    return functions