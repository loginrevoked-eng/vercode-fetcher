"""
Clean template system - generates HTML on-demand without global state mutation
"""
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Fmt:
    placeholder: str
    replacement: str

    def format(self, text: str) -> str:
        return text.replace(f"{{{self.placeholder}}}", self.replacement)


class TemplateRenderer:
    """Stateless template renderer - loads templates once, renders per-request"""
    
    def __init__(self, html_template_path: str = "static/maglinks.html"):
        self.html_template_path = html_template_path
        with open(self.html_template_path, "r", encoding="utf-8") as f:
            self.html_template = f.read()
    
    def render(self, replacements: Dict[str, str]) -> str:
        """Render HTML with replacements without mutating template"""
        html = self.html_template
        
        for placeholder, replacement in replacements.items():
            html = html.replace(f"{{{placeholder}}}", replacement)
        
        return html
    
    def reload_template(self):
        """Reload template from disk"""
        with open(self.html_template_path, "r", encoding="utf-8") as f:
            self.html_template = f.read()
