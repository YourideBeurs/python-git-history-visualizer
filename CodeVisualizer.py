import sqlite3
import os

import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx

import matplotlib.cm as cm

from datetime import datetime

class CodeVisualizer:
    def __init__(self, path:str):
        self.path = path

    def build_db_if_not_exists(self):
        if os.path.exists(self.path):
            os.remove(self.path)

        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE commits (
            hash TEXT PRIMARY KEY,
            author TEXT,
            date DATE
        )
        ''')

        cursor.execute('''
        CREATE TABLE commit_files (
            commit_hash TEXT,
            file_path TEXT,
            PRIMARY KEY (commit_hash, file_path),
            FOREIGN KEY (commit_hash) REFERENCES commits (hash),
            FOREIGN KEY (file_path) REFERENCES files (full_path)
        )
        ''')

        cursor.execute('''
        CREATE TABLE files (
            full_path TEXT PRIMARY KEY
        )
        ''')

        cursor.execute('''
        CREATE TABLE functions (
            name TEXT,
            file_full_path TEXT,
            PRIMARY KEY (name, file_full_path),
            FOREIGN KEY (file_full_path) REFERENCES files (full_path)
        )
        ''')

        cursor.execute('''
        CREATE TABLE function_dependencies (
            caller_path TEXT,
            callee_path TEXT,
            PRIMARY KEY (caller_path, callee_path),
            FOREIGN KEY (caller_path) REFERENCES functions (name),
            FOREIGN KEY (callee_path) REFERENCES functions (name)
        )
        ''')

        conn.commit()
        conn.close()

    def process_dependencies(self, dep_visualizer):
        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()

        for caller, callee in dep_visualizer.function_dependencies:
            caller_file_path, caller_function_name = caller.rsplit('.', 1)
            callee_file_path, callee_function_name = callee.rsplit('.', 1)

            cursor.execute(''' INSERT OR IGNORE INTO files (full_path) VALUES (?) ''', (caller_file_path,))
        
            cursor.execute(''' INSERT OR IGNORE INTO files (full_path) VALUES (?) ''', (callee_file_path,))
            
            cursor.execute(''' INSERT OR IGNORE INTO functions (name, file_full_path) VALUES (?, ?) ''', (caller_function_name, caller_file_path))
            
            cursor.execute(''' INSERT OR IGNORE INTO functions (name, file_full_path) VALUES (?, ?) ''', (callee_function_name, callee_file_path))
            
            cursor.execute(''' INSERT OR IGNORE INTO function_dependencies (caller_path, callee_path) VALUES (?, ?) ''', (caller_function_name, callee_function_name))

        conn.commit()
        conn.close()
    
    def process_git_commits(self, git_visualizer):
        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()

        for commit in git_visualizer.commits:
            cursor.execute('SELECT hash FROM commits WHERE hash = ?', (commit.hash,))
            if cursor.fetchone() is None:
                cursor.execute('''
                INSERT INTO commits (hash, author, date) VALUES (?, ?, ?)
                ''', (commit.hash, commit.author, commit.date))

                for file_path in commit.files:
                    file_path = './python/' + file_path
                    cursor.execute('''
                    INSERT OR IGNORE INTO files (full_path) VALUES (?)
                    ''', (file_path,))
                    
                    cursor.execute('''
                    INSERT INTO commit_files (commit_hash, file_path) VALUES (?, ?)
                    ''', (commit.hash, file_path))

        conn.commit()
        conn.close()


    def show_file_changes_from_git_scatter(self, 
                                           pre_filtering=True,
                                           query=None, 
                                           enable_hue=True,
                                           filter_commits_callback=None,
                                           rename_file_callback=None):
        """
        Visualizes file changes as a scatter plot, showing files modified by commit date and author.

        This method focuses on the top 25 most frequently changed files.
        """
        authors = []
        dates = []
        files = []

        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()

        if pre_filtering:
            if query:
                cursor.execute(query)
            else:
                cursor.execute('''
                            SELECT cf.file_path
                            FROM commits c
                            INNER JOIN commit_files cf
                            ON c.hash = cf.commit_hash
                            WHERE cf.file_path LIKE '%.py'
                            GROUP BY cf.file_path
                            ORDER BY count(*) DESC
                            LIMIT 25
                ''')

            top_25_files = cursor.fetchall()
            top_25_files = [file[0] for file in top_25_files]
        
            cursor.execute('''
                        SELECT c.*, cf.file_path
                        FROM commits c
                        INNER JOIN commit_files cf
                        ON c.hash = cf.commit_hash                       
            ''')

        commits = cursor.fetchall()
        conn.close()

        filtered_commits = [commit for commit in commits if not pre_filtering or commit[3] in top_25_files]

        filtered_commits = [
            (commit[0], commit[1], datetime.strptime(commit[2], '%Y-%m-%d %H:%M:%S%z'), commit[3]) 
            for commit in filtered_commits 
        ]

        if filter_commits_callback:
            filtered_commits = filter_commits_callback(filtered_commits)

        for commit in filtered_commits:
            authors.append(commit[1])
            dates.append(commit[2])
            if rename_file_callback:
                files.append(rename_file_callback(commit[3]))
            else:
                files.append(commit[3])

        plt.figure(figsize=(24, 16))

        if enable_hue:
            scatter_plot = sns.scatterplot(x=dates, y=files, hue=authors, palette='viridis')
        else:
            scatter_plot = sns.scatterplot(x=dates, y=files, palette='viridis')

        plt.title('Files by Commit Date and Author')
        plt.xlabel('Commit Date')
        plt.ylabel('Filename')
        plt.xticks(rotation=45)
        plt.grid(True)

        if enable_hue:
            plt.legend(title='Author', bbox_to_anchor=(1.005, 1), loc='upper left')

        plt.tight_layout()
        plt.show()
    
    def show_file_dependencies(self, 
                               files_callback=None, 
                               rename_node_callback=None,
                               use_git_visualizer=False, 
                               query=None, 
                               **kwargs):
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

        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()

        if query:
            cursor.execute(query)
        else:
            cursor.execute('''
                        SELECT DISTINCT f1.file_full_path, f2.file_full_path
                        FROM function_dependencies fd
                        INNER JOIN functions f1
                        ON fd.caller_path = f1.name
                        INNER JOIN functions f2
                        ON fd.callee_path = f2.name
                        WHERE f1.file_full_path != f2.file_full_path;
            ''')

        deps = cursor.fetchall()

        cursor.execute('''
                    SELECT cf.file_path, count(*)
                    FROM commits c
                    INNER JOIN commit_files cf
                    ON c.hash = cf.commit_hash
                    WHERE cf.file_path LIKE '%.py'
                    GROUP BY cf.file_path
                    ORDER BY count(*) DESC      
        ''')

        changes_count = cursor.fetchall()
        conn.close()
        
        changes_count_dict = {filename: count for filename, count in changes_count}

        for caller, callee in deps:
            G.add_edge(caller, callee)

        node_counts = [changes_count_dict.get(node, 0) for node in G.nodes()]
        max_count = max(node_counts) if node_counts else 1
        min_count = min(node_counts) if node_counts else 0

        normalized_counts = [(count - min_count) / (max_count - min_count) if max_count > min_count else 0.5 for count in node_counts]

        colormap = cm.get_cmap(kwargs.get('colormap', 'coolwarm'))

        node_colors = [colormap(value) for value in normalized_counts]

        modified_labels = {
        node: (rename_node_callback(node) if rename_node_callback else node) for node in G.nodes()
        }

        plt.figure(figsize=kwargs.get('figsize', (10, 8))) 
        pos = nx.spring_layout(G)

        nx.draw(G, pos, 
                labels = modified_labels,
                with_labels=kwargs.get('with_labels', True), 
                node_color=node_colors,
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