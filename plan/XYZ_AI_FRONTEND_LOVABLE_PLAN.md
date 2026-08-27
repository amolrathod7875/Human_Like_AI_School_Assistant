# XYZ AI — Lovable Frontend Master Plan

## 0. Purpose

Build the complete XYZ AI frontend using **Lovable AI** and deploy it on **Vercel**.

The frontend must present XYZ AI as a polished, premium, human-like school assistant for Students, Parents, Teachers, and Principal / School Management.

The backend remains the source of truth for identity, permissions, school data, AI decisions, tool execution, and conversation persistence.

---

# 1. Locked Frontend Stack

```text
Frontend Builder      Lovable AI
Frontend Hosting      Vercel
Authentication        Firebase Authentication
Backend               Python + FastAPI
Database              Firebase Firestore
LLM                   Cohere
Voice                 Vapi
Avatar                Frontend-based interactive avatar
```

RAG and Vector Database are not required for V1.

---

# 2. Product Design Direction

The product should feel like a **premium AI product for a modern school ecosystem**, not a generic ERP dashboard.

Design priorities:

- strong typography
- clear visual hierarchy
- generous spacing
- subtle motion
- premium surfaces
- restrained gradients
- responsive layouts
- high-quality empty/loading/error states
- consistent component system

Avoid:

- excessive rounded cards
- excessive shadows
- random gradients
- noisy dashboards
- too many colors
- unnecessary animation
- generic template layouts

---

# 3. Color System

## Dark Mode — Orange + Black

```text
Background       #050505
Surface           #0B0B0B
Elevated Surface  #111111
Primary Accent    #FF6A00
Secondary Orange  #FF8A3D
Primary Text      #FFFFFF
Secondary Text    #A7A7A7
Border            #242424
Success           #22C55E
Warning           #F59E0B
Error             #EF4444
```

Orange should be used mainly for:

- primary CTAs
- active navigation
- AI assistant accents
- progress indicators
- important interaction states
- selected states

Do not flood the UI with orange.

## Light Mode — Blue + White

```text
Background       #FFFFFF
Surface           #F8FAFC
Elevated Surface  #FFFFFF
Primary Accent    #2563EB
Secondary Blue    #3B82F6
Primary Text      #0F172A
Secondary Text    #64748B
Border            #E2E8F0
Success           #16A34A
Warning           #D97706
Error             #DC2626
```

The light theme should feel:

- clean
- trustworthy
- academic
- professional
- modern

---

# 4. Theme System

Support:

```text
Light
Dark
System
```

Requirements:

- smooth theme transition
- preserve current route
- preserve user state
- no layout shift
- consistent component colors
- avatar and charts respect the current theme

Keep theme tokens centralized.

---

# 5. Typography

Use a modern sans-serif system.

Hierarchy:

```text
Display
H1
H2
H3
Body
Small
Caption
```

Use large typography for landing-page storytelling and concise typography for dashboards.

Avoid too many font sizes.

---

# 6. Global Motion System

Use motion for feedback and hierarchy.

Recommended:

```text
Micro-interactions   150–250ms
Panel transitions    250–450ms
Hero/scroll motion   slower, smooth
```

Use:

- opacity
- transform
- scale
- subtle elevation
- spring-like transitions

Avoid:

- bouncing UI
- constant motion
- distracting parallax
- animation that blocks interaction

Support `prefers-reduced-motion`.

---

# 7. Hover Effects

Hover effects are required wherever an element is meaningfully interactive.

## Buttons

Use:

```text
slight scale
subtle brightness
soft shadow/glow
```

Target:

```text
scale ≈ 1.02
transition ≈ 180–220ms
```

## Interactive Cards

Use:

```text
translateY(-2px to -4px)
stronger border/accent
slightly stronger shadow
```

Only apply this to clickable cards.

## Navigation

Hover:

- text/icon color transition
- subtle background highlight

