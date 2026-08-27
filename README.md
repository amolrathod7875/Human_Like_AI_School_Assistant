# Human_Like_AI_School_Assistant

An AI-powered school assistant backend that enables natural language interactions for students, parents, teachers, and school administrators. The system provides attendance tracking, conversation management, and human escalation capabilities through voice and text interfaces.

## Overview

This is a FastAPI-based backend that uses:
- **Database**: Google Cloud Firestore (NoSQL document database)
- **Authentication**: Firebase Authentication
- **AI**: Cohere LLM integration for natural language processing
- **Voice**: Vapi integration for voice interactions
- **Avatar**: Frontend-driven avatar with backend metadata contract

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  (FastAPI - /api/v1/chat, /api/v1/voice, /api/v1/avatar)   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                           │
│  (Business Logic - attendance, conversation, escalation)    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Repository Layer                          │
│  (FirestoreRepository[T] - Generic typed data access)     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Firestore Database                        │
│  (users, students, classes, attendance, conversations, etc) │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

The system uses **Google Cloud Firestore** as its NoSQL document database. All collections are accessed through typed repository classes in `app/repositories/firestore/`.

### Collection Overview

| Collection | Repository | Description |
|------------|------------|-------------|
| `users` | `UserRepository` | User profiles with roles and relationships |
| `students` | `StudentRepository` | Student-specific profiles |
| `classes` | `ClassRepository` | Class/grade definitions |
| `attendance` | `AttendanceRepository` | Daily attendance records |
| `conversations` | `ConversationRepository` | Conversation headers |
| `conversations/{id}/messages` | `MessageRepository` | Messages within conversations (subcollection) |
| `support_requests` | `SupportRequestRepository` | Escalation/support requests |
| `audit_logs` | `AuditLogRepository` | Audit trail for actions |

---

### `users` Collection

**Document ID**: Application-assigned ID (not Firebase UID)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `firebase_uid` | `string` | Firebase Authentication UID |
| `name` | `string` | Display name |
| `email` | `string` (optional) | Email address |
| `role` | `enum` | STUDENT, PARENT, TEACHER, PRINCIPAL |
| `is_active` | `boolean` | Account status |
| `student_id` | `string` (optional) | Linked student profile ID (for parents) |
| `parent_ids` | `string[]` | Linked parent IDs (for students) |
| `class_id` | `string` (optional) | Assigned class ID (for students/teachers) |
| `child_ids` | `string[]` | Children IDs (for parents) |
| `teacher_class_ids` | `string[]` | Class IDs taught by this teacher |

**Indexes**: Queryable by `firebase_uid`

---

### `students` Collection

**Document ID**: Application-assigned student ID

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `user_id` | `string` | Associated user profile ID |
| `name` | `string` | Student full name |
| `class_id` | `string` (optional) | Enrolled class ID |
| `parent_ids` | `string[]` | Parent user IDs with access |
| `roll_number` | `string` (optional) | School roll number |
| `is_active` | `boolean` | Active status |

**Indexes**: Queryable by `class_id`, `parent_ids` (array contains), `name`

---

### `classes` Collection

**Document ID**: Application-assigned class ID

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `name` | `string` | Class name (e.g., "Class 5-A") |
| `grade` | `string` (optional) | Grade level |
| `teacher_id` | `string` (optional) | Class teacher user ID |
| `student_ids` | `string[]` | Enrolled student IDs |

**Indexes**: Queryable by `teacher_id`

---

### `attendance` Collection

**Document ID**: Application-assigned ID

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `student_id` | `string` | Student ID |
| `class_id` | `string` | Class ID |
| `date` | `string` | ISO date (YYYY-MM-DD) |
| `status` | `enum` | PRESENT, ABSENT, LATE |
| `marked_by` | `string` (optional) | User ID who marked attendance |

**Indexes**: Queryable by `student_id`, `class_id`, `date`, `student_id+date`, `student_id+date range`

---

### `conversations` Collection

**Document ID**: Application-assigned conversation ID

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `user_id` | `string` | Conversation owner ID |
| `title` | `string` (optional) | Conversation title |
| `role` | `enum` (optional) | STUDENT, PARENT, TEACHER, PRINCIPAL |
| `language` | `string` (optional) | Language code (e.g., "en-IN") |
| `metadata` | `object` | Additional metadata |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last update timestamp |

**Indexes**: Queryable by `user_id`

---

### `conversations/{conversation_id}/messages` Subcollection

