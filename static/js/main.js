/**
 * 主交互脚本
 */

document.addEventListener('DOMContentLoaded', function() {
    // 导航切换功能
    const navItems = document.querySelectorAll('.nav-item');
    const pageSections = document.querySelectorAll('.page-section');
    const breadcrumbText = document.getElementById('breadcrumb-text');

    // 页面标题映射
    const pageTitles = {
        'home': '首页',
        'doctor': '医生模式',
        'public': '大众模式',
        'ai-center': 'AI分析中心',
        'forum': '交流论坛',
        'science': '科普中心',
        'records': '我的记录',
        'favorites': '我的收藏',
        'share': '我的分享',
        'logout': '退出登录'
    };

    // 导航点击事件
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const page = this.getAttribute('data-page');

            // 处理退出登录
            if (page === 'logout') {
                if (confirm('确定要退出登录吗？')) {
                    alert('已退出登录');
                }
                return;
            }

            // 更新导航激活状态
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');

            // 切换页面内容
            pageSections.forEach(section => {
                section.classList.remove('active');
            });

            const targetPage = document.getElementById('page-' + page);
            if (targetPage) {
                targetPage.classList.add('active');
            }

            // 更新面包屑
            if (breadcrumbText && pageTitles[page]) {
                breadcrumbText.textContent = pageTitles[page];
            }

            // 滚动到顶部
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });

    // 搜索框功能
    const searchInput = document.querySelector('.search-box input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const query = this.value.trim();
                if (query) {
                    alert('搜索: ' + query);
                }
            }
        });
    }

    // 上传区域点击效果
    const uploadAreas = document.querySelectorAll('.upload-area');
    uploadAreas.forEach(area => {
        // 如果上传区域已经有 onclick 属性或特定 ID，跳过（避免覆盖自定义功能）
        if (area.getAttribute('onclick') || area.id) {
            return;
        }
        // 模拟文件选择
        area.addEventListener('click', function() {
            alert('点击上传功能 - 实际项目中会打开文件选择对话框');
        });
    });

    // 按钮点击效果
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // 阻止冒泡，避免触发父元素事件
            e.stopPropagation();

            // 如果按钮没有特定功能，显示提示
            if (!this.closest('a') && !this.getAttribute('onclick')) {
                const btnText = this.textContent.trim();
                if (btnText && btnText !== '+' && !btnText.includes('查看')) {
                    console.log('按钮点击:', btnText);
                }
            }
        });
    });

    // 卡片悬停效果增强
    const cards = document.querySelectorAll('.card, .organ-card, .ability-card, .feature-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.3s ease';
        });
    });

    // 表格行点击效果
    const tableRows = document.querySelectorAll('.data-table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            console.log('查看病例详情');
        });
    });

    // 论坛帖子交互
    const forumActions = document.querySelectorAll('.forum-action');
    forumActions.forEach(action => {
        action.addEventListener('click', function(e) {
            e.stopPropagation();
            const icon = this.querySelector('i');
            if (icon && icon.classList.contains('fa-thumbs-up')) {
                // 点赞功能
                const countSpan = this.childNodes[this.childNodes.length - 1];
                if (countSpan && countSpan.textContent) {
                    let count = parseInt(countSpan.textContent.trim());
                    if (!isNaN(count)) {
                        if (this.classList.contains('liked')) {
                            count--;
                            this.classList.remove('liked');
                            this.style.color = '';
                        } else {
                            count++;
                            this.classList.add('liked');
                            this.style.color = 'var(--primary)';
                        }
                        countSpan.textContent = ' ' + count;
                    }
                }
            } else if (icon && icon.classList.contains('fa-comment')) {
                alert('打开评论区域');
            } else if (icon && icon.classList.contains('fa-share')) {
                alert('分享功能');
            }
        });
    });

    // 话题点击
    const topicItems = document.querySelectorAll('.topic-item');
    topicItems.forEach(item => {
        item.addEventListener('click', function() {
            const title = this.querySelector('.topic-title-text');
            if (title) {
                console.log('查看话题:', title.textContent);
            }
        });
    });

    // 器官卡片点击
    const organCards = document.querySelectorAll('.organ-card');
    organCards.forEach(card => {
        card.addEventListener('click', function() {
            const organName = this.querySelector('.organ-name');
            if (organName) {
                console.log('选择器官:', organName.textContent);
            }
        });
    });

    // 通知图标点击
    const notificationIcon = document.querySelector('.notification-icon');
    if (notificationIcon) {
        notificationIcon.addEventListener('click', function() {
            alert('您有 3 条新通知');
        });
    }

    // 用户信息点击
    const userInfo = document.querySelector('.user-info');
    if (userInfo) {
        userInfo.addEventListener('click', function() {
            alert('打开用户菜单');
        });
    }

    // 页面加载动画
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.style.opacity = '0';
        setTimeout(() => {
            mainContent.style.transition = 'opacity 0.5s ease';
            mainContent.style.opacity = '1';
        }, 100);
    }

    // 响应式侧边栏（移动端）
    const sidebar = document.querySelector('.sidebar');
    const header = document.querySelector('.header');

    function handleResize() {
        const width = window.innerWidth;
        if (width <= 768) {
            // 移动端处理
            if (sidebar) {
                sidebar.style.transform = 'translateX(-100%)';
            }
            if (header) {
                header.style.left = '0';
            }
            if (mainContent) {
                mainContent.style.marginLeft = '0';
            }
        } else {
            // 桌面端处理
            if (sidebar) {
                sidebar.style.transform = 'translateX(0)';
            }
            if (header) {
                header.style.left = '';
            }
            if (mainContent) {
                mainContent.style.marginLeft = '';
            }
        }
    }

    window.addEventListener('resize', handleResize);
    handleResize(); // 初始化

    console.log('平台已加载完成');
});

/**
 * 工具函数
 */

// 格式化日期
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}`;
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 平滑滚动到指定元素
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 12px 24px;
        background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : 'var(--primary)'};
        color: white;
        border-radius: 8px;
        font-size: 14px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: fadeIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 模拟数据加载
function simulateLoading(element, callback) {
    const originalContent = element.innerHTML;
    element.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin" style="font-size: 24px; color: var(--primary);"></i><p style="margin-top: 12px; color: var(--text-secondary);">加载中...</p></div>';

    setTimeout(() => {
        element.innerHTML = originalContent;
        if (callback) callback();
    }, 1000);
}
