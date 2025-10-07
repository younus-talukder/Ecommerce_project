document.addEventListener('DOMContentLoaded', function () {
    const bar = document.getElementById('page-progress-bar');
    function startBar() {
        bar.style.display = 'block';
        bar.style.width = '0%';
        bar.style.opacity = '0.95';
        setTimeout(() => { bar.style.width = '70%'; }, 80);
    }
    function finishBar() {
        bar.style.width = '100%';
        setTimeout(() => {
            bar.style.opacity = '0';
            setTimeout(() => {
                bar.style.display = 'none';
                bar.style.width = '0%';
                bar.style.opacity = '0.95';
            }, 350);
        }, 350);
    }
    document.querySelectorAll('a').forEach(function (el) {
        el.addEventListener('click', function (e) {
            const href = el.getAttribute('href');
            if (href && !href.startsWith('http') && href !== '#' && !el.hasAttribute('target')) {
                startBar();
            }
        });
    });
    window.addEventListener('pageshow', finishBar);
});