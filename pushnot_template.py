from typing import List
from dataclasses import dataclass

@dataclass
class Fmt:
    placeholder: str
    replacement: str

    def format(self, text: str) -> str:
        return text.replace(
            f"{{{self.placeholder}}}", self.replacement)

class Template:
    def __init__(self, js:str="static/app.js", html:str="static/maglinks.html"):
        self.js_path = js
        self.html_path = html
        with open(self.js_path, "r", encoding="utf-8") as f:
            self.js_template = f.read()
        with open(self.html_path, "r", encoding="utf-8") as f:
            self.html_template = f.read()
    
    def format(self, fmts:List[Fmt]) -> 'Template':
        # Start fresh from templates each time
        self.js_text = self.js_template
        self.html_text = self.html_template
        
        # Apply replacements to both JS and HTML
        for fmt in fmts:
            self.js_text = fmt.format(self.js_text)
            self.html_text = fmt.format(self.html_text)
        return self

    def html(self) -> str:
        return self.html_text

    def js(self) -> str:
        return self.js_text

    def write_all(self):
        with open(self.html_path, "w", encoding="utf-8") as f:
            f.write(self.html())
        with open(self.js_path, "w", encoding="utf-8") as f:
            f.write(self.js())

    def refetch(self):
        with open(self.js_path, "r", encoding="utf-8") as f:
            self.js_template = f.read()
        with open(self.html_path, "r", encoding="utf-8") as f:
            self.html_template = f.read()
        return self
