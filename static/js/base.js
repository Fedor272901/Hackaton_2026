/*
 * Базовый JavaScript (base.js) - общие скрипты для всего приложения.
 * Здесь можно разместить функции, которые используются на всех страницах.
 * Например: обработка кликов, валидация форм, AJAX-запросы.
 */

// Ждём полной загрузки DOM перед выполнением кода
document.addEventListener('DOMContentLoaded', function() {
    console.log('Hackathon App initialized');

    // Добавляем активный класс для текущей страницы в навигации
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-links a');

    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.opacity = '1';
            link.style.fontWeight = 'bold';
        }
    });

    // Пример: можно добавить обработку кликов по кнопкам
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // Если ссылка пустая (#), предотвращаем переход
            if (this.getAttribute('href') === '#') {
                e.preventDefault();
                console.log('Button clicked (placeholder action)');
            }
        });
    });
});