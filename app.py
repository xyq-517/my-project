from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import hashlib
import os
import io
import requests
import dashscope
from dashscope import Generation
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.secret_key = 'medical_detection_platform_secret_key_2024'

# 配置千问API
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY', '')

# 后端服务配置
# SEGMENT_API_URL: 分割服务地址 (5003端口)
# CLASSIFY_API_URL: 分类服务地址 (5005端口，使用/api/classify接口)
SEGMENT_API_URL = os.getenv('SEGMENT_API_URL', 'http://127.0.0.1:5003/api/segment')
CLASSIFY_API_URL = os.getenv('CLASSIFY_API_URL', 'http://127.0.0.1:5005/api/classify')

# 数据集配置 - 映射数据集名称到原始图像和预测图像目录
DATASET_CONFIG = {
    'kits19': {
        'originals': r'D:\shengwu\using\unet-pytorch\VOCdevkit_kits19\VOC2007\JPEGImages',
        'predictions': r'D:\shengwu\using\unet-pytorch\img_out',
    },
    'lidc': {
        'originals': r'D:\shengwu\using\unet-pytorch\VOCdevkit_lidc_test\VOC2007\JPEGImages',
        'predictions': r'D:\shengwu\using\unet-pytorch\img_out',
    },
}

# ========== 切片浏览器API ==========

@app.route('/api/patient-slices', methods=['GET'])
def get_patient_slices():
    """获取患者的所有切片列表"""
    try:
        patient_id = request.args.get('patient_id', '').strip()
        dataset = request.args.get('dataset', '').strip()

        if not patient_id or not dataset:
            return jsonify({'success': False, 'error': '缺少patient_id或dataset参数'}), 400

        if dataset not in DATASET_CONFIG:
            return jsonify({'success': False, 'error': f'未知数据集: {dataset}'}), 400

        pred_dir = DATASET_CONFIG[dataset]['predictions']
        if not os.path.isdir(pred_dir):
            return jsonify({'success': False, 'error': f'预测目录不存在: {pred_dir}'}), 404

        pattern = f'case_{patient_id}_'
        slices = []
        for filename in os.listdir(pred_dir):
            if filename.startswith(pattern) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                parts = filename.replace(pattern, '').split('.')
                slice_num = parts[0]
                slices.append({
                    'index': len(slices),
                    'filename': filename,
                    'slice_num': slice_num,
                })

        slices.sort(key=lambda x: int(x['slice_num']) if x['slice_num'].isdigit() else 0)

        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'dataset': dataset,
            'total': len(slices),
            'slices': slices,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/slice-image', methods=['GET'])
def get_slice_image():
    """获取切片图像（原始或预测）"""
    try:
        patient_id = request.args.get('patient_id', '').strip()
        slice_num = request.args.get('slice_num', '').strip()
        dataset = request.args.get('dataset', '').strip()
        img_type = request.args.get('type', 'prediction').strip()

        if not patient_id or not slice_num or not dataset:
            return jsonify({'error': '缺少必要参数'}), 400

        if dataset not in DATASET_CONFIG:
            return jsonify({'error': f'未知数据集: {dataset}'}), 400

        if img_type == 'original':
            img_dir = DATASET_CONFIG[dataset]['originals']
        else:
            img_dir = DATASET_CONFIG[dataset]['predictions']

        filename = f'case_{patient_id}_{slice_num}.jpg'
        filepath = os.path.join(img_dir, filename)

        if not os.path.isfile(filepath):
            for ext in ['.png', '.jpeg']:
                alt_path = os.path.join(img_dir, f'case_{patient_id}_{slice_num}{ext}')
                if os.path.isfile(alt_path):
                    filepath = alt_path
                    break

        if not os.path.isfile(filepath):
            return jsonify({'error': '图像文件不存在'}), 404

        mime_type = 'image/jpeg'
        if filepath.lower().endswith('.png'):
            mime_type = 'image/png'

        with open(filepath, 'rb') as f:
            image_data = f.read()

        return image_data, 200, {'Content-Type': mime_type}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

# 模拟用户数据库
USERS = {}