Active:

- accent color
- indicator
- optional subtle icon movement

## Chat Controls

Do not animate entire message bubbles on hover.

Only interactive controls should react:

- copy
- speaker
- retry
- feedback
- menu

---

# 8. Accessibility

Support:

- keyboard navigation
- visible focus states
- semantic HTML
- readable contrast
- reduced motion
- accessible form labels
- accessible buttons/icons
- loading/error states

Never communicate information through hover alone.

---

# 9. Routes

Recommended route structure:

```text
/
├── Landing
├── /login
├── /signup
│
├── /app
│   ├── /dashboard
│   ├── /assistant
│   ├── /attendance
│   ├── /conversations
│   ├── /profile
│   └── /settings
│
├── /teacher
│   ├── /dashboard
│   ├── /attendance
│   └── /assistant
│
├── /principal
│   ├── /dashboard
│   ├── /analytics
│   └── /assistant
│
└── /support
```

Exact route names may be adjusted once the backend API is finalized.

---

# 10. Landing Page — Overall Goal

The landing page should communicate:

> XYZ AI is a human-like AI school assistant that connects students, parents, teachers, and school management.

It should feel like a **premium AI/SaaS product site**.

---

# 11. Landing Page — Scrollytelling

Use a **scroll-linked storytelling experience**.

The page should feel like one continuous narrative, not a collection of unrelated sections.

Suggested sequence:

```text
1. Hero
   ↓
2. School communication problem
   ↓
3. Meet XYZ AI
   ↓
4. Four roles
   ↓
5. AI chat intelligence
   ↓
6. Voice + Avatar
   ↓
7. Security
   ↓
8. Multilingual support
   ↓
9. Human escalation
   ↓
10. Final CTA
```

Scroll should progressively reveal or transform visuals.

Use:

- opacity transitions
- scale
- horizontal movement
- pinned visual elements where useful
- progress indicators
- subtle parallax
- animated connectors

Do not lock scrolling or make the experience frustrating.

Support reduced-motion mode.

---

# 12. Landing Hero

Suggested direction:

```text
A smarter way to connect
every member of the school.

Meet XYZ AI — a human-like school assistant
for students, parents, teachers and school leaders.
```

Primary CTA:

```text
Try XYZ AI
```

Secondary CTA:

```text
See How It Works
```

Hero visual:

- AI assistant/avatar
- conversation preview
- subtle ambient glow
- dark mode orange/black styling
- light mode blue/white styling

Do not overload the hero with floating objects.

---

# 13. Problem Storytelling Section

Show fragmented school communication.

Example:

```text
Student ─┐
Parent  ─┼── fragmented communication
Teacher ─┤
Principal┘

        ↓

      XYZ AI
```

Use scroll progression to visually move from fragmented communication to one intelligent assistant.

---

# 14. Four Roles Section

Introduce:

```text
Student
Parent
Teacher
Principal
```

Each should have:

- icon/avatar
- description
- persona tone
- example user prompt

Examples:

```text
Student:
"What is my attendance?"
```

```text
Parent:
"How much attendance does my child have?"
```

```text
Teacher:
"Mark Rahul absent today."
```

```text
Principal:
"What is the overall attendance?"
```

Keep the examples aligned with the assignment.

---

# 15. AI Assistant Showcase

Create an animated sequence showing that XYZ AI is not just a chatbot.

Example:

```text
Parent:
How much attendance does my child have?

       ↓

XYZ AI:
Checking Rahul's attendance...

       ↓

Authorized tool action

       ↓

XYZ AI:
Rahul currently has 91.2% attendance.
```

Make the internal process visually understandable without exposing technical secrets or chain-of-thought.

Use friendly activity labels such as:

```text
Checking attendance...
Checking your child's record...
Preparing your answer...
```

---

# 16. Voice + Avatar Landing Section

Show:

```text
Speak
 ↓
Understand
 ↓
Act
 ↓
Respond
```

