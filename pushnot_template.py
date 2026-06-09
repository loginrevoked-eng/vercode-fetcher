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
    def __init__(self, path: str):
        self.path = path
        self.text = ""
        with open(self.path, "r") as f:
            self.text = f.read()
    
    def format(self, fmts:List[Fmt]) -> str:
        text = self.text
        for fmt in fmts:
            text = fmt.format(text)
        return text