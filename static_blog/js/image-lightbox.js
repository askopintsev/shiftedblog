// Image Lightbox functionality for post detail pages
document.addEventListener('DOMContentLoaded', function() {
    // Get all images in post body content
    const postBodyContent = document.querySelector('.post-body-content');
    if (!postBodyContent) return;

    const images = postBodyContent.querySelectorAll('img');
    if (images.length === 0) return;

    // Get or create modal structure
    let modal = document.getElementById('imageLightboxModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'image-lightbox-modal';
        modal.id = 'imageLightboxModal';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'image-lightbox-content';
        
        const modalImg = document.createElement('img');
        modalImg.id = 'lightboxImage';
        modalImg.alt = 'Enlarged image';
        
        const closeBtn = document.createElement('span');
        closeBtn.className = 'image-lightbox-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.setAttribute('aria-label', 'Close');
        
        modalContent.appendChild(modalImg);
        modal.appendChild(modalContent);
        modal.appendChild(closeBtn);
        document.body.appendChild(modal);
    }
    
    const modalImg = document.getElementById('lightboxImage');
    const closeBtn = modal.querySelector('.image-lightbox-close');

    // Function to open lightbox
    function openLightbox(img) {
        modalImg.src = img.src;
        modalImg.alt = img.alt || 'Enlarged image';
        modal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    // Function to close lightbox
    function closeLightbox() {
        modal.classList.remove('active');
        document.body.style.overflow = ''; // Restore scrolling
    }

    // Add click event to all images
    images.forEach(function(img) {
        img.addEventListener('click', function() {
            openLightbox(img);
        });
    });

    // Close on close button click
    closeBtn.addEventListener('click', closeLightbox);

    // Close on modal background click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeLightbox();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeLightbox();
        }
    });
});