# 模拟文章数据库
ARTICLES = [
    {
        'id': 1,
        'title': '肺结节',
        'summary': '肺结节是指肺部影像上各种大小、边缘清楚或模糊、直径小于等于3cm的局灶性圆形致密影。',
        'tags': ['肺结节', '科普', '肺部'],
        'url': 'https://baike.baidu.com/item/%E8%82%BA%E7%BB%93%E8%8A%82/8554561'
    },
    {
        'id': 2,
        'title': '肝囊肿',
        'summary': '肝囊肿是一种常见的良性肝脏疾病，有单纯性和多囊性两种形式，以及包虫病这一特殊类型。',
        'tags': ['肝囊肿', '科普', '肝脏'],
        'url': 'https://baike.baidu.com/item/%E8%82%9D%E5%9B%8A%E8%82%BF/10487056'
    },
    {
        'id': 3,
        'title': '计算机断层扫描',
        'summary': '计算机断层扫描（CT）是通过旋转X射线源对人体进行分层扫描，结合计算机重建生成横断面及三维图像的数字化成像技术。',
        'tags': ['CT检查', '科普', '检查须知'],
        'url': 'https://baike.baidu.com/item/%E8%AE%A1%E7%AE%97%E6%9C%BA%E6%96%AD%E5%B1%82%E6%89%AB%E6%8F%8F/6255440'
    },
    {
        'id': 4,
        'title': '脾脏常见疾病与健康：了解你的身体卫士',
        'summary': '你知道吗？人体的免疫功能，其实是由许多器官和组织共同协作完成的。',
        'tags': ['脾脏疾病', '科普', '脾脏'],
        'url': 'https://www.sohu.com/a/890671377_122001004'
    },
    {
        'id': 5,
        'title': '肾结石',
        'summary': '肾结石，是由尿液中的一些成分在肾脏内形成的结石，常导致患者出现泌尿系症状',
        'tags': ['肾结石', '科普', '肾脏'],
        'url': 'https://baike.baidu.com/item/%E8%82%BE%E7%BB%93%E7%9F%B3/257557'
    },
    {
        'id': 6,
        'title': '肠胃疾病',
        'summary': '胃肠病是常见病多发病，总发病率约占人口的20%左右。',
        'tags': ['肠胃疾病', '科普', '肠胃'],
        'url': 'https://baike.baidu.com/item/%E8%82%A0%E8%83%83%E7%96%BE%E7%97%85/3587428'
    },
    {
        'id': 7,
        'title': '肝脏疾病有哪些',
        'summary': '胃肠病是常见病多发病，总发病率约占人口的20%左右。',
        'tags': ['肝脏疾病', '科普', '肝脏'],
        'url': 'https://health.baidu.com/m/detail/ar_5965329514407017632'
    },
    {
        'id': 8,
        'title': '2026肝癌流行病学趋势：新发86.5万例，靶免治疗成主流',
        'summary': '肝癌是全球致死率极高的恶性肿瘤，2022年全球新发病例约86.5万例，死亡病例约75.8万例，死亡发病比高达87.6%，整体预后极差。',
        'tags': ['肝癌', '科普', '肝脏'],
        'url': 'https://www.cn-healthcare.com/articlewm/20260506/content-1671663.html'
    },
    {
        'id': 9,
        'title': '肾病',
        'summary': '肾病（nephrosis）是肾脏病变的统称，指由各种原因引起成肾脏结构、功能的损害，从而导致肾脏病理损伤、血液或尿液成分异常等病症，患者的常见症状有水肿、尿少或无尿、血尿、蛋白尿、高血压、贫血、腰痛等。肾病的病因很多，包括遗传因素、感染、药物中毒、免疫疾病、代谢性疾病等。',
        'tags': ['肾病', '科普', '肾脏'],
        'url': 'https://baike.baidu.com/item/%E8%82%BE%E7%97%85/245562'
    },
    {
        'id': 10,
        'title': '关于肾结石，看这一篇就够了',
        'summary': '《爱情公寓》中的吕子乔被诊断为肾结石时候的那一声哀嚎，至今让人印象深刻，肾结石要么不发病，发病起来疼起来要命。突发侧腹或下腹疼痛、恶心呕吐、大汗淋漓、面色苍白、尿血、排尿困难或疼痛……，这些都是肾绞痛的症状。',
        'tags': ['肾结石', '科普', '肾脏'],
        'url': 'https://y.dxy.cn/hospital/12494/940369.html'
    },
    {
        'id': 11,
        'title': '肾肿瘤大部分为恶性 早期往往无明显症状丨世界肾脏日',
        'summary': '3月14日是世界肾脏日，肾肿瘤究竟是个啥？我们应该如何尽早发现？得了肾肿瘤，应该怎么办？',
        'tags': ['肾肿瘤', '科普', '肝脏'],
        'url': 'https://news.qq.com/rain/a/20240315A06IME00/'
    },
    {
        'id': 12,
        'title': '体检发现"肝血管瘤"怎么办？会变成癌症吗？',
        'summary': '不少人在拿到体检报告的时候，都会发现体检报告上出现"肝血管瘤"字样。那肝脏内有肿瘤到底要不要紧？ 病情发展下去会变癌吗？ 血管瘤会破裂吗？今天就来大家了解一下体检报告上的"肝血管瘤"。',
        'tags': ['肝血管瘤', '科普', '肝脏'],
        'url': 'https://zhuanlan.zhihu.com/p/258540948'
    },
    {
        'id': 13,
        'title': '胰腺癌为何被称为"癌中之王"？深度解析其恶性本质与治疗困境 ',
        'summary': '胰腺癌，这个令医学界与患者闻之色变的疾病，因其极高的致死率和治疗难度，被冠以"癌中之王"的称号。',
        'tags': ['胰腺癌', '科普', '胰腺'],
        'url': 'https://www.sohu.com/a/943110916_121355825'
    },
    {
        'id': 14,
        'title': '国家卫生健康委办公厅关于印发原发性肝癌诊疗指南（2026年版）的通知',
        'summary': '为进一步提高原发性肝癌诊疗规范化水平，保障医疗质量安全，维护患者健康权益，我委组织对《原发性肝癌诊疗指南（2024年版）》进行修订，形成了《原发性肝癌诊疗指南（2026年版）》。',
        'tags': ['原发性肝癌诊疗', '科普', '肝脏'],
        'url': 'https://www.nhc.gov.cn/yzygj/c100067/202604/3371c9cb2f7f4f55b18c709ff2c53ab8.shtml'
    },

]

