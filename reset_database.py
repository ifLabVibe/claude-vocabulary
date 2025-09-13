#!/usr/bin/env python3
"""
数据库重置脚本
清除所有学习记录，保留词汇库数据，为全新开始做准备
"""

import sqlite3
import os
from datetime import datetime

DATABASE = 'vocabulary.db'

def reset_database():
    """重置数据库，清除所有学习记录"""
    
    if not os.path.exists(DATABASE):
        print(f"❌ 数据库文件 {DATABASE} 不存在")
        return False
    
    print("🔄 开始重置数据库...")
    print(f"📅 重置时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # 1. 清除每日词池表
        print("🗑️  清除每日词池数据...")
        cursor.execute('DELETE FROM daily_pool')
        affected_rows = cursor.rowcount
        print(f"   ✅ 删除了 {affected_rows} 条每日词池记录")
        
        # 2. 清除所有学习维度表的数据
        learning_tables = [
            'daily_r1_recognition',
            'daily_r2_spelling', 
            'daily_r3_listening',
            'daily_r4_speaking'
        ]
        
        for table in learning_tables:
            print(f"🗑️  清除 {table} 数据...")
            cursor.execute(f'DELETE FROM {table}')
            affected_rows = cursor.rowcount
            print(f"   ✅ 删除了 {affected_rows} 条记录")
        
        # 3. 清除学习进度表
        print("🗑️  清除学习进度数据...")
        cursor.execute('DELETE FROM daily_progress')
        affected_rows = cursor.rowcount
        print(f"   ✅ 删除了 {affected_rows} 条进度记录")
        
        # 4. 清除学习记录表
        print("🗑️  清除学习记录数据...")
        cursor.execute('DELETE FROM learning_records')
        affected_rows = cursor.rowcount
        print(f"   ✅ 删除了 {affected_rows} 条学习记录")
        
        # 5. 清除复习队列表
        print("🗑️  清除复习队列数据...")
        cursor.execute('DELETE FROM review_queue')
        affected_rows = cursor.rowcount
        print(f"   ✅ 删除了 {affected_rows} 条复习记录")
        
        # 6. 重置master_vocabulary表的状态
        print("🔄 重置词汇状态...")
        cursor.execute("UPDATE master_vocabulary SET status = 'unlearned'")
        affected_rows = cursor.rowcount
        print(f"   ✅ 重置了 {affected_rows} 个单词的状态为 'unlearned'")
        
        # 7. 重置自增ID（可选，让ID从1重新开始）
        print("🔄 重置自增ID...")
        tables_to_reset = [
            'daily_pool', 'daily_r1_recognition', 'daily_r2_spelling',
            'daily_r3_listening', 'daily_r4_speaking', 'daily_progress',
            'learning_records', 'review_queue'
        ]
        
        for table in tables_to_reset:
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
        
        # 提交所有更改
        conn.commit()
        
        # 验证重置结果
        print("\n📊 验证重置结果:")
        
        # 检查词汇总数
        cursor.execute("SELECT COUNT(*) FROM master_vocabulary")
        total_vocab = cursor.fetchone()[0]
        print(f"   📚 词汇库总单词数: {total_vocab}")
        
        # 检查unlearned状态的单词数
        cursor.execute("SELECT COUNT(*) FROM master_vocabulary WHERE status = 'unlearned'")
        unlearned_count = cursor.fetchone()[0]
        print(f"   🆕 未学习单词数: {unlearned_count}")
        
        # 检查所有学习表是否为空
        empty_tables = []
        for table in ['daily_pool', 'daily_progress', 'learning_records', 'review_queue']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count == 0:
                empty_tables.append(table)
            else:
                print(f"   ⚠️  {table} 仍有 {count} 条记录")
        
        if len(empty_tables) == 4:
            print("   ✅ 所有学习记录表已清空")
        
        conn.close()
        
        print(f"\n🎉 数据库重置完成！")
        print("💡 现在您可以重新开始全新的单词学习之旅了！")
        print("🚀 下次运行应用时，系统将自动初始化第一天的60个单词")
        
        return True
        
    except Exception as e:
        print(f"❌ 重置数据库时发生错误: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def backup_database():
    """在重置前创建数据库备份"""
    if os.path.exists(DATABASE):
        backup_name = f"vocabulary_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        try:
            import shutil
            shutil.copy2(DATABASE, backup_name)
            print(f"💾 数据库备份已创建: {backup_name}")
            return backup_name
        except Exception as e:
            print(f"⚠️  备份失败: {e}")
            return None
    return None

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 个人单词学习系统 - 数据库重置工具")
    print("=" * 60)
    
    # 确认操作
    print("\n⚠️  警告: 此操作将清除所有学习记录，但保留词汇库数据")
    print("📝 包括:")
    print("   - 每日学习记录")
    print("   - 学习进度")
    print("   - 复习计划")
    print("   - 所有历史数据")
    print("\n✅ 保留:")
    print("   - 3739个CET4词汇库")
    
    confirm = input("\n❓ 确定要重置吗? (输入 'YES' 确认): ")
    
    if confirm.upper() != 'YES':
        print("❌ 操作已取消")
        return
    
    # 创建备份
    print("\n📦 创建数据库备份...")
    backup_file = backup_database()
    
    # 执行重置
    success = reset_database()
    
    if success:
        print("\n" + "=" * 60)
        print("✨ 重置成功！准备开始新的学习之旅！")
        if backup_file:
            print(f"💾 备份文件: {backup_file}")
        print("=" * 60)
    else:
        print("\n❌ 重置失败，请检查错误信息")

if __name__ == "__main__":
    main()