// SAN Autoresponder JavaScript functionality

// Utility functions
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// API endpoints
const API_BASE = '/api';

// Auth utilities
const auth = {
    getToken: () => localStorage.getItem('token'),
    getUsername: () => localStorage.getItem('username'),
    isLoggedIn: () => !!auth.getToken() && !!auth.getUsername(),
    logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        window.location.href = '/auth';
    }
};

// API utilities
const api = {
    get: async (endpoint) => {
        const token = auth.getToken();
        console.log('API GET request with token:', token ? 'TOKEN_PRESENT' : 'NO_TOKEN');
        
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        return await response.json();
    },
    
    post: async (endpoint, data) => {
        const token = auth.getToken();
        console.log('API POST request with token:', token ? 'TOKEN_PRESENT' : 'NO_TOKEN');
        console.log('API POST data:', data);
        
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        return await response.json();
    }
};

// UI utilities
const ui = {
    showLoading: (element) => {
        element.classList.add('show');
    },
    
    hideLoading: (element) => {
        element.classList.remove('show');
    },
    
    showAlert: (message, type = 'danger') => {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        document.body.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = document.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    },
    
    formatDateTime: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString();
    },
    
    getSentimentClass: (sentiment) => {
        const positive = ['happiness', 'enthusiasm'];
        const negative = ['sadness', 'fear', 'anger', 'disgust'];
        
        if (positive.includes(sentiment)) return 'sentiment-positive';
        if (negative.includes(sentiment)) return 'sentiment-negative';
        return 'sentiment-neutral';
    },
    
    getSentimentIcon: (sentiment) => {
        const positive = ['happiness', 'enthusiasm'];
        const negative = ['sadness', 'fear', 'anger', 'disgust'];
        
        if (positive.includes(sentiment)) return 'fa-smile';
        if (negative.includes(sentiment)) return 'fa-frown';
        return 'fa-meh';
    },
    
    getRussianSentiment: (sentiment) => {
        const mapping = {
            'happiness': 'Радость',
            'sadness': 'Грусть',
            'anger': 'Гнев',
            'fear': 'Страх',
            'disgust': 'Отвращение',
            'enthusiasm': 'Энтузиазм',
            'neutral': 'Нейтрально'
        };
        return mapping[sentiment] || sentiment;
    }
};

