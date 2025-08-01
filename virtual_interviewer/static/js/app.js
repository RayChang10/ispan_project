/**
 * 虛擬面試顧問 - 通用JavaScript功能
 */

// API基礎設定
const API_BASE_URL = '/api';

// 通用工具函數
const Utils = {
    /**
     * 顯示通知訊息
     */
    showNotification: function(message, type = 'info', duration = 3000) {
        const notification = $(`
            <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                <i class="fas fa-${this.getIconByType(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        
        $('body').append(notification);
        
        // 自動消失
        setTimeout(() => {
            notification.alert('close');
        }, duration);
    },
    
    /**
     * 根據類型獲取圖標
     */
    getIconByType: function(type) {
        const icons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    },
    
    /**
     * 顯示載入狀態
     */
    showLoading: function(element, text = '處理中...') {
        const $element = $(element);
        $element.prop('disabled', true);
        $element.data('original-html', $element.html());
        $element.html(`<span class="loading me-2"></span>${text}`);
    },
    
    /**
     * 隱藏載入狀態
     */
    hideLoading: function(element) {
        const $element = $(element);
        $element.prop('disabled', false);
        $element.html($element.data('original-html'));
    },
    
    /**
     * 格式化日期時間
     */
    formatDateTime: function(date) {
        return new Date(date).toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    /**
     * 格式化時間為相對時間
     */
    formatRelativeTime: function(date) {
        const now = new Date();
        const diff = now - new Date(date);
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return '剛才';
        if (minutes < 60) return `${minutes}分鐘前`;
        if (hours < 24) return `${hours}小時前`;
        if (days < 7) return `${days}天前`;
        return this.formatDateTime(date);
    },
    
    /**
     * 驗證表單數據
     */
    validateForm: function(formData, rules) {
        const errors = [];
        
        for (const field in rules) {
            const value = formData[field];
            const rule = rules[field];
            
            // 必填驗證
            if (rule.required && (!value || value.trim() === '')) {
                errors.push(`${rule.label || field} 為必填欄位`);
                continue;
            }
            
            // 最小長度驗證
            if (rule.minLength && value && value.length < rule.minLength) {
                errors.push(`${rule.label || field} 至少需要 ${rule.minLength} 個字元`);
            }
            
            // 最大長度驗證
            if (rule.maxLength && value && value.length > rule.maxLength) {
                errors.push(`${rule.label || field} 不能超過 ${rule.maxLength} 個字元`);
            }
            
            // 電子郵件驗證
            if (rule.type === 'email' && value && !this.isValidEmail(value)) {
                errors.push(`${rule.label || field} 格式不正確`);
            }
        }
        
        return errors;
    },
    
    /**
     * 驗證電子郵件格式
     */
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
};

// API通訊類別
const API = {
    /**
     * 發送GET請求
     */
    get: function(endpoint, params = {}) {
        const url = new URL(API_BASE_URL + endpoint, window.location.origin);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        
        return $.ajax({
            url: url.toString(),
            method: 'GET',
            contentType: 'application/json'
        });
    },
    
    /**
     * 發送POST請求
     */
    post: function(endpoint, data = {}) {
        return $.ajax({
            url: API_BASE_URL + endpoint,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data)
        });
    },
    
    /**
     * 發送PUT請求
     */
    put: function(endpoint, data = {}) {
        return $.ajax({
            url: API_BASE_URL + endpoint,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(data)
        });
    },
    
    /**
     * 發送DELETE請求
     */
    delete: function(endpoint) {
        return $.ajax({
            url: API_BASE_URL + endpoint,
            method: 'DELETE',
            contentType: 'application/json'
        });
    },
    
    /**
     * 處理API錯誤
     */
    handleError: function(xhr, textStatus, errorThrown) {
        let message = '發生未知錯誤';
        
        if (xhr.responseJSON && xhr.responseJSON.message) {
            message = xhr.responseJSON.message;
        } else if (xhr.status === 404) {
            message = '請求的資源不存在';
        } else if (xhr.status === 500) {
            message = '伺服器內部錯誤';
        } else if (xhr.status === 0) {
            message = '網路連線錯誤';
        }
        
        Utils.showNotification(message, 'danger');
        console.error('API Error:', {
            status: xhr.status,
            statusText: xhr.statusText,
            responseText: xhr.responseText,
            textStatus: textStatus,
            errorThrown: errorThrown
        });
    }
};

// 本地儲存管理
const Storage = {
    /**
     * 設定本地儲存
     */
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('無法儲存到本地儲存:', e);
            return false;
        }
    },
    
    /**
     * 取得本地儲存
     */
    get: function(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            console.error('無法從本地儲存讀取:', e);
            return defaultValue;
        }
    },
    
    /**
     * 移除本地儲存
     */
    remove: function(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('無法移除本地儲存:', e);
            return false;
        }
    },
    
    /**
     * 清空本地儲存
     */
    clear: function() {
        try {
            localStorage.clear();
            return true;
        } catch (e) {
            console.error('無法清空本地儲存:', e);
            return false;
        }
    }
};

// 文檔就緒時執行
$(document).ready(function() {
    // 初始化工具提示
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // 初始化彈出框
    $('[data-bs-toggle="popover"]').popover();
    
    // 全域AJAX錯誤處理
    $(document).ajaxError(function(event, xhr, settings, thrownError) {
        API.handleError(xhr, 'error', thrownError);
    });
    
    // 全域AJAX載入指示器
    $(document).ajaxStart(function() {
        $('body').addClass('ajax-loading');
    }).ajaxStop(function() {
        $('body').removeClass('ajax-loading');
    });
    
    // 自動調整textarea高度
    $('textarea').on('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
});

// 全域變數
window.Utils = Utils;
window.API = API;
window.Storage = Storage; 