Visual elements:

- microphone
- waveform
- avatar
- speaking state
- response bubble

Avatar states:

```text
IDLE
LISTENING
THINKING
SPEAKING
```

The waveform should animate only while voice is active.

---

# 17. Security Section

Security should be presented as a product capability.

Show:

```text
Identity verification
Role protection
Authorized actions
Protected data
Prompt-injection resistance
```

Visual flow:

```text
User
 ↓
Identity
 ↓
Permission
 ↓
Authorized Tool
 ↓
School Data
```

Do not expose actual prompts, credentials, or internal implementation details.

---

# 18. Multilingual Section

Show support for all required languages:

```text
English
Hindi
Tamil
Telugu
Marathi
Bengali
Gujarati
Punjabi
Kannada
Malayalam
Urdu
```

Use animated language chips or a flowing selector.

Keep the visual presentation elegant and readable.

---

# 19. Human Escalation Section

Show that XYZ AI knows when a human should take over.

Example:

```text
Parent:
I want to speak with my child's teacher.

XYZ AI:
Of course.
Would you like me to request a call?

[Request Call]
```

Then show:

```text
AI
 ↓
Human Support
```

Communicate trust and transparency.

---

# 20. Final Landing CTA

Example direction:

```text
Bring a more human school experience
to every conversation.
```

Buttons:

```text
Try XYZ AI
Explore the Assistant
```

Make this section visually strong and minimal.

---

# 21. Authentication Screens

Create:

```text
/login
/signup
```

Use Firebase Authentication.

## Login

Fields:

- email
- password

## Signup

Fields:

- name
- email
- password
- role where appropriate

Important:

Frontend role selection is not authoritative.

The backend determines the user's actual application role.

---

# 22. Application Shell

Use a reusable shell.

```text
┌───────────────────────────────────────────────┐
│ Top Bar                                       │
├──────────────┬────────────────────────────────┤
│ Sidebar      │ Main Content                   │
│              │                                │
│ Dashboard    │                                │
│ Assistant    │                                │
│ Attendance   │                                │
│ Conversations│                                │
│ Profile      │                                │
│ Settings     │                                │
└──────────────┴────────────────────────────────┘
```

Responsive behavior:

- desktop sidebar
- tablet collapsible sidebar
- mobile drawer/bottom navigation

---

# 23. Student Dashboard

Show:

- attendance
- recent conversations
- assistant shortcut
- academic summary where backend data exists
- notifications where supported

Attendance example:

```text
91.2%
Attendance
```

Use loading skeletons before data arrives.

Only clickable cards should have hover elevation.

---

# 24. Parent Dashboard

Show:

- children
- each child's attendance
- recent conversations
- assistant CTA
- support/contact actions

Allow switching between authorized children.

The frontend must not assume a child ID is valid; the backend remains authoritative.

---

# 25. Teacher Dashboard

Show:

- assigned classes
- attendance actions
- recent activity
- assistant
- quick attendance controls

Buttons should have:

```text
hover
pressed
loading
success
failure
```

Do not use a hover animation on destructive/critical controls that could imply they have already executed.

---

# 26. Principal Dashboard

Focus on analytics.

Show backend-provided:

- overall attendance
- class-level attendance
- trends
- summary metrics
- management AI assistant

Charts should use real API data.

Do not create fake analytics that look like real school statistics.

---

# 27. AI Assistant Page

This is the most important product screen.

Suggested layout:

```text
┌───────────────────────────────────────────────┐
│ XYZ AI                         Avatar / Voice │
├───────────────┬───────────────────────────────┤
│ Conversations │ Chat                          │
│               │                               │
│ Today         │ AI messages                   │
│ Yesterday     │ User messages                 │
│               │                               │
│               │                               │
│               │───────────────────────────────│
│               │ Input + Mic + Send            │
└───────────────┴───────────────────────────────┘
```