# 页面标题映射
PAGE_TITLES = {
    'home': '首页',
    'doctor': '医生模式',
    'public': '大众模式',
    'ai_center': 'AI分析中心',
    'forum': '交流论坛',
    'science': '科普中心',
    'my': '我的',
}


def hash_password(password):
    """密码加密"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_nav_items(current_page):
    """生成导航项列表，标记当前激活页面"""
    user = get_current_user()

    nav_config = [
        {'page': 'home', 'icon': 'fas fa-home', 'label': '首页'},
    ]

    if user:
        user_mode = user.get('mode', 'public')
        if user_mode == 'doctor':
            nav_config.append({'page': 'doctor', 'icon': 'fas fa-user-md', 'label': '医生模式'})
        else:
            nav_config.append({'page': 'public', 'icon': 'fas fa-users', 'label': '大众模式'})
    else:
        nav_config.append({'page': 'doctor', 'icon': 'fas fa-user-md', 'label': '医生模式'})
        nav_config.append({'page': 'public', 'icon': 'fas fa-users', 'label': '大众模式'})

    nav_config.extend([
        {'page': 'ai_center', 'icon': 'fas fa-brain', 'label': 'AI分析中心'},
        {'page': 'forum', 'icon': 'fas fa-comments', 'label': '交流论坛'},
        {'page': 'science', 'icon': 'fas fa-book-medical', 'label': '科普中心'},
        {'divider': True},
        {'page': 'my', 'icon': 'fas fa-user', 'label': '我的'},
        {'divider': True},
    ])

    for item in nav_config:
        if not item.get('divider'):
            item['active'] = (item['page'] == current_page)

    return nav_config


def get_current_user():
    """获取当前登录用户"""
    if 'username' in session:
        return {
            'username': session['username'],
            'mode': session.get('mode', 'public')
        }
    return None


# ========== 登录注册路由 ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        mode = request.form.get('mode', 'public')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return redirect(url_for('login'))

        if username not in USERS:
            flash('用户名不存在', 'error')
            return redirect(url_for('login'))

        if USERS[username]['password'] != hash_password(password):
            flash('密码错误', 'error')
            return redirect(url_for('login'))

        session['username'] = username
        session['mode'] = mode
        flash('登录成功！', 'success')

        if mode == 'doctor':
            return redirect(url_for('doctor'))
        return redirect(url_for('public'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        mode = request.form.get('mode', 'public')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return redirect(url_for('register'))

        if len(username) < 3:
            flash('用户名至少3个字符', 'error')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('密码至少6个字符', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return redirect(url_for('register'))

        if username in USERS:
            flash('用户名已存在', 'error')
            return redirect(url_for('register'))

        USERS[username] = {
            'password': hash_password(password),
            'username': username,
            'mode': mode
        }
        flash('注册成功！请登录', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    """退出登录"""
    session.pop('username', None)
    session.pop('mode', None)
    session.pop('_flashes', None)
    flash('已退出登录', 'info')
    return redirect(url_for('login'))


# ========== 公开页面路由（无需登录） ==========

@app.route('/')
def index():
    return render_template('index.html',
                           page='home',
                           page_title=PAGE_TITLES['home'],
                           nav_items=get_nav_items('home'),
                           user=get_current_user(),
                           articles=ARTICLES[:3])


@app.route('/doctor')
def doctor():
    return render_template('doctor.html',
                           page='doctor',
                           page_title=PAGE_TITLES['doctor'],
                           nav_items=get_nav_items('doctor'),
                           user=get_current_user())


@app.route('/public')
def public():
    return render_template('public.html',
                           page='public',
                           page_title=PAGE_TITLES['public'],
                           nav_items=get_nav_items('public'),
                           user=get_current_user())


@app.route('/ai-center')
def ai_center():
    return render_template('ai_center.html',
                           page='ai_center',
                           page_title=PAGE_TITLES['ai_center'],
                           nav_items=get_nav_items('ai_center'),
                           user=get_current_user())


@app.route('/forum')
def forum():
    return render_template('forum.html',
                           page='forum',
                           page_title=PAGE_TITLES['forum'],
                           nav_items=get_nav_items('forum'),
                           user=get_current_user())


@app.route('/science')
def science():
    selected_category = request.args.get('category')

    categories = set()
    for article in ARTICLES:
        if len(article['tags']) >= 3:
            categories.add(article['tags'][2])

    if selected_category:
        filtered_articles = [article for article in ARTICLES
                             if len(article['tags']) >= 3 and article['tags'][2] == selected_category]
    else:
        filtered_articles = ARTICLES

    return render_template('science.html',
                           page='science',
                           page_title=PAGE_TITLES['science'],
                           nav_items=get_nav_items('science'),
                           user=get_current_user(),
                           articles=ARTICLES,
                           categories=sorted(categories),
                           selected_category=selected_category,
                           filtered_articles=filtered_articles)


# ========== 需要登录的页面路由 ==========

@app.route('/my')
def my():
    # 获取当前用户模式
    current_user = get_current_user()
    user_mode = session.get('mode', 'public')
    if current_user and current_user.get('mode'):
        user_mode = current_user['mode']
    return render_template('my.html',
                           page='my',
                           page_title=PAGE_TITLES['my'],
                           nav_items=get_nav_items('my'),
                           user=current_user,
                           user_mode=user_mode)



# ========== AI聊天API ==========

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI聊天接口"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400

        if not dashscope.api_key:
            return jsonify({'error': 'API Key未配置，请在.env文件中设置DASHSCOPE_API_KEY'}), 500

        messages = [
            {"role": "system",
             "content": "你是一个专业的医疗AI助手，可以回答医疗健康相关的问题。请注意：你的回答仅供参考，不能替代专业医生的诊断。如果用户有严重症状，请建议他们及时就医。"},
            {"role": "user", "content": user_message}
        ]

        response = Generation.call(
            model='qwen-turbo',
            messages=messages
        )

        print(f"Response status: {response.status_code}")
        print(f"Response output: {response.output}")
        print(f"Response output type: {type(response.output)}")

        if response.status_code == 200:
            if response.output:
                print(f"Output attributes: {dir(response.output)}")
                if hasattr(response.output, 'text'):
                    ai_response = response.output.text
                    return jsonify({
                        'success': True,
                        'response': ai_response
                    })
                elif hasattr(response.output, 'choices') and response.output.choices:
                    ai_response = response.output.choices[0].message.content
                    return jsonify({
                        'success': True,
                        'response': ai_response
                    })
                else:
                    return jsonify({
                        'error': 'AI响应格式错误，请稍后重试'
                    }), 500
            else:
                return jsonify({
                    'error': 'AI响应为空，请稍后重试'
                }), 500
        else:
            return jsonify({
                'error': f'AI服务错误: {response.message}'
            }), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'服务器错误: {str(e)}'
        }), 500


# ========== 图像分割API代理 ==========

@app.route('/api/segment', methods=['POST'])
def segment_image():
    """图像分割代理接口 - 转发到后端分割服务"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名不能为空'}), 400

        # 将文件读取到内存
        file_content = file.read()

        # 计算MD5哈希值
        image_hash = hashlib.md5(file_content).hexdigest()
        print(f"\n[前端] 收到分割请求")
        print(f"[前端] 文件名: {file.filename}")
        print(f"[前端] MD5哈希: {image_hash}")

        # 转发到后端分割服务
        files = {'file': (file.filename, io.BytesIO(file_content), file.content_type or 'image/jpeg')}
        response = requests.post(SEGMENT_API_URL, files=files, timeout=120)

        if response.status_code == 200:
            result = response.json()
            # 将哈希值添加到返回结果中
            result['image_hash'] = image_hash
            print(f"[前端] 分割成功，数据集: {result.get('dataset', 'unknown')}")
            if result.get('original_name'):
                print(f"[前端] 匹配原图: {result['original_name']}")
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': f'分割服务错误: {response.status_code}'
            }), 500

    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': '无法连接到分割服务，请确认后端服务已启动 (python api_web_final.py)'
        }), 503
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


