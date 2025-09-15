(function () {
    const { $, renderNavbar, showToast, Auth, navigate, rel } = window.JobMate;

    let selectedFile = null;

    // 檢查登入狀態
    function checkAuth() {
        if (!Auth.isAuthed()) {
            showToast('請先登入', 'error');
            navigate('/frontend/auth/login.html');
            return false;
        }
        return true;
    }

    // 初始化頁面
    function initPage() {
        console.log('=== 履歷選擇頁面開始初始化 ===');
        console.log('當前頁面:', window.location.href);

        renderNavbar($('#root'));
        console.log('導覽列已渲染');

        // 綁定事件
        bindEvents();
        console.log('事件已綁定');

        // 檢查登入狀態
        if (!checkAuth()) {
            console.log('登入檢查失敗');
            return;
        }

        console.log('=== 履歷選擇頁面初始化完成 ===');
    }

    // 綁定事件
    function bindEvents() {
        // 上傳履歷按鈕
        $('#uploadResumeBtn').addEventListener('click', showUploadSection);

        // 填寫履歷按鈕
        $('#fillResumeBtn').addEventListener('click', () => {
            navigate('/frontend/app/resume.html');
        });

        // 返回選擇按鈕
        $('#backToChoiceBtn').addEventListener('click', hideUploadSection);

        // 檔案選擇
        $('#resumeFileInput').addEventListener('change', handleFileSelect);

        // 拖拽區域點擊
        $('#fileDropZone').addEventListener('click', () => {
            $('#resumeFileInput').click();
        });

        // 拖拽功能
        setupDragAndDrop();

        // 移除檔案按鈕
        $('#removeFileBtn').addEventListener('click', removeSelectedFile);

        // 處理檔案按鈕
        $('#processFileBtn').addEventListener('click', processResumeFile);
    }

    // 顯示上傳區域
    function showUploadSection() {
        $('#uploadSection').style.display = 'block';
        $('#uploadOption').style.display = 'none';
        $('#fillOption').style.display = 'none';
    }

    // 隱藏上傳區域
    function hideUploadSection() {
        $('#uploadSection').style.display = 'none';
        $('#uploadOption').style.display = 'block';
        $('#fillOption').style.display = 'block';
        removeSelectedFile();
    }

    // 處理檔案選擇
    function handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            selectedFile = file;
            displayFileInfo(file);
            $('#processFileBtn').disabled = false;
        }
    }

    // 顯示檔案資訊
    function displayFileInfo(file) {
        $('#fileName').textContent = file.name;
        $('#fileInfo').style.display = 'block';
        $('#fileDropZone').style.display = 'none';
    }

    // 移除選中的檔案
    function removeSelectedFile() {
        selectedFile = null;
        $('#resumeFileInput').value = '';
        $('#fileInfo').style.display = 'none';
        $('#fileDropZone').style.display = 'block';
        $('#processFileBtn').disabled = true;
    }

    // 設置拖拽功能
    function setupDragAndDrop() {
        const dropZone = $('#fileDropZone');

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (isValidFileType(file)) {
                    selectedFile = file;
                    displayFileInfo(file);
                    $('#processFileBtn').disabled = false;
                } else {
                    showToast('不支援的檔案格式，請上傳 PDF、DOC 或 DOCX 檔案', 'error');
                }
            }
        });
    }

    // 驗證檔案類型
    function isValidFileType(file) {
        const validTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        return validTypes.includes(file.type) ||
            file.name.endsWith('.pdf') ||
            file.name.endsWith('.doc') ||
            file.name.endsWith('.docx');
    }

    // 處理履歷檔案
    async function processResumeFile() {
        if (!selectedFile) {
            showToast('請先選擇檔案', 'error');
            return;
        }

        try {
            $('#processFileBtn').disabled = true;
            $('#processFileBtn').textContent = '處理中...';

            // 創建 FormData 物件
            const formData = new FormData();
            formData.append('file', selectedFile);

            // 直接解析履歷檔案
            console.log('發送履歷解析請求到:', '/api/users/parse_resume');
            const response = await fetch('/api/users/parse_resume', {
                method: 'POST',
                body: formData
            });

            console.log('上傳回應狀態:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('上傳失敗，回應內容:', errorText);
                throw new Error(`檔案上傳失敗 (${response.status}): ${errorText}`);
            }

            const result = await response.json();

            if (result.success) {
                showToast('檔案上傳成功！正在跳轉到履歷頁面...', 'success');

                // 延遲一下讓用戶看到成功訊息，然後跳轉到履歷頁面
                setTimeout(() => {
                    // 將上傳資訊傳遞到履歷頁面
                    const params = new URLSearchParams();
                    params.set('from', 'upload');
                    params.set('fileId', result.data.fileId || '');
                    params.set('filename', result.data.filename || '');
                    console.log('跳轉到履歷頁面，參數:', params.toString());
                    navigate('/frontend/app/resume.html?' + params.toString());
                }, 1000);
            } else {
                throw new Error(result.message || '檔案處理失敗');
            }

        } catch (error) {
            console.error('處理檔案時發生錯誤:', error);
            showToast(error.message || '處理檔案時發生錯誤', 'error');
        } finally {
            $('#processFileBtn').disabled = false;
            $('#processFileBtn').textContent = '處理檔案';
        }
    }

    // 頁面載入完成後初始化
    document.addEventListener('DOMContentLoaded', initPage);
})();
