# 🌟 Claude Vocabulary - 智能化个人单词学习系统

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-2.0+-green.svg" alt="Flask Version">
  <img src="https://img.shields.io/badge/SQLite-3.0+-orange.svg" alt="SQLite">
  <img src="https://img.shields.io/badge/License-MIT-red.svg" alt="License">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg" alt="Status">
</div>

<div align="center">
  <h3>🎯 科学记忆 • 🧠 智能复习 • 📱 现代界面 • 🔊 多维学习</h3>
  <p><em>基于艾宾浩斯遗忘曲线的高效单词学习软件，支持认、写、听、说四维度学习</em></p>
</div>

---

## ✨ 核心特色

### 🎯 **科学学习理念**
- **高强度分组学习**：每日60词分3组，确保深度掌握
- **四维度独立训练**：认（英译汉）、写（汉译英）、听（听音识词）、说（语音评测）
- **一遍过逻辑**：必须连续全对才能通过，杜绝投机取巧
- **智能复习机制**：基于艾宾浩斯遗忘曲线的科学复习

### 🎨 **现代化界面设计**
- **莫兰蒂配色方案**：优雅的渐变色彩，护眼且美观
- **玻璃拟态效果**：毛玻璃质感，层次感丰富
- **流畅动画交互**：入场动画、悬停效果、进度条动画
- **响应式布局**：完美适配桌面和移动设备

### 🧠 **智能化学习体验**
- **自适应难度**：根据掌握情况动态调整
- **机器辅助判断**：拼写检查 + 用户最终确认
- **进度持久化**：随时中断，无缝续学
- **详细学习分析**：完整的学习数据统计

---

## 🚀 快速开始

### 📋 系统要求
- Python 3.8+
- SQLite 3.0+
- 现代浏览器（Chrome、Firefox、Safari、Edge）

