# DevMentor AI 🚀

DevMentor AI is a state-of-the-art, AI-powered learning platform designed to provide a personalized, adaptive, and interactive educational experience. It goes beyond static courses by dynamically generating roadmaps, testing knowledge with scenario-based quizzes, and providing a 24/7 AI mentor.

![DevMentor AI Dashboard](https://raw.githubusercontent.com/devsoni0419/project1/main/preview.png) *(Placeholder for dashboard screenshot)*

## ✨ Key Features

- **🎯 Personalized Roadmaps**: Generate comprehensive, multi-day learning paths tailored to your specific career goals or skill interests.
- **🧠 Adaptive Intelligence**: The platform monitors your progress and performance, identifying "Weak Topics" and suggesting roadmap adjustments in real-time.
- **📝 Scenario-Based Quizzes**: Every task completion triggers an AI-generated quiz that focuses on practical application rather than rote memorization.
- **💬 Dev Studio AI Assistant**: A dedicated conversational workspace for deep-diving into complex topics, debugging code, and resolving doubts.
- **⏰ Smart Study Reminders**: Integrated Pushover notifications that nudge you at your scheduled study times to ensure consistent progress.
- **📊 Real-time Dashboard**: Track your completion status, visualize learning gaps, and receive AI-driven recommendations.
- **🔐 Secure Authentication**: Full user management system to persist your progress across sessions.

## 🛠️ Tech Stack

### Frontend
- **HTML5 & CSS3**: Custom, modern UI with glassmorphism and responsive design.
- **JavaScript (Vanilla ES6+)**: Clean, modular logic for API interactions and dynamic DOM updates.

### Backend
- **FastAPI (Python)**: High-performance, asynchronous web framework.
- **SQLAlchemy & SQLite**: Robust database management for users, goals, and tasks.
- **Pydantic**: Strict data validation and schema enforcement.
- **Google Gemini AI**: Powering the roadmap generation, quiz logic, and mentor assistance.

### Deployment & DevOps
- **Vercel**: Unified deployment for both static frontend and serverless backend functions.
- **Pushover API**: External notification service for study reminders.

## 📂 Project Structure

```text
├── backend/                # FastAPI Application
│   ├── routers/            # API endpoints (Auth, Goals, Tasks, Assistant)
│   ├── services/           # AI logic and external service integrations
│   ├── models.py           # Database models (SQLAlchemy)
│   └── main.py             # Server entry point & Background tasks
├── frontend/               # Static Web Files
│   ├── css/                # Custom stylesheets
│   ├── js/                 # API services and UI logic
│   └── index.html          # Main Application Dashboard
├── api/                    # Vercel Serverless Functions
├── scripts/                # Utility and Database setup scripts
├── vercel.json             # Deployment configuration
└── requirements.txt        # Python dependencies
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- A standard web browser
- (Optional) Pushover account for notifications

### 1. Backend Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/devsoni0419/project1.git
   cd project1
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables (`.env`):
   ```env
   # Example .env contents
   DATABASE_URL=sqlite:///./devmentor.db
   GEMINI_API_KEY=your_key_here
   PUSHOVER_USER_KEY=your_pushover_key
   PUSHOVER_API_TOKEN=your_pushover_token
   ```
5. Run the server:
   ```bash
   uvicorn backend.main:app --reload
   ```

### 2. Frontend Setup
1. Open `frontend/index.html` in your browser via a local server (like VS Code Live Server).
2. Ensure the API configuration in `frontend/js/api_config.js` (if applicable) points to `http://localhost:8000`.

## 📈 Roadmap
- [x] Core AI Roadmap Generation
- [x] Logic-based Quiz Engine
- [x] Real-time Study Reminders
- [ ] Mobile App (PWA) Integration
- [ ] Peer-to-Peer Learning Groups
- [ ] Collaborative Coding Sandboxes

## 📄 License
This project is licensed under the MIT License.

---
*Built with ❤️ for the next generation of developers.*
