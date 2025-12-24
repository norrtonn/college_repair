// Функция фильтрации заявок по статусу
function filterRequests() {
    const filter = document.getElementById('statusFilter').value;
    const rows = document.querySelectorAll('.request-row');
    
    rows.forEach(row => {
        if (filter === 'all' || row.classList.contains(`status-${filter}`)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Обновление времени в реальном времени
function updateDateTime() {
    const now = new Date();
    const dateTimeElement = document.getElementById('current-datetime');
    
    if (dateTimeElement) {
        const options = { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        };
        dateTimeElement.textContent = now.toLocaleDateString('ru-RU', options);
    }
}

// Загрузка заявок через AJAX (опционально)
function loadRequests() {
    fetch('/api/requests')
        .then(response => response.json())
        .then(data => {
            console.log('Заявки загружены:', data);
            // Здесь можно обновить таблицу через JavaScript
        })
        .catch(error => console.error('Ошибка:', error));
}

// Подтверждение перед удалением
function confirmAction(message) {
    return confirm(message || 'Вы уверены?');
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Обновляем время каждую секунду
    setInterval(updateDateTime, 1000);
    updateDateTime();
    
    // Загружаем заявки, если на странице есть таблица
    if (document.querySelector('.requests-table')) {
        loadRequests();
    }
    
    // Добавляем обработчики для форм
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обработка...';
            }
        });
    });
    
    // Показать/скрыть описание проблемы
    document.querySelectorAll('.problem-description').forEach(cell => {
        cell.addEventListener('click', function() {
            const fullText = this.getAttribute('data-full') || this.textContent;
            if (this.classList.contains('expanded')) {
                this.textContent = fullText.substring(0, 50) + '...';
                this.classList.remove('expanded');
            } else {
                this.textContent = fullText;
                this.classList.add('expanded');
            }
        });
    });
});

// Анимация появления элементов
function animateOnScroll() {
    const elements = document.querySelectorAll('.stat-card, .action-btn');
    
    elements.forEach((element, index) => {
        setTimeout(() => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(20px)';
            element.style.transition = 'opacity 0.5s, transform 0.5s';
            
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, 100);
        }, index * 100);
    });
}

// Вызываем анимацию при загрузке
window.addEventListener('load', animateOnScroll);