Desktop can use a three-column layout if the avatar is active:

```text
Conversation | Chat | Avatar
```

Mobile should prioritize chat.

---

# 28. Chat UX

Support:

- user messages
- AI messages
- timestamps
- typing/processing state
- tool activity status
- copy
- speaker
- retry
- feedback

Never show raw chain-of-thought.

Use friendly tool status text:

```text
Checking attendance...
Checking your child's record...
Preparing your answer...
```

Message animation should be subtle.

---

# 29. Voice UX

Voice states:

```text
IDLE
LISTENING
PROCESSING
SPEAKING
ERROR
```

Controls:

```text
Start speaking
Stop
Mute
Replay
```

Use waveform animation while listening/speaking.

Make the active microphone state visually obvious.

---

# 30. AI Avatar

Avatar is frontend-owned.

States:

```text
IDLE
LISTENING
THINKING
SPEAKING
```

Backend may return:

```json
{
  "avatar": {
    "state": "speaking",
    "emotion": "friendly"
  }
}
```

Possible animations:

- blinking
- subtle head movement
- mouth movement during speech
- listening glow
- thinking pulse

Prefer a polished stylized character over an uncanny hyper-realistic avatar.

---

# 31. Conversation History

Dedicated conversation sidebar.

Each item:

- title
- timestamp
- preview
- selected state

Support:

- new conversation
- open conversation
- archive/delete if supported by backend

Hover:

- background highlight
- accent indicator
- action menu

---

# 32. Attendance Screens

Role-aware UI.

## Student

Read-only attendance.

## Parent

Read-only attendance for authorized children.

## Teacher

Interactive attendance marking.

## Principal

Management analytics.

Frontend visibility is a UX convenience only. Backend permissions remain authoritative.

---

# 33. Escalation UI

When human support is appropriate:

```text
Talk to Teacher
Contact School Management
```

Then confirmation:

```text
Would you like to request a call?

[Request Call]
[Cancel]
```

After backend response:

Success:

```text
Your request has been submitted.
```

Failure:

```text
We could not submit the request.
Please try again.
```

Never show success merely because the user clicked a button.

---

# 34. Loading States

Every async action should have meaningful feedback.

Examples:

```text
Checking attendance...
Sending message...
Connecting voice...
Starting assistant...
Submitting request...
```

Use skeletons for dashboard sections.

---

# 35. Error Handling

Friendly messages:

```text
Something went wrong.
Please try again.

Your session has expired.
Please sign in again.

We couldn't connect to the assistant.
Please try again in a moment.

Your request could not be completed.
```

Never expose raw stack traces or raw provider errors to users.

---

# 36. Frontend API Client

Centralize API access.

Recommended:

```text
src/api/
├── client
├── auth
├── ai
├── attendance
├── conversations
├── escalation
└── voice
```

The common client handles:

- backend base URL
- Firebase ID token
- common headers
- JSON parsing
- error normalization
- request IDs if returned
- safe retry behavior

Do not scatter raw fetch calls across every component.

---

# 37. Firebase Frontend Integration

Flow:

```text
Firebase User
   ↓
getIdToken()
   ↓
Authorization: Bearer <token>
   ↓
FastAPI
```

Use Firebase for:

- login
- signup
- session persistence
- logout
- ID token retrieval

Never create a second frontend JWT system.

---

# 38. Role-Aware UI

The UI may hide irrelevant features.

Example:

Student:

```text
No mark-attendance control
```

Teacher:

```text
Mark attendance available
```

Principal:

```text
School analytics available
```

Again, backend authorization is the actual security boundary.

---

# 39. Responsive Design

Support:

```text
mobile
tablet
desktop
large desktop
```

Pay special attention to:

- chat
- avatar
- voice controls
- dashboard tables
- analytics charts
- sidebar

Mobile priorities:

```text
chat first
voice controls accessible
avatar compact
no horizontal scrolling
```