**Document ID**: Application-assigned message ID

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `role` | `enum` | user, assistant, system, tool |
| `content` | `string` | Message content |
| `timestamp` | `datetime` | Message timestamp |
| `intent` | `string` (optional) | Detected intent |
| `entities` | `object` | Extracted entities |
| `tool_calls` | `any[]` | Tool call requests |
| `tool_results` | `any[]` | Tool execution results |
| `metadata` | `object` | Additional metadata |

---

### `support_requests` Collection

**Document ID**: Application-assigned ID

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `user_id` | `string` | Requesting user ID |
| `requested_by` | `string` | Requester identifier |
| `requester_role` | `string` | Role of requester |
| `target_type` | `enum` | TEACHER, MANAGEMENT |
| `target_id` | `string` (optional) | Target user ID |
| `student_id` | `string` (optional) | Related student ID |
| `reason` | `string` | Reason for request |
| `status` | `enum` | PENDING, CONFIRMED, FAILED, CANCELLED |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last update timestamp |

**Indexes**: Queryable by `user_id`, `status`

---

### `audit_logs` Collection

**Document ID**: Application-assigned ID

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Document ID |
| `actor_id` | `string` | User performing action |
| `action` | `string` | Action type |
| `target` | `string` (optional) | Target resource |
| `metadata` | `object` | Additional context |
| `timestamp` | `datetime` | Action timestamp |

---

## Data Relationships

```
┌─────────────┐       ┌─────────────┐
│    users    │       │  students   │
├─────────────┤       ├─────────────┤
│ role        │       │ user_id     │◄────┐
│ student_id  │◄──┐   │ class_id    │─────┼─────┐
│ parent_ids  │   │   └─────────────┘     │     │
│ child_ids   │   │                       │     │
│ class_id    │───┘                       │     │
│ teacher_    │───────────────────────────┘     │
│ class_ids   │                                │
└─────────────┘                                │
      │                                        │
      │          ┌─────────────┐               │
      │          │   classes   │               │
      │          ├─────────────┤               │
      └──────────► teacher_id  │◄──────────────┘
                 │ student_ids │
                 └─────────────┘
                        ▲
                        │
                 ┌─────────────┐
                 │ attendance  │
                 ├─────────────┤
                 │ student_id  │
                 │ class_id    │
                 │ date        │
                 └─────────────┘
```

## Role-Based Access

| Role | Permissions |
|------|-------------|
| STUDENT | View own attendance, participate in conversations |
| PARENT | View children's attendance, participate in conversations |
| TEACHER | Mark attendance, view class attendance, participate in conversations |
| PRINCIPAL | School-wide access, view all attendance data |

## API Endpoints

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/ai/chat` | AI chat interaction |
| POST | `/api/v1/voice/webhook` | Vapi voice webhook |
| POST | `/api/v1/voice/respond` | Voice response |
| GET | `/api/v1/avatar/contract` | Avatar metadata spec |
| POST | `/api/v1/avatar/contract` | Get avatar response |

### Attendance Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/attendance/me` | Get own attendance |
| GET | `/api/v1/attendance/child/{child_id}` | Get child's attendance |
| GET | `/api/v1/attendance/overall` | School-wide attendance |
| POST | `/api/v1/attendance/mark` | Mark attendance |

### Escalation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/escalation/request` | Create support request |
| GET | `/api/v1/escalation/{request_id}` | Get request status |

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_NAME` | xyz-ai-backend | App title |
| `SERVICE_NAME` | xyz-ai-backend | Service identifier |
| `ENVIRONMENT` | development | Runtime environment |
| `DEBUG` | false | Enable debug mode |
| `API_V1_PREFIX` | /api/v1 | API prefix |
| `BACKEND_CORS_ORIGINS` | ["*"] | CORS origins |
| `LOG_LEVEL` | INFO | Logging level |

## Running Locally

```powershell
conda activate vidhoor
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Testing

```powershell
pytest
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # App factory and middleware
│   ├── core/                # Config, errors, logging, responses
│   ├── api/v1/              # API routes
│   ├── services/            # Business logic
│   ├── repositories/        # Data access layer
│   ├── providers/           # External service adapters
│   ├── schemas/             # Pydantic models
│   ├── ai/                  # AI orchestration, tools, persona
│   ├── auth/                # Authentication and authorization
│   └── security/            # Security utilities
├── tests/                   # Test suite
├── requirements.txt
└── README.md
```
