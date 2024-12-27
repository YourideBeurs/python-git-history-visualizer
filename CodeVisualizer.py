import sqlite3
import os

class CodeVisualizer:
    def build_db_if_not_exists(self, path:str):
        if os.path.exists(path):
            os.remove(path)

        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE commits (
            hash TEXT PRIMARY KEY,
            author TEXT,
            date TEXT
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

    def process_dependencies(self, path:str, dep_visualizer):
        conn = sqlite3.connect(path)
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
    
    def process_git_commits(self, path:str, git_visualizer):
        conn = sqlite3.connect(path)
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