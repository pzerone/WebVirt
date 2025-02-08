from typing import Optional
import datetime
from sqlmodel import Field, SQLModel
from app.database.main import engine


class DBVirtualMachine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vmid: int
    name: str
    core_count: int
    memory: int
    port: int
    owner: str
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
    )
    expiry: datetime.datetime = Field()


SQLModel.metadata.create_all(engine)
