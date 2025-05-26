from dataclasses import dataclass

@dataclass
class Files:
    client: str
    dashboard: str
    console: str
    output: str
    carrier: str = "Atlasat" # default carrier, if not specified