# ========== 图像分类API代理 ==========

@app.route('/api/classify', methods=['POST'])
def classify_image():
    """图像分类代理接口 - 转发到后端分类服务"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名不能为空'}), 400

        file_content = file.read()
        image_hash = hashlib.md5(file_content).hexdigest()
        print(f"\n[前端] 收到分类请求")
        print(f"[前端] 文件名: {file.filename}")
        print(f"[前端] MD5哈希: {image_hash}")

        files = {'file': (file.filename, io.BytesIO(file_content), file.content_type or 'image/jpeg')}
        response = requests.post(CLASSIFY_API_URL, files=files, timeout=120)

        if response.status_code == 200:
            result = response.json()
            result['image_hash'] = image_hash
            print(f"[前端] 分类成功，类别: {result.get('class_name', 'unknown')}")
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': f'分类服务错误: {response.status_code}'
            }), 500

    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': '无法连接到分类服务，请确认后端分类服务已启动'
        }), 503
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/segment-health', methods=['GET'])
def segment_health():
    """检查分割服务健康状态"""
    try:
        response = requests.get(SEGMENT_API_URL.replace('/api/segment', '/api/health'), timeout=5)
        if response.status_code == 200:
            return jsonify({'status': 'ok', 'segment_service': 'connected'})
        else:
            return jsonify({'status': 'error', 'segment_service': 'unavailable'}), 503
    except:
        return jsonify({'status': 'error', 'segment_service': 'not_running'}), 503


# ========== AI健康趋势分析API ==========

@app.route('/api/trend-analysis', methods=['POST'])
def trend_analysis():
    """AI健康趋势分析接口 - 基于检测记录和描述进行趋势分析"""
    try:
        data = request.get_json()
        records = data.get('records', [])
        description = data.get('description', '')

        if not records and not description:
            return jsonify({'success': False, 'error': '请提供检测记录或描述信息'}), 400

        if not dashscope.api_key:
            return jsonify({'success': False, 'error': 'API Key未配置，请在.env文件中设置DASHSCOPE_API_KEY'}), 500

        prompt = build_trend_analysis_prompt(records, description)

        messages = [
            {"role": "system",
             "content": "你是一位专业的医疗AI分析师，擅长分析医学影像分割检测数据的健康趋势。请基于提供的检测记录数据和用户描述，给出专业、客观的健康趋势分析。请注意：你的分析仅供参考，不能替代专业医生的诊断。"},
            {"role": "user", "content": prompt}
        ]

        response = Generation.call(
            model='qwen-turbo',
            messages=messages
        )

        if response.status_code == 200:
            if response.output:
                if hasattr(response.output, 'text'):
                    ai_response = response.output.text
                    return jsonify({'success': True, 'response': ai_response})
                elif hasattr(response.output, 'choices') and response.output.choices:
                    ai_response = response.output.choices[0].message.content
                    return jsonify({'success': True, 'response': ai_response})
                else:
                    return jsonify({'success': False, 'error': 'AI响应格式错误，请稍后重试'}), 500
            else:
                return jsonify({'success': False, 'error': 'AI响应为空，请稍后重试'}), 500
        else:
            return jsonify({'success': False, 'error': f'AI服务错误: {response.message}'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500


def build_trend_analysis_prompt(records, description):
    """构建趋势分析的AI提示词"""

    def safe_format_metric(value):
        """安全格式化指标值，支持数字和字符串"""
        try:
            return f"{float(value):.4f}"
        except (ValueError, TypeError):
            return str(value) if value is not None else 'N/A'

    prompt = "请对以下医学影像分割检测数据进行健康趋势分析：\n\n"

    if records:
        prompt += "【检测记录数据】\n"
        for idx, record in enumerate(records, 1):
            prompt += f"\n--- 记录 {idx} ---\n"
            prompt += f"检测时间：{record.get('time', '未知')}\n"
            prompt += f"数据集：{record.get('dataset', '未知').upper()}\n"
            prompt += f"原图名称：{record.get('original_name', '未知')}\n"

            metrics = record.get('metrics', {})
            if metrics:
                prompt += "分割质量指标：\n"
                if metrics.get('accuracy') is not None:
                    prompt += f"  - Accuracy（准确率）: {safe_format_metric(metrics['accuracy'])}\n"
                if metrics.get('dice_kidney') is not None:
                    prompt += f"  - Dice_Kidney（肾脏Dice系数）: {safe_format_metric(metrics['dice_kidney'])}\n"
                if metrics.get('iou_kidney') is not None:
                    prompt += f"  - IoU_Kidney（肾脏交并比）: {safe_format_metric(metrics['iou_kidney'])}\n"
                if metrics.get('hd95_kidney') is not None:
                    prompt += f"  - HD95_Kidney（肾脏95%豪斯多夫距离）: {safe_format_metric(metrics['hd95_kidney'])}\n"
        prompt += "\n"

    if description:
        prompt += "【用户补充描述】\n"
        prompt += description + "\n\n"

    prompt += """请从以下几个方面进行专业分析：