// Dashboard functionality
const dashboard = {
    init: () => {
        if (!auth.isLoggedIn()) {
            window.location.href = '/auth';
            return;
        }
        
        dashboard.setupEventListeners();
    },
    
    setupEventListeners: () => {
        // Logout button
        $('#logoutBtn')?.addEventListener('click', auth.logout);
        
        // Sample review button
        $('#sampleReviewBtn')?.addEventListener('click', () => {
            const sampleReviews = [
                "Я очень доволен покупкой! Качество отличное, доставка быстрая. Обязательно порекомендую друзьям.",
                "Ужасное обслуживание! Заказ пришел с опозданием, да еще и поврежденным. Больше никогда не куплю здесь.",
                "Нормально, ничего особенного. Для своей цены сойдет, но можно найти и лучше.",
                "Превосходно! Превзошло все ожидания. Качество на высоте, персонал вежливый. Спасибо!",
                "Очень расстроен. Товар сломался через неделю использования. Качество явно хромает."
            ];
            
            $('#reviewText').value = sampleReviews[Math.floor(Math.random() * sampleReviews.length)];
        });
        
        // Review form submission
        $('#reviewForm')?.addEventListener('submit', dashboard.handleSubmit);
    },
    
    handleSubmit: async (e) => {
        e.preventDefault();
        
        const reviewText = $('#reviewText').value;
        const loadingSpinner = $('#loadingSpinner');
        const resultCard = $('#resultCard');
        const errorAlert = $('#errorAlert');
        const loadingText = $('#loadingText');
        
        console.log('Submitting review:', reviewText);
        
        ui.showLoading(loadingSpinner);
        resultCard.classList.add('d-none');
        errorAlert.classList.add('d-none');
        errorAlert.textContent = '';
        loadingText.textContent = 'Анализируем отзыв...';
        
        try {
            console.log('Sending API request with data:', { review_text: reviewText });
            const data = await api.post('/reviews/submit', { review_text: reviewText });
            
            if (data.review_id) {
                // Polling - check result every 2 seconds until we get a successful response
                console.log('Review submitted, starting polling for result...');
                const pollInterval = setInterval(async () => {
                    try {
                        console.log('Polling for review result ID:', data.review_id);
                        const response = await fetch(`${API_BASE}/reviews/${data.review_id}`, {
                            headers: {
                                'Authorization': `Bearer ${auth.getToken()}`
                            }
                        });
                        
                        if (response.ok) {
                            const resultData = await response.json();
                            console.log('Review result received:', resultData);
                            
                            // Stop polling
                            clearInterval(pollInterval);
                            
                            dashboard.displayResult(resultData);
                            dashboard.addToHistory(resultData);
                            ui.hideLoading(loadingSpinner);
                            resultCard.classList.remove('d-none');
                        } else {
                            console.log('Review not ready yet (status:', response.status, '), continuing to poll...');
                            // Continue polling - don't stop on 404 or other errors
                        }
                    } catch (error) {
                        console.log('Network error, continuing to poll...');
                        // Continue polling on network errors
                    }
                }, 2000);
                
                // Change text after 10 seconds to be more friendly :)))
                setTimeout(() => {
                    if (resultCard.classList.contains('d-none')) {
                        loadingText.textContent = 'Еще немного, генерируем результат...';
                    }
                }, 10000);
                
            } else {
                throw new Error(data.detail || 'Не удалось отправить отзыв');
            }
        } catch (error) {
            errorAlert.classList.remove('d-none');
            errorAlert.textContent = 'Ошибка отправки отзыва: ' + error.message;
            ui.hideLoading(loadingSpinner);
        }
    },
    
    displayResult: (data) => {
        const sentiment = data.sentiment || 'neutral';
        const score = Math.round((data.score || 0) * 100);
        const reviewId = data.review_id || 'N/A';
        const createdAt = data.created_at || new Date().toISOString();
        const reply = data.reply || 'Ответ не сгенерирован';
        
        // Set sentiment badge
        const sentimentBadge = $('#sentimentBadge');
        const sentimentText = $('#sentimentText');
        
        sentimentBadge.className = `sentiment-badge ${ui.getSentimentClass(sentiment)}`;
        sentimentText.textContent = ui.getRussianSentiment(sentiment);
        sentimentBadge.innerHTML = `<i class="fas ${ui.getSentimentIcon(sentiment)} me-2"></i>${sentimentBadge.innerHTML}`;
        
        // Set confidence
        $('#confidenceBar').style.width = score + '%';
        $('#confidenceText').textContent = score + '%';
        
        // Set other fields
        $('#reviewId').value = reviewId;
        $('#analysisDate').value = ui.formatDateTime(createdAt);
        $('#recommendedResponse').textContent = reply;
    },
    
    addToHistory: (data) => {
        const historyList = $('#historyList');
        
        // Clear "no reviews" message if it exists
        if (historyList.children.length === 1 && historyList.children[0].classList.contains('text-muted')) {
            historyList.innerHTML = '';
        }

        const historyItem = document.createElement('div');
        historyItem.className = 'review-item';
        historyItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-3">
                <div>
                    <h6 class="mb-1">Анализ от ${ui.formatDateTime(data.created_at)}</h6>
                    <p class="text-muted mb-2">${data.review_text.substring(0, 100)}${data.review_text.length > 100 ? '...' : ''}</p>
                </div>
                <span class="sentiment-badge ${ui.getSentimentClass(data.sentiment)}">
                    <i class="fas ${ui.getSentimentIcon(data.sentiment)} me-2"></i>
                    ${ui.getRussianSentiment(data.sentiment)}
                </span>
            </div>
            <div class="alert alert-info mb-0">
                ${data.reply}
            </div>
        `;

        historyList.insertBefore(historyItem, historyList.firstChild);
    }
};

// Auth functionality
const authPage = {
    init: () => {
        // Form switching
        $('#showRegister')?.addEventListener('click', (e) => {
            e.preventDefault();
            $('#loginForm').classList.add('d-none');
            $('#registerForm').classList.remove('d-none');
        });
        
        $('#showLogin')?.addEventListener('click', (e) => {
            e.preventDefault();
            $('#registerForm').classList.add('d-none');
            $('#loginForm').classList.remove('d-none');
        });
        
        // Login form submission
        $('#loginFormElement')?.addEventListener('submit', authPage.handleLogin);
        
        // Register form submission
        $('#registerFormElement')?.addEventListener('submit', authPage.handleRegister);
    },
    
    handleLogin: async (e) => {
        e.preventDefault();
        
        const username = $('#loginUsername').value;
        const password = $('#loginPassword').value;
        const alertDiv = $('#loginAlert');
        
        alertDiv.classList.add('d-none');
        alertDiv.textContent = '';
        
        try {
            const data = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const result = await data.json();
            
            if (data.ok) {
                localStorage.setItem('token', result.access_token);
                localStorage.setItem('username', username);
                window.location.href = '/dashboard';
            } else {
                alertDiv.classList.remove('d-none');
                alertDiv.textContent = result.detail || 'Ошибка входа';
            }
        } catch (error) {
            alertDiv.classList.remove('d-none');
            alertDiv.textContent = 'Произошла ошибка. Пожалуйста, попробуйте снова.';
        }
    },
    
    handleRegister: async (e) => {
        e.preventDefault();
        
        const username = $('#registerUsername').value;
        const password = $('#registerPassword').value;
        const confirmPassword = $('#confirmPassword').value;
        const alertDiv = $('#registerAlert');
        const successDiv = $('#registerSuccess');
        
        alertDiv.classList.add('d-none');
        alertDiv.textContent = '';
        successDiv.classList.add('d-none');
        successDiv.textContent = '';
        
        if (password !== confirmPassword) {
            alertDiv.classList.remove('d-none');
            alertDiv.textContent = 'Пароли не совпадают';
            return;
        }
        
        try {
            const data = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const result = await data.json();
            
            if (data.ok) {
                successDiv.classList.remove('d-none');
                successDiv.textContent = 'Регистрация успешна! Пожалуйста, войдите.';
                $('#registerFormElement').reset();
                
                // Switch to login form after 2 seconds
                setTimeout(() => {
                    $('#registerForm').classList.add('d-none');
                    $('#loginForm').classList.remove('d-none');
                }, 2000);
            } else {
                alertDiv.classList.remove('d-none');
                alertDiv.textContent = result.detail || 'Ошибка регистрации';
            }
        } catch (error) {
            alertDiv.classList.remove('d-none');
            alertDiv.textContent = 'Произошла ошибка. Пожалуйста, попробуйте снова.';
        }
    }
};

// Initialize app based on current page
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    
    if (path === '/auth') {
        authPage.init();
    } else if (path === '/dashboard') {
        dashboard.init();
    }
});
