// Sayfa yüklendiğinde çalışacak fonksiyonlar
document.addEventListener('DOMContentLoaded', function() {
    // Form elemanlarını seç
    const countrySelect = document.getElementById('country');
    const citySelect = document.getElementById('city');
    const frequencySelect = document.getElementById('frequency');
    
    // Form elemanları varsa işlemleri yap
    if (countrySelect && citySelect && frequencySelect) {
        // Seçimleri localStorage'dan geri yükle
        if (localStorage.getItem('lastCountry')) {
            countrySelect.value = localStorage.getItem('lastCountry');
        }
        if (localStorage.getItem('lastCity')) {
            citySelect.value = localStorage.getItem('lastCity');
        }
        if (localStorage.getItem('lastFrequency')) {
            frequencySelect.value = localStorage.getItem('lastFrequency');
        }
        
        // Seçimleri kaydet
        countrySelect.addEventListener('change', function() {
            localStorage.setItem('lastCountry', this.value);
        });
        
        citySelect.addEventListener('change', function() {
            localStorage.setItem('lastCity', this.value);
        });
        
        frequencySelect.addEventListener('change', function() {
            localStorage.setItem('lastFrequency', this.value);
        });
    }
    
    // Form gönderiminde loading durumu
    const checkForm = document.getElementById('checkForm');
    if (checkForm) {
        checkForm.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Başlatılıyor...';
        });
    }
});

// Tarih formatla
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString('tr-TR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Bildirimleri göster
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 5 saniye sonra otomatik kapat
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Hata yönetimi
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Hata:', msg, 'URL:', url, 'Satır:', lineNo, 'Sütun:', columnNo, 'Hata objesi:', error);
    showNotification('Bir hata oluştu: ' + msg, 'danger');
    return false;
}; 