### 🛠 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/claude-vocabulary.git
   cd claude-vocabulary
   ```

2. **安装依赖**
   ```bash
   pip install flask
   ```

3. **初始化数据库**
   ```bash
   python reset_database.py
   ```

4. **启动服务**
   ```bash
   python app.py
   ```

5. **打开浏览器**
   ```
   访问：http://127.0.0.1:5002
   ```

---

## 🎮 使用指南

### 🏠 **主界面导航**

<table>
  <tr>
    <td><strong>📚 今日新学习</strong></td>
    <td>开始当日的新词学习，包含3组共60个单词的系统化训练</td>
  </tr>
  <tr>
    <td><strong>🔄 智能复习</strong></td>
    <td>基于艾宾浩斯遗忘曲线的科学复习，确保长期记忆</td>
  </tr>
  <tr>
    <td><strong>📈 学习历程</strong></td>
    <td>查看历史学习记录，追踪学习进度和成果</td>
  </tr>
  <tr>
    <td><strong>⚙️ 单词管理</strong></td>
    <td>搜索单词、手动添加词汇、管理个人词库</td>
  </tr>
  <tr>
    <td><strong>🤖 智能学习</strong></td>
    <td>AI驱动的自适应学习模式（开发中）</td>
  </tr>
</table>

### 📖 **学习流程**

#### 🎯 **分组深度学习**
```
第1组：认→写→认→写→认→写 (3轮强化)
第2组：认→写→认→写→认→写 (3轮强化)
交叉复习：第1组+第2组 各1轮巩固
第3组：认→写→认→写→认→写 (3轮强化)
交叉复习：第2组+第3组 各1轮巩固
```

#### 🏆 **大乱斗模式**
完成分组学习后解锁，60词混合练习，可自定义练习次数。

### 🔄 **四维度学习**

| 维度 | 名称 | 描述 | 特色功能 |
|------|------|------|----------|
| 🔤 | **认（英译汉）** | 看英文写中文 | 音标辅助、例句提示 |
| ✏️ | **写（汉译英）** | 看中文写英文 | 拼写检查、智能提示 |
| 🎧 | **听（听音识词）** | 听发音写单词 | 语音合成、双重输入 |
| 🎤 | **说（语音评测）** | 看中文说英文 | 语音识别、发音评分 |

---

## 🏗 技术架构

### 🔧 **技术栈**
- **后端框架**：Flask (轻量级Python Web框架)
- **数据库**：SQLite (零配置，高性能)
- **前端技术**：HTML5 + CSS3 + Vanilla JavaScript
- **语音技术**：Web Speech API (浏览器原生支持)
- **UI设计**：响应式布局 + 玻璃拟态风格

### 🗄 **数据库设计**

```sql
-- 核心数据表结构
master_vocabulary     -- 总词库（3739个CET4词汇）
daily_pool           -- 每日词池（60词分3组）
daily_r1_recognition -- 认读学习表
daily_r2_spelling    -- 拼写学习表
daily_r3_listening   -- 听力学习表
daily_r4_speaking    -- 口语学习表
learning_records     -- 学习记录表
review_queue         -- 复习队列表
```

### 📊 **核心算法**
- **艾宾浩斯遗忘曲线**：1→2→4→7→15→30→60天间隔复习
- **自适应难度调整**：根据错误率动态调整复习频率
- **智能分组算法**：确保词汇分布的科学性和均衡性

---

## 🎨 界面预览

### 🏠 **主界面**
- 优雅的莫兰蒂配色渐变背景
- 玻璃拟态卡片式布局
- 流畅的悬停和点击动效

### 📚 **学习界面**
- 大字体单词显示，护眼友好
- 进度条实时反馈，动画生动
- 智能提示系统，学习高效

### 📈 **统计界面**
- 可视化学习数据展示
- 详细的进度追踪分析
- 历史记录完整保存

---

## 🔥 核心功能

### 🎯 **学习管理**
- [x] 每日自动词汇分配
- [x] 四维度独立学习进度
- [x] 智能复习队列管理
- [x] 学习进度持久化保存

### 🧠 **智能辅助**
- [x] 拼写错误自动检测
- [x] 发音准确度评估
- [x] 学习建议智能推荐
- [x] 用户自主最终判断

### 📊 **数据分析**
- [x] 学习时间统计
- [x] 掌握程度分析
- [x] 复习效果追踪
- [x] 历史数据回顾

### 🎨 **用户体验**
- [x] 响应式设计适配
- [x] 深色模式支持
- [x] 无障碍访问优化
- [x] 键盘快捷键支持

---

## 📝 开发计划

### ✅ **已完成功能**
- [x] 核心学习系统开发
- [x] 数据库设计与实现
- [x] 用户界面美化优化
- [x] 四维度学习模式
- [x] 智能复习机制
- [x] 学习数据统计

### 🚧 **开发中功能**
- [ ] AI智能学习路径推荐
- [ ] 社交学习功能
- [ ] 学习成就系统
- [ ] 多语言界面支持

### 🔮 **未来计划**
- [ ] 移动端原生应用
- [ ] 云端数据同步
- [ ] 学习社区建设
- [ ] AI语音助手集成

---

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 🐛 **Bug报告**
在GitHub Issues中报告问题，请包含：
- 详细的问题描述
- 复现步骤
- 系统环境信息
- 错误截图（如有）

### 💡 **功能建议**
通过Issues提交新功能建议，请说明：
- 功能需求背景
- 预期效果描述
- 实现思路（可选）

### 🔧 **代码贡献**
1. Fork项目到你的GitHub
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

### 🎯 **许可说明**
- ✅ 商业使用
- ✅ 修改源码
- ✅ 分发传播
- ✅ 私人使用
- ❌ 提供担保
- ❌ 承担责任

---

## 👨‍💻 关于开发者

### 🎓 **项目背景**
这是一个专为高效英语学习而设计的个人项目，结合了认知科学、教育心理学和现代Web技术，致力于为学习者提供科学、高效、美观的单词学习体验。

### 📫 **联系方式**
- **GitHub**: [@your-username](https://github.com/your-username)
- **Email**: your.email@example.com
- **博客**: https://your-blog.com

---

## 🙏 致谢

### 🎨 **设计灵感**
感谢莫兰蒂色彩美学为项目界面设计提供的灵感

### 📚 **学术支持**
感谢艾宾浩斯遗忘曲线理论为复习算法提供的科学依据

### 🛠 **技术支持**
感谢开源社区提供的优秀框架和工具库

---

<div align="center">
  <h3>🌟 如果这个项目对你有帮助，请给个Star！</h3>
  <p><strong>让我们一起打造更好的学习工具！</strong></p>

  [![Star History Chart](https://api.star-history.com/svg?repos=your-username/claude-vocabulary&type=Date)](https://star-history.com/#your-username/claude-vocabulary&Date)
</div>

---

<div align="center">
  <sub>Built with ❤️ by Claude Vocabulary Team</sub>
</div>