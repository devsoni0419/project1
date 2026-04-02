var API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.startsWith('192.168.'))
    ? `http://${window.location.hostname}:8000/api` 
    : "/api";

let currentGoal = null;
let currentTasks = [];
let allRoadmaps = [];
let dialogResolver = null;

document.addEventListener("DOMContentLoaded", () => {
    const userId = localStorage.getItem("userId");
    if (!userId) {
        window.location.href = "login.html";
        return;
    }
    
    document.getElementById("user-greeting").innerText = `Hello, ${localStorage.getItem("username")}`;
    
    // Initial Load
    refreshView();
    
    document.getElementById("goal-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("btn-create-goal");
        const btnText = document.getElementById("btn-text");
        
        btn.disabled = true;
        btnText.innerHTML = 'Generating... <i class="fa-solid fa-circle-notch fa-spin"></i>';
        
        const title = document.getElementById("goal-title").value;
        const hours = document.getElementById("daily-hours").value;
        
        try {
            const res = await fetch(`${API_URL}/goals/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": localStorage.getItem("userId")
                },
                body: JSON.stringify({ title, daily_study_hours: parseFloat(hours) })
            });
            const goal = await res.json();
            selectRoadmap(goal);
        } catch (error) {
            console.error("Error creating goal", error);
            showDialog({
                title: "Connection Error",
                message: "Failed to create goal. Make sure the FastAPI backend is running!",
                type: "alert"
            });
        } finally {
            btn.disabled = false;
            btnText.innerHTML = 'Generate Roadmap <i class="fa-solid fa-wand-magic-sparkles"></i>';
        }
    });
});

async function refreshView() {
    try {
        const res = await fetch(`${API_URL}/goals/`, {
            headers: { "X-User-ID": localStorage.getItem("userId") }
        });
        allRoadmaps = await res.json();
        
        if (allRoadmaps.length > 0 && !currentGoal) {
            showLibrary();
        } else if (currentGoal) {
            await loadActiveRoadmap(currentGoal.id);
        } else {
            showOnboarding();
        }
    } catch(err) {
        showOnboarding();
    }
}

function showLibrary() {
    currentGoal = null;
    document.getElementById("onboarding-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.add("hidden");
    document.getElementById("btn-back-to-library").classList.add("hidden");
    
    const library = document.getElementById("library-section");
    library.classList.remove("hidden");
    
    const grid = document.getElementById("roadmaps-grid");
    grid.innerHTML = "";
    
    allRoadmaps.forEach(goal => {
        const card = document.createElement("div");
        card.className = "roadmap-card glass-card";
        card.onclick = () => selectRoadmap(goal);
        
        const date = new Date(goal.created_at).toLocaleDateString();
        card.innerHTML = `
            <div class="card-icon"><i class="fa-solid fa-route"></i></div>
            <button class="delete-goal-btn" onclick="event.stopPropagation(); deleteGoal(${goal.id})">
                <i class="fa-solid fa-trash-can"></i>
            </button>
            <h4>${goal.title}</h4>
            <p>Started: ${date}</p>
            <div class="card-footer">
                <span><i class="fa-solid fa-clock"></i> ${goal.daily_study_hours}h/day</span>
                <span class="view-btn">Open <i class="fa-solid fa-chevron-right"></i></span>
            </div>
        `;
        grid.appendChild(card);
    });
}

function showOnboarding() {
    currentGoal = null;
    document.getElementById("library-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.add("hidden");
    document.getElementById("onboarding-section").classList.remove("hidden");
    document.getElementById("btn-back-to-library").classList.remove("hidden");
}

async function selectRoadmap(goal) {
    currentGoal = goal;
    document.getElementById("library-section").classList.add("hidden");
    document.getElementById("onboarding-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.remove("hidden");
    document.getElementById("btn-back-to-library").classList.remove("hidden");
    document.getElementById("active-goal-title").innerText = goal.title;
    
    // Add Regenerate Button
    const header = document.getElementById("active-goal-title").parentElement;
    let oldBtn = document.getElementById("btn-regenerate-roadmap");
    if (oldBtn) oldBtn.remove();
    
    const regenBtn = document.createElement("button");
    regenBtn.id = "btn-regenerate-roadmap";
    regenBtn.className = "secondary-btn btn-sm";
    regenBtn.style.marginLeft = "15px";
    regenBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Regenerate Details';
    regenBtn.onclick = () => regenerateRoadmap(goal.id);
    header.appendChild(regenBtn);
    
    // Ensure "My Roadmaps" list is refreshed if we go back later
    const res = await fetch(`${API_URL}/goals/`, {
        headers: { "X-User-ID": localStorage.getItem("userId") }
    });
    allRoadmaps = await res.json();
    
    await loadActiveRoadmap(goal.id);
}

async function loadActiveRoadmap(goalId) {
    try {
        // AGENTIC AI: Check for delays when loading the roadmap
        await fetch(`${API_URL}/tasks/check_delays/${goalId}`, { method: "POST" });
        
        const res = await fetch(`${API_URL}/tasks/?goal_id=${goalId}`);
        currentTasks = await res.json();
        renderTasks();
        updateUI();
        updateInsights();
    } catch(err) {
        console.error("Error loading roadmap tasks", err);
    }
}

function renderTasks() {
    const container = document.getElementById("tasks-container");
    container.innerHTML = "";
    
    currentTasks.forEach(task => {
        const el = document.createElement("div");
        el.className = `task-item ${task.is_completed ? 'completed' : ''}`;
        el.onclick = () => openTaskModal(task);
        
        el.innerHTML = `
            <div class="task-info">
                <span class="day-badge">Day ${task.day_number}</span>
                <h4>${task.topic}</h4>
                <p>${task.description}</p>
            </div>
            <div class="task-status">
                <i class="fa-solid ${task.is_completed ? 'fa-circle-check' : 'fa-circle'}"></i>
            </div>
        `;
        container.appendChild(el);
    });
}

function updateUI() {
    const total = currentTasks.length;
    if (total === 0) return;
    const completed = currentTasks.filter(t => t.is_completed).length;
    const pct = Math.round((completed / total) * 100);
    document.getElementById("overall-progress").style.width = `${pct}%`;
    
    // Fetch real streak from backend if possible, or use currentGoal logic
    // For now we assume the User response in auth has streak, but we'll refresh it if we add a GET /auth/me
}

async function updateInsights() {
    if (!currentGoal) return;
    
    try {
        const res = await fetch(`${API_URL}/tasks/performance/${currentGoal.id}`);
        const data = await res.json();
        
        const panel = document.getElementById("insights-panel");
        const status = document.getElementById("insight-status");
        const desc = document.getElementById("insight-desc");
        const weakList = document.getElementById("weak-topics-list");
        const recoText = document.getElementById("ai-reco-text");
        
        panel.classList.remove("hidden");
        status.innerText = data.status;
        desc.innerText = `Focus status for your ${currentGoal.title} journey.`;
        
        // Render Weak Topics
        weakList.innerHTML = data.weak_topics.length > 0 
            ? data.weak_topics.map(topic => `<li>${topic}</li>`).join('')
            : '<li>Zero weak areas detected! Keep it up.</li>';
            
        // Render AI Recommendation
        recoText.innerText = data.recommendation;
        
        // Agentic styling for status
        const mainCard = status.closest('.insight-card');
        mainCard.style.borderColor = data.status === "Adjustment Recommended" ? "#F59E0B" : "var(--accent-secondary)";
        
    } catch(err) {
        console.error("Error fetching performance insights", err);
    }
}

let activeTask = null;

function openTaskModal(task) {
    activeTask = task;
    document.getElementById("modal-task-title").innerText = `Day ${task.day_number}: ${task.topic}`;
    if(typeof marked !== 'undefined') {
        document.getElementById("modal-task-desc").innerHTML = marked.parse(task.description);
    } else {
        document.getElementById("modal-task-desc").innerText = task.description;
    }
    
    const btn = document.getElementById("btn-complete-task");
    if(task.is_completed) {
        btn.innerHTML = 'Unmark Completed <i class="fa-solid fa-xmark"></i>';
        btn.onclick = () => toggleTaskStatus(task.id, false);
    } else {
        btn.innerHTML = 'Take the Quiz to Complete <i class="fa-solid fa-arrow-right"></i>';
        btn.onclick = () => openQuizModal(task.id);
    }
    
    // Reminder Logic
    const reminderInput = document.getElementById("reminder-time");
    if (reminderInput) {
        reminderInput.value = task.reminder_time ? task.reminder_time.substring(0, 16) : "";
    }
    
    document.getElementById("task-modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("task-modal").classList.add("hidden");
}

async function toggleTaskStatus(taskId, isCompleted) {
    closeModal();
    try {
        await fetch(`${API_URL}/tasks/${taskId}?is_completed=${isCompleted}`, { method: "PUT" });
        await loadActiveRoadmap(currentGoal.id);
    } catch(err) {
        showToast("Action failed.", "error");
    }
}

async function setTaskReminder() {
    if(!activeTask) return;
    const dt = document.getElementById("reminder-time").value;
    const statusText = document.getElementById("reminder-status");
    try {
        const res = await fetch(`${API_URL}/tasks/${activeTask.id}/reminder`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reminder_time: dt })
        });
        if (res.ok) {
            statusText.innerText = "Reminder saved! ⏰";
            activeTask.reminder_time = dt;
        } else {
            statusText.innerText = "Save failed.";
        }
    } catch(err) {
        statusText.innerText = "Error saving reminder.";
    }
}

let activeQuizData = null;

async function openQuizModal(taskId) {
    closeModal();
    const quizModal = document.getElementById("quiz-modal");
    const loadingDiv = document.getElementById("quiz-loading");
    const contentDiv = document.getElementById("quiz-content");
    const container = document.getElementById("questions-container");
    
    quizModal.classList.remove("hidden");
    loadingDiv.classList.remove("hidden");
    contentDiv.classList.add("hidden");
    container.innerHTML = "";
    
    try {
        const res = await fetch(`${API_URL}/tasks/${taskId}/quiz/generate`);
        activeQuizData = await res.json();
        
        const isFallback = activeQuizData.questions[0].question.includes("Concept check") || activeQuizData.questions[0].question.includes("Quick check");
        
        if (isFallback) {
            container.innerHTML = `<p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:15px;">
                <i class="fa-solid fa-circle-info"></i> AI is currently busy. Using a simplified check.
            </p>`;
        }
        
        activeQuizData.questions.forEach((q, i) => {
            container.innerHTML += `
                <div class="quiz-question" style="margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 12px;">
                    <p style="margin-bottom: 12px;"><strong>${i + 1}. ${q.question}</strong></p>
                    ${q.options.map(opt => `
                        <label class="quiz-option" style="display: flex; align-items: center; gap: 10px; margin-top:8px; cursor:pointer;">
                            <input type="radio" name="q${i}" value="${opt}" required> <span>${opt}</span>
                        </label>
                    `).join('')}
                </div>
            `;
        });
        
        loadingDiv.classList.add("hidden");
        contentDiv.classList.remove("hidden");
    } catch(err) {
        loadingDiv.innerHTML = "Error generating AI quiz. Please try again.";
    }
}

function closeQuizModal() {
    document.getElementById("quiz-modal").classList.add("hidden");
    // Reset views
    document.getElementById("quiz-content").classList.remove("hidden");
    document.getElementById("quiz-result").classList.add("hidden");
    document.getElementById("quiz-loading").classList.add("hidden");
}

document.getElementById("quiz-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if(!activeQuizData || !activeTask) return;
    
    const formData = new FormData(e.target);
    let score = 0;
    const missed_questions = [];
    const user_answers = [];
    let reviewHTML = "";

    activeQuizData.questions.forEach((q, i) => {
        const userAns = formData.get(`q${i}`);
        // Robust matching: trim, lowercase, and remove quotes/punctuation
        const normalize = (s) => (s || "").trim().toLowerCase().replace(/[.,!?;:'"“”]/g, '');
        const isCorrect = normalize(userAns) === normalize(q.correct_answer);
        
        if(isCorrect) {
            score++;
            reviewHTML += `
                <div class="review-item correct">
                    <span class="review-badge badge-correct">Correct</span>
                    <span class="review-q">${q.question}</span>
                    <span class="review-ans user">Your Answer: ${userAns}</span>
                </div>
            `;
        } else {
            missed_questions.push(q.question);
            user_answers.push(userAns || "No answer");
            reviewHTML += `
                <div class="review-item incorrect">
                    <span class="review-badge badge-incorrect">Incorrect</span>
                    <span class="review-q">${q.question}</span>
                    <span class="review-ans user">Your Answer: ${userAns || "No answer"}</span>
                    <span class="review-ans correct">Correct Answer: ${q.correct_answer}</span>
                </div>
            `;
        }
    });
    
    const percentage = score / activeQuizData.questions.length;
    document.getElementById("quiz-review-list").innerHTML = reviewHTML;
    
    try {
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalHTML = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
        
        const res = await fetch(`${API_URL}/tasks/${activeTask.id}/quiz`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                task_id: activeTask.id,
                score: percentage,
                total_questions: activeQuizData.questions.length,
                weak_areas: percentage < 1.0 ? `Reviewing missed concepts...` : "None",
                missed_questions: missed_questions,
                user_answers: user_answers
            })
        });
        const result = await res.json();
        
        // 1. Show score in UI
        const scorePct = Math.round(percentage * 100);
        const total = activeQuizData.questions.length;
        document.getElementById("quiz-score-text").innerHTML = `${scorePct}%<br><span style="font-size: 0.4em; opacity: 0.8; font-weight: 400;">(${score}/${total})</span>`;
        
        const titleEl = document.getElementById("quiz-result-title");
        const descEl = document.getElementById("quiz-result-desc");
        
        if (scorePct >= 80) {
            titleEl.innerText = "Excellent Work!";
            descEl.innerText = "You've mastered this topic. Ready for the next challenge!";
        } else if (scorePct >= 60) {
            titleEl.innerText = "Good Job!";
            descEl.innerText = "You have a solid understanding, but keep practicing those concepts.";
        } else {
            titleEl.innerText = "Keep Learning!";
            descEl.innerText = "This topic is tricky. We've updated your roadmap to help you master it.";
        }
        
        // 2. Switch views immediately
        document.getElementById("quiz-loading").classList.add("hidden");
        document.getElementById("quiz-content").classList.add("hidden");
        document.getElementById("quiz-result").classList.remove("hidden");
        
        // 3. Trigger roadmap reload in background
        loadActiveRoadmap(currentGoal.id);

        // 4. Show dialog AFTER updating UI if needed
        if (result.replanned) {
            showDialog({
                title: "Roadmap Adaptive Update",
                message: "AI has adjusted your roadmap to help you master the topics you missed! Day 1 now focuses on your core gaps.",
                type: "alert"
            });
        }
    } catch(err) {
        showToast("Failed to submit quiz.", "error");
    } finally {
        const submitBtn = e.target.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Quiz';
        }
    }
});

function getFullRoadmapContext() {
    if (!currentGoal) return "";
    
    const completedTasks = currentTasks.filter(t => t.is_completed).map(t => t.topic);
    const remainingTasks = currentTasks.filter(t => !t.is_completed).map(t => t.topic);
    const weakAreas = currentTasks.filter(t => t.quiz && t.quiz.score < 0.6).map(t => t.quiz.weak_areas);
    
    return `
    User is currently working on the roadmap: "${currentGoal.title}".
    Overall Progress: ${completedTasks.length}/${currentTasks.length} tasks completed.
    Completed Topics: ${completedTasks.join(", ") || "None yet"}.
    Upcoming Topics: ${remainingTasks.join(", ")}.
    Identified Weak Areas: ${weakAreas.join(", ") || "None mentioned"}.
    `;
}

async function analyzeCode(action) {
    const isStudio = !document.getElementById("dev-studio-view").classList.contains("hidden");
    const code = document.getElementById("code-editor") ? document.getElementById("code-editor").value : "";
    const chatInput = document.getElementById("chat-editor").value;
    const lang = document.getElementById("code-lang") ? document.getElementById("code-lang").value : "text";
    
    // UI Feedback: which container to use
    const responseContainer = isStudio ? document.getElementById("studio-ai-response") : document.getElementById("ai-response");
    const responseContent = responseContainer.querySelector(".response-content");
    
    if(!code.trim() && !chatInput.trim()) {
        showToast("Please provide code or a question!", "info");
        return;
    }
    
    const contextText = getFullRoadmapContext();
    
    responseContainer.classList.remove("hidden");
    responseContent.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Mentoring in progress...`;
    
    try {
        const res = await fetch(`${API_URL}/assistant/analyze`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ 
                code, 
                language: lang, 
                action, 
                question: chatInput, 
                context_text: contextText 
            })
        });
        const data = await res.json();
        responseContent.innerHTML = typeof marked !== 'undefined' ? marked.parse(data.response) : data.response;
        
        // Agentic Intent: Replanning
        if (data.should_replan && data.replan_topic) {
            const confirmReplan = await showDialog({
                title: "Roadmap Adjustment Identified",
                message: `The AI Mentor noticed you might be struggling with **${data.replan_topic}**. \n\nWould you like to instantly re-plan your remaining roadmap to focus on this topic?`,
                type: "confirm"
            });
            
            if (confirmReplan) {
                triggerManualReplan(data.replan_topic);
            }
        }
        
        responseContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch(err) {
        responseContent.innerHTML = "AI Mentor unreachable. Check your API keys.";
    }
}

function switchAssistantTab(tab) {
    const studyTab = document.getElementById("tab-study");
    const studioTab = document.getElementById("tab-studio");
    const studyView = document.getElementById("study-assistant-view");
    const studioView = document.getElementById("dev-studio-view");
    
    if (tab === 'study') {
        studyTab.classList.add("active");
        studioTab.classList.remove("active");
        studyView.classList.remove("hidden");
        studioView.classList.add("hidden");
    } else {
        studyTab.classList.remove("active");
        studioTab.classList.add("active");
        studyView.classList.add("hidden");
        studioView.classList.remove("hidden");
    }
}

async function triggerManualReplan(topic) {
    if (!currentGoal) return;
    try {
        const res = await fetch(`${API_URL}/tasks/replan_manual/${currentGoal.id}?topic=${encodeURIComponent(topic)}`, {
            method: "POST"
        });
        
        showToast("Roadmap updated: " + topic + " revision added.");
        
        const titleSpan = document.getElementById("active-goal-title");
        if (titleSpan) {
            const h3 = titleSpan.closest("h3");
            if (h3) {
                h3.classList.add("pulse");
                setTimeout(() => h3.classList.remove("pulse"), 2000);
            }
        }
        await loadActiveRoadmap(currentGoal.id);
    } catch(err) {
        showToast("Failed to adjust roadmap.");
    }
}

async function deleteGoal(goalId) {
    const confirmed = await showDialog({
        title: "Delete Roadmap?",
        message: "Are you sure you want to delete this roadmap and all its tasks? This action cannot be undone.",
        type: "confirm"
    });
    if (!confirmed) return;
    
    try {
        const res = await fetch(`${API_URL}/goals/${goalId}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Roadmap deleted successfully.");
            const resFetch = await fetch(`${API_URL}/goals/`, {
                headers: { "X-User-ID": localStorage.getItem("userId") }
            });
            allRoadmaps = await resFetch.json();
            showLibrary();
        } else {
            showToast("Failed to delete roadmap.");
        }
    } catch (err) {
        showToast("Error connecting to server.");
    }
}

async function regenerateRoadmap(goal_id) {
    const confirmed = await showDialog({
        title: "Regenerate Roadmap?",
        message: "This will replace your current roadmap with a new, highly-detailed version using Gemini 3. Continue?",
        type: "confirm"
    });
    if (!confirmed) return;
    
    const btn = document.getElementById("btn-regenerate-roadmap");
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Regenerating...';
    
    try {
        const res = await fetch(`${API_URL}/goals/${goal_id}/regenerate`, { method: "POST" });
        if (res.ok) {
            showToast("Roadmap upgraded with rich details!");
            await loadActiveRoadmap(goal_id);
        } else {
            showToast("Regeneration failed.");
        }
    } catch (err) {
        showToast("Error connecting to server.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast-notification ${type}`;
    
    let icon = "fa-circle-check";
    if (type === "error") icon = "fa-circle-exclamation";
    if (type === "info") icon = "fa-circle-info";
    
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function showDialog({title, message, type = "alert", placeholder = "Enter here..."}) {
    return new Promise((resolve) => {
        const modal = document.getElementById("dialog-modal");
        const titleEl = document.getElementById("dialog-title");
        const msgEl = document.getElementById("dialog-message");
        const promptContainer = document.getElementById("dialog-prompt-container");
        const inputEl = document.getElementById("dialog-input");
        const cancelBtn = document.getElementById("dialog-cancel-btn");
        const confirmBtn = document.getElementById("dialog-confirm-btn");
        
        titleEl.innerText = title;
        msgEl.innerText = message;
        
        // Setup type
        if (type === "confirm" || type === "prompt") {
            cancelBtn.classList.remove("hidden");
        } else {
            cancelBtn.classList.add("hidden");
        }
        
        if (type === "prompt") {
            promptContainer.classList.remove("hidden");
            inputEl.value = "";
            inputEl.placeholder = placeholder;
            setTimeout(() => inputEl.focus(), 100);
        } else {
            promptContainer.classList.add("hidden");
        }
        
        confirmBtn.innerText = type === "confirm" ? "Yes, Proceed" : (type === "prompt" ? "Submit" : "OK");
        
        modal.classList.remove("hidden");
        dialogResolver = resolve;
    });
}

function finalizeDialog(result) {
    const modal = document.getElementById("dialog-modal");
    const inputEl = document.getElementById("dialog-input");
    
    modal.classList.add("hidden");
    
    if (dialogResolver) {
        if (result && document.getElementById("dialog-prompt-container").classList.contains("hidden") === false) {
            dialogResolver(inputEl.value);
        } else {
            dialogResolver(result);
        }
        dialogResolver = null;
    }
}

async function requestManualReplanPopup() {
    const topic = await showDialog({
        title: "Focus Area Re-plan",
        message: "What specific topic would you like the AI to focus on or revise?",
        type: "prompt",
        placeholder: "e.g., Time Complexity"
    });
    
    if (topic && topic.trim()) {
        triggerManualReplan(topic);
    }
}
