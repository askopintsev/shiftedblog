/**
 * Ensure post gallery carousels respond to prev/next button clicks.
 * Bootstrap 5.0.0-beta2 data-bs-slide can fail; we wire clicks explicitly.
 */
document.addEventListener('DOMContentLoaded', function() {
    var carousels = document.querySelectorAll('.post-gallery-carousel');
    if (!carousels.length || typeof bootstrap === 'undefined') return;

    carousels.forEach(function(carouselEl) {
        var instance = bootstrap.Carousel.getInstance(carouselEl);
        if (!instance) {
            instance = new bootstrap.Carousel(carouselEl);
        }

        var prevBtn = carouselEl.querySelector('.carousel-control-prev');
        var nextBtn = carouselEl.querySelector('.carousel-control-next');
        if (prevBtn) {
            prevBtn.addEventListener('click', function(e) {
                e.preventDefault();
                instance.prev();
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function(e) {
                e.preventDefault();
                instance.next();
            });
        }

        var indicators = carouselEl.querySelectorAll('.carousel-indicators [data-bs-slide-to]');
        indicators.forEach(function(btn, index) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                instance.to(index);
            });
        });
    });
});