1. **数据概览**：总结检测记录的基本情况（数据集类型、检测次数、时间跨度等）

2. **指标解读**：
   - 解释各项分割指标的含义（Accuracy、Dice、IoU、HD95、Precision、Recall）
   - 分析各指标数值反映的检测质量

3. **趋势分析**：
   - 对比多条记录的分割指标变化趋势
   - 识别指标改善或恶化的模式
   - 分析可能的原因

4. **健康评估**：
   - 基于分割结果评估病灶/病变情况
   - 判断病情发展趋势（稳定、改善、恶化）

5. **建议与注意事项**：
   - 给出后续检查建议
   - 日常健康管理建议
   - 何时需要就医

6. **风险提示**：
   - 指出需要特别关注的指标或变化
   - 提醒可能存在的风险

请注意：
- 分析应客观、专业，避免过度解读
- 明确指出这是基于AI分割结果的分析，仅供参考
- 建议用户在必要时咨询专业医生
- 使用通俗易懂的语言，让普通用户也能理解"""

    return prompt

# ========== 病例对比分析API ==========

@app.route('/api/case-comparison', methods=['POST'])
def case_comparison():
    """病例对比分析接口 - 对比同一患者不同时间点的检测记录"""
    try:
        data = request.get_json()
        patient_name = data.get('patient_name', '')
        records = data.get('records', [])
        description = data.get('description', '')

        if not records or len(records) < 2:
            return jsonify({'success': False, 'error': '请至少提供2条检测记录进行对比'}), 400

        if not dashscope.api_key:
            return jsonify({'success': False, 'error': 'API Key未配置，请在.env文件中设置DASHSCOPE_API_KEY'}), 500

        prompt = build_case_comparison_prompt(patient_name, records, description)

        messages = [
            {"role": "system",
             "content": "你是一位资深的医学影像AI分析专家，擅长对比分析同一患者不同时间点的医学影像分割数据，评估病情变化趋势和治疗效果。请基于提供的病例对比数据，给出专业、客观的对比分析报告。请注意：你的分析仅供参考，不能替代专业医生的诊断意见。"},
            {"role": "user", "content": prompt}
        ]

        response = Generation.call(
            model='qwen-turbo',
            messages=messages
        )

        if response.status_code == 200:
            if response.output:
                if hasattr(response.output, 'text'):
                    ai_response = response.output.text
                    return jsonify({'success': True, 'response': ai_response})
                elif hasattr(response.output, 'choices') and response.output.choices:
                    ai_response = response.output.choices[0].message.content
                    return jsonify({'success': True, 'response': ai_response})
                else:
                    return jsonify({'success': False, 'error': 'AI响应格式错误，请稍后重试'}), 500
            else:
                return jsonify({'success': False, 'error': 'AI响应为空，请稍后重试'}), 500
        else:
            return jsonify({'success': False, 'error': f'AI服务错误: {response.message}'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500


def build_case_comparison_prompt(patient_name, records, description):
    """构建病例对比分析的AI提示词"""

    def safe_format_metric(value):
        """安全格式化指标值"""
        try:
            return f"{float(value):.4f}"
        except (ValueError, TypeError):
            return str(value) if value is not None else 'N/A'

    first_record = records[0]

    prompt = f"请对以下同一患者不同时间点的医学影像分割检测数据进行对比分析：\n\n"

    prompt += "【患者基本信息】\n"
    prompt += f"姓名：{first_record.get('patientName', '未知')}\n"
    prompt += f"年龄：{first_record.get('patientAge', '未知')} 岁\n"
    prompt += f"性别：{first_record.get('patientGender', '未知')}\n"
    prompt += f"科室：{first_record.get('patientDepartment', '未知')}\n"
    if first_record.get('patientId'):
        prompt += f"病历号：{first_record['patientId']}\n"
    if first_record.get('patientRemark'):
        prompt += f"备注：{first_record['patientRemark']}\n"
    prompt += "\n"

    prompt += "【对比检测记录】\n"
    prompt += f"共 {len(records)} 条检测记录，按时间顺序排列：\n"

    for idx, record in enumerate(records, 1):
        prompt += f"\n--- 第 {idx} 次检测 ---\n"
        prompt += f"检测时间：{record.get('time', '未知')}\n"
        prompt += f"数据集：{record.get('dataset', '未知').upper()}\n"
        prompt += f"原图名称：{record.get('original_name', '未知')}\n"
        prompt += f"预测图名称：{record.get('predict_name', '未知')}\n"
        if record.get('gold_name'):
            prompt += f"金标准名称：{record.get('gold_name', '未知')}\n"

        metrics = record.get('metrics', {})
        if metrics:
            prompt += "分割质量指标：\n"
            if metrics.get('accuracy') is not None:
                prompt += f"  - Accuracy（准确率）: {safe_format_metric(metrics['accuracy'])}\n"
            if metrics.get('dice_kidney') is not None:
                prompt += f"  - Dice_Kidney（肾脏Dice系数）: {safe_format_metric(metrics['dice_kidney'])}\n"
            if metrics.get('iou_kidney') is not None:
                prompt += f"  - IoU_Kidney（肾脏交并比）: {safe_format_metric(metrics['iou_kidney'])}\n"
            if metrics.get('hd95_kidney') is not None:
                prompt += f"  - HD95_Kidney（肾脏95%豪斯多夫距离）: {safe_format_metric(metrics['hd95_kidney'])}\n"

    if len(records) >= 2:
        prompt += "\n【指标变化统计】\n"
        metric_labels = ['accuracy', 'dice_kidney', 'iou_kidney', 'hd95_kidney']
        metric_names = ['Accuracy', 'Dice_Kidney', 'IoU_Kidney', 'HD95_Kidney']
        for label, name in zip(metric_labels, metric_names):
            first_val = records[0].get('metrics', {}).get(label)
            last_val = records[-1].get('metrics', {}).get(label)
            if first_val is not None and last_val is not None:
                try:
                    diff = float(last_val) - float(first_val)
                    pct = (diff / abs(float(first_val))) * 100 if float(first_val) != 0 else 0
                    direction = "上升" if diff > 0 else ("下降" if diff < 0 else "持平")
                    prompt += f"  - {name}: {safe_format_metric(first_val)} → {safe_format_metric(last_val)} ({direction} {abs(pct):.1f}%)\n"
                except (ValueError, TypeError):
                    pass

    prompt += "\n"

    if description:
        prompt += "【医生/用户补充描述】\n"
        prompt += description + "\n\n"

    prompt += """请从以下方面进行专业的病例对比分析：

