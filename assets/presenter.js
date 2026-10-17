// ========================================
// Presenter Screen Logic
// Slideshow, QR code, polling
// ========================================

const API_BASE = '';
const POLL_INTERVAL = 3000;
const SLIDE_INTERVAL = 5000;

const urlParams = new URLSearchParams(window.location.search);
const EVENT_SLUG = urlParams.get('event') || 'my-event';

let drawings = [];
let currentSlide = 0;
let slideshowTimer = null;
let eventConfig = null;

// DOM refs
const qrSection = document.querySelector('.qr-section');
const slideshowPair = document.getElementById('slideshowPair');
const slideshowEmpty = document.getElementById('slideshowEmpty');
const beforeImg = document.getElementById('beforeImg');
const afterImg = document.getElementById('afterImg');
const pageTitle = document.querySelector('title');
const pageHeader = document.querySelector('.presenter-header h1');
const qrLabel = document.querySelector('.qr-label');
const eventDate = document.getElementById('eventDate');
const afterLabel = document.getElementById('afterLabel');
const afterFrame = document.getElementById('afterFrame');

const STYLE_LABELS = { pixel: 'BAD PIXEL ART', doodle: 'LINE DOODLE' };

// Show a configured date nicely: ISO dates (2026-06-12) are formatted, anything else is shown as-is
function formatDate(value) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [y, m, d] = value.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  }
  return value;
}

// Init - start centered, move to corner when photos arrive
if (drawings.length === 0) {
  qrSection.classList.add('centered');
}

// Fetch event config and initialize
async function initEvent() {
  try {
    const res = await fetch(`${API_BASE}/api/config?event=${EVENT_SLUG}`);
    if (res.ok) {
      eventConfig = await res.json();
      const title = eventConfig.title || 'Drawtify';
      pageTitle.textContent = title;
      pageHeader.textContent = title;
      if (eventConfig.date) {
        eventDate.textContent = formatDate(eventConfig.date);
        eventDate.hidden = false;
      }
      if (eventConfig.title) {
        qrLabel.textContent = `Drawtify yourself at ${title}!`;
      }
    } else {
      console.warn('No config found for event:', EVENT_SLUG);
    }
  } catch (err) {
    console.error('Failed to load config:', err);
  }

  initQR();

  // Make QR section clickable to open capture page
  qrSection.style.cursor = 'pointer';
  qrSection.addEventListener('click', () => {
    const captureUrl = `${window.location.origin}/capture.html?event=${EVENT_SLUG}`;
    window.open(captureUrl, '_blank');
  });

  pollPhotos();
  setInterval(pollPhotos, POLL_INTERVAL);
}

// Generate QR code on load
function initQR() {
  const captureUrl = `${window.location.origin}/capture.html?event=${EVENT_SLUG}`;
  new QRCode(document.getElementById('qrcode'), {
    text: captureUrl,
    width: 180,
    height: 180,
    colorDark: '#000000',
    colorLight: '#ffffff',
    correctLevel: QRCode.CorrectLevel.M,
  });
}

// Poll for new mspaintified photos
async function pollPhotos() {
  try {
    const res = await fetch(`${API_BASE}/api/photos?event=${EVENT_SLUG}&type=drawings`);
    const data = await res.json();

    if (!res.ok) throw new Error(data.error);

    if (data.photos && data.photos.length > 0) {
      // Drawings are stored as <event>/drawings/<uuid>--<style>.png
      // Map them back to the original <event>/photos/<uuid>.jpg
      const newPhotos = data.photos.map(photo => {
        const filename = photo.key.split('/').pop().replace(/\.[^.]+$/, '');
        const sep = filename.lastIndexOf('--');
        const stem = sep >= 0 ? filename.slice(0, sep) : filename;
        const style = sep >= 0 ? filename.slice(sep + 2) : 'pixel';
        return {
          afterKey: photo.key,
          beforeKey: `${EVENT_SLUG}/photos/${stem}.jpg`,
          style,
        };
      });

      // Check if we have new photos
      const hadPhotos = drawings.length > 0;
      drawings = newPhotos;

      if (!hadPhotos) {
        // First photo arrived!
        qrSection.classList.remove('centered');
        slideshowEmpty.classList.add('hidden');
        startSlideshow();
      }
    }
  } catch (err) {
    console.error('Poll error:', err);
  }
}

// Start the slideshow
function startSlideshow() {
  if (slideshowTimer) return;
  showSlide(0);
  slideshowTimer = setInterval(nextSlide, SLIDE_INTERVAL);
}

// Show a specific slide
function showSlide(index) {
  if (drawings.length === 0) return;

  currentSlide = index % drawings.length;
  const photo = drawings[currentSlide];

  beforeImg.src = `${API_BASE}/api/photos/${photo.beforeKey}`;
  const afterUrl = `${API_BASE}/api/photos/${photo.afterKey}`;
  if (photo.style === 'doodle') {
    // Line doodles are black-on-white: turn the white into transparency
    makeTransparent(afterUrl).then((url) => {
      if (drawings[currentSlide] && drawings[currentSlide].afterKey === photo.afterKey) afterImg.src = url;
    }).catch(() => { afterImg.src = afterUrl; });
  } else {
    afterImg.src = afterUrl;
  }
  afterLabel.textContent = STYLE_LABELS[photo.style] || 'AFTER';
  afterFrame.classList.toggle('transparent-bg', photo.style === 'doodle');

  slideshowPair.classList.remove('active');
  // Force reflow
  void slideshowPair.offsetWidth;
  slideshowPair.classList.add('active');
}

// Advance to next slide
function nextSlide() {
  showSlide(currentSlide + 1);
}

// Go to previous slide
function prevSlide() {
  showSlide(currentSlide - 1 + drawings.length);
}

// Keyboard controls
function handleKeydown(e) {
  if (drawings.length === 0) return;

  if (e.key === 'ArrowRight') {
    e.preventDefault();
    // Stop auto-slideshow so manual control takes over
    if (slideshowTimer) {
      clearInterval(slideshowTimer);
      slideshowTimer = null;
    }
    nextSlide();
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault();
    if (slideshowTimer) {
      clearInterval(slideshowTimer);
      slideshowTimer = null;
    }
    prevSlide();
  } else if (e.key === ' ') {
    // Space to toggle auto-slideshow
    e.preventDefault();
    if (slideshowTimer) {
      clearInterval(slideshowTimer);
      slideshowTimer = null;
    } else {
      slideshowTimer = setInterval(nextSlide, SLIDE_INTERVAL);
    }
  }
}

document.addEventListener('keydown', handleKeydown);

// Init
initEvent();
