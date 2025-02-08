from pydantic import BaseModel

class VirtualMachine(BaseModel):
    name: str = ""
    core_count: int
    memory: int
    duration: float | None