---

# 40. Component Structure

Recommended:

```text
src/components/
├── ui/
├── layout/
├── landing/
├── auth/
├── dashboard/
├── assistant/
├── chat/
├── voice/
├── avatar/
├── attendance/
├── escalation/
├── analytics/
└── shared/
```

Keep reusable components isolated from page-specific logic.

---

# 41. State Management

Separate:

```text
Auth State
UI State
Conversation State
AI State
Voice State
Dashboard Data
```

Do not put the entire application into one giant global store.

---

# 42. Frontend Security

Never put these in browser-accessible source:

- Cohere server API key
- Vapi private/server secret
- Firebase Admin private key
- Firestore server credentials

The frontend may use Firebase client configuration as required by Firebase Authentication.

Never call Cohere directly from the browser.

Never perform privileged Firestore operations directly from the browser.

---

# 43. Premium Interaction Details

Use subtle interaction throughout.

## Sidebar

Hover:

```text
small icon movement
soft background
```

## Primary CTA

Hover:

```text
scale 1.02
soft accent glow
```

## Interactive Cards

Hover:

```text
translateY(-3px)
slightly stronger border
```

## Avatar

Hover:

```text
subtle glow
```

Do not animate every element.

---

# 44. Dark Mode Premium Treatment

Dark mode should feel like:

```text
black base
orange accent
soft gray surfaces
white typography
```

Use sparingly:

- orange ambient glow
- soft glass panels
- thin gray borders
- subtle accent gradients

Hero direction:

```text
black background
↓
subtle orange ambient glow
↓
AI avatar
↓
conversation preview
```

---

# 45. Light Mode Premium Treatment

Light mode should feel like:

```text
white base
blue accents
soft gray surfaces
dark navy typography
```

Use:

- clean cards
- soft blue highlights
- subtle gradients
- generous whitespace

Both themes must feel like the same product.

---

# 46. Scrollytelling Implementation Guidance

Use scroll position to control:

- opacity
- scale
- horizontal movement
- element reveal
- progress
- pinned visual state

Suggested timeline:

```text
0–15%     Hero
15–30%    Problem
30–45%    Roles
45–60%    AI intelligence
60–72%    Voice/avatar
72–84%    Security
84–92%    Multilingual
92–100%   CTA
```

Do not make the scroll feel locked.

Use transform/opacity animations for performance.

Support reduced motion.

---

# 47. Landing Performance

Scrollytelling must remain fast.

Requirements:

- optimize images
- lazy-load heavy content
- avoid giant videos unless necessary
- avoid excessive WebGL
- minimize DOM complexity
- prefer GPU-friendly transform/opacity animations
- test on mobile

---

# 48. Backend API Contract

Primary endpoint:

```http
POST /api/v1/ai/chat
```

Request:

```json
{
  "conversation_id": "conv_001",
  "message": "How much attendance does my child have?"
}
```

Headers:

```http
Authorization: Bearer <firebase-id-token>
Content-Type: application/json
```

Response:

```json
{
  "success": true,
  "data": {
    "conversation_id": "conv_001",
    "message_id": "msg_001",
    "text": "Rahul currently has 91.2% attendance.",
    "language": "en-IN",
    "persona": "parent",
    "avatar": {
      "state": "speaking",
      "emotion": "friendly"
    }
  }
}
```

The exact contract must follow the final backend contract after wiring.

---

# 49. Frontend Development Order

## Phase 1 — Design System

```text
1. Theme
2. Typography
3. Color tokens
4. Buttons
5. Inputs
6. Cards
7. Navigation
8. Toasts
9. Dialogs
10. Loading states
```

## Phase 2 — Landing

```text
11. Hero
12. Scrollytelling engine
13. Problem
14. Roles
15. AI showcase
16. Voice/avatar
17. Security
18. Languages
19. Human escalation
20. CTA
```

## Phase 3 — Authentication

