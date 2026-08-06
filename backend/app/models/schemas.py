from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    OWNER = "owner"
    WIFE = "wife"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    CSV = "csv"
    XLSX = "xlsx"
    WEB = "web"


# ---- Auth / User ----


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: UserRole


# ---- Chat ----


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32000)
    conversation_id: Optional[UUID] = None
    model: Optional[str] = None
    regenerate_message_id: Optional[UUID] = None
    agent_id: Optional[str] = None


class AgentInfoOut(BaseModel):
    id: str
    name: str
    title: str
    description: str
    skills: List[str]
    status: str = "ready"
    icon: str = "bot"


class AgentCatalogResponse(BaseModel):
    agents: List[AgentInfoOut]


class AgentAskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32000)
    conversation_id: Optional[UUID] = None
    model: Optional[str] = None


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    model: Optional[str] = None
    created_at: datetime


class ConversationOut(BaseModel):
    id: UUID
    title: str
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: List[MessageOut] = []


class HistoryResponse(BaseModel):
    conversations: List[ConversationOut]


# ---- Documents ----


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_type: FileType
    file_size: Optional[int] = None
    status: DocumentStatus
    chunk_count: int = 0
    error_message: Optional[str] = None
    source_type: Optional[str] = "upload"
    source_url: Optional[str] = None
    is_shared: bool = False
    created_at: datetime
    updated_at: datetime


class DocumentsResponse(BaseModel):
    documents: List[DocumentOut]


# ---- Memory ----


class MemoryOut(BaseModel):
    id: UUID
    key: Optional[str] = None
    content: str
    category: str = "general"
    created_at: datetime
    updated_at: datetime


class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1)
    key: Optional[str] = None
    category: str = "general"


# ---- Health ----


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str


# ---- Automation ----


class AutomationModuleInfo(BaseModel):
    id: str
    title: str
    description: str
    example: str
    status: str


class AutomationCatalogResponse(BaseModel):
    modules: List[AutomationModuleInfo]


class AutomationStartRequest(BaseModel):
    module: str = Field(..., min_length=2, max_length=40)
    prompt: str = Field(..., min_length=1, max_length=8000)


class AutomationItemOut(BaseModel):
    id: UUID
    run_id: UUID
    item_type: str
    title: str
    content: dict
    status: str
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AutomationRunOut(BaseModel):
    id: UUID
    module: str
    title: str
    prompt: str
    status: str
    plan_summary: Optional[str] = None
    preview: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[AutomationItemOut] = []


class AutomationHistoryItem(BaseModel):
    id: UUID
    module: str
    title: str
    prompt: str
    status: str
    plan_summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AutomationHistoryResponse(BaseModel):
    runs: List[AutomationHistoryItem]


class AutomationItemUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: dict