1. **患者概况**：简要总结患者基本信息和检测背景

2. **分割质量对比**：
   - 逐项对比各次检测的分割指标（Accuracy、Dice、IoU、HD95、Precision、Recall）
   - 分析指标变化的意义（如Dice系数提高可能意味着分割精度改善）
   - 注意HD95指标的特殊性（值越低越好，表示分割边界与金标准越接近）

3. **病情变化趋势分析**：
   - 基于分割结果的变化，分析病灶/病变区域的变化趋势
   - 评估病情是稳定、改善还是恶化
   - 分析可能的临床意义

4. **治疗效果评估**（如适用）：
   - 如果有治疗信息，结合指标变化评估治疗效果
   - 对比治疗前后的分割结果差异

5. **风险提示与关注重点**：
   - 指出需要特别关注的指标变化
   - 提示可能存在的风险
   - 标记需要紧急关注的情况

6. **建议**：
   - 后续检查建议（复查频率、检查项目等）
   - 治疗方案调整建议（如适用）
   - 日常管理建议

请注意：
- 分析应客观、专业，基于数据说话
- 明确标注这是AI辅助分析，仅供参考
- 建议结合临床实际和其他检查结果综合判断
- 如发现异常变化，建议及时就医或会诊
- 使用专业但易懂的语言"""

    return prompt


# ========== AI单条记录智能分析API ==========

@app.route('/api/record-analysis', methods=['POST'])
def record_analysis():
    """AI单条检测记录智能分析接口 - 对分割或分类结果进行深度分析"""
    try:
        data = request.get_json()
        record = data.get('record', {})

        if not record:
            return jsonify({'success': False, 'error': '请提供检测记录数据'}), 400

        if not dashscope.api_key:
            return jsonify({'success': False, 'error': 'API Key未配置，请在.env文件中设置DASHSCOPE_API_KEY'}), 500

        prompt = build_record_analysis_prompt(record)

        messages = [
            {"role": "system",
             "content": "你是一位资深的医学影像AI分析专家，擅长对单条医学影像分割或分类检测结果进行深度智能分析。请基于提供的检测数据，给出专业、全面、通俗易懂的医学分析。请注意：你的分析仅供参考，不能替代专业医生的诊断意见。请使用中文回答。"},
            {"role": "user", "content": prompt}
        ]

        response = Generation.call(
            model='qwen-turbo',
            messages=messages
        )

        if response.status_code == 200:
            if response.output:
                if hasattr(response.output, 'text'):
                    ai_response = response.output.text
                    return jsonify({'success': True, 'response': ai_response})
                elif hasattr(response.output, 'choices') and response.output.choices:
                    ai_response = response.output.choices[0].message.content
                    return jsonify({'success': True, 'response': ai_response})
                else:
                    return jsonify({'success': False, 'error': 'AI响应格式错误，请稍后重试'}), 500
            else:
                return jsonify({'success': False, 'error': 'AI响应为空，请稍后重试'}), 500
        else:
            return jsonify({'success': False, 'error': f'AI服务错误: {response.message}'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500


def build_record_analysis_prompt(record):
    """构建单条记录AI分析的提示词"""

    def safe_format_metric(value):
        """安全格式化指标值"""
        try:
            return f"{float(value):.4f}"
        except (ValueError, TypeError):
            return str(value) if value is not None else 'N/A'

    is_classify = record.get('mode') == 'classify'
    dataset = record.get('dataset', 'unknown')

    prompt = "请对以下医学影像检测结果进行全面的智能分析：\n\n"

    # 基本信息
    prompt += "【检测基本信息】\n"
    prompt += f"检测时间：{record.get('time', '未知')}\n"
    prompt += f"检测模式：{'图像分类' if is_classify else '图像分割'}\n"
    prompt += f"数据集：{dataset.upper()}\n"
    if record.get('original_name'):
        prompt += f"原图名称：{record.get('original_name')}\n"
    if record.get('predict_name'):
        prompt += f"预测图名称：{record.get('predict_name')}\n"
    if record.get('gold_name'):
        prompt += f"金标准名称：{record.get('gold_name')}\n"
    prompt += "\n"

    # 分类模式数据
    if is_classify:
        prompt += "【分类结果数据】\n"
        prompt += f"预测类别：{record.get('class_name', '未知')}\n"
        confidence = record.get('confidence', 0)
        prompt += f"置信度：{(confidence * 100):.2f}%\n"
        prompt += "\n"
    else:
        # 分割模式数据
        prompt += "【分割质量指标】\n"
        metrics = record.get('metrics', {})
        if metrics:
            if metrics.get('accuracy') is not None:
                prompt += f"  - Accuracy（准确率）: {safe_format_metric(metrics['accuracy'])}\n"
            if metrics.get('dice_kidney') is not None:
                prompt += f"  - Dice_Kidney（肾脏Dice系数）: {safe_format_metric(metrics['dice_kidney'])}\n"
            if metrics.get('iou_kidney') is not None:
                prompt += f"  - IoU_Kidney（肾脏交并比）: {safe_format_metric(metrics['iou_kidney'])}\n"
            if metrics.get('hd95_kidney') is not None:
                prompt += f"  - HD95_Kidney（肾脏95%豪斯多夫距离）: {safe_format_metric(metrics['hd95_kidney'])}\n"
        else:
            prompt += "  无分割指标数据\n"
        prompt += "\n"

    # 数据集背景知识
    prompt += "【数据集背景】\n"
    if dataset == 'kits19':
        prompt += "该数据集为KiTS19（Kidney Tumor Segmentation 2019），用于肾脏肿瘤分割。包含肾脏、肾肿瘤和背景的三类分割。\n"
    elif dataset == 'lidc':
        prompt += "该数据集为LIDC-IDRI（Lung Image Database Consortium），用于肺结节检测与分割。\n"
    else:
        prompt += "数据集信息未知。\n"
    prompt += "\n"

    prompt += """请作为一位经验丰富、语言生动的医学影像诊断专家，基于本次检测所针对的医学切片图像，撰写一份专业而富有人文关怀的医学分析报告。

