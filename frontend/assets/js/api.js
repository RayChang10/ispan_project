// JobMate360 API 串接模組
(function () {
    const { showToast } = window.JobMate;

    // API 基礎設定 - 使用相對路徑，與後端服務一致
    const API_BASE_URL = '/api';

    // 簡化的 API 端點解析
    async function resolveApiBase() {
        return API_BASE_URL;
    }

    // 通用 API 調用函數
    async function apiCall(endpoint, options = {}) {
        try {
            const baseUrl = await resolveApiBase();
            const url = `${baseUrl}${endpoint}`;

            const defaultOptions = {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            const response = await fetch(url, { ...defaultOptions, ...options });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API 調用失敗 (${endpoint}):`, error);
            showToast(`API 調用失敗: ${error.message}`, 'error');
            throw error;
        }
    }

    // 職缺搜尋 API
    const JobSearchAPI = {
        // 一般職缺搜尋
        async searchJobs(query, topK = 10) {
            return await apiCall('/job_search/search', {
                method: 'POST',
                body: JSON.stringify({ query, top_k: topK })
            });
        },

        // 根據履歷搜尋職缺
        async searchJobsByResume(resumeData, query = '') {
            return await apiCall('/job_search/search_by_resume', {
                method: 'POST',
                body: JSON.stringify({ resume_data: resumeData, query })
            });
        },

        // 分析履歷與職缺契合度
        async analyzeFit(resumeData, jobData) {
            return await apiCall('/job_search/analyze_fit', {
                method: 'POST',
                body: JSON.stringify({ resume_data: resumeData, job_data: jobData })
            });
        },

        // 履歷健檢
        async resumeHealthCheck(resumeData, targetJob = null) {
            return await apiCall('/job_search/resume_health_check', {
                method: 'POST',
                body: JSON.stringify({ resume_data: resumeData, target_job: targetJob })
            });
        },

        // 檢查服務狀態
        async checkStatus() {
            return await apiCall('/job_search/status');
        }
    };

    // 工作流程 API（已移除，統一使用 JobSearchAPI）

    // 面試 API（保持現有功能）
    const InterviewAPI = {
        async sendMessage(message, userId = 'default_user') {
            return await apiCall('/interview', {
                method: 'POST',
                body: JSON.stringify({ message, user_id: userId })
            });
        }
    };

    // 認證 API（保持現有功能）
    const AuthAPI = {
        async login(email, password) {
            return await apiCall('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });
        },

        async register(email, password, name) {
            return await apiCall('/auth/register', {
                method: 'POST',
                body: JSON.stringify({ email, password, name })
            });
        }
    };

    // 導出 API 模組
    window.JobMateAPI = {
        JobSearch: JobSearchAPI,
        Interview: InterviewAPI,
        Auth: AuthAPI,
        apiCall,
        resolveApiBase
    };

    console.log('📡 JobMate API 模組已載入');
})();