```text
21. Login
22. Signup
23. Firebase session
24. Protected routes
```

## Phase 4 — App Shell

```text
25. Sidebar
26. Header
27. Theme switcher
28. Notifications
29. Responsive navigation
```

## Phase 5 — Dashboards

```text
30. Student
31. Parent
32. Teacher
33. Principal
```

## Phase 6 — Assistant

```text
34. Chat
35. History
36. Voice UI
37. Avatar
38. Tool status
39. Escalation UI
```

## Phase 7 — Backend Wiring

```text
40. API client
41. Firebase token handling
42. Chat API
43. Attendance API
44. Conversation API
45. Escalation API
46. Vapi integration
```

## Phase 8 — Polish

```text
47. Responsive fixes
48. Accessibility
49. Hover states
50. Micro-interactions
51. Performance
52. Error states
53. Final visual consistency
```

---

# 50. Lovable Build Rules

When implementing this plan in Lovable:

1. Build the design system first.
2. Build the landing page with mock data first.
3. Build application screens with mock API responses initially.
4. Keep API calls behind a single API client.
5. Do not hardcode school data into components.
6. Keep theme tokens centralized.
7. Keep landing animations separate from dashboard logic.
8. Use scroll-linked storytelling for the landing page.
9. Support reduced motion.
10. Use hover effects only where interaction is meaningful.
11. Do not expose backend/provider secrets.
12. Do not call Cohere directly from the browser.
13. Do not perform privileged Firestore operations from the browser.
14. Do not invent backend endpoints.
15. Keep avatar rendering frontend-owned and consume backend avatar-state metadata.
16. Maintain responsive behavior throughout development.
17. Prefer reusable components over page-specific duplicates.

---

# 51. Final Frontend Architecture

```text
Lovable Frontend
│
├── Design System
│   ├── Theme
│   ├── Typography
│   ├── Colors
│   ├── Components
│   └── Motion
│
├── Landing
│   └── Scrollytelling
│
├── Authentication
│   └── Firebase Auth
│
├── Application Shell
│   ├── Student
│   ├── Parent
│   ├── Teacher
│   └── Principal
│
├── AI Assistant
│   ├── Chat
│   ├── Conversation History
│   ├── Voice
│   ├── Avatar
│   └── Escalation
│
├── Dashboards
│   ├── Attendance
│   └── Analytics
│
└── API Layer
    ├── Auth
    ├── AI
    ├── Conversations
    ├── Attendance
    ├── Escalation
    └── Voice
```

---

# 52. Final Frontend Acceptance Criteria

## Branding

- dark mode uses orange + black
- light mode uses blue + white
- theme switching works
- typography is consistent

## Landing

- premium hero
- scrollytelling experience
- all core AI capabilities explained
- responsive
- reduced-motion supported
- performance acceptable

## Authentication

- Firebase login
- Firebase logout
- session persistence
- protected routes

## Roles

- student dashboard
- parent dashboard
- teacher dashboard
- principal dashboard

## Assistant

- chat
- history
- voice UI
- avatar states
- tool status
- escalation UI
- loading/error handling

## Backend Integration

- Firebase ID token sent to backend
- AI chat connected
- attendance connected
- conversations connected
- escalation connected
- Vapi connected

## UX

- intentional hover states
- focus states
- responsive layouts
- smooth transitions
- consistent spacing
- no false success states

---

# 53. Final Product Principle

The frontend should make XYZ AI **feel premium and human**, while the backend makes it **secure and trustworthy**.

```text
Frontend
→ premium experience

Backend
→ intelligence + authorization + actions

Firebase
→ identity

Firestore
→ school data

Cohere
→ language intelligence

Vapi
→ voice

Avatar
→ human-like visual interaction
```

The frontend and backend should remain loosely coupled through stable API contracts.

The frontend should never replace backend security, and the backend should not dictate unnecessary visual implementation details.
