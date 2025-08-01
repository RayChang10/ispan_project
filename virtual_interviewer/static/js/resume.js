/**
 * 虛擬面試顧問 - 履歷建立頁面功能
 */

let experienceCount = 0;
let keywordCount = 1;
let skillCount = 0;

// 履歷管理器
const ResumeManager = {
    /**
     * 初始化履歷表單
     */
    init: function() {
        this.bindEvents();
        this.loadDraftData();
        this.addSkill(); // 預設添加一個技能
        this.addExperience(); // 預設添加一個工作經驗
    },
    
    /**
     * 綁定事件監聽器
     */
    bindEvents: function() {
        // 表單提交
        $('#resumeForm').on('submit', (e) => {
            e.preventDefault();
            this.submitResume();
        });
        
        // 儲存草稿
        $('#saveAsDraft').on('click', () => {
            this.saveAsDraft();
        });
        
        // 監聽表單變化以自動儲存草稿
        $('#resumeForm').on('input change', () => {
            this.autoSaveDraft();
        });
    },
    
    /**
     * 添加關鍵字輸入欄位
     */
    addKeyword: function() {
        keywordCount++;
        const keywordHtml = `
            <div class="d-flex align-items-center mb-2" id="keyword_${keywordCount}">
                <input type="text" class="form-control me-2" name="keywords[]" placeholder="例如：Python, 資料分析, 專案管理...">
                <button type="button" class="btn btn-success btn-sm me-1" onclick="addKeyword()">
                    <i class="fas fa-plus"></i>
                </button>
                <button type="button" class="btn btn-danger btn-sm" onclick="removeKeyword(${keywordCount})">
                    <i class="fas fa-minus"></i>
                </button>
            </div>
        `;
        $('#keywordsContainer').append(keywordHtml);
    },
    
    /**
     * 移除關鍵字輸入欄位
     */
    removeKeyword: function(id) {
        $(`#keyword_${id}`).remove();
    },
    
    /**
     * 添加技能輸入欄位
     */
    addSkill: function() {
        skillCount++;
        const skillHtml = `
            <div class="experience-card p-4 mb-4" id="skill_${skillCount}">
                ${skillCount > 1 ? `
                    <button type="button" class="btn btn-danger btn-sm delete-btn" onclick="removeSkill(${skillCount})">
                        <i class="fas fa-times"></i>
                    </button>
                ` : ''}
                
                <h5 class="text-primary mb-4">
                    <i class="fas fa-cogs me-2"></i>專業技能 ${skillCount}
                </h5>
                
                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">技能名稱 <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" name="skills[${skillCount}][skill_name]" 
                               placeholder="例如：Python、專案管理、數據分析..." required>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">技能描述</label>
                        <textarea class="form-control" name="skills[${skillCount}][skill_description]" rows="3"
                                  placeholder="請詳細描述您的技能水平、相關經驗或具體應用案例..."></textarea>
                    </div>
                </div>
            </div>
        `;
        
        $('#skillsContainer').append(skillHtml);
    },
    
    /**
     * 移除技能輸入欄位
     */
    removeSkill: function(id) {
        if (confirm('確定要刪除這個技能嗎？')) {
            $(`#skill_${id}`).fadeOut(300, function() {
                $(this).remove();
            });
        }
    },
    
    /**
     * 添加工作經驗
     */
    addExperience: function() {
        experienceCount++;
        const experienceHtml = `
            <div class="experience-card p-4 mb-4" id="experience_${experienceCount}">
                ${experienceCount > 1 ? `
                    <button type="button" class="btn btn-danger btn-sm delete-btn" onclick="removeExperience(${experienceCount})">
                        <i class="fas fa-times"></i>
                    </button>
                ` : ''}
                
                <h5 class="text-primary mb-4">
                    <i class="fas fa-briefcase me-2"></i>工作經驗 ${experienceCount}
                </h5>
                
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label class="form-label">公司名稱 <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" name="experiences[${experienceCount}][company_name]" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">產業類型</label>
                        <select class="form-select" name="experiences[${experienceCount}][industry_type]">
                            <option value="">請選擇產業類型</option>
                            <option value="資訊科技">資訊科技</option>
                            <option value="金融服務">金融服務</option>
                            <option value="製造業">製造業</option>
                            <option value="醫療保健">醫療保健</option>
                            <option value="教育">教育</option>
                            <option value="零售業">零售業</option>
                            <option value="房地產">房地產</option>
                            <option value="媒體廣告">媒體廣告</option>
                            <option value="餐飲服務">餐飲服務</option>
                            <option value="交通運輸">交通運輸</option>
                            <option value="政府公職">政府公職</option>
                            <option value="非營利組織">非營利組織</option>
                            <option value="其他">其他</option>
                        </select>
                    </div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label class="form-label">工作地點</label>
                        <select class="form-select" name="experiences[${experienceCount}][work_location]">
                            <option value="">請選擇工作地點</option>
                            <option value="台北市">台北市</option>
                            <option value="新北市">新北市</option>
                            <option value="桃園市">桃園市</option>
                            <option value="台中市">台中市</option>
                            <option value="台南市">台南市</option>
                            <option value="高雄市">高雄市</option>
                            <option value="新竹縣市">新竹縣市</option>
                            <option value="其他縣市">其他縣市</option>
                            <option value="海外">海外</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">職務名稱 <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" name="experiences[${experienceCount}][position_title]" required>
                    </div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label class="form-label">職務類別 (第一層)</label>
                        <select class="form-select" name="experiences[${experienceCount}][position_category_1]">
                            <option value="">請選擇職務類別</option>
                            <option value="資訊">資訊</option>
                            <option value="工程">工程</option>
                            <option value="業務">業務</option>
                            <option value="行銷">行銷</option>
                            <option value="人資">人資</option>
                            <option value="財務">財務</option>
                            <option value="營運">營運</option>
                            <option value="研發">研發</option>
                            <option value="設計">設計</option>
                            <option value="管理">管理</option>
                            <option value="其他">其他</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">職務類別 (第二層)</label>
                        <select class="form-select" name="experiences[${experienceCount}][position_category_2]">
                            <option value="">請選擇細分類別</option>
                            <option value="軟體開發">軟體開發</option>
                            <option value="系統分析">系統分析</option>
                            <option value="資料分析">資料分析</option>
                            <option value="網路管理">網路管理</option>
                            <option value="專案管理">專案管理</option>
                            <option value="產品管理">產品管理</option>
                            <option value="品質管理">品質管理</option>
                            <option value="客戶服務">客戶服務</option>
                            <option value="其他">其他</option>
                        </select>
                    </div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label class="form-label">開始日期</label>
                        <input type="date" class="form-control" name="experiences[${experienceCount}][start_date]">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">結束日期</label>
                        <input type="date" class="form-control" name="experiences[${experienceCount}][end_date]">
                        <div class="form-check mt-2">
                            <input class="form-check-input" type="checkbox" name="experiences[${experienceCount}][is_current]" 
                                   onchange="toggleEndDate(${experienceCount}, this)">
                            <label class="form-check-label">目前任職中</label>
                        </div>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">工作描述</label>
                    <textarea class="form-control" name="experiences[${experienceCount}][job_description]" rows="4"
                              placeholder="請描述您在這個職位的主要工作內容和職責..."></textarea>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">主要技能</label>
                    <textarea class="form-control" name="experiences[${experienceCount}][job_skills]" rows="3"
                              placeholder="請列出在此工作中使用或學到的主要技能..."></textarea>
                </div>
                
                <div class="row mb-3">
                    <div class="col-md-8">
                        <label class="form-label">薪資待遇</label>
                        <input type="text" class="form-control" name="experiences[${experienceCount}][salary]" 
                               placeholder="例如：50000 或 面議">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">薪資類型</label>
                        <select class="form-select" name="experiences[${experienceCount}][salary_type]">
                            <option value="">請選擇</option>
                            <option value="月薪">月薪</option>
                            <option value="年薪">年薪</option>
                            <option value="時薪">時薪</option>
                            <option value="面議">面議</option>
                        </select>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">管理責任</label>
                    <select class="form-select" name="experiences[${experienceCount}][management_responsibility]">
                        <option value="">請選擇管理責任</option>
                        <option value="無管理責任">無管理責任</option>
                        <option value="團隊負責人">團隊負責人 (1-5人)</option>
                        <option value="部門主管">部門主管 (6-15人)</option>
                        <option value="高階主管">高階主管 (16人以上)</option>
                        <option value="專案管理">專案管理責任</option>
                    </select>
                </div>
            </div>
        `;
        
        $('#experiencesContainer').append(experienceHtml);
    },
    
    /**
     * 移除工作經驗
     */
    removeExperience: function(id) {
        if (confirm('確定要刪除這個工作經驗嗎？')) {
            $(`#experience_${id}`).fadeOut(300, function() {
                $(this).remove();
            });
        }
    },
    
    /**
     * 切換結束日期輸入
     */
    toggleEndDate: function(id, checkbox) {
        const endDateInput = $(`input[name="experiences[${id}][end_date]"]`);
        if (checkbox.checked) {
            endDateInput.prop('disabled', true).val('');
        } else {
            endDateInput.prop('disabled', false);
        }
    },
    
    /**
     * 提交履歷
     */
    submitResume: function() {
        Utils.showLoading('button[type="submit"]', '建立中...');
        
        const formData = this.collectFormData();
        
        // 驗證表單
        const errors = this.validateFormData(formData);
        if (errors.length > 0) {
            Utils.hideLoading('button[type="submit"]');
            Utils.showNotification('請檢查以下錯誤：<br>' + errors.join('<br>'), 'danger', 5000);
            return;
        }
        
        // 提交到後端
        API.post('/users', formData)
            .done((response) => {
                Utils.hideLoading('button[type="submit"]');
                if (response.success) {
                    // 清除草稿
                    Storage.remove('resumeDraft');
                    
                    // 顯示成功訊息
                    $('#successModal').modal('show');
                    
                    // 儲存用戶ID到本地儲存
                    Storage.set('currentUserId', response.user_id);
                    
                    Utils.showNotification('履歷建立成功！', 'success');
                }
            })
            .fail(() => {
                Utils.hideLoading('button[type="submit"]');
            });
    },
    
    /**
     * 收集表單資料
     */
    collectFormData: function() {
        const formData = {
            name: $('#name').val(),
            desired_position: $('#desired_position').val(),
            desired_field: $('#desired_field').val(),
            desired_location: $('#desired_location').val(),
            introduction: $('#introduction').val(),
            keywords: [],
            skills: [],
            work_experiences: []
        };
        
        // 收集關鍵字
        $('input[name="keywords[]"]').each(function() {
            const value = $(this).val().trim();
            if (value) {
                formData.keywords.push(value);
            }
        });
        formData.keywords = formData.keywords.join(', ');
        
        // 收集技能
        $('.experience-card[id^="skill_"]').each(function() {
            const skillData = {};
            $(this).find('input, textarea').each(function() {
                const name = $(this).attr('name');
                if (name && name.includes('[')) {
                    const fieldName = name.match(/\[([^\]]+)\]$/)[1];
                    skillData[fieldName] = $(this).val();
                }
            });
            
            if (skillData.skill_name) {
                formData.skills.push(skillData);
            }
        });
        
        // 收集工作經驗
        $('.experience-card').each(function() {
            const experienceData = {};
            $(this).find('input, select, textarea').each(function() {
                const name = $(this).attr('name');
                if (name && name.includes('[')) {
                    const fieldName = name.match(/\[([^\]]+)\]$/)[1];
                    experienceData[fieldName] = $(this).val();
                }
            });
            
            // 如果是目前任職中，清空結束日期
            const isCurrentCheckbox = $(this).find('input[type="checkbox"]');
            if (isCurrentCheckbox.is(':checked')) {
                experienceData.end_date = null;
            }
            
            if (experienceData.company_name) {
                formData.work_experiences.push(experienceData);
            }
        });
        
        return formData;
    },
    
    /**
     * 驗證表單資料
     */
    validateFormData: function(formData) {
        const errors = [];
        
        if (!formData.name) errors.push('姓名為必填欄位');
        if (!formData.desired_position) errors.push('期望職稱為必填欄位');
        if (!formData.desired_field) errors.push('期望工作領域為必填欄位');
        if (!formData.desired_location) errors.push('期望工作地點為必填欄位');
        
        // 驗證技能
        if (formData.skills.length === 0) {
            errors.push('至少需要填寫一項專業技能');
        } else {
            formData.skills.forEach((skill, index) => {
                if (!skill.skill_name) {
                    errors.push(`專業技能 ${index + 1} 的技能名稱為必填欄位`);
                }
            });
        }
        
        // 驗證工作經驗
        if (formData.work_experiences.length === 0) {
            errors.push('至少需要填寫一個工作經驗');
        } else {
            formData.work_experiences.forEach((exp, index) => {
                if (!exp.company_name) {
                    errors.push(`工作經驗 ${index + 1} 的公司名稱為必填欄位`);
                }
                if (!exp.position_title) {
                    errors.push(`工作經驗 ${index + 1} 的職務名稱為必填欄位`);
                }
            });
        }
        
        return errors;
    },
    
    /**
     * 儲存草稿
     */
    saveAsDraft: function() {
        const formData = this.collectFormData();
        Storage.set('resumeDraft', formData);
        Utils.showNotification('草稿已儲存', 'success', 2000);
    },
    
    /**
     * 自動儲存草稿
     */
    autoSaveDraft: function() {
        // 節流函數，避免頻繁儲存
        clearTimeout(this.autoSaveTimer);
        this.autoSaveTimer = setTimeout(() => {
            this.saveAsDraft();
        }, 5000);
    },
    
    /**
     * 載入草稿資料
     */
    loadDraftData: function() {
        const draftData = Storage.get('resumeDraft');
        if (!draftData) return;
        
        // 載入基本資料
        $('#name').val(draftData.name || '');
        $('#desired_position').val(draftData.desired_position || '');
        $('#desired_field').val(draftData.desired_field || '');
        $('#desired_location').val(draftData.desired_location || '');
        $('#introduction').val(draftData.introduction || '');
        
        // 載入關鍵字
        if (draftData.keywords) {
            const keywords = draftData.keywords.split(', ');
            keywords.forEach((keyword, index) => {
                if (index === 0) {
                    $('input[name="keywords[]"]').first().val(keyword);
                } else {
                    this.addKeyword();
                    $('input[name="keywords[]"]').last().val(keyword);
                }
            });
        }
        
        // 載入技能
        if (draftData.skills && draftData.skills.length > 0) {
            // 清除預設的技能欄位
            $('#skillsContainer').empty();
            skillCount = 0;
            
            draftData.skills.forEach((skill) => {
                this.addSkill();
                $(`input[name="skills[${skillCount}][skill_name]"]`).val(skill.skill_name || '');
                $(`textarea[name="skills[${skillCount}][skill_description]"]`).val(skill.skill_description || '');
            });
        }
        
        Utils.showNotification('已載入草稿資料', 'info', 2000);
    }
};

// 全域函數（供HTML調用）
function addKeyword() {
    ResumeManager.addKeyword();
}

function removeKeyword(id) {
    ResumeManager.removeKeyword(id);
}

function addSkill() {
    ResumeManager.addSkill();
}

function removeSkill(id) {
    ResumeManager.removeSkill(id);
}

function addExperience() {
    ResumeManager.addExperience();
}

function removeExperience(id) {
    ResumeManager.removeExperience(id);
}

function toggleEndDate(id, checkbox) {
    ResumeManager.toggleEndDate(id, checkbox);
}

function saveAsDraft() {
    ResumeManager.saveAsDraft();
}

// 當文檔就緒時初始化
$(document).ready(function() {
    ResumeManager.init();
}); 