【角色设定】
你是一位既专业严谨又善于沟通的放射科医生，擅长用通俗易懂的语言向患者解释复杂的医学影像。你的报告既有医学专业性，又充满温度和关怀。

【分析原则】
- 分析对象是医学影像切片本身反映的病理情况，而非AI模型的分割性能
- 报告要像与患者面对面交流一样自然、生动
- 适当使用比喻、举例等方式让医学知识更易理解
- 避免过于死板的学术腔调，语言要有亲和力

【报告结构】请按以下维度展开，每个部分都要充实、具体：


1. 病灶可能性评估
   基于模型检测结果，评估是否存在异常。用"可能性较高/中等/较低"等表述，避免绝对化。解释为什么会这样判断，让患者理解依据。

2. 影像特征描述
   详细描述切片中可见的组织结构。如有异常区域，描述其：位置（具体在器官的哪个部位）、大小（可用日常物品比喻）、形态（圆形/不规则等）、边界（清晰/模糊）、密度/信号特点等。如无明显异常，描述正常组织的表现。

3. 临床意义解读
   将影像发现与患者的健康状况联系起来。用通俗的语言解释：这可能意味着什么？

4. 生活调理建议
   根据分析结果，给出具体可操作的建议：饮食上吃什么、避免什么？生活习惯上如何调整？心理上如何保持平和？运动方面有什么建议？


5. 温馨提示
   用温暖的语言提醒：AI分析只是辅助参考，最终诊断需要医生结合完整资料判断。鼓励患者积极面对，不要过度焦虑，也不要忽视问题。


【写作要求】
- 语言风格：专业但不晦涩，亲切但不随意，像一位耐心的医生在详细解释
- 内容深度：每个部分都要充实，不要简单几句话带过，要让患者获得足够的信息
- 表达方式：适当使用"您"来称呼患者，增加亲切感；可以用"打个比方""简单来说"等过渡语
- 重点突出：关键信息可以用"**重点内容**"的形式标注
- 避免使用：HTML标签、Markdown代码语法、表格、列表符号等格式标记
- 字数要求：报告应充实丰富，总字数建议在500-800字之间
- 免责声明：在报告开头和结尾处，必须明确标注"本分析由AI辅助生成，仅供参考，不能替代专业医生的诊断意见。如有异常发现，请务必及时前往正规医院就诊，由专业医生结合完整临床资料进行诊断。"""

    return prompt


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
