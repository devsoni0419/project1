var API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.startsWith('192.168.'))
    ? `http://${window.location.hostname}:8000/api` 
    : "/api";

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("btn-login");
            const btnText = document.getElementById("btn-text");
            const errorDiv = document.getElementById("login-error");
            
            btn.disabled = true;
            btnText.innerHTML = 'Logging In... <i class="fa-solid fa-circle-notch fa-spin"></i>';
            errorDiv.style.display = 'none';
            
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;
            
            try {
                const res = await fetch(`${API_URL}/auth/login`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ username, password })
                });
                
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.detail || "Login failed");
                }
                
                const data = await res.json();
                localStorage.setItem("userId", data.user_id);
                localStorage.setItem("username", data.username);
                window.location.href = "index.html";
            } catch (error) {
                errorDiv.innerText = error.message;
                errorDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btnText.innerHTML = 'Log In <i class="fa-solid fa-arrow-right"></i>';
            }
        });
    }

    if (signupForm) {
        signupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("btn-signup");
            const btnText = document.getElementById("btn-text");
            const errorDiv = document.getElementById("signup-error");
            
            btn.disabled = true;
            btnText.innerHTML = 'Signing Up... <i class="fa-solid fa-circle-notch fa-spin"></i>';
            errorDiv.style.display = 'none';
            
            const username = document.getElementById("username").value;
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            
            // Password validation (min 8 chars, 1 letter, 1 number, 1 special char)
            const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$/;
            if (!passwordRegex.test(password)) {
                errorDiv.innerText = "Password must be at least 8 characters long, contain at least one letter, one number, and one special character.";
                errorDiv.style.display = 'block';
                btn.disabled = false;
                btnText.innerHTML = 'Sign Up <i class="fa-solid fa-user-plus"></i>';
                return;
            }
            
            try {
                const res = await fetch(`${API_URL}/auth/signup`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ username, email, password })
                });
                
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.detail || "Signup failed");
                }
                
                const data = await res.json();
                localStorage.setItem("userId", data.user_id);
                localStorage.setItem("username", data.username);
                window.location.href = "index.html";
            } catch (error) {
                errorDiv.innerText = error.message;
                errorDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btnText.innerHTML = 'Sign Up <i class="fa-solid fa-user-plus"></i>';
            }
        });
    }

    const toggleBtns = document.querySelectorAll(".toggle-password");
    toggleBtns.forEach(btn => {
        btn.addEventListener("click", function() {
            const input = this.previousElementSibling;
            if (input.type === "password") {
                input.type = "text";
                this.classList.remove("fa-eye");
                this.classList.add("fa-eye-slash");
            } else {
                input.type = "password";
                this.classList.remove("fa-eye-slash");
                this.classList.add("fa-eye");
            }
        });
    });
});

function getUserId() {
    return localStorage.getItem("userId");
}

function logout() {
    localStorage.removeItem("userId");
    localStorage.removeItem("username");
    window.location.href = "login.html";
}
