from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import json
import random
from datetime import datetime, date, timedelta
import os

app = Flask(__name__)

DATABASE = 'vocabulary.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    
    # 总词库表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS master_vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            phonetic TEXT,
            translation TEXT,
            example_sentence TEXT,
            status TEXT DEFAULT 'unlearned'
        )
    ''')
    
    # 每日词池表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_word_id INTEGER,
            date TEXT,
            group_number INTEGER,
            FOREIGN KEY (master_word_id) REFERENCES master_vocabulary (id)
        )
    ''')
    
    # 每日学习表 - R1认
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_r1_recognition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_pool_id INTEGER,
            word TEXT,
            phonetic TEXT,
            translation TEXT,
            example_sentence TEXT,
            is_mastered INTEGER DEFAULT 0,
            FOREIGN KEY (daily_pool_id) REFERENCES daily_pool (id)
        )
    ''')
    
    # 每日学习表 - R2写
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_r2_spelling (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_pool_id INTEGER,
            word TEXT,
            phonetic TEXT,
            translation TEXT,
            example_sentence TEXT,
            is_mastered INTEGER DEFAULT 0,
            FOREIGN KEY (daily_pool_id) REFERENCES daily_pool (id)
        )
    ''')
    
    # 每日学习表 - R3听（预留）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_r3_listening (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_pool_id INTEGER,
            word TEXT,
            phonetic TEXT,
            translation TEXT,
            example_sentence TEXT,
            is_mastered INTEGER DEFAULT 0,
            FOREIGN KEY (daily_pool_id) REFERENCES daily_pool (id)
        )
    ''')
    
    # 每日学习表 - R4说（预留）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_r4_speaking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_pool_id INTEGER,
            word TEXT,
            phonetic TEXT,
            translation TEXT,
            example_sentence TEXT,
            is_mastered INTEGER DEFAULT 0,
            FOREIGN KEY (daily_pool_id) REFERENCES daily_pool (id)
        )
    ''')
    
    # 学习记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_word_id INTEGER,
            first_studied_at TEXT,
            FOREIGN KEY (master_word_id) REFERENCES master_vocabulary (id)
        )
    ''')
    
    # 复习队列表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learning_record_id INTEGER,
            master_word_id INTEGER,
            next_review_date TEXT,
            review_interval INTEGER,
            FOREIGN KEY (learning_record_id) REFERENCES learning_records (id),
            FOREIGN KEY (master_word_id) REFERENCES master_vocabulary (id)
        )
    ''')
    
    # 学习进度表 - 检查并添加缺失的字段
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            current_stage TEXT,
            current_group INTEGER,
            current_round INTEGER,
            current_dimension TEXT,
            stage_progress TEXT,
            completed_stages TEXT
        )
    ''')
    
    # 检查并添加缺失的字段（用于升级现有数据库）
    try:
        conn.execute('SELECT stage_progress FROM daily_progress LIMIT 1')
    except:
        conn.execute('ALTER TABLE daily_progress ADD COLUMN stage_progress TEXT')
        
    try:
        conn.execute('SELECT completed_stages FROM daily_progress LIMIT 1')
    except:
        conn.execute('ALTER TABLE daily_progress ADD COLUMN completed_stages TEXT')
    
    conn.commit()
    conn.close()

def import_vocabulary_from_json():
    """从JSON文件导入词汇到master_vocabulary表"""
    conn = get_db()
    
    # 检查是否已经导入过数据
    count = conn.execute('SELECT COUNT(*) FROM master_vocabulary').fetchone()[0]
    if count > 0:
        print(f"词汇库已存在 {count} 个单词")
        conn.close()
        return
    
    try:
        with open('CET4luan_2.json', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                data = json.loads(line)
                word_info = data['content']['word']
                
                # 提取信息
                word = word_info['wordHead']
                phonetic = word_info.get('content', {}).get('usphone', '')
                
                # 获取中文释义
                translations = []
                trans_list = word_info.get('content', {}).get('trans', [])
                for trans in trans_list:
                    translations.append(trans.get('tranCn', ''))
                translation = '；'.join(filter(None, translations))
                
                # 获取例句
                example_sentence = ''
                sentences = word_info.get('content', {}).get('sentence', {}).get('sentences', [])
                if sentences:
                    example_sentence = sentences[0].get('sContent', '')
                
                # 插入数据库
                conn.execute('''
                    INSERT OR IGNORE INTO master_vocabulary 
                    (word, phonetic, translation, example_sentence, status)
                    VALUES (?, ?, ?, ?, 'unlearned')
                ''', (word, phonetic, translation, example_sentence))
        
        conn.commit()
        imported_count = conn.execute('SELECT COUNT(*) FROM master_vocabulary').fetchone()[0]
        print(f"成功导入 {imported_count} 个单词到词汇库")
        
    except Exception as e:
        print(f"导入词汇时出错: {e}")
    finally:
        conn.close()

class LearningFlowManager:
    """自动化学习流程管理器"""
    
    LEARNING_STAGES = [
        # 第1组：认→写→认→写→认→写（3轮）
        {'stage': 'group1_main', 'group': 1, 'dimensions': ['recognition', 'spelling'], 'rounds': 3},
        # 第2组：认→写→认→写→认→写（3轮）  
        {'stage': 'group2_main', 'group': 2, 'dimensions': ['recognition', 'spelling'], 'rounds': 3},
        # 交叉复习：第1组(认→写)1轮 + 第2组(认→写)1轮
        {'stage': 'cross_review_1_2', 'groups': [1, 2], 'dimensions': ['recognition', 'spelling'], 'rounds': 1},
        # 第3组：认→写→认→写→认→写（3轮）
        {'stage': 'group3_main', 'group': 3, 'dimensions': ['recognition', 'spelling'], 'rounds': 3},
        # 交叉复习：第2组(认→写)1轮 + 第3组(认→写)1轮  
        {'stage': 'cross_review_2_3', 'groups': [2, 3], 'dimensions': ['recognition', 'spelling'], 'rounds': 1},
        # 大乱斗（可选）
        {'stage': 'final_battle', 'groups': [1, 2, 3], 'dimensions': ['recognition', 'spelling'], 'rounds': 1}
    ]
    
    @staticmethod
    def get_current_progress(date_str):
        """获取当前学习进度"""
        conn = get_db()
        progress = conn.execute(
            'SELECT * FROM daily_progress WHERE date = ?', (date_str,)
        ).fetchone()
        conn.close()
        
        if not progress:
            return LearningFlowManager.create_initial_progress(date_str)
        
        return {
            'current_stage': progress['current_stage'] or 'group1_main',
            'current_group': progress['current_group'] or 1,
            'current_round': progress['current_round'] or 1,
            'current_dimension': progress['current_dimension'] or 'recognition',
            'stage_progress': json.loads(progress['stage_progress'] or '{}'),
            'completed_stages': json.loads(progress['completed_stages'] or '[]')
        }
    
    @staticmethod
    def create_initial_progress(date_str):
        """创建初始学习进度"""
        initial_progress = {
            'current_stage': 'group1_main',
            'current_group': 1,
            'current_round': 1,
            'current_dimension': 'recognition',
            'stage_progress': {},
            'completed_stages': []
        }
        
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO daily_progress 
            (date, current_stage, current_group, current_round, current_dimension, stage_progress, completed_stages)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            date_str, 
            initial_progress['current_stage'],
            initial_progress['current_group'],
            initial_progress['current_round'],
            initial_progress['current_dimension'],
            json.dumps(initial_progress['stage_progress']),
            json.dumps(initial_progress['completed_stages'])
        ))
        conn.commit()
        conn.close()
        
        return initial_progress
    
    @staticmethod
    def update_progress(date_str, progress):
        """更新学习进度"""
        conn = get_db()
        conn.execute('''
            UPDATE daily_progress 
            SET current_stage = ?, current_group = ?, current_round = ?, 
                current_dimension = ?, stage_progress = ?, completed_stages = ?
            WHERE date = ?
        ''', (
            progress['current_stage'],
            progress['current_group'],
            progress['current_round'],
            progress['current_dimension'],
            json.dumps(progress['stage_progress']),
            json.dumps(progress['completed_stages']),
            date_str
        ))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_current_stage_info(stage_name):
        """获取当前阶段信息"""
        for stage in LearningFlowManager.LEARNING_STAGES:
            if stage['stage'] == stage_name:
                return stage
        return None
    
    @staticmethod
    def advance_to_next_phase(progress):
        """推进到下一个学习阶段"""
        current_stage_info = LearningFlowManager.get_current_stage_info(progress['current_stage'])
        
        if not current_stage_info:
            return progress
        
        # 检查是否是交叉复习阶段
        is_cross_review = 'cross_review' in progress['current_stage']
        
        if is_cross_review:
            # 交叉复习逻辑：需要处理多个组
            return LearningFlowManager.advance_cross_review_phase(progress, current_stage_info)
        else:
            # 单组学习逻辑
            return LearningFlowManager.advance_single_group_phase(progress, current_stage_info)
    
    @staticmethod
    def reset_round_progress(date_str, group, dimension):
        """重置指定组和维度的单词掌握状态，用于开始新一轮学习"""
        conn = get_db()
        
        table_map = {
            'recognition': 'daily_r1_recognition',
            'spelling': 'daily_r2_spelling'
        }
        
        if dimension not in table_map:
            conn.close()
            return
            
        table_name = table_map[dimension]
        
        # 重置指定组和维度的单词掌握状态，只重置状态1（掌握了），不重置状态2（我会这个）
        conn.execute(f'''
            UPDATE {table_name} SET is_mastered = 0
            WHERE daily_pool_id IN (
                SELECT id FROM daily_pool WHERE date = ? AND group_number = ?
            ) AND is_mastered = 1
        ''', (date_str, group))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def advance_single_group_phase(progress, stage_info):
        """推进单组学习阶段"""
        # 在同一轮内，先完成认，再完成写
        if progress['current_dimension'] == 'recognition':
            progress['current_dimension'] = 'spelling'
            return progress
        
        # 如果写也完成了，检查是否需要下一轮
        if progress['current_round'] < stage_info['rounds']:
            progress['current_round'] += 1
            progress['current_dimension'] = 'recognition'
            
            # 重置当前组的所有维度的掌握状态，开始新一轮
            from datetime import date
            today_str = date.today().isoformat()
            LearningFlowManager.reset_round_progress(today_str, progress['current_group'], 'recognition')
            LearningFlowManager.reset_round_progress(today_str, progress['current_group'], 'spelling')
            
            return progress
        
        # 当前阶段完成，进入下一个阶段
        return LearningFlowManager.move_to_next_stage(progress)
    
    @staticmethod
    def advance_cross_review_phase(progress, stage_info):
        """推进交叉复习阶段"""
        groups = stage_info['groups']
        current_group_index = groups.index(progress['current_group'])
        
        # 在同一组内，先完成认，再完成写
        if progress['current_dimension'] == 'recognition':
            progress['current_dimension'] = 'spelling'
            return progress
        
        # 如果当前组的写也完成了，切换到下一组
        if current_group_index < len(groups) - 1:
            progress['current_group'] = groups[current_group_index + 1]
            progress['current_dimension'] = 'recognition'
            return progress
        
        # 所有组都完成，进入下一个阶段
        return LearningFlowManager.move_to_next_stage(progress)
    
    @staticmethod
    def move_to_next_stage(progress):
        """移动到下一个学习阶段"""
        current_stage_index = None
        for i, stage in enumerate(LearningFlowManager.LEARNING_STAGES):
            if stage['stage'] == progress['current_stage']:
                current_stage_index = i
                break
        
        if current_stage_index is None or current_stage_index >= len(LearningFlowManager.LEARNING_STAGES) - 1:
            # 所有阶段完成
            progress['current_stage'] = 'completed'
            return progress
        
        # 移动到下一阶段
        next_stage = LearningFlowManager.LEARNING_STAGES[current_stage_index + 1]
        progress['completed_stages'].append(progress['current_stage'])
        progress['current_stage'] = next_stage['stage']
        progress['current_round'] = 1
        progress['current_dimension'] = 'recognition'
        
        # 设置当前组（单组或交叉复习的第一组）
        if 'group' in next_stage:
            progress['current_group'] = next_stage['group']
        elif 'groups' in next_stage:
            progress['current_group'] = next_stage['groups'][0]
        
        return progress
    
    @staticmethod
    def get_stage_description(stage_name, group, round_num, dimension):
        """获取阶段描述"""
        stage_info = LearningFlowManager.get_current_stage_info(stage_name)
        if not stage_info:
            return "未知阶段"
        
        dimension_name = "认（英译汉）" if dimension == 'recognition' else "写（汉译英）"
        
        if stage_name == 'group1_main':
            return f"第1组主学习 - 第{round_num}轮{dimension_name}"
        elif stage_name == 'group2_main':
            return f"第2组主学习 - 第{round_num}轮{dimension_name}"
        elif stage_name == 'group3_main':
            return f"第3组主学习 - 第{round_num}轮{dimension_name}"
        elif stage_name == 'cross_review_1_2':
            return f"交叉复习(1-2组) - 第{group}组{dimension_name}"
        elif stage_name == 'cross_review_2_3':
            return f"交叉复习(2-3组) - 第{group}组{dimension_name}"
        elif stage_name == 'final_battle':
            return f"大乱斗模式 - 第{group}组{dimension_name}"
        elif stage_name == 'completed':
            return "🎉 今日学习全部完成！"
        
        return f"{stage_name} - 第{group}组第{round_num}轮{dimension_name}"

def check_and_migrate_unfinished_tasks():
    """检查并迁移前一天未完成的任务到今天"""
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    today_str = today.isoformat()
    
    conn = get_db()
    
    # 检查昨天是否有未完成的学习任务
    yesterday_progress = conn.execute(
        'SELECT * FROM daily_progress WHERE date = ?', (yesterday,)
    ).fetchone()
    
    if not yesterday_progress:
        conn.close()
        return False, "昨天没有学习记录"
    
    # 检查昨天的任务是否已完成
    if yesterday_progress['current_stage'] == 'completed':
        conn.close()
        return False, "昨天的任务已完成"
    
    # 检查今天是否已有任务或进度记录
    today_pool = conn.execute(
        'SELECT COUNT(*) FROM daily_pool WHERE date = ?', (today_str,)
    ).fetchone()[0]
    
    today_progress = conn.execute(
        'SELECT COUNT(*) FROM daily_progress WHERE date = ?', (today_str,)
    ).fetchone()[0]
    
    if today_pool > 0 or today_progress > 0:
        conn.close()
        return False, "今天已有学习任务或进度记录，无法迁移"
    
    print(f"检测到昨天({yesterday})的任务未完成，正在迁移到今天...")
    
    try:
        # 1. 更新daily_pool表中的日期
        conn.execute('UPDATE daily_pool SET date = ? WHERE date = ?', (today_str, yesterday))
        
        # 2. 重置所有学习维度表的掌握状态为0（重新开始学习）
        learning_tables = ['daily_r1_recognition', 'daily_r2_spelling', 'daily_r3_listening', 'daily_r4_speaking']
        for table in learning_tables:
            conn.execute(f'''
                UPDATE {table} SET is_mastered = 0 
                WHERE daily_pool_id IN (
                    SELECT id FROM daily_pool WHERE date = ?
                )
            ''', (today_str,))
        
        # 3. 更新昨天的学习进度记录日期
        # 由于前面已经确认今天没有进度记录，可以直接更新
        conn.execute('''
            UPDATE daily_progress SET 
                date = ?,
                current_stage = 'group1_main',
                current_group = 1,
                current_round = 1,
                current_dimension = 'recognition',
                stage_progress = '{}',
                completed_stages = '[]'
            WHERE date = ?
        ''', (today_str, yesterday))
        
        conn.commit()
        print(f"成功将昨天的任务完整迁移到今天并重置学习状态")
        
        conn.close()
        return True, f"已将昨天({yesterday})未完成的任务迁移到今天并重置学习进度"
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"迁移任务时出错: {e}")
        return False, f"迁移失败: {e}"

def initialize_today_words():
    """初始化今日学习单词"""
    today = date.today().isoformat()
    conn = get_db()
    
    # 检查今日是否已初始化
    existing = conn.execute(
        'SELECT COUNT(*) FROM daily_pool WHERE date = ?', (today,)
    ).fetchone()[0]
    
    if existing > 0:
        conn.close()
        return False  # 已经初始化过
    
    # 先检查并迁移昨天未完成的任务
    migrated, message = check_and_migrate_unfinished_tasks()
    if migrated:
        print(message)
        return True  # 迁移成功，无需重新初始化
    
    # 重新获取数据库连接（因为迁移函数中已关闭）
    conn = get_db()
    
    # 从master_vocabulary中随机选择60个unlearned状态的单词
    unlearned_words = conn.execute('''
        SELECT * FROM master_vocabulary 
        WHERE status = 'unlearned' 
        ORDER BY RANDOM() 
        LIMIT 60
    ''').fetchall()
    
    if len(unlearned_words) < 60:
        conn.close()
        return False  # 可用单词不足60个
    
    # 将这些单词状态改为learning
    word_ids = [word['id'] for word in unlearned_words]
    placeholders = ','.join(['?' for _ in word_ids])
    conn.execute(f'''
        UPDATE master_vocabulary 
        SET status = 'learning' 
        WHERE id IN ({placeholders})
    ''', word_ids)
    
    # 分成3组，每组20个单词
    for group_num in range(1, 4):
        start_idx = (group_num - 1) * 20
        end_idx = start_idx + 20
        group_words = unlearned_words[start_idx:end_idx]
        
        for word in group_words:
            # 插入到daily_pool
            cursor = conn.execute('''
                INSERT INTO daily_pool (master_word_id, date, group_number)
                VALUES (?, ?, ?)
            ''', (word['id'], today, group_num))
            daily_pool_id = cursor.lastrowid
            
            # 复制到4个学习表
            word_data = (
                daily_pool_id, word['word'], word['phonetic'], 
                word['translation'], word['example_sentence']
            )
            
            for table in ['daily_r1_recognition', 'daily_r2_spelling', 
                         'daily_r3_listening', 'daily_r4_speaking']:
                conn.execute(f'''
                    INSERT INTO {table} 
                    (daily_pool_id, word, phonetic, translation, example_sentence)
                    VALUES (?, ?, ?, ?, ?)
                ''', word_data)
    
    conn.commit()
    conn.close()
    return True

def complete_daily_learning():
    """完成今日学习，将词汇标记为learned并加入复习队列"""
    today = date.today().isoformat()
    conn = get_db()
    
    try:
        # 获取今日学习的所有单词
        words_learned = conn.execute('''
            SELECT DISTINCT dp.master_word_id, mv.word
            FROM daily_pool dp
            JOIN master_vocabulary mv ON dp.master_word_id = mv.id
            WHERE dp.date = ?
        ''', (today,)).fetchall()
        
        for word in words_learned:
            master_word_id = word['master_word_id']
            
            # 更新master_vocabulary状态为learned
            conn.execute('''
                UPDATE master_vocabulary 
                SET status = 'learned' 
                WHERE id = ?
            ''', (master_word_id,))
            
            # 插入学习记录
            cursor = conn.execute('''
                INSERT INTO learning_records (master_word_id, first_studied_at)
                VALUES (?, ?)
            ''', (master_word_id, today))
            
            learning_record_id = cursor.lastrowid
            
            # 加入复习队列（第一次复习间隔1天）
            next_review = (date.today() + timedelta(days=1)).isoformat()
            conn.execute('''
                INSERT INTO review_queue 
                (learning_record_id, master_word_id, next_review_date, review_interval)
                VALUES (?, ?, ?, ?)
            ''', (learning_record_id, master_word_id, next_review, 1))
        
        conn.commit()
        print(f"完成今日学习，共{len(words_learned)}个单词加入复习队列")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"完成学习记录时出错: {e}")
        return False
    finally:
        conn.close()

def get_review_words():
    """获取今日需要复习的单词"""
    today = date.today().isoformat()
    conn = get_db()
    
    review_words = conn.execute('''
        SELECT rq.*, mv.word, mv.phonetic, mv.translation, mv.example_sentence,
               lr.first_studied_at
        FROM review_queue rq
        JOIN master_vocabulary mv ON rq.master_word_id = mv.id
        JOIN learning_records lr ON rq.learning_record_id = lr.id
        WHERE rq.next_review_date <= ?
        ORDER BY rq.next_review_date, RANDOM()
    ''', (today,)).fetchall()
    
    conn.close()
    
    return [{
        'id': word['id'],
        'master_word_id': word['master_word_id'],
        'word': word['word'],
        'phonetic': word['phonetic'],
        'translation': word['translation'],
        'example_sentence': word['example_sentence'],
        'review_interval': word['review_interval'],
        'first_studied_at': word['first_studied_at']
    } for word in review_words]

def update_review_schedule(review_id, success):
    """更新复习计划"""
    conn = get_db()
    
    # 获取当前复习记录
    review = conn.execute(
        'SELECT * FROM review_queue WHERE id = ?', (review_id,)
    ).fetchone()
    
    if not review:
        conn.close()
        return False
    
    current_interval = review['review_interval']
    
    if success:
        # 复习成功，增加间隔（艾宾浩斯间隔：1, 2, 4, 7, 15, 30天）
        interval_map = {1: 2, 2: 4, 4: 7, 7: 15, 15: 30, 30: 60}
        new_interval = interval_map.get(current_interval, 60)
        
        if new_interval >= 60:
            # 间隔达到60天，认为已经长期记忆，删除复习记录
            conn.execute('DELETE FROM review_queue WHERE id = ?', (review_id,))
        else:
            # 更新下次复习时间
            next_review = (date.today() + timedelta(days=new_interval)).isoformat()
            conn.execute('''
                UPDATE review_queue 
                SET next_review_date = ?, review_interval = ?
                WHERE id = ?
            ''', (next_review, new_interval, review_id))
    else:
        # 复习失败，重置为1天后复习
        next_review = (date.today() + timedelta(days=1)).isoformat()
        conn.execute('''
            UPDATE review_queue 
            SET next_review_date = ?, review_interval = 1
            WHERE id = ?
        ''', (next_review, review_id))
    
    conn.commit()
    conn.close()
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/today_status')
def today_status():
    today = date.today().isoformat()
    conn = get_db()
    
    # 检查今日是否已初始化
    pool_count = conn.execute(
        'SELECT COUNT(*) FROM daily_pool WHERE date = ?', (today,)
    ).fetchone()[0]
    
    if pool_count == 0:
        conn.close()
        return jsonify({
            'initialized': False,
            'message': '今日单词尚未初始化'
        })
    
    # 检查学习进度
    progress = conn.execute(
        'SELECT * FROM daily_progress WHERE date = ?', (today,)
    ).fetchone()
    
    conn.close()
    
    if progress is None:
        return jsonify({
            'initialized': True,
            'message': '今日单词已准备完毕，共60个单词分为3组'
        })
    else:
        return jsonify({
            'initialized': True,
            'message': f'今日学习进行中：{progress["current_stage"]}'
        })

@app.route('/today_learning')
def today_learning():
    # 检查并初始化今日单词
    if not initialize_today_words():
        # 如果初始化失败，可能是已经初始化过或词汇不足
        pass
    
    return render_template('today_learning.html')

@app.route('/api/learning_progress')
def learning_progress():
    today = date.today().isoformat()
    progress = LearningFlowManager.get_current_progress(today)
    
    # 获取阶段描述
    stage_description = LearningFlowManager.get_stage_description(
        progress['current_stage'], 
        progress['current_group'], 
        progress['current_round'], 
        progress['current_dimension']
    )
    
    return jsonify({
        'current_stage': progress['current_stage'],
        'current_group': progress['current_group'],
        'current_dimension': progress['current_dimension'],
        'current_round': progress['current_round'],
        'stage_description': stage_description,
        'completed_stages': progress['completed_stages']
    })

@app.route('/start_auto_learning')
def start_auto_learning():
    """开始自动化学习"""
    # 检查并初始化今日单词
    if not initialize_today_words():
        pass
    
    today = date.today().isoformat()
    progress = LearningFlowManager.get_current_progress(today)
    
    # 如果已完成所有学习
    if progress['current_stage'] == 'completed':
        return render_template('learning_completed.html')
    
    # 跳转到当前应该学习的内容
    return redirect(url_for('auto_learning_page'))

@app.route('/auto_learning')
def auto_learning_page():
    """自动化学习页面"""
    today = date.today().isoformat()
    progress = LearningFlowManager.get_current_progress(today)
    
    if progress['current_stage'] == 'completed':
        return render_template('learning_completed.html')
    
    return render_template('auto_learning.html', 
                         group=progress['current_group'],
                         dimension=progress['current_dimension'])

@app.route('/api/complete_current_phase', methods=['POST'])
def complete_current_phase():
    """完成当前学习阶段，自动推进到下一阶段"""
    today = date.today().isoformat()
    progress = LearningFlowManager.get_current_progress(today)
    
    # 推进到下一个阶段
    progress = LearningFlowManager.advance_to_next_phase(progress)
    
    # 更新数据库
    LearningFlowManager.update_progress(today, progress)
    
    # 如果所有学习完成，加入复习队列
    if progress['current_stage'] == 'completed':
        complete_daily_learning()
    
    # 返回新的进度信息
    stage_description = LearningFlowManager.get_stage_description(
        progress['current_stage'], 
        progress['current_group'], 
        progress['current_round'], 
        progress['current_dimension']
    )
    
    return jsonify({
        'success': True,
        'next_stage': progress['current_stage'],
        'next_group': progress['current_group'],
        'next_dimension': progress['current_dimension'],
        'stage_description': stage_description,
        'is_completed': progress['current_stage'] == 'completed'
    })

@app.route('/learning/<dimension>/<int:group>')
def learning_page(dimension, group):
    if dimension not in ['recognition', 'spelling', 'listening', 'speaking']:
        return "维度不支持", 400
    
    if group not in [1, 2, 3]:
        return "组别无效", 400
    
    return render_template('learning.html', dimension=dimension, group=group)

@app.route('/api/get_words/<dimension>/<int:group>')
def get_words(dimension, group):
    """获取指定组和维度的单词"""
    today = date.today().isoformat()
    conn = get_db()
    
    # 根据维度确定表名
    table_map = {
        'recognition': 'daily_r1_recognition',
        'spelling': 'daily_r2_spelling',
        'listening': 'daily_r3_listening',
        'speaking': 'daily_r4_speaking'
    }
    
    if dimension not in table_map:
        conn.close()
        return jsonify({'error': '不支持的维度'}), 400
    
    table_name = table_map[dimension]
    
    # 获取指定组的未掌握单词
    words = conn.execute(f'''
        SELECT lr.*, dp.group_number
        FROM {table_name} lr
        JOIN daily_pool dp ON lr.daily_pool_id = dp.id
        WHERE dp.date = ? AND dp.group_number = ? AND lr.is_mastered = 0
        ORDER BY lr.id
    ''', (today, group)).fetchall()
    
    conn.close()
    
    return jsonify([{
        'id': word['id'],
        'word': word['word'],
        'phonetic': word['phonetic'],
        'translation': word['translation'],
        'example_sentence': word['example_sentence']
    } for word in words])

@app.route('/api/mark_word', methods=['POST'])
def mark_word():
    """标记单词掌握状态"""
    data = request.json
    word_id = data.get('word_id')
    dimension = data.get('dimension')
    mastered = data.get('mastered', False)
    
    if not word_id or not dimension:
        return jsonify({'error': '参数不完整'}), 400
    
    table_map = {
        'recognition': 'daily_r1_recognition',
        'spelling': 'daily_r2_spelling',
        'listening': 'daily_r3_listening',
        'speaking': 'daily_r4_speaking'
    }

    if dimension not in table_map:
        return jsonify({'error': '不支持的维度'}), 400
    
    conn = get_db()
    
    if mastered:
        # 如果掌握了，标记为已掌握状态1（可重置）
        conn.execute(f'UPDATE {table_map[dimension]} SET is_mastered = 1 WHERE id = ?', (word_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/reset_group_progress', methods=['POST'])
def reset_group_progress():
    """重置指定组和维度的学习进度，让已掌握的单词重新可学"""
    data = request.json
    group = data.get('group')
    dimension = data.get('dimension')
    
    if not group or not dimension:
        return jsonify({'error': '参数不完整'}), 400
    
    table_map = {
        'recognition': 'daily_r1_recognition',
        'spelling': 'daily_r2_spelling',
        'listening': 'daily_r3_listening',
        'speaking': 'daily_r4_speaking'
    }
    
    if dimension not in table_map:
        return jsonify({'error': '不支持的维度'}), 400
    
    today = date.today().isoformat()
    conn = get_db()
    
    try:
        # 重置指定组和维度的单词掌握状态，只重置状态1（掌握了），不重置状态2（我会这个）
        table_name = table_map[dimension]
        conn.execute(f'''
            UPDATE {table_name} SET is_mastered = 0
            WHERE daily_pool_id IN (
                SELECT id FROM daily_pool WHERE date = ? AND group_number = ?
            ) AND is_mastered = 1
        ''', (today, group))
        
        affected_rows = conn.cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'已重置第{group}组{dimension}维度的进度，共{affected_rows}个单词可重新学习'
        })
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'重置失败: {str(e)}'}), 500

@app.route('/api/skip_word', methods=['POST'])
def skip_word():
    """跳过单词（我会这个）- 从当前维度表中删除"""
    data = request.json
    word_id = data.get('word_id')
    dimension = data.get('dimension')
    
    if not word_id or not dimension:
        return jsonify({'error': '参数不完整'}), 400
    
    table_map = {
        'recognition': 'daily_r1_recognition',
        'spelling': 'daily_r2_spelling',
        'listening': 'daily_r3_listening',
        'speaking': 'daily_r4_speaking'
    }
    
    if dimension not in table_map:
        return jsonify({'error': '不支持的维度'}), 400
    
    conn = get_db()
    
    # 跳过单词（我会这个）- 标记为已掌握状态2（不可重置）
    conn.execute(f'UPDATE {table_map[dimension]} SET is_mastered = 2 WHERE id = ?', (word_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '已跳过该单词'})

@app.route('/review')
def review_page():
    """复习页面"""
    return render_template('review.html')

@app.route('/api/review_words')
def api_get_review_words():
    """获取今日需要复习的单词"""
    words = get_review_words()
    return jsonify(words)

@app.route('/api/review_word', methods=['POST'])
def review_word():
    """复习单词结果"""
    data = request.json
    review_id = data.get('review_id')
    success = data.get('success', False)
    
    if not review_id:
        return jsonify({'error': '参数不完整'}), 400
    
    result = update_review_schedule(review_id, success)
    
    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'error': '更新复习计划失败'}), 500

@app.route('/history')
def history_page():
    """历史记录页面"""
    return render_template('history.html')

@app.route('/api/history_dates')
def get_history_dates():
    """获取所有有学习记录的日期"""
    conn = get_db()
    
    dates = conn.execute('''
        SELECT DISTINCT date FROM daily_pool 
        ORDER BY date DESC
    ''').fetchall()
    
    conn.close()
    
    return jsonify([{'date': date['date']} for date in dates])

@app.route('/api/history/<date>')
def get_history_by_date(date):
    """获取指定日期的学习历史"""
    conn = get_db()
    
    # 获取该日期的词汇按组分类
    groups_data = {}
    for group_num in [1, 2, 3]:
        # 获取该组的词汇
        words = conn.execute('''
            SELECT mv.word, mv.phonetic, mv.translation, mv.example_sentence
            FROM daily_pool dp
            JOIN master_vocabulary mv ON dp.master_word_id = mv.id
            WHERE dp.date = ? AND dp.group_number = ?
            ORDER BY mv.word
        ''', (date, group_num)).fetchall()
        
        groups_data[f'group_{group_num}'] = [{
            'word': word['word'],
            'phonetic': word['phonetic'],
            'translation': word['translation'],
            'example_sentence': word['example_sentence']
        } for word in words]
    
    # 获取学习进度信息
    progress = conn.execute('''
        SELECT * FROM daily_progress WHERE date = ?
    ''', (date,)).fetchone()
    
    progress_info = None
    if progress:
        progress_info = {
            'current_stage': progress['current_stage'],
            'current_group': progress['current_group'],
            'current_dimension': progress['current_dimension'],
            'completed_stages': json.loads(progress['completed_stages'] or '[]')
        }
    
    conn.close()
    
    return jsonify({
        'date': date,
        'groups': groups_data,
        'progress': progress_info,
        'total_words': sum(len(words) for words in groups_data.values())
    })

@app.route('/word_management')
def word_management_page():
    """单词管理页面"""
    return render_template('word_management.html')

@app.route('/api/search_word', methods=['POST'])
def search_word():
    """搜索单词"""
    data = request.json
    word = data.get('word', '').strip().lower()
    
    if not word:
        return jsonify({'error': '请输入单词'}), 400
    
    conn = get_db()
    
    # 搜索单词（不区分大小写）
    result = conn.execute(
        'SELECT * FROM master_vocabulary WHERE LOWER(word) = ?', (word,)
    ).fetchone()
    
    conn.close()
    
    if result:
        return jsonify({
            'found': True,
            'word': {
                'id': result['id'],
                'word': result['word'],
                'phonetic': result['phonetic'] or '',
                'translation': result['translation'] or '',
                'example_sentence': result['example_sentence'] or '',
                'status': result['status']
            }
        })
    else:
        return jsonify({'found': False})

@app.route('/api/add_word_to_today', methods=['POST'])
def add_word_to_today():
    """将单词添加到今日学习"""
    data = request.json
    word_id = data.get('word_id')
    
    if not word_id:
        return jsonify({'error': '缺少单词ID'}), 400
    
    today = date.today().isoformat()
    conn = get_db()
    
    try:
        # 检查单词是否存在
        word = conn.execute(
            'SELECT * FROM master_vocabulary WHERE id = ?', (word_id,)
        ).fetchone()
        
        if not word:
            conn.close()
            return jsonify({'error': '单词不存在'}), 400
        
        # 检查是否已经在今日学习中
        existing = conn.execute(
            'SELECT COUNT(*) FROM daily_pool dp JOIN master_vocabulary mv ON dp.master_word_id = mv.id WHERE dp.date = ? AND mv.id = ?',
            (today, word_id)
        ).fetchone()[0]
        
        if existing > 0:
            conn.close()
            return jsonify({'error': '该单词已在今日学习列表中'}), 400
        
        # 获取今日已有的组数，确定新单词放在哪一组
        group_counts = conn.execute(
            'SELECT group_number, COUNT(*) as count FROM daily_pool WHERE date = ? GROUP BY group_number ORDER BY group_number',
            (today,)
        ).fetchall()
        
        # 找到单词数最少的组，如果没有组或每组都满20个，创建新组
        target_group = 1
        if group_counts:
            for group_num, count in group_counts:
                if count < 20:
                    target_group = group_num
                    break
            else:
                # 所有组都满了，找到最大组号+1
                target_group = max([g[0] for g in group_counts]) + 1
        
        # 插入到daily_pool
        cursor = conn.execute(
            'INSERT INTO daily_pool (master_word_id, date, group_number) VALUES (?, ?, ?)',
            (word_id, today, target_group)
        )
        daily_pool_id = cursor.lastrowid
        
        # 插入到各个学习维度表
        word_data = (
            daily_pool_id, word['word'], word['phonetic'], 
            word['translation'], word['example_sentence']
        )
        
        learning_tables = ['daily_r1_recognition', 'daily_r2_spelling', 
                         'daily_r3_listening', 'daily_r4_speaking']
        for table in learning_tables:
            conn.execute(f'''
                INSERT INTO {table} 
                (daily_pool_id, word, phonetic, translation, example_sentence)
                VALUES (?, ?, ?, ?, ?)
            ''', word_data)
        
        # 更新master_vocabulary状态为learning
        conn.execute(
            'UPDATE master_vocabulary SET status = ? WHERE id = ?',
            ('learning', word_id)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'单词 "{word["word"]}" 已添加到今日学习（第{target_group}组）'
        })
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'添加失败: {str(e)}'}), 500

@app.route('/api/create_and_add_word', methods=['POST'])
def create_and_add_word():
    """创建新单词并添加到今日学习"""
    data = request.json
    word = data.get('word', '').strip()
    phonetic = data.get('phonetic', '').strip()
    translation = data.get('translation', '').strip()
    example_sentence = data.get('example_sentence', '').strip()
    
    if not word or not translation:
        return jsonify({'error': '单词和翻译为必填项'}), 400
    
    today = date.today().isoformat()
    conn = get_db()
    
    try:
        # 检查单词是否已存在
        existing = conn.execute(
            'SELECT id FROM master_vocabulary WHERE LOWER(word) = ?', (word.lower(),)
        ).fetchone()
        
        if existing:
            conn.close()
            return jsonify({'error': '该单词已存在于词库中'}), 400
        
        # 插入新单词到master_vocabulary
        cursor = conn.execute(
            'INSERT INTO master_vocabulary (word, phonetic, translation, example_sentence, status) VALUES (?, ?, ?, ?, ?)',
            (word, phonetic, translation, example_sentence, 'learning')
        )
        word_id = cursor.lastrowid
        
        # 获取今日已有的组数，确定新单词放在哪一组
        group_counts = conn.execute(
            'SELECT group_number, COUNT(*) as count FROM daily_pool WHERE date = ? GROUP BY group_number ORDER BY group_number',
            (today,)
        ).fetchall()
        
        target_group = 1
        if group_counts:
            for group_num, count in group_counts:
                if count < 20:
                    target_group = group_num
                    break
            else:
                target_group = max([g[0] for g in group_counts]) + 1
        
        # 插入到daily_pool
        cursor = conn.execute(
            'INSERT INTO daily_pool (master_word_id, date, group_number) VALUES (?, ?, ?)',
            (word_id, today, target_group)
        )
        daily_pool_id = cursor.lastrowid
        
        # 插入到各个学习维度表
        word_data = (daily_pool_id, word, phonetic, translation, example_sentence)
        
        learning_tables = ['daily_r1_recognition', 'daily_r2_spelling', 
                         'daily_r3_listening', 'daily_r4_speaking']
        for table in learning_tables:
            conn.execute(f'''
                INSERT INTO {table} 
                (daily_pool_id, word, phonetic, translation, example_sentence)
                VALUES (?, ?, ?, ?, ?)
            ''', word_data)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'新单词 "{word}" 已创建并添加到今日学习（第{target_group}组）'
        })
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'创建失败: {str(e)}'}), 500

@app.route('/api/get_today_words')
def get_today_words():
    """获取今日所有学习单词"""
    today = date.today().isoformat()
    conn = get_db()
    
    words = conn.execute('''
        SELECT dp.id as daily_pool_id, dp.group_number, mv.id as master_id, 
               mv.word, mv.phonetic, mv.translation, mv.example_sentence,
               -- 检查各维度是否还有未掌握的单词
               CASE WHEN EXISTS(SELECT 1 FROM daily_r1_recognition WHERE daily_pool_id = dp.id) THEN 1 ELSE 0 END as has_recognition,
               CASE WHEN EXISTS(SELECT 1 FROM daily_r2_spelling WHERE daily_pool_id = dp.id) THEN 1 ELSE 0 END as has_spelling
        FROM daily_pool dp
        JOIN master_vocabulary mv ON dp.master_word_id = mv.id
        WHERE dp.date = ?
        ORDER BY dp.group_number, mv.word
    ''', (today,)).fetchall()
    
    conn.close()
    
    result = []
    for word in words:
        result.append({
            'daily_pool_id': word['daily_pool_id'],
            'master_id': word['master_id'],
            'word': word['word'],
            'phonetic': word['phonetic'] or '',
            'translation': word['translation'] or '',
            'example_sentence': word['example_sentence'] or '',
            'group_number': word['group_number'],
            'has_recognition': bool(word['has_recognition']),
            'has_spelling': bool(word['has_spelling']),
            'can_remove': word['has_recognition'] or word['has_spelling']  # 只有还有学习记录的才能移除
        })
    
    return jsonify(result)

@app.route('/api/remove_word_from_today', methods=['POST'])
def remove_word_from_today():
    """从今日学习中移除单词"""
    data = request.json
    daily_pool_id = data.get('daily_pool_id')
    
    if not daily_pool_id:
        return jsonify({'error': '缺少daily_pool_id'}), 400
    
    conn = get_db()
    
    try:
        # 获取单词信息
        word_info = conn.execute('''
            SELECT dp.master_word_id, mv.word, mv.status
            FROM daily_pool dp
            JOIN master_vocabulary mv ON dp.master_word_id = mv.id
            WHERE dp.id = ?
        ''', (daily_pool_id,)).fetchone()
        
        if not word_info:
            conn.close()
            return jsonify({'error': '单词不存在'}), 400
        
        master_word_id = word_info['master_word_id']
        word_text = word_info['word']
        
        # 从各个学习维度表中删除记录
        learning_tables = ['daily_r1_recognition', 'daily_r2_spelling', 
                         'daily_r3_listening', 'daily_r4_speaking']
        for table in learning_tables:
            conn.execute(f'DELETE FROM {table} WHERE daily_pool_id = ?', (daily_pool_id,))
        
        # 从daily_pool中删除
        conn.execute('DELETE FROM daily_pool WHERE id = ?', (daily_pool_id,))
        
        # 恢复master_vocabulary的状态为unlearned
        conn.execute(
            'UPDATE master_vocabulary SET status = ? WHERE id = ?',
            ('unlearned', master_word_id)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'单词 "{word_text}" 已从今日学习中移除'
        })
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'移除失败: {str(e)}'}), 500

@app.route('/history/<date>')
def history_detail_page(date):
    """历史记录详情页面"""
    return render_template('history_detail.html', date=date)

if __name__ == '__main__':
    init_db()
    import_vocabulary_from_json()  # 启动时导入词汇
    app.run(debug=True, port